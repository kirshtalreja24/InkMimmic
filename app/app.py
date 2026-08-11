"""
app.py — Local web app for per-user handwriting fine-tuning + generation.

Guided flow:
  1. Create / select a user
  2. Upload handwriting page photos
  3. Segment pages into lines
  4. Transcribe each line (type what it says)
  5. Reconstruct approximate online strokes
  6. Build training data + fine-tune a per-user model
  7. Generate text in the user's handwriting + download

Run from the repo root:
    streamlit run app/app.py
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import sys
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup: root, diffusion_model/, training/ must all be importable.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
DIFFUSION_DIR = REPO_ROOT / 'diffusion_model'
TRAINING_DIR = REPO_ROOT / 'training'
USERS_DIR = Path(__file__).parent / 'users'

for p in (str(REPO_ROOT), str(DIFFUSION_DIR), str(TRAINING_DIR), str(Path(__file__).parent)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
import tensorflow as tf  # noqa: E402

# Allow GPU memory to grow instead of pre-allocating everything (the app may
# load both a fine-tuning model and a generation model).
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError:
        pass

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import streamlit as st  # noqa: E402

# Project modules
import segment  # noqa: E402
import stroke_reconstruct  # noqa: E402
import build_train_data  # noqa: E402
import finetune  # noqa: E402
import generate_page  # noqa: E402


# ---------------------------------------------------------------------------
# User registry helpers
# ---------------------------------------------------------------------------
def user_dir(name: str) -> Path:
    return USERS_DIR / name


def list_users() -> list[str]:
    if not USERS_DIR.is_dir():
        return []
    return sorted(
        d.name for d in USERS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    )


def ensure_user(name: str):
    for sub in ('photos', 'lines', 'strokes', 'overlays', 'data', 'weights', 'outputs'):
        (user_dir(name) / sub).mkdir(parents=True, exist_ok=True)
    USERS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------
def extract_line_crops(photo_path: str, binary: np.ndarray, start_idx: int, lines) -> int:
    """Crop each detected text line from the binarized page and save inverted
    (ink=dark on white) to users/<name>/lines/lineNN.png. Returns new start_idx."""
    lines_out = user_dir(st.session_state.user) / 'lines'
    overlays_out = user_dir(st.session_state.user) / 'overlays'

    idx = start_idx
    for line_idx, words in enumerate(lines):
        blobs = [b for word in words for b in word]
        if not blobs:
            continue
        xs0 = min(b[0] for b in blobs)
        ys0 = min(b[1] for b in blobs)
        xs1 = max(b[0] + b[2] for b in blobs)
        ys1 = max(b[1] + b[3] for b in blobs)
        pad = 6
        y0 = max(ys0 - pad, 0)
        y1 = min(ys1 + pad, binary.shape[0])
        x0 = max(xs0 - pad, 0)
        x1 = min(xs1 + pad, binary.shape[1])

        crop = binary[y0:y1, x0:x1]
        if crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 8:
            continue
        name = f'line{idx:02d}'
        out_path = lines_out / f'{name}.png'
        cv2.imwrite(str(out_path), 255 - crop)  # ink=dark, bg=white
        idx += 1

    return idx


def reconstruct_user_lines() -> dict:
    """Run stroke reconstruction on every line crop. Returns {line00: status}."""
    u = user_dir(st.session_state.user)
    lines_dir = u / 'lines'
    strokes_dir = u / 'strokes'
    overlays_dir = u / 'overlays'
    lines_dir.mkdir(exist_ok=True)
    strokes_dir.mkdir(exist_ok=True)
    overlays_dir.mkdir(exist_ok=True)

    status = {}
    for img_path in sorted(lines_dir.glob('line*.png')):
        key = img_path.stem
        npy_path = strokes_dir / f'{key}.npy'
        if npy_path.exists():
            status[key] = 'done'
            continue
        try:
            strokes, abs_points, skeleton = stroke_reconstruct.reconstruct_strokes(
                str(img_path), target_points=450, ink_dark=True
            )
            np.save(str(npy_path), strokes)
            overlay = overlays_dir / f'{key}_overlay.png'
            stroke_reconstruct.save_validation_overlay(
                str(img_path), abs_points, skeleton, str(overlay)
            )
            status[key] = 'done'
        except Exception as e:  # noqa: BLE001
            status[key] = f'failed: {e}'
    return status


def build_dataset() -> Path:
    """Assemble train_strokes.p + holdout from transcript.json + strokes."""
    u = user_dir(st.session_state.user)
    transcript_path = u / 'transcript.json'
    if not transcript_path.is_file():
        raise RuntimeError('Transcribe at least one line first.')

    build_train_data.build_user_data(
        user_dir=str(u),
        output_dir=str(u / 'data'),
        holdout_ratio=0.2,
    )
    return u / 'data' / 'train_strokes.p'


# ---------------------------------------------------------------------------
# Threaded runner for long jobs (fine-tune) with live stdout streaming
# ---------------------------------------------------------------------------
def run_with_stream(fn) -> queue.Queue:
    q = queue.Queue()

    def runner():
        old_stdout, old_stderr = sys.stdout, sys.stderr

        class Tee:
            def __init__(self, q):
                self.q = q

            def write(self, s):
                self.q.put(s)
                return len(s)

            def flush(self):
                pass

        sys.stdout = Tee(q)
        sys.stderr = Tee(q)
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            q.put(f'\n[ERROR] {type(e).__name__}: {e}\n')
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            q.put(None)

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    return q


def drain_stdout(q, container, sentinel: list) -> None:
    """Drain queued stdout lines into a Streamlit empty() container."""
    lines = []
    while True:
        try:
            item = q.get_nowait()
        except queue.Empty:
            break
        if item is None:
            sentinel[0] = True
        else:
            lines.append(item)
            container.code(''.join(lines))


# ---------------------------------------------------------------------------
# Generator cache — build a PageGenerator once per (weights path, mtime)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_generator(w_path: str) -> generate_page.PageGenerator:
    return generate_page.PageGenerator(weights_path=w_path)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.set_page_config(page_title='AI Handwriter', layout='wide')

st.title('✍️ AI Handwriter')
st.caption('Fine-tune a handwriting model on your own writing, then generate text in that style.')

# --- Sidebar: user management ---
st.sidebar.header('User')
users = list_users()
if 'user' not in st.session_state:
    st.session_state.user = users[0] if users else None

new_user = st.sidebar.text_input('New user name')
if st.sidebar.button('Create user') and new_user.strip():
    name = new_user.strip().replace(' ', '_')
    ensure_user(name)
    st.session_state.user = name
    st.sidebar.success(f'User "{name}" created')

if users:
    selected = st.sidebar.selectbox(
        'Select user', users, index=users.index(st.session_state.user) if st.session_state.user in users else 0
    )
    st.session_state.user = selected

if not st.session_state.user:
    st.info('Create or select a user on the left to begin.')
    st.stop()

u = user_dir(st.session_state.user)
ensure_user(st.session_state.user)
st.header(f'👤 {st.session_state.user}')

lines_dir = u / 'lines'
strokes_dir = u / 'strokes'
line_names = sorted(p.stem for p in lines_dir.glob('line*.png')) if lines_dir.is_dir() else []
done_lines = [p.stem for p in strokes_dir.glob('line*.npy')] if strokes_dir.is_dir() else []
transcript = {}
if (u / 'transcript.json').is_file():
    with open(u / 'transcript.json', 'r', encoding='utf-8') as f:
        transcript = json.load(f)

# ---------------------------------------------------------------------------
# Step 1: Upload
# ---------------------------------------------------------------------------
with st.expander('1️⃣ Upload handwriting pages', expanded=not line_names):
    uploaded = st.file_uploader(
        'Upload page photos (JPEG/PNG) of the user\'s handwriting',
        type=['jpg', 'jpeg', 'png'], accept_multiple_files=True,
    )
    if uploaded:
        for f in uploaded:
            dest = u / 'photos' / f.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(f.getvalue())
        st.success(f'Saved {len(uploaded)} photo(s)')

# ---------------------------------------------------------------------------
# Step 2: Segment
# ---------------------------------------------------------------------------
with st.expander('2️⃣ Segment pages into lines', expanded=not line_names):
    photos = sorted((u / 'photos').glob('*.*')) if (u / 'photos').is_dir() else []
    if not photos:
        st.caption('No photos yet.')
    else:
        if st.button('Run segmentation', type='primary'):
            start_idx = len(line_names)
            progress = st.progress(0.0)
            for i, photo in enumerate(photos):
                try:
                    binary = segment.preprocess(str(photo))
                    blobs = segment.find_blobs(binary)
                    lines = segment.group_into_lines(blobs)
                    start_idx = extract_line_crops(str(photo), binary, start_idx, lines)
                    st.write(f'  {photo.name}: {len(lines)} lines')
                except Exception as e:  # noqa: BLE001
                    st.warning(f'  {photo.name} failed: {e}')
                progress.progress((i + 1) / len(photos))
            st.success('Segmentation done.')

    if line_names:
        st.caption(f'Detected {len(line_names)} line(s):')
        cols = st.columns(4)
        for i, name in enumerate(line_names):
            with cols[i % 4]:
                st.image(str(lines_dir / f'{name}.png'), caption=name, use_container_width=True)

# ---------------------------------------------------------------------------
# Step 3: Transcribe
# ---------------------------------------------------------------------------
with st.expander('3️⃣ Transcribe each line', expanded=bool(line_names)):
    if not line_names:
        st.caption('Segment first.')
    else:
        st.caption('Type what each line says. Lines left blank are skipped.')
        new_transcript = {}
        cols = st.columns(2)
        for i, name in enumerate(line_names):
            with cols[i % 2]:
                st.image(str(lines_dir / f'{name}.png'), caption=name, width=320)
                val = transcript.get(name, '')
                new_transcript[name] = st.text_input(
                    f'Line text ({name})', value=val, key=f'transcript_{name}',
                    label_visibility='collapsed',
                )
        if st.button('Save transcriptions', type='primary'):
            with open(u / 'transcript.json', 'w', encoding='utf-8') as f:
                json.dump(new_transcript, f, indent=2)
            done = sum(1 for v in new_transcript.values() if v.strip())
            st.success(f'Saved. {done}/{len(line_names)} lines transcribed.')

# ---------------------------------------------------------------------------
# Step 4: Reconstruct strokes
# ---------------------------------------------------------------------------
with st.expander('4️⃣ Reconstruct strokes from lines', expanded=False):
    if not line_names:
        st.caption('Segment first.')
    else:
        if st.button('Reconstruct strokes', type='primary'):
            with st.spinner('Reconstructing strokes…'):
                status = reconstruct_user_lines()
            n_done = sum(1 for v in status.values() if v == 'done')
            n_fail = sum(1 for v in status.values() if v != 'done')
            st.success(f'Reconstructed {n_done}/{len(status)} lines' +
                       (f' ({n_fail} failed)' if n_fail else ''))

        overlays = sorted((u / 'overlays').glob('*_overlay.png')) if (u / 'overlays').is_dir() else []
        if overlays:
            st.caption('Check that reconstructed strokes match the original writing:')
            cols = st.columns(2)
            for i, ov in enumerate(overlays):
                with cols[i % 2]:
                    st.image(str(ov), caption=ov.stem.replace('_overlay', ''), use_container_width=True)

# ---------------------------------------------------------------------------
# Step 5: Build dataset + fine-tune
# ---------------------------------------------------------------------------
with st.expander('5️⃣ Build dataset & fine-tune model', expanded=False):
    st.caption('Requires: segmented lines + transcriptions + reconstructed strokes.')
    col1, col2, col3 = st.columns(3)
    steps = col1.number_input('Training steps', min_value=500, value=5000, step=500)
    lr = col2.number_input('Learning rate', min_value=1e-6, value=1e-4, format='%.1e', step=5e-5)
    batch = col3.number_input('Batch size', min_value=8, value=32, step=8)

    base_weights = DIFFUSION_DIR / 'weights' / 'model_weights.h5'
    if not base_weights.is_file():
        st.error(f'Base weights missing: {base_weights}')
    else:
        if st.button('Build dataset + fine-tune', type='primary'):
            try:
                with st.spinner('Building training data…'):
                    train_pickle = build_dataset()
                st.write(f'Train data: {train_pickle}')
            except Exception as e:  # noqa: BLE001
                st.error(f'Dataset build failed: {e}')
                st.stop()

            out_dir = u / 'weights'
            out_dir.mkdir(exist_ok=True)
            code_placeholder = st.empty()
            sentinel = [False]

            # IMPORTANT: read session_state on the MAIN thread and capture it
            # in a plain variable before the background thread starts.
            # st.session_state is not reliably accessible from inside a
            # background thread -- reading it there was the cause of the
            # AttributeError, which was then silently swallowed below,
            # while the app still reported "success" regardless.
            current_user = st.session_state.user

            q = run_with_stream(
                lambda: finetune.finetune(
                    data_path=str(train_pickle),
                    base_weights=str(base_weights),
                    user_name=current_user,
                    steps=int(steps),
                    batch_size=int(batch),
                    lr=float(lr),
                    output_dir=str(out_dir),
                )
            )
            # Stream output until done, and track whether an error was logged
            error_seen = [False]
            while not sentinel[0]:
                time.sleep(0.2)
                drain_stdout(q, code_placeholder, sentinel)
            drain_stdout(q, code_placeholder, sentinel)

            expected_weights = out_dir / f'model_{current_user}.h5'
            if expected_weights.is_file():
                st.success(f'Fine-tuning complete. Weights → {expected_weights}')
            else:
                st.error(
                    f'Fine-tuning did not produce a weights file at {expected_weights}. '
                    'Check the log above for an [ERROR] line -- that is the real failure reason.'
                )

        finetuned = (u / 'weights' / f'model_{st.session_state.user}.h5')
        if finetuned.is_file():
            st.info(f'Fine-tuned weights exist: {finetuned}')

# ---------------------------------------------------------------------------
# Step 6: Generate
# ---------------------------------------------------------------------------
with st.expander('6️⃣ Generate handwriting', expanded=False):
    st.caption('Type text to render in this user\'s handwriting.')

    # Choose a style reference line
    style_choices = line_names if line_names else []
    default_style = style_choices[0] if style_choices else None
    style_name = st.selectbox(
        'Style reference line', style_choices,
        index=0 if style_choices else None,
        format_func=lambda n: n,
    )

    text = st.text_area('Text to generate', height=150)
    paper = st.selectbox('Paper style', ['white', 'ruled', 'graph'])
    tries = st.slider('Generation attempts (keeps best)', 1, 5, 3)

    weights_candidates = []
    finetuned_w = u / 'weights' / f'model_{st.session_state.user}.h5'
    if finetuned_w.is_file():
        weights_candidates.append(('Fine-tuned (this user)', str(finetuned_w)))
    weights_candidates.append(('IAM base (pretrained)', str(base_weights)))

    weights_choice = st.radio('Model weights', weights_candidates, index=0)

    if st.button('Generate page', type='primary'):
        if not text.strip():
            st.warning('Enter some text first.')
            st.stop()
        if not style_name or not (lines_dir / f'{style_name}.png').is_file():
            st.warning('No valid style reference line. Segment a page first.')
            st.stop()

        gate = generate_page._load_classifier()
        gen = load_generator(weights_choice[1])
        out_dir = u / 'outputs'
        out_dir.mkdir(exist_ok=True)

        with st.spinner(f'Generating ({tries} attempt(s))… this can take a minute or two per attempt.'):
            page_path = gen.generate_page(
                text,
                str(lines_dir / f'{style_name}.png'),
                str(out_dir),
                n_tries=tries,
                paper=paper,
                gate=gate,
            )
        st.image(page_path, caption='Generated page', use_container_width=True)

        with open(page_path, 'rb') as f:
            st.download_button(
                'Download page PNG',
                f.read(),
                file_name=f'{st.session_state.user}_handwriting.png',
                mime='image/png',
            )