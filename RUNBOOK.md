# RUNBOOK — What has been done & how to run everything

This is the operating manual for the project. It explains what now exists,
what changed from the original audit, and — step by step — how to set up the
environment, run every piece, and verify it works.

---

## 1. What this project is

A tool that turns a few **photographs of your handwriting** into a per-user
model that can **generate new text in that style** and render it as a page
image — so typed text comes out looking hand-written.

Two very different things happen in the repo:

| Side | Tooling | What it does |
|---|---|---|
| **Recognition** (pre-existing, strong) | `preprocessing.py`, `segment.py`, `training/classifier.py` | Clean a phone photo of a page and cut it into lines/characters; classify characters |
| **Generation** (the product) | `diffusion_model/` (HANDWRITER, arXiv:2011.06704) | Given text + a style reference, generate stroke data that renders as handwriting |

The generation model is **stroke-level**: its input is online pen data —
`(dx, dy, pen_up)` per point — plus the text, plus a line image for a frozen
style extractor. That's the key constraint that shaped everything below.

---

## 2. What has been done

### 2.1 Original state (the audit — `summary.txt`, 2026-08-05)

- A working recognition pipeline (`preprocessing.py` + `segment.py`), a
  character classifier, and a labeling app.
- The diffusion model was **dead code**: TensorFlow wasn't installed anywhere.
- The model's training input (online strokes) **did not exist** anywhere in
  the repo — only offline page photos.
- Two generation paths (a char-GAN and the diffusion model) were both
  non-runnable end-to-end.

### 2.2 What was built (2026-08-08)

| New file | Purpose |
|---|---|
| `requirements-app.txt` | One unified env: TF≥2.16 + torch + cv2 + streamlit + skimage (`numpy<2`). TF and torch must coexist in one process. |
| `diffusion_model/utils.py` (patched) | Keras 3 fix: `tf.data.experimental.AUTOTUNE` → `tf.data.AUTOTUNE`. |
| `diffusion_model/stroke_reconstruct.py` | **Reconstructs approximate online strokes from offline line crops.** Skeletonize → graph trace → order chains → resample to ≤480 pts → normalize exactly like the IAM parser. Writes validation overlays. |
| `diffusion_model/build_train_data.py` | Assembles per-user training pickles in the model's exact input format; reads `transcript.json`; splits train/holdout. |
| `diffusion_model/finetune.py` | Per-user decoder fine-tuning: loads the IAM base, low LR (1e-4..1e-5), short runs, dropout, per-user weight output. |
| `diffusion_model/renderer.py` | High-quality PIL ink renderer (anti-aliasing, variable stroke width, paper styles) replacing the matplotlib output. |
| `diffusion_model/generate_page.py` | Full-page generation: per-user weights + the user's own style line, word-wrap, best-of-N with a classifier read-back gate. |
| `diffusion_model/generate_handwriting.py` (edited) | Default classifier checkpoint now points at the canonical `classifier_final4.pt`. |
| `app/app.py` | Local Streamlit web app running the whole flow: upload → segment → transcribe → reconstruct → fine-tune → generate → download. |

### 2.3 What was removed (archived → `docs/archive/`, deleted → gone)

**Archived (reversible — kept for the FYP writeup):**
- `testa.py` (superseded), `generation/` (dead GAN path), `training/gan.py`
- `explanation.txt`, `stuff.txt` (stale/one-off notes)
- Redundant classifier checkpoints (`classifier.pt`, `classifier_final.pt`,
  `classifier_final2.pt`, `classifier_final3.pt`)

**Deleted (regenerable / stale):**
- `chars/`, `chars1/`, `chars5/`, `chars7/` — stale segmentation runs
  (`chars9/` kept as canonical)
- `diffusion_model/result.png`, `paragraph_result/`, `_line_candidates/`
- `training/emnist_sample_check.png`

