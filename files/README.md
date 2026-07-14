# InkMimic × DiffusionPen — implementation kit

This folder is the code half of `InkMimic_DiffusionPen_Pipeline.docx`. It
does **not** replace the cloned `koninik/DiffusionPen` repo — it sits
*alongside* it and adds the one thing that repo doesn't have: a script that
takes your own handwriting photos + arbitrary text instead of IAM benchmark
data.

```
inkmimic_diffusionpen/
├── requirements.txt        # pip installs
├── check_environment.py    # Phase 0 sanity check
├── style_preprocessing.py  # Phase 2 — your photos -> model-ready tensor
├── inference.py             # Phase 3 — the actual custom script
└── README.md                # this file
```

Everything below was verified by pulling `train.py`, `unet.py`,
`feature_extractor.py`, and `utils/auxilary_functions.py` directly from
`https://github.com/koninik/DiffusionPen` and reading the real forward-pass
logic — same as the pipeline doc's Section 5. No guessing at the API.

---

## Phase 0 — get the documented demo running, unmodified

**Do this first. Don't touch `inference.py` until this works.**

1. Clone the repo and install dependencies:

   ```bash
   git clone https://github.com/koninik/DiffusionPen.git
   cd DiffusionPen
   pip install -r ../inkmimic_diffusionpen/requirements.txt
   python ../inkmimic_diffusionpen/check_environment.py
   ```

2. Download the three asset folders from Hugging Face
   (`https://huggingface.co/konnik/DiffusionPen`) into the repo root:
   - `saved_iam_data/` — preprocessed IAM `.pt` tensors
   - `style_models/` — style encoder weights (`iam_style_diffusionpen.pth`)
   - `diffusionpen_iam_model_path/` — UNet weights (`models/ckpt.pt`,
     `models/ema_ckpt.pt`)

   Easiest with the `huggingface_hub` CLI:
   ```bash
   pip install huggingface_hub
   huggingface-cli download konnik/DiffusionPen --local-dir . --local-dir-use-symlinks False
   ```

3. Download `stable-diffusion-v1-5` locally (needed for the VAE + DDIM
   scheduler config):
   ```bash
   huggingface-cli download stable-diffusion-v1-5/stable-diffusion-v1-5 --local-dir ./stable-diffusion-v1-5
   ```

4. Run the documented command, unmodified:
   ```bash
   python train.py --save_path ./diffusionpen_iam_model_path \
       --style_path ./style_models/iam_style_diffusionpen.pth \
       --train_mode sampling --sampling_mode single_sampling
   ```

   **If this doesn't produce an image, stop here and fix it before going
   further** — Phases 2-5 all depend on these exact same weight files
   loading correctly.

No GPU on hand? Run steps 1-4 in a Colab or Kaggle notebook with a free
GPU runtime — `check_environment.py` will tell you if you're on CPU only
and roughly what to expect.

---

## Phase 1 — understand the real contract (read-only, no code to run)

Read, in this order, inside your clone:
1. `feature_extractor.py` (20 lines — the style encoder wrapper)
2. `unet.py`, specifically `UNetModel.__init__` (~line 969) and
   `UNetModel.forward` (~line 1266)
3. `train.py`, specifically `Diffusion.sampling()` (~line 255)

The three findings that matter, already folded into `inference.py`:
- **Style conditioning is additive**, not cross-attention: 5 images →
  mobilenetv2_100 → mean-pooled → linear projection → added straight into
  the diffusion timestep embedding.
- **Text conditioning is cross-attention** via CANINE
  (`google/canine-c`), not `letter2index.json` — that file is only used
  for a separate training-time auxiliary head.
- **There's no "unseen writer" special case.** When you pass
  `style_extractor=<your embeddings>`, the UNet's `forward()` throws away
  the writer-ID label path entirely (`unet.py` line ~1288). Your photos
  don't need to resemble any IAM writer ID — the model was never doing
  identity lookup when image features are supplied.

---

## Phase 2 — feed YOUR photo into the style encoder

```bash
cd DiffusionPen   # so any relative imports resolve
python ../inkmimic_diffusionpen/style_preprocessing.py /path/to/folder/of/your/handwriting/photos
```

