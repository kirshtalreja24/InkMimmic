# AI Handwriter

Turn a few photographs of your handwriting into a per-user model that can
generate new text in that style — then render assignment-length pages from
plain typed text.

The repo has two parts that share the same generation core
(`diffusion_model/generate_page.py`) but are otherwise independent — see
`docs/adr/workflow.md` for the full split:

- **Workflow A — research pipeline** (below): per-writer fine-tuning,
  driven by `app/app.py` or the CLI. FYP/research artifact, not part of the
  live product.
- **Workflow B — Inkmimic product**: a stateless FastAPI backend
  (`api/server.py`) plus a web app (`inkmimic/inkmimic/`) and mobile app
  (`inkmimic-mobile/`) that call it. No per-writer fine-tuning — style
  transfer from whatever sample image the request supplies. This is what's
  live for real users; see [Running the product](#running-the-product-inkmimic)
  below.

```
page photos ──▶ segmentation ──▶ line crops ──▶ stroke reconstruction
   (segment.py)   (preprocessing.py)   (stroke_reconstruct.py)
                                                        │
typed transcription (per line)                          ▼
              └─────────────────────▶ build_train_data.py ──▶ train_strokes.p
                                                                  │
                                                IAM pretrained weights ─▶ finetune.py ──▶ model_<user>.h5
                                                                  │
typed text ────────────────────────────────────────────────────────▶ generate_page.py ──▶ page PNG
```

## What's here

| Path | Role |
|---|---|
| `preprocessing.py` | Page cleanup: perspective, deskew, CLAHE, shadow removal, Sauvola binarization, ruled/grid-line removal, stroke repair |
| `segment.py` | Page → lines → words → character crops, with valley-based splitting of pen-joined letters + `manifest.csv` |
| `training/` | `SmallCNN` character classifier (62 classes) + auto-labeling + the line-scoring used to pick clean style references |
| `labeling/` | Streamlit manual-labeling UI |
| `diffusion_model/` | The generation model — HANDWRITER stroke-level diffusion (arXiv:2011.06704), IAM-pretrained weights |
| `diffusion_model/stroke_reconstruct.py` | Reconstruct approximate online strokes `(dx, dy, pen_up)` from offline line crops (skeletonize → trace → resample) |
| `diffusion_model/build_train_data.py` | Assemble per-user training pickles in the model's exact input format |
| `diffusion_model/finetune.py` | Per-user decoder fine-tuning (loads IAM base, low LR, short runs) |
| `diffusion_model/renderer.py` | High-quality ink renderer (variable stroke width, paper styles) replacing the matplotlib output |
| `diffusion_model/generate_page.py` | Full-page generation: per-user weights + style line, word-wrap, best-of-N with a legibility gate — shared by both workflows |
| `app/` | Local Streamlit web app (Workflow A): upload → segment → transcribe → reconstruct → fine-tune → generate → download |
| `data/` | Raw page photos, per writer (kirsh, mayra, alizeh, random) |
| `dataset/` | Labeled character crops (for the classifier) |
| `api/server.py` | Workflow B backend — FastAPI, exposes `/api/generate` and `/api/analyze-style` for the Inkmimic apps over the same diffusion core |
| `inkmimic/inkmimic/` | Inkmimic web app — React + Vite + Tailwind + Supabase |
| `inkmimic-mobile/` | Inkmimic mobile app — Expo + React Native, mirrors the web app |
| `packages/inkmimic-core/` | npm workspace package shared by both Inkmimic apps — session/auth + the `api/server.py` client |

## Setup

The generation model is TensorFlow; the classifier/segmentation are PyTorch.
They must live in **one** interpreter (the app and `generate_handwriting.py`
import both in the same process).

```bash
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements-app.txt
```

`requirements-app.txt` pins `tensorflow>=2.16` (Keras 3; the repo's old
`tensorflow==2.3.0` pin won't install on Python 3.12) alongside torch/cv2/
streamlit/scikit-image. If TensorFlow complains about numpy, pin `numpy<2`.

## Quick start (no training — style transfer)

```bash
cd diffusion_model
python inference.py --textstring "Hello world" --writersource assets/a02-050-03.tif --name smoke
```

## Full per-user flow (web app)

```bash
streamlit run app/app.py
```

1. Create/select a user.
2. Upload 1–3 page photos of their handwriting.
3. Run segmentation → approve the detected line crops.
4. Transcribe each line (type what it says).
5. Reconstruct strokes → check the overlays.
6. Build dataset + fine-tune (GPU recommended; a few minutes per user).
7. Generate text in their style → download the page PNG.

### CLI equivalent

```bash
# 1. Segment a page into lines AND reconstruct strokes for each line.
#    Writes app/users/<name>/{lines,strokes,overlays}/... (the same layout the
#    web app uses). Repeat for every page of the user's handwriting.
python diffusion_model/stroke_reconstruct.py --input data/alizeh/IMG_8589.jpeg \
    --page --output_dir app/users/<name>

# 2. Transcribe each detected line: create app/users/<name>/transcript.json
#    as { "line00": "what this line says", "line01": "...", ... }
#    (the web app does this for you with text boxes).

# 3. Build the training pickle (train + holdout split)
python diffusion_model/build_train_data.py --user_dir app/users/<name> --output_dir app/users/<name>/data

# 4. Fine-tune the decoder on the user's strokes
python diffusion_model/finetune.py --user_data app/users/<name>/data/train_strokes.p \
    --user <name> --steps 5000 --batchsize 32 --lr 1e-4

# 5. Generate a page with the fine-tuned model
python diffusion_model/generate_page.py --text "Your text here" \
    --weights diffusion_model/weights/model_<name>.h5 \
    --style app/users/<name>/lines/line00.png --out out --tries 3
```

Note: `segment.py` on its own outputs per-*character* crops. For line-level
crops + strokes, use `stroke_reconstruct.py --page` (or the web app), which
drives `segment.py` internally and rebuilds full-line crops.

## Running the product (Inkmimic)

Workflow B — no per-writer fine-tuning, just style transfer from whatever
sample image the request supplies (or the default IAM style line if none is
given). Uses the same `venv` from [Setup](#setup) for the backend.

```bash
# 1. Backend (from the repo root, venv active)
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# 2. Web app
cd inkmimic/inkmimic
npm install
cp .env.example .env   # fill in Supabase keys, or leave unset for local mode
npm run dev

# 3. Mobile app (instead of, or alongside, the web app)
cd inkmimic-mobile
npm install
cp .env.example .env
npx expo start
```

See `inkmimic/inkmimic/README.md` and `inkmimic-mobile/README.md` for
per-app details (Supabase setup, project structure), and
`docs/adr/workflow.md` for how a request flows end to end.

## Training-data format

`build_train_data.py` writes pickles that `diffusion_model/utils.py:preprocess_data()`
consumes directly:

```
list of ( strokes [N,3] float32,   # (dx, dy, pen_up), differential, std-normalized
          text     [L] int32,      # tokenizer.encode(line) + end token
          sample   [96, W, 1] uint8 )  # the writer's own line image (style ref)
```

Vocab is fixed at 73 ASCII tokens (`A–Z a–z 0–9 .?!,'"-` + space). Characters
outside it (parens, `$`, `&`, `@`, …) are flagged and replaced with `_`.

## Honest limitations

- **Reconstruction fidelity.** Strokes are traced from photos, so pen order
  and timing are approximations. The fine-tuned model captures slant, size,
  spacing, rhythm, and *some* letterform shape — it will not be
  indistinguishable from the writer's real hand.
- **Style ceiling.** The MobileNetV2 style extractor is frozen (ImageNet
  features); the model's style conditioning was trained to be "similar",
  not "identical".
- **Generation is stochastic.** The app retries best-of-N and scores each
  attempt with the character classifier's read-back.
- The old GAN generation path (`generation/`, `training/gan.py`) was dead code
  and is archived under `docs/archive/`.

## Docs

- `CONTEXT.md` — project glossary, covers both workflows (start here in a new session)
- `docs/adr/workflow.md` — the two actual end-to-end workflows (research pipeline vs. product) in full detail
- `docs/adr/` — architecture decision records (why things are built the way they are)
- `RUNBOOK.md` — step-by-step operating manual for the research pipeline (Workflow A)
- `TESTING_GUIDE.md` — how to test the generation pipeline
- `plan.md` — how the diffusion backbone was chosen over a from-scratch GAN
- `diffusion_model/INTEGRATION_GUIDE.md` — how the pieces connect
- `diffusion_model/UPSTREAM_README.md` — the original HANDWRITER paper's README
- `summary.txt` — the full model & data audit (2026-08-05)
- `docs/archive/` — superseded files kept for the FYP writeup
- `inkmimic/inkmimic/README.md`, `inkmimic-mobile/README.md` — per-app docs for the Inkmimic product (Workflow B)