**Kept:** `classifier_final4.pt` (canonical) + `classifier_emnist.pt`
(pretrain base). Both venvs left in place — delete the duplicate only after
the new unified env is verified (see §5).

---

## 3. Current repo structure (top level)

```
ai_handwritter.dot/
├── app/                    # NEW — Streamlit web app
│   ├── app.py              #   the full product flow
│   └── users/              #   per-user working dirs (created at runtime)
├── diffusion_model/        # generation model + the new pipeline
│   ├── nn.py  utils.py  preprocessing.py  train.py  inference.py
│   ├── generate_handwriting.py   # style-transfer glue (pre-existing)
│   ├── stroke_reconstruct.py     # NEW
│   ├── build_train_data.py       # NEW
│   ├── finetune.py               # NEW
│   ├── renderer.py               # NEW
│   ├── generate_page.py          # NEW
│   └── weights/model_weights.h5  # IAM-pretrained base (~40 MB)
├── preprocessing.py        # page cleanup (keep)
├── segment.py              # page → lines/characters (keep)
├── training/               # classifier pipeline (keep)
├── labeling/               # manual-labeling UI (keep)
├── data/                   # raw page photos per writer
├── dataset/                # labeled character crops (classifier)
├── chars9/                 # canonical segmentation output
├── docs/archive/           # NEW — archived/dead code
├── requirements.txt        # old PyTorch-only requirements
├── requirements-app.txt    # NEW — the unified env to use
├── plan.md  PRD.md  summary.txt  README.md  RUNBOOK.md
```

---

## 4. Prerequisites

- **Python 3.12** (the repo targets `python 3.12.4`)
- **Windows** (commands below are PowerShell/CMD style; adapt for Unix)
- **GPU recommended** for fine-tuning (a few minutes per user vs. much slower
  on CPU). CPU works if you keep steps low and batch small.
- **Internet on first run**: MobileNetV2 (the frozen style extractor)
  downloads ImageNet weights once into `~/.keras/`.
- Disk: a few GB for the env + weights.

---

## 5. Setup (one time)

The generation model is TensorFlow; the classifier/segmentation are PyTorch.
They must live in **one** interpreter (the app and `generate_handwriting.py`
import both in the same process).

```powershell
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements-app.txt
```

If TensorFlow errors about numpy, force `pip install "numpy<2"` and retry.

**Verify everything imports in one interpreter:**

```powershell
python -c "import tensorflow, torch, cv2, streamlit, skimage; print('env OK')"
```

---

## 6. How to run everything

### Path A — Web app (recommended, the real product flow)

```powershell
streamlit run app/app.py
```

In the browser:

1. **Sidebar** → create or select a user.
2. **Step 1** — upload 1–3 page photos of the user's handwriting.
3. **Step 2** — run *Segmentation*; approve the detected line crops.
4. **Step 3** — *Transcribe* each line (type what it says); blank lines are
   skipped. Press *Save transcriptions*.
5. **Step 4** — *Reconstruct strokes*; check the overlays (original |
   skeleton | reconstructed). If a line reconstructs badly, re-do/remove it
   rather than training on it.
6. **Step 5** — set *steps / learning rate / batch*, press *Build dataset +
   fine-tune*. Output streams live; weights land in
   `app/users/<name>/weights/model_<name>.h5`.
7. **Step 6** — type text, pick a style-reference line + paper style, press
   *Generate page*. Retries best-of-N and shows the winner; download the PNG.

### Path B — CLI (same pipeline, step by step)

