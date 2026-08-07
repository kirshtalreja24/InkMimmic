# diffusion_model/ — Integration Guide

This document explains what `diffusion_model/` is, how it connects to the rest
of `ai_handwriter`, and every command you need to run it. Written so you (or
anyone else opening this project later) can understand it without having to
reconstruct the reasoning from scratch.

---

## 1. What problem this solves

Your original `ai_handwriter` project (`segment.py` + `training/classifier.py`)
segments a scanned page into individual character images and classifies them
(91.7% accuracy). That's a **recognition** system — given an image, it tells
you what letter it is.

`diffusion_model/` adds the opposite direction: **generation** — given typed
text, produce a new image of handwriting in a particular style. It's a
pretrained diffusion model (from the public repo
[tcl9876/Diffusion-Handwriting-Generation](https://github.com/tcl9876/Diffusion-Handwriting-Generation),
based on the paper *"Diffusion Models for Handwriting Generation"*) that takes
two inputs — a string of text, and one reference image of handwriting — and
generates a stroke-by-stroke rendering of that text in a style resembling the
reference image.

Important nuance: this is **style transfer**, not a model trained on your
specific handwriting. It was pretrained on the IAM handwriting dataset (many
different writers) and uses a lightweight image feature extractor
(MobileNetV2) to pick up on general visual characteristics — slant, letter
width, spacing — from whatever reference image you give it, at generation
time, with no training step involved. Real fine-tuning on your own
handwriting specifically would require raw pen-stroke coordinate data (x, y
over time), which this project doesn't currently collect (your data is
photos, not stroke sequences) — see Section 6 for more on this limitation.

---

## 2. How the pieces connect

```
                    ai_handwriter/                          diffusion_model/
                    ───────────────                         ─────────────────
  scanned page  ──▶  segment.py                              nn.py
   (your photo)      (cuts into lines +                       (StyleExtractor: image→style vector)
                       character crops)                       (DiffusionWriter: text+style→strokes)
                          │
                          ▼
                    training/classifier.py            ┌──▶  utils.py
                    (scores each line's                │     (tokenizer, diffusion sampling loop,
                     legibility, 0.0–1.0)               │      stroke rendering)
                          │                             │
                          ▼                             │
              [highest-confidence line auto-picked] ────┤
                                                          │
                                                          ▼
                                              generate_handwriting.py  ◀── glue code (this file)
                                                          │
                                                          ▼
                                                 generated handwriting image
```

`generate_handwriting.py` is the only new file that talks to both sides. It:
1. Calls your existing `segment.py` to cut a scanned page into lines
2. Calls your existing `classifier.py`'s `SmallCNN` to score each line's clarity
3. Auto-picks the clearest line as the style reference (no manual cropping)
4. Feeds that line + your typed text into the diffusion model
5. Saves the generated image

**Nothing in `ai_handwriter`'s existing files was changed.** `generate_handwriting.py`
only *imports and calls* `segment.py` and `classifier.py` — it doesn't modify them.

---

## 3. The two real bugs this integration had to work around

These aren't things you did wrong — they're genuine incompatibilities between
the two codebases that had to be patched. Documented here so future-you (or
anyone else) isn't confused if they diff the code later.

### Bug 1 — MobileNetV2 fixed input shape (`nn.py`)
The diffusion repo's `StyleExtractor` originally builds MobileNetV2 with a
hardcoded `input_shape=(96, 96, 3)`. But style reference images are wide
rectangular line crops, not squares — so this literally cannot accept them in
modern Keras (older TF/Keras versions were looser about this; current Keras
enforces it strictly). **Fix applied to `diffusion_model/nn.py`:** changed to
`input_shape=None`, which lets it accept any width. Verified this doesn't
break anything — MobileNetV2 is fully convolutional, so a flexible input
shape produces a variable-length feature sequence, which is exactly what the
diffusion model's cross-attention expects.

### Bug 2 — Duplicate module name: `preprocessing.py`
Both `ai_handwriter/` (your segmentation preprocessing: grayscale, Sauvola
threshold, deskew) and `diffusion_model/` (the diffusion repo's image
loading for style extraction: `read_img()`) have a file literally named
`preprocessing.py` — same name, unrelated code. Python only keeps one module
cached under a given name per process, so whichever one imports first would
silently "win" and break the other. **Fix:** `generate_handwriting.py` loads
the diffusion repo's copy under a private alias
(`diffusion_preprocessing`, via `importlib`) instead of a plain `import
preprocessing`, so your `segment.py`'s own `import preprocessing` is left
free to resolve to *your* file, undisturbed.

---

## 4. Setup (one-time)