This should print something like:
```
OK — produced batch of shape (5, 3, 64, 256), dtype=torch.float32, range=[-1.000, 1.000]
```

If it errors, the problem is almost certainly in your source photos
(non-RGB mode, zero-byte files, wrong extension) — fix those before
moving to Phase 3. 5–10 clear, well-lit word/line crops work better than
one big page photo; segment_handwriting.py from the rest of the InkMimic
pipeline (or even simple manual crops) is fine as input here.

---

## Phase 3 — run the actual custom inference script

```bash
# still inside your DiffusionPen clone, with inkmimic_diffusionpen/ as a sibling folder
python ../inkmimic_diffusionpen/inference.py \
    --style_dir /path/to/your/handwriting/photos \
    --text "hello world" \
    --output out.png \
    --repo_dir . \
    --save_path ./diffusionpen_iam_model_path \
    --style_path ./style_models/iam_style_diffusionpen.pth \
    --stable_dif_path ./stable-diffusion-v1-5
```

What it does, step by step (printed as it runs, `[1/6]`–`[6/6]`):
1. Picks a device (CUDA if available, else CPU — expect CPU to be slow).
2. Loads + preprocesses 5 of your photos via `style_preprocessing.py`.
3. Tokenizes `--text` with `CanineTokenizer` (max length 40).
4. Loads the pretrained mobilenetv2_100 style encoder, runs your 5 images
   through it → `(5, 1280)` embedding.
5. Builds the UNet with the exact same hyperparameters the checkpoint was
   trained with, loads `ema_ckpt.pt`.
6. Runs 50-step DDIM sampling, decodes the final latent through the SD-1.5
   VAE, saves `out.png`.

**Text vocabulary limit:** DiffusionPen's text encoder was trained
against 80 characters — digits, `A-Z`, `a-z`, space, and basic punctuation
(`_!"#&'()*+,-./:;?`). No accents, no `@`/`%`/`$`, no newlines.
`inference.py` warns (doesn't crash) if you pass anything outside that
set — treat a warning as "this word's rendering quality is unverified."

**If VRAM runs out:** this is heavier than an LSTM — SD's VAE alone is
~80M params, plus the UNet. Try Colab/Kaggle's GPU runtime before
concluding your local machine can't do it.

---

## Phase 4 — quality pass

Once Phase 3 produces *a* PNG, the actual work is deciding if it's *good
enough*:

1. Re-run Phase 3 with 5, then 10, then 20 photos in `--style_dir`
   (`--num_style_images` still samples 5 for the model, but a bigger pool
   to sample from may improve which 5 get picked — try `--seed` variation
   too).
2. Eyeball legibility and how close the letterforms are to your actual
   handwriting.
3. Decide the minimum reference-sample count for your onboarding flow —
   this is a product decision, not something the code can answer for you.

No script for this phase — it's manual comparison. If you want it
automated later (e.g. an HTR-based legibility score), that's a good
Phase 4.5 addition, not part of this kit.

---

## Phase 5 — bolt on the product layer

`out.png` from Phase 3 is a raw word/line image on a plain background —
this is exactly the "Level 3 output" the original InkMimic PRD expects.
Everything downstream (paper texture, ruling, ink color, scan-effect
compositing, PDF export) stays as already planned; none of it needs to
know DiffusionPen was involved. No new code needed here beyond wiring
`inference.py`'s output path into whatever function currently consumes a
Level 2/3 word image.

---

## Known gaps / things this kit does NOT solve for you

- **Paragraph/multi-line layout.** The repo's `paragraph` sampling mode
  exists but full-page layout, margins, and line-wrapping are not owned by
  this model — keep your own layout logic downstream, per the PRD.
- **PencilKit stroke data.** DiffusionPen is image-only. If Path 1
  (Apple Pencil capture) needs to feed this model, it has to be rendered
  to an image first, losing pressure/timing — see the pipeline doc's
  risk table, row 4, for the two options (treat DiffusionPen as Path-2-only,
  or accept the lossy conversion).
- **Style fidelity is unverified for YOUR handwriting specifically.** The
  paper's metrics are on IAM writers. Phase 4 is not optional if you care
  about output quality — budget real time for it.
