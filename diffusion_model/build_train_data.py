"""

build_train_data.py — Build per-user training pickles for the diffusion model.

Assembles reconstructed strokes + typed transcriptions + line images into the
exact pickle format that diffusion_model/utils.py::preprocess_data() expects:

    list of (strokes [N,3] float32, text [L] int32, sample [96,W,1] uint8)

Usage:
    python build_train_data.py --user alizeh --user_dir ../app/users/alizeh \\
        --holdout_ratio 0.2 --output_dir ./data
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from pathlib import Path

import cv2
import numpy as np

THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(THIS_DIR))

from utils import Tokenizer  # noqa: E402


# ---------------------------------------------------------------------------
# Image loading — matches diffusion_model/preprocessing.py::read_img
# ---------------------------------------------------------------------------
def _remove_whitespace(img: np.ndarray, thresh: int = 127) -> np.ndarray:
    """Remove blank rows/cols (pixel > thresh is considered blank)."""
    row_mins = np.amin(img, axis=1)
    col_mins = np.amin(img, axis=0)
    rows = np.where(row_mins < thresh)[0]
    cols = np.where(col_mins < thresh)[0]
    if len(rows) == 0 or len(cols) == 0:
        return img
    return img[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]


def read_line_image(path: str, height: int = 96) -> np.ndarray:
    """Load a line image and resize to target height, keeping aspect ratio.

    Returns [height, W, 1] uint8 — ink-dark on white background.
    """
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Cannot read line image: {path}")
    img = img[:, :, np.newaxis] if img.ndim == 2 else img

    # Remove purely white rows/cols
    img_squeezed = img.squeeze(-1) if img.ndim == 3 else img
    img_squeezed = _remove_whitespace(img_squeezed)

    h, w = img_squeezed.shape[:2]
    new_w = max(1, int(height * w / h))
    resized = cv2.resize(img_squeezed, (new_w, height), interpolation=cv2.INTER_AREA)

    if resized.ndim == 2:
        resized = resized[:, :, np.newaxis]

    return resized.astype(np.uint8)


def _pad_img(img: np.ndarray, width: int, height: int) -> np.ndarray:
    """Pad an image to (height, width, 1) with white (255)."""
    if img.shape[1] >= width:
        return img[:, :width, :]
    pad_len = width - img.shape[1]
    padding = np.full((height, pad_len, 1), 255, dtype=np.uint8)
    return np.concatenate((img, padding), axis=1)


# ---------------------------------------------------------------------------
# Tokenization validation
# ---------------------------------------------------------------------------
def validate_transcription(text: str, tokenizer: Tokenizer) -> tuple[str, list[str]]:
    """Check every char in text against the tokenizer's vocab.

    Returns (cleaned_text, list_of_unsupported_chars).
    Unsupported chars are replaced with '_' (token 2).
    """
    valid_chars = set(tokenizer.text)
    unsupported = []
    cleaned = []
    for ch in text:
        if ch in valid_chars:
            cleaned.append(ch)
        else:
            unsupported.append(ch)
            cleaned.append('_')
    return ''.join(cleaned), unsupported


# ---------------------------------------------------------------------------
# Per-user data directory layout
# ---------------------------------------------------------------------------
# app/users/<name>/
#   lines/          — line crop PNGs (line00.png, line01.png, ...)
#   strokes/        — per-line .npy stroke files (line00.npy, ...)
#   transcript.txt  — one transcription per line, in order
#   train_strokes.p — the output pickle
#   holdout_strokes.p — the holdout pickle (for quality gating)

def load_user_data(user_dir: str) -> list[dict]:
    """Load all transcribed lines from a user directory.

    Supports two transcript formats:
      - transcript.txt  — one transcription per line, in line order (blank lines skipped)
      - transcript.json — { "line00": "text", ... } (the web app's format)

    Lines with an empty transcription (or a missing line image / stroke file)
    are skipped, so a partially-transcribed page works fine.

    Returns list of {'line_num': int, 'image_path': str, 'strokes_path': str,
                      'transcription': str}.
    """
    user_dir = Path(user_dir)
    lines_dir = user_dir / 'lines'
    strokes_dir = user_dir / 'strokes'

    if not lines_dir.is_dir():
        raise FileNotFoundError(f"No lines/ directory in {user_dir}")
    if not strokes_dir.is_dir():
        raise FileNotFoundError(f"No strokes/ directory in {user_dir}")

    # --- Read transcriptions (txt or json) ---
    transcript_txt = user_dir / 'transcript.txt'
    transcript_json = user_dir / 'transcript.json'
    if transcript_json.is_file():
        import json
        with open(transcript_json, 'r', encoding='utf-8') as f:
            by_key = json.load(f)
        # Normalize keys "line00" -> index 0
        trans_by_idx = {}
        for k, v in by_key.items():
            try:
                idx = int(k.replace('line', ''))
            except (ValueError, AttributeError):
                idx = len(trans_by_idx)
            trans_by_idx[idx] = (v or '').strip()
        max_idx = max(trans_by_idx) if trans_by_idx else -1
        transcriptions = [trans_by_idx.get(i, '') for i in range(max_idx + 1)]
    elif transcript_txt.is_file():
        with open(transcript_txt, 'r', encoding='utf-8') as f:
            transcriptions = [line.rstrip('\n') for line in f.readlines()]
    else:
        raise FileNotFoundError(f"No transcript.txt or transcript.json in {user_dir}")

    # --- Pair non-empty transcriptions with their line image + strokes ---
    data = []
    for i, text in enumerate(transcriptions):
        text = text.strip()
        if not text:
            continue
        img_path = lines_dir / f'line{i:02d}.png'
        strokes_path = strokes_dir / f'line{i:02d}.npy'
        if not img_path.is_file():
            print(f"  Line {i:02d}: transcribed but no line image, skipping")
            continue
        if not strokes_path.is_file():
            print(f"  Line {i:02d}: transcribed but no strokes file, skipping")
            continue
        data.append({
            'line_num': i,
            'image_path': str(img_path),
            'strokes_path': str(strokes_path),
            'transcription': text,
        })

    return data


# ---------------------------------------------------------------------------
# Build the pickle
# ---------------------------------------------------------------------------
def build_pickle(
    user_data: list[dict],
    tokenizer: Tokenizer,
    max_text_len: int = 50,
    max_seq_len: int = 480,
    img_width: int = 1400,
    img_height: int = 96,
) -> list[tuple]:
    """Build training triples in the exact format preprocess_data() expects.

    Each triple: (strokes [N,3] float32, text [L] int32, sample [96,W,1] uint8)
    """
    dataset = []
    skipped = 0

    for entry in user_data:
        # Load strokes
        strokes = np.load(entry['strokes_path']).astype(np.float32)

        # Validate and tokenize text
        text_clean, unsupported = validate_transcription(entry['transcription'], tokenizer)
        if unsupported:
            print(f"  Line {entry['line_num']}: replaced unsupported chars: {unsupported}")

        tokens = tokenizer.encode(text_clean)  # includes end token

        if len(tokens) >= max_text_len:
            print(f"  Line {entry['line_num']}: text too long ({len(tokens)} tokens), truncating to {max_text_len - 1}")
            tokens = tokens[:max_text_len - 1] + [1]  # re-add end token

        # Pad strokes — replicate utils.pad_stroke_seq logic
        if len(strokes) > max_seq_len:
            print(f"  Line {entry['line_num']}: too many stroke points ({len(strokes)}), truncating")
            strokes = strokes[:max_seq_len]

        if np.amax(np.abs(strokes[:, :2])) > 15:
            print(f"  Line {entry['line_num']}: stroke values too large (max={np.amax(np.abs(strokes[:, :2])):.1f}), skipping")
            skipped += 1
            continue

        # Pad strokes to max_seq_len
        if len(strokes) < max_seq_len:
            pad_len = max_seq_len - len(strokes)
            zeros = np.zeros((pad_len, 2), dtype=np.float32)
            ones = np.ones((pad_len, 1), dtype=np.float32)
            padding = np.concatenate((zeros, ones), axis=-1)
            strokes = np.concatenate((strokes, padding), axis=0).astype(np.float32)

        # Pad tokens to max_text_len
        tokens_arr = np.array(tokens, dtype=np.int32)
        if len(tokens_arr) < max_text_len:
            tokens_arr = np.concatenate([
                tokens_arr,
                np.zeros(max_text_len - len(tokens_arr), dtype=np.int32)
            ])

        # Load and prepare line image
        sample = read_line_image(entry['image_path'], height=img_height)
        if sample.shape[1] >= img_width:
            sample = sample[:, :img_width, :]
        else:
            sample = _pad_img(sample, img_width, img_height)

        dataset.append((strokes, tokens_arr, sample))

    if skipped:
        print(f"  Skipped {skipped} lines (stroke values out of range)")

    return dataset


def build_user_data(
    user_dir: str,
    output_dir: str,
    holdout_ratio: float = 0.2,
    max_text_len: int = 50,
    max_seq_len: int = 480,
    img_width: int = 1400,
    img_height: int = 96,
):
    """End-to-end: load user data → build pickle → save train + holdout splits."""
    tokenizer = Tokenizer()
    user_data = load_user_data(user_dir)
    print(f"Loaded {len(user_data)} lines for user at {user_dir}")

    # Split into train / holdout
    n_holdout = max(1, int(len(user_data) * holdout_ratio))
    np.random.seed(42)
    indices = np.random.permutation(len(user_data))
    holdout_indices = set(indices[:n_holdout])
    train_data = [user_data[i] for i in range(len(user_data)) if i not in holdout_indices]
    holdout_data = [user_data[i] for i in holdout_indices]

    print(f"  Train: {len(train_data)} lines, Holdout: {len(holdout_data)} lines")

    # Build pickles
    train_triples = build_pickle(train_data, tokenizer, max_text_len, max_seq_len, img_width, img_height)
    holdout_triples = build_pickle(holdout_data, tokenizer, max_text_len, max_seq_len, img_width, img_height)

    os.makedirs(output_dir, exist_ok=True)

    train_path = os.path.join(output_dir, 'train_strokes.p')
    with open(train_path, 'wb') as f:
        pickle.dump(train_triples, f)
    print(f"  Saved {len(train_triples)} training triples → {train_path}")

    holdout_path = os.path.join(output_dir, 'holdout_strokes.p')
    with open(holdout_path, 'wb') as f:
        pickle.dump(holdout_triples, f)
    print(f"  Saved {len(holdout_triples)} holdout triples → {holdout_path}")

    # Save a metadata file
    meta = {
        'user_dir': str(user_dir),
        'n_train': len(train_triples),
        'n_holdout': len(holdout_triples),
        'max_text_len': max_text_len,
        'max_seq_len': max_seq_len,
        'img_width': img_width,
        'img_height': img_height,
        'vocab_size': tokenizer.vocab_size,
    }
    meta_path = os.path.join(output_dir, 'data_meta.json')
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
    print(f"  Metadata → {meta_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Build training data pickle for per-user fine-tuning.')
    parser.add_argument('--user_dir', required=True, help='Path to app/users/<name>/ directory')
    parser.add_argument('--output_dir', default='./data', help='Where to save train_strokes.p and holdout_strokes.p')
    parser.add_argument('--holdout_ratio', type=float, default=0.2, help='Fraction of lines held out for quality gating')
    parser.add_argument('--max_text_len', type=int, default=50)
    parser.add_argument('--max_seq_len', type=int, default=480)
    parser.add_argument('--img_width', type=int, default=1400)
    parser.add_argument('--img_height', type=int, default=96)
    args = parser.parse_args()

    build_user_data(
        args.user_dir, args.output_dir, args.holdout_ratio,
        args.max_text_len, args.max_seq_len, args.img_width, args.img_height,
    )


if __name__ == '__main__':
    main()