```bash
cd ai_handwriter
source venv/bin/activate            # your existing venv, reused as-is
pip install tensorflow matplotlib pillow h5py    # the only new dependencies
```
No new venv needed — see the note in Section 6 on why one shared environment
is actually required here, not just convenient.

`diffusion_model/nn.py` already has the MobileNetV2 patch applied (Section 3,
Bug 1) — nothing further needed unless you re-clone the original repo fresh.

---

## 5. Commands

All run from inside `diffusion_model/`, with your venv active.

### Generate a single line of text
```bash
python generate_handwriting.py \
    --page /path/to/scanned_page.jpg \
    --text "hello world" \
    --out result
```
Produces `result.png` in the current directory.

### Generate a paragraph
```bash
python generate_handwriting.py \
    --page /path/to/scanned_page.jpg \
    --text "This is a longer piece of text that will be automatically split into multiple wrapped lines and stitched together." \
    --out paragraph_result_dir \
    --paragraph
```
`--out` becomes a **directory** in this mode (not a filename) — it'll contain
each generated line (`para_line_00.png`, `para_line_01.png`, ...) plus the
final stitched image, `paragraph_output.png`.

Why paragraphs need special handling: the model was trained with a max text
length of 50 characters and max stroke-sequence length of 480 points
(one sentence, roughly) — see `train.py`'s `--textlen`/`--seqlen` defaults in
the original repo. It also has no concept of line breaks; raw long text would
render as one continuous, ever-thinner strip rather than a wrapped block.
`--paragraph` mode works around both: it word-wraps your text into ~45-char
chunks, generates each as its own line (reusing one style vector so they all
match), then stitches them vertically.

### Other useful flags
| Flag | Purpose | Default |
|---|---|---|
| `--mode` | segmentation mode: `auto`, `prose` (continuous sentences), `isolated` (specimen sheets, one glyph per box) | `auto` |
| `--checkpoint` | path to your classifier checkpoint | `training/classifier_final2.pt` |
| `--weights` | path to the diffusion model's pretrained weights | `./weights/model_weights.h5` |
| `--work_dir` | where segmented crops + candidate line images get saved | `./_line_candidates` |

### Inspecting what got picked as the style reference
Every run prints each candidate line's confidence score and which one won:
```
  line01_style_ref.png: avg confidence 0.572
Selected './_line_candidates/line01_style_ref.png' (confidence 0.572) out of 1 lines.
```
Open that file directly if you want to see exactly which handwriting sample
is shaping the output, or if a generation looks off and you want to check
whether a bad line got auto-selected.

---

## 6. Known limitations (read before troubleshooting further)

- **Style match is approximate, not exact.** There's no "strength" knob — the
  diffusion model was never trained to precisely replicate a specific
  person's handwriting, just to condition loosely on visual style. Clean,
  well-lit, single-line reference images help; there's a hard ceiling beyond
  that without real fine-tuning.
- **Real fine-tuning needs stroke data, not photos.** The model predicts
  sequential pen movement (dx, dy, pen-lift), not pixels. Training on your
  own handwriting specifically would require capturing that — e.g. a
  stylus/tablet app that logs x/y coordinates over time — which nothing in
  this project currently does.
- **Generation is stochastic.** Every run starts from random noise, so the
  same text + same style reference gives a different result each time. Run
  it a few times and pick the best if one output looks weak.
- **Long lines can drift off the horizontal.** Because strokes are a
  cumulative sum of small predicted offsets, small per-step bias in the
  model can cause a visible slant over a long line. A short post-processing
  fix (linear detrend) can straighten this — ask if you want it added back
  into this script as a `--straighten` flag.
- **One shared Python environment is required, not optional.**
  `generate_handwriting.py` imports from `segment.py`/`classifier.py`
  (PyTorch) and `nn.py`/`utils.py` (TensorFlow) *in the same running
  process* — Python can't reach across two separate venvs within one
  process, so both libraries genuinely have to live together in one
  environment.

---

## 7. File reference

| File | Lives in | Role |
|---|---|---|
| `segment.py` | `ai_handwriter/` | Cuts scanned pages into lines + character crops (yours, untouched) |
| `training/classifier.py` | `ai_handwriter/training/` | `SmallCNN`, trained checkpoint, scores character/line confidence (yours, untouched) |
| `training/dataset.py` | `ai_handwriter/training/` | Image loading/normalization helpers used by the classifier (yours, untouched) |
| `nn.py` | `diffusion_model/` | `StyleExtractor` (image→style vector) and `DiffusionWriter` (the generation model) — patched per Section 3, Bug 1 |
| `utils.py` | `diffusion_model/` | Tokenizer, diffusion sampling loop, stroke-to-image rendering |
| `preprocessing.py` | `diffusion_model/` | `read_img()` — loads/normalizes the style reference image |
| `weights/model_weights.h5` | `diffusion_model/` | Pretrained weights (IAM dataset), ~40MB |
| `generate_handwriting.py` | `diffusion_model/` | **New.** Glue code connecting all of the above |