```powershell
# 1. Segment + reconstruct strokes for a whole page.
#    Writes app/users/<name>/{lines,strokes,overlays}/...  (repeat per page)
python diffusion_model/stroke_reconstruct.py --input data/alizeh/IMG_8589.jpeg ^
    --page --output_dir app/users/<name>

# 2. Transcribe: create app/users/<name>/transcript.json
#      { "line00": "what this line says", "line01": "...", ... }
#    (The web app does this with text boxes; edit the JSON directly here.)

# 3. Build the training pickle (80/20 train/holdout)
python diffusion_model/build_train_data.py --user_dir app/users/<name> ^
    --output_dir app/users/<name>/data

# 4. Fine-tune the decoder
python diffusion_model/finetune.py --user_data app/users/<name>/data/train_strokes.p ^
    --user <name> --steps 5000 --batchsize 32 --lr 1e-4

# 5. Generate a page with the fine-tuned model
python diffusion_model/generate_page.py --text "Your assignment text here..." ^
    --weights diffusion_model/weights/model_<name>.h5 ^
    --style app/users/<name>/lines/line00.png --out out --tries 3
```

### Path C — No training: style transfer only (quick demo)

Works today with the IAM base weights; output is *in the style of* the
reference line but not per-writer identical.

```powershell
cd diffusion_model
python inference.py --textstring "Hello world" --name smoke
#      ^-- picks a random style from ./assets/ if no --writersource given

# Or use your own page: segment → pick a clean line → generate
python generate_handwriting.py --page ..\data\alizeh\IMG_8589.jpeg ^
    --text "Hello world" --out result --paragraph
```

### Other tools that still work

| Tool | Command |
|---|---|
| Manual character labeling | `streamlit run labeling/label_app.py` |
| Train the character classifier | `cd training; python classifier.py train --dataset_dir ../dataset --epochs 15 --out classifier_final4.pt` |
| Auto-label new segmentation crops | `cd training; python classifier.py auto_label --checkpoint classifier_final4.pt --chars_dir ../chars9 --out_dir ../dataset_auto` |
| Inspect a reconstructed line (single crop) | `python diffusion_model/stroke_reconstruct.py --input some_line.png --output_dir out` |

---

## 7. Data formats (so you can debug or hand-build data)

### Per-user directory (`app/users/<name>/`)

```
photos/            uploaded page photos
lines/lineNN.png   line crops (ink-dark on white), N = 00, 01, …
strokes/lineNN.npy reconstructed strokes, shape (M, 3) float32
overlays/          validation overlays per line
transcript.json    { "line00": "text", ... }
data/              train_strokes.p + holdout_strokes.p + data_meta.json
weights/           model_<name>.h5 (the fine-tuned model)
outputs/           generated pages
```

### The training pickle (`train_strokes.p`)

A list of tuples, consumed directly by `diffusion_model/utils.py:preprocess_data()`:

```
( strokes [N,3] float32,   # (dx, dy, pen_up) — differential, std-normalized
  text     [L] int32,      # tokenizer.encode(line) + [1] end token
  sample   [96, W, 1] uint8 )  # the writer's own line image (style ref)
```

- `MAX_SEQ_LEN = 480` points per line (longer lines are truncated; lines with
  any `|coord| > 15` are dropped).
- `MAX_TEXT_LEN = 50` tokens per line.

### Vocabulary

73 ASCII tokens: `A–Z a–z 0–9 . ? ! , ' " -` + space (plus `_` as the unknown
slot and an end token). Anything else (parens, `$`, `&`, `@`, …) is replaced
with `_` and reported — assignments should avoid those characters until the
vocab is extended (future work).

---

## 8. Fine-tuning parameters explained

| Flag | Default | Meaning |
|---|---|---|
| `--steps` | 5000 | Training steps. Short runs (5–15k) avoid catastrophic forgetting of the IAM prior. |
| `--batchsize` | 32 | Clamped to dataset size automatically (a batch larger than the data would train nothing). |
| `--lr` | 1e-4 | Peak learning rate. 1e-4..1e-5 is the safe window; higher → the model forgets the prior. |
| `--warmup` | 500 | Warmup steps to ramp LR. Keep low for fine-tuning. |
| `--dropout` | 0.1 | Regularization — matters on few dozen lines. |
| `--output_dir` | `./weights` | Writes `model_<user>.h5`; never overwrites `model_weights.h5`. |