---

## 8. Per-user fine-tuning (NEW)

Section 6 said real fine-tuning needs stroke data the project didn't collect.
That's no longer true — the pipeline below reconstructs approximate online
strokes from the offline page photos already in `data/`, fine-tunes the
decoder per writer, and renders full pages. The local web app in `app/`
orchestrates the whole flow; this section documents the CLI pieces and the
exact data formats.

### 8.1 Environment change

Earlier, this guide recommended installing TensorFlow into the existing
PyTorch venv. That's still the rule — the app and `generate_handwriting.py`
import PyTorch (`segment.py`, `classifier.py`) and TensorFlow (`nn.py`,
`utils.py`) in the **same process**. Use `requirements-app.txt` (TF >= 2.16 /
Keras 3, numpy<2) rather than the repo's old `tensorflow==2.3.0` pin, which
won't install on Python 3.12. `utils.py` has been patched for Keras 3:
`tf.data.experimental.AUTOTUNE` → `tf.data.AUTOTUNE`.

### 8.2 Step A — Reconstruct strokes from photos

`diffusion_model/stroke_reconstruct.py` converts a binarized line crop
(ink-dark on white) into an approximate online stroke sequence:

```
skeletonize → pixel graph → chains between junctions/endpoints
→ left→right ordering with pen-up between chains
→ arc-length resample to ≤ 480 points (the model's MAX_SEQ_LEN)
→ normalize exactly like preprocessing.parse_stroke_xml()
```

Output per line is a `(N, 3) float32` array of `(dx, dy, pen_up)` — the same
format the IAM data used, so nothing else in the training path changes.

```bash
python diffusion_model/stroke_reconstruct.py --input line01.png --output_dir out/strokes
```

`--page` mode segments a full page via `segment.py` first. Every run writes a
validation overlay (original | skeleton | reconstructed) so you can eyeball
fidelity before training on a line.

### 8.3 Step B — Build training data

`diffusion_model/build_train_data.py` assembles the pickle that
`utils.preprocess_data()` reads. Per user:

```
app/users/<name>/
  lines/           line crops (line00.png, …)
  strokes/         lineNN.npy reconstructed strokes
  transcript.json  { "line00": "text", … }   ← typed once per line
```

```bash
python diffusion_model/build_train_data.py \
    --user_dir app/users/<name> --output_dir app/users/<name>/data
```

Writes `train_strokes.p` (80%) and `holdout_strokes.p` (20%). Lines with an
empty transcription or missing stroke file are skipped. Characters outside
the 73-token vocab are replaced with `_` and reported.

### 8.4 Step C — Fine-tune the decoder

`diffusion_model/finetune.py` loads the IAM-pretrained weights, then trains
the decoder only (the `StyleExtractor` is frozen and, being precomputed in
`create_dataset`, is never in the training graph):

```bash
python diffusion_model/finetune.py --user_data app/users/<name>/data/train_strokes.p \
    --user <name> --steps 5000 --batchsize 32 --lr 1e-4
```

Settings that matter: peak LR 1e-4..1e-5 (high LR → catastrophic forgetting of
the IAM prior), short runs (5–15k steps), dropout 0.1. Batch size is clamped to
the dataset size so a small per-user set never trains on zero batches. Output:
`weights/model_<name>.h5` — the base `model_weights.h5` is never overwritten.

### 8.5 Step D — Generate a page

`diffusion_model/renderer.py` replaces the matplotlib output with an
anti-aliased PIL renderer (variable stroke width from pen velocity, ink color,
white/ruled/graph paper). `diffusion_model/generate_page.py` wraps generation:
per-user weights + the user's own style line, word-wrap to ≤45 chars/line,
best-of-N stochastic retries, and an optional legibility gate that scores each
attempt by reading it back with the trained `SmallCNN`.

```bash
python diffusion_model/generate_page.py --text "Assignment text…" \
    --weights diffusion_model/weights/model_<name>.h5 \
    --style app/users/<name>/lines/line00.png --out out --tries 3
```

### 8.6 Quality expectations

Reconstruction from photos is an approximation: pen order and timing are lost,
and loops/crossings are ambiguous. The fine-tuned model will be noticeably
*more like* the writer than the IAM base (slant, size, spacing, rhythm, and
partial letterform shape), but it is not forge-grade. If the web app's
overlays show a line reconstructing badly, reject that line rather than
training on it.