The StyleExtractor stays **frozen** — style vectors are precomputed once, so
it never enters the training graph. Only the decoder is fine-tuned.

---

## 9. Verification checklist (run in order)

Each gate must pass before the next:

1. **Env:** `python -c "import tensorflow, torch, cv2, streamlit, skimage"`.
2. **Inference smoke test:** `cd diffusion_model; python inference.py --textstring "The quick brown fox" --name smoke` → saves `smoke.png`.
3. **Reconstruction:** `stroke_reconstruct.py --page` on one `data/alizeh` page → overlays look like the original writing.
4. **Data build:** `build_train_data.py` → `train_strokes.p` loads with no dropped lines; tokenizer round-trips the transcription.
5. **Fine-tune:** loss decreases; `model_<user>.h5` saved.
6. **Quality:** generate a held-out line's text → readable, and visibly closer to the writer's style than the IAM base.
7. **App:** walk one user through the whole `streamlit run app/app.py` flow.

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `tensorflow==2.3.0` install error | Use `requirements-app.txt` (TF≥2.16, Keras 3). The old pin can't build on Python 3.12. |
| numpy version conflict with TF | `pip install "numpy<2"`. |
| `tf.data.experimental.AUTOTUNE` AttributeError | Already patched in `utils.py`. If you re-clone upstream, re-apply: → `tf.data.AUTOTUNE`. |
| MobileNetV2 download prompt/failure on first run | Needs internet once; weights go to `~/.keras/`. |
| Fine-tune trains "nothing" (loss frozen / no steps) | Batch size ≥ dataset size → now auto-clamped. Check `train_strokes.p` has lines: `build_train_data` prints counts. |
| OCR/read-back gate unavailable in generate | `_load_classifier` falls back to a heuristic; check `training/classifier_final4.pt` exists. |
| Generated lines drift off horizontal | Not yet implemented; add a linear detrend in `renderer.py` (documented in `INTEGRATION_GUIDE.md` §6). |
| Out of memory (VRAM) | Reduce `--batchsize`; run fine-tune and generate sequentially, not at the same time. |
| "preprocessing" name collision | Both projects ship a `preprocessing.py` — always run via `app/` or `generate_handwriting.py` which alias them (see `INTEGRATION_GUIDE.md` §3). |

---

## 11. Honest limitations & expectations

- **Reconstruction fidelity.** Strokes are *traced from photos*, so pen order
  and timing are approximations; loops/crossings can be ambiguous. The
  fine-tuned model captures **slant, size, spacing, rhythm, and partial
  letterform shape** — it is noticeably *more like* the writer than the IAM
  base, but it is **not forge-grade** and won't perfectly replicate hand-inked
  nuance.
- **Style ceiling.** The MobileNetV2 style extractor is frozen (ImageNet
  features) and the model was trained for "similar, not identical". Fidelity
  above a certain level requires unfreezing it (risky on few lines) or a
  newer backbone (future work).
- **Generation is stochastic.** The app retries best-of-N and scores with the
  classifier's read-back; run more attempts for better quality.
- **Vocabulary** is 73 ASCII chars — no parens/`$`/`&`/`@`.

For the FYP viva: the defensible story is *"pretrained stroke-diffusion
backbone + our own segmentation/preprocessing feeding it reconstructed
strokes for per-user fine-tuning."* The recognition side (`preprocessing.py`,
`segment.py`) remains your strongest, most defensible asset.

---

## 12. Docs & references

- `summary.txt` — the full model & data audit, plus an addendum marking what
  changed on 2026-08-08.
- `plan.md` — how the diffusion backbone was chosen over a from-scratch GAN.
- `diffusion_model/INTEGRATION_GUIDE.md` — how the pieces connect, the two
  integration bugs fixed, and the new §8 (fine-tuning pipeline).
- `README.md` — quick start.
- `docs/archive/` — superseded files kept for the FYP writeup.
