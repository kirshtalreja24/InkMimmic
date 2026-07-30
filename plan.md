# Plan: Pre-trained Model Integration for Handwriting Generation

> Updated 2024-07-30 — compares HiGAN+ vs Diffusion-Handwriting-Generation
> and gives an honest recommendation.

---

## TL;DR

**Use the Diffusion-Handwriting-Generation repo.** It's the better fit by a
wide margin. Read on for why.

---

## 1. The Two Options Side by Side

### Option A: HiGAN+ (ganji15/HiGANplus)

**What it is:** A GAN with disentangled style/content representations.
Generates word-level images (64px tall) conditioned on text + style reference.

| Attribute | Detail |
|---|---|
| Framework | PyTorch 1.11 |
| Output | Image of a single **word** (64px height, variable width) |
| Style input | A reference handwriting image → style encoder |
| Pre-trained weights | `deploy_HiGAN+.pth` (exists in repo) |
| Dataset | IAM word-level (HDF5 files you must request separately from university) |
| License | "Academic research purposes" (restrictive) |
| Repo activity | 46 stars, 15 forks, 12 commits — minimal maintenance |
| OS requirement | Ubuntu 20/22 (stated in README) |

**How inference works:**
```bash
python eval_demo.py --config configs/gan_iam.yml \
    --ckpt pretrained/deploy_HiGAN+.pth --mode style
```
Provide a reference image → generates a word in that style. You'd need to
call it once per word and compose them into a line/page yourself.

---

### Option B: Diffusion-Handwriting-Generation (tcl9876/Diffusion-Handwriting-Generation)

**What it is:** A diffusion model (DDPM) for handwriting generation. Takes
any text string and a style reference image → generates handwriting of the
entire text, stroke by stroke, then renders it.

| Attribute | Detail |
|---|---|
| Framework | TensorFlow 2.3 |
| Output | **Full text rendering** — generates stroke sequences (x, y, pen-lift), rendered via matplotlib into an image |
| Style input | A single line-level handwriting image (96px tall) |
| Pre-trained weights | ✅ **Included in repo** (`weights/model_weights.h5`, 38.6MB) |
| Dataset | IAM On-Line database (for training only — not needed for inference) |
| License | **MIT** (permissive — use anywhere) |
| Repo activity | 121 stars, 13 commits |
| OS requirement | Cross-platform (Python + TensorFlow) |

**How inference works:**
```bash
python inference.py \
    --textstring "Hello World" \
    --writersource ./assets/sample_handwriting.png \
    --name output \
    --show True
```

That command:
1. Loads the pre-trained diffusion model (38.6MB)
2. Reads the style reference image (any handwriting line image, 96px tall)
3. Extracts style via a frozen MobileNetV2 backbone
4. Runs 60-step reverse diffusion to generate stroke coordinates
5. Renders strokes into a matplotlib figure
6. Saves as PNG

One call generates the **entire text string** — no word-by-word composition
needed.

---

## 2. Head-to-Head Comparison

| Factor | HiGAN+ | Diffusion-HW-Gen | Winner |
|---|---|---|---|
| **Ease of setup** | Need to request IAM HDF5 files even for inference; PyTorch 1.11 specifically; Ubuntu only | `pip install` + run; weights included; cross-platform | ✅ Diffusion |
| **Pre-trained weights** | Checkpoint exists but may need IAM data present for the config to load | **Ships in repo** — 38.6MB, ready to go | ✅ Diffusion |
| **Output granularity** | Single word at a time → you compose | Full text string in one call | ✅ Diffusion |
| **Style conditioning** | Reference image → style encoder | Reference image → MobileNetV2 style extractor | Tie |
| **Output type** | Pixel image (64px fixed height) | Stroke trajectories → rendered to any resolution | ✅ Diffusion |
| **Character support** | A-Z, a-z, 0-9 (80-class vocabulary) | Full ASCII: letters, digits, punctuation, spaces (73 tokens) | ✅ Diffusion |
| **License** | Academic only | **MIT** — use it anywhere | ✅ Diffusion |
| **Code quality** | Modular but complex (networks/, lib/, configs/) | Simple — 5 files, ~500 lines total, readable | ✅ Diffusion |
| **Our framework** | PyTorch (matches our training/ code) | TensorFlow (doesn't match) | ✅ HiGAN+ |
| **Paper quality** | ACM ToG 2022 (top venue) | arXiv 2020 (preprint, but well-cited) | Slight edge HiGAN+ |
| **Generation quality** | Higher visual quality (GANs excel at sharpness) | Good quality, slightly less sharp (diffusion produces smoother strokes) | Slight edge HiGAN+ |
| **Diversity** | Can mode-collapse (GAN issue) | Naturally diverse (diffusion sampling) | ✅ Diffusion |

**Score: Diffusion wins 8-2 with 1 tie.**

---

## 3. How the Diffusion Model Works (Architecture Deep Dive)

```
Input:  "Hello World" (text string)
        + style reference image (one line of someone's handwriting)

                    ┌──────────────────────────────┐
   Text ──→ Tokenizer ──→ Embedding ──→ ┐         │
                                          ├─→ DiffusionWriter (U-Net style)
   Style image ──→ MobileNetV2 ────────→ ┘    │   │
                   (frozen, ImageNet          │   │
                    pre-trained)         60 diffusion steps
                                              │   │
   Random noise ──→ x_T ──→ denoise ──→ ... ──→ x_0
                                              │
                                    [dx, dy, pen_lift]
                                    stroke sequence
                                              │
                                         render with
                                         matplotlib
                                              │
                                         output.png
```

### Key components in the code:

| File | What it does |
|---|---|
| `nn.py` → `StyleExtractor` | Frozen MobileNetV2 that reads a 96×96px handwriting image and outputs a style vector (14×1280 tensor) |
| `nn.py` → `Text_Style_Encoder` | Merges text embeddings + style vector via cross-attention |
| `nn.py` → `DiffusionWriter` | The main model: a 1D U-Net with conv blocks + attention layers, conditioned on noise level (sigma), text, and style |
| `utils.py` → `run_batch_inference()` | The diffusion sampling loop: 60 reverse steps from noise → clean strokes |
| `utils.py` → `Tokenizer` | Maps ASCII characters to token IDs (73-token vocabulary) |
| `utils.py` → `show()` | Renders stroke sequences (cumulative sum of dx/dy) as matplotlib line plots |

### What the model actually outputs:

The model predicts **stroke sequences**, not pixel images directly:
- Each timestep outputs `(dx, dy)` — relative pen movement
- Plus a `pen_lift` probability — is the pen on the paper or in the air?
- These are accumulated: `positions = cumsum(strokes)` to get absolute coordinates
- Then plotted with `matplotlib` as line segments

This is fundamentally different from image-based generation (HiGAN+/our GAN):
- **Pro:** Resolution-independent — you can render strokes at any scale
- **Pro:** Natural pen-lift handling — spaces between letters are implicit
- **Pro:** Output looks like actual pen movement, not a pixel approximation
- **Con:** Rendering is via matplotlib (kinda ugly line plots by default)
- **Con:** No ink texture, pen pressure variation, or paper effects out of the box

---

## 4. Integration Plan

### Phase 1: Get it running (Day 1)

```bash
# 1. Copy the repo into our project
cd D:\ai_handwritter.dot
git clone https://github.com/tcl9876/Diffusion-Handwriting-Generation.git third_party/diffusion_hw

# 2. Install TensorFlow (separate from our PyTorch venv)
pip install tensorflow==2.3.0 matplotlib pillow h5py numpy==1.18.5
# NOTE: TF 2.3 is old. If it won't install, try tensorflow==2.10.0 or
#       tensorflow==2.15.0 — the code uses basic Keras APIs that haven't
#       changed. May need minor fixes.

# 3. Test with included assets
cd third_party/diffusion_hw
python inference.py --textstring "Hello World" --show True
# This should use a random style from ./assets/ and display the output
```

### Phase 2: Connect our pipeline (Day 2-3)

Create `generation/diffusion_generate.py`:

```python
"""
Bridge between our preprocessing/segmentation pipeline and the
Diffusion-Handwriting-Generation model.

Usage:
    python diffusion_generate.py \
        --text "The quick brown fox" \
        --style_image data/alizeh/IMG_8589.jpeg \
        --output output.png
"""

import sys
import os
from pathlib import Path

# Add diffusion model to path
DIFFUSION_DIR = Path(__file__).parent.parent / "third_party" / "diffusion_hw"
sys.path.insert(0, str(DIFFUSION_DIR))

import tensorflow as tf
import numpy as np
from PIL import Image

# Import diffusion model components
import nn
import utils
import preprocessing as dhg_preprocess


class HandwritingGenerator:
    def __init__(self, weights_path=None):
        if weights_path is None:
            weights_path = str(DIFFUSION_DIR / "weights" / "model_weights.h5")

        self.tokenizer = utils.Tokenizer()
        self.beta_set = utils.get_beta_set()

        # Build model
        C1 = 128
        self.style_extractor = nn.StyleExtractor()
        self.model = nn.DiffusionWriter(num_layers=2, c1=C1, c2=C1*3//2, c3=C1*2)

        # Dummy forward pass to initialize weights (TF requirement)
        _stroke = tf.random.normal([1, 400, 2])
        _text = tf.random.uniform([1, 40], dtype=tf.int32, maxval=50)
        _noise = tf.random.uniform([1, 1])
        _style = tf.random.normal([1, 14, 1280])
        _ = self.model(_stroke, _text, _noise, _style)

        self.model.load_weights(weights_path)
        print(f"Loaded diffusion model from {weights_path}")

    def _prepare_style_image(self, image_path):
        """Load a handwriting image and extract its style vector.

        The model expects a 96px-tall grayscale image of a LINE of
        handwriting (not a full page, not a single character). Our
        preprocessing + segmentation pipeline can supply this — we
        just need one clean line-level crop.
        """
        img = dhg_preprocess.read_img(image_path, 96)
        img = tf.expand_dims(img, 0)
        return self.style_extractor(img)

    def generate(self, text, style_image_path, output_path=None, seed=None):
        """Generate handwriting for 'text' in the style of 'style_image_path'."""
        if seed is not None:
            tf.random.set_seed(seed)

        style_vector = self._prepare_style_image(style_image_path)
        timesteps = len(text) * 16
        timesteps = timesteps - (timesteps % 8) + 8

        strokes = utils.run_batch_inference(
            self.model, self.beta_set, text, style_vector,
            tokenizer=self.tokenizer, time_steps=timesteps,
            diffusion_mode='new', show_samples=False, path=output_path,
        )
        return strokes


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--text", required=True)
    p.add_argument("--style_image", required=True)
    p.add_argument("--output", default="generated.png")
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()

    gen = HandwritingGenerator()
    gen.generate(args.text, args.style_image, args.output, args.seed)
    print(f"Saved to {args.output}")
```

### Phase 3: Extract line-level style references (Day 3-4)

The diffusion model needs a **line-level** image for style (not a whole page,
not a single character). We need to add a mode to our segmentation pipeline
that exports full text lines instead of individual characters:

```python
# In segment.py, add a function like:
def extract_line_images(image_path, output_dir):
    """Save each detected text line as a separate image for style reference."""
    binary = preprocess(image_path)
    blobs = find_blobs(binary)
    lines = group_into_lines(blobs)

    for i, words in enumerate(lines):
        # Get bounding box of entire line
        all_boxes = [b for word in words for b in word]
        x0 = min(b[0] for b in all_boxes)
        y0 = min(b[1] for b in all_boxes)
        x1 = max(b[0]+b[2] for b in all_boxes)
        y1 = max(b[1]+b[3] for b in all_boxes)

        line_img = binary[y0:y1, x0:x1]
        cv2.imwrite(f"{output_dir}/line_{i:02d}.png", line_img)
```

### Phase 4: Improve rendering (Week 2)

The default matplotlib rendering is basic — black strokes on white. For our
FYP we'd want:

1. **Custom renderer** — replace `utils.show()` with a proper PIL/OpenCV
   renderer that supports:
   - Ink color (blue, black, whatever the reference pen was)
   - Stroke thickness variation (simulate pen pressure from velocity)
   - Paper backgrounds (lined, blank, graph)
   - Anti-aliasing

2. **Multi-line layout** — the model generates one line at a time. For pages:
   - Split input text into lines (by width or by sentence)
   - Generate each line with the same style vector
   - Compose vertically with proper line spacing

3. **Connect to the inkmimic web UI** — the React frontend just needs an API
   endpoint that takes (text, style_image) and returns a generated image.

---

## 5. Pros of the Diffusion Model

| # | Pro |
|---|---|
| 1 | **Weights ship in the repo.** 38.6MB .h5 file, git clone and go. |
| 2 | **Full text in one call.** No per-word or per-character loop. |
| 3 | **Style from any handwriting image.** One line image = personalized output. |
| 4 | **MIT license.** Use it in your FYP, modify it, ship it, no restrictions. |
| 5 | **Stroke output is resolution-independent.** Render at any size, any DPI. |
| 6 | **Punctuation support.** Letters, digits, `.?!,'"- ` all work. |
| 7 | **Tiny codebase.** 5 files, ~500 LOC. You can understand the whole thing. |
| 8 | **No extra dataset needed for inference.** IAM is only for retraining. |
| 9 | **Diverse outputs.** Run the same text twice → different natural variation. |
| 10 | **Our existing preprocessing still adds value.** We use it to extract clean line images for style reference. |

## 6. Cons of the Diffusion Model

| # | Con | Severity | Mitigation |
|---|---|---|---|
| 1 | **TensorFlow, not PyTorch.** Our existing training/ code is all PyTorch. The generation pipeline would use a different framework. | Medium | Keep them separate. Our classifier (PyTorch) does labeling, the diffusion model (TF) does generation. They don't need to share a runtime. |
| 2 | **TF 2.3 is ancient** (Nov 2020). May not install on modern Python/CUDA. | High | Test with `tensorflow==2.10.0` or `2.15.0` first. The code only uses basic Keras APIs (Dense, Conv1D, MobileNetV2) that haven't changed. If needed, we can port the ~300 LOC model to TF 2.15+ in a day. |
| 3 | **Stroke rendering is ugly by default.** matplotlib line plots — no ink texture, no pressure, no paper. | Medium | Replace `utils.show()` with a custom PIL/cairo renderer. This is a self-contained improvement (~50 LOC). |
| 4 | **Style quality depends on the reference image.** A blurry or poorly cropped style image → bad style extraction. | Low | Our preprocessing pipeline already handles this well — just feed it a clean line-level crop. |
| 5 | **Slow on CPU.** 60 diffusion steps × forward pass each. Could be 30-60 seconds per sentence on CPU. | Medium | Use GPU (Colab) for demos. For production, look into DDIM (fewer steps) or distillation. |
| 6 | **Fixed architecture.** No easy way to add new characters (e.g. Arabic, Urdu). | High | Would require retraining on new data. But for English A-Z/a-z/0-9 + punctuation, it works. |
| 7 | **No ink thickness or pen pressure.** Strokes are uniform-width lines. | Low | Post-process: vary line width based on velocity (fast strokes = thin, slow = thick). ~20 LOC. |
| 8 | **MobileNetV2 style extractor is frozen.** Can't fine-tune the style extraction without unfreezing and retraining. | Medium | The frozen ImageNet features are surprisingly good for handwriting style. Only matters if your handwriting is very unusual. |
| 9 | **Single-line output.** Multi-line text needs manual line-splitting and composition. | Medium | Write a compose layer that generates line-by-line and stacks them. Straightforward. |
| 10 | **No direct integration with our web UI (inkmimic).** Need to build an API bridge. | Medium | Wrap `HandwritingGenerator` in a FastAPI/Flask endpoint. The web UI's `ai-core/` package is already an empty placeholder waiting for this. |

---

## 7. What Happens to Our Existing Code

| File | Keep? | Role |
|---|---|---|
| `preprocessing.py` | ✅ Keep | Still used to clean reference images for style extraction |
| `segment.py` | ✅ Keep | Still used to extract line-level crops for style reference |
| `testa.py` | ⚠️ Archive | Legacy — superseded by segment.py |
| `training/classifier.py` | ✅ Keep | Still useful for auto-labeling if we ever build our own dataset |
| `training/dataset.py` | ✅ Keep | Same |
| `training/train_emnist.py` | ✅ Keep | Same |
| `training/gan.py` | ❌ Deprioritize | Our DCGAN is superseded by the diffusion model for generation |
| `generation/generate.py` | ❌ Replace | Replaced by `generation/diffusion_generate.py` |
| `training/predict.py` | ✅ Keep | Character prediction still useful independently |
| `training/normalize_scale.py` | ✅ Keep | Data prep utility |
| `training/sort_case.py` | ✅ Keep | Data prep utility |
| `inkmimic/` | ✅ Keep | Web UI — the `ai-core/` package connects to the new Generator |

---

## 8. Updated Project Structure

```
ai_handwritter.dot/
├── preprocessing.py          # image cleanup (our code, reuse)
├── segment.py                # character/line extraction (our code, reuse)
├── testa.py                  # legacy, kept for reference
│
├── generation/
│   ├── generate.py           # old GAN-based generator (archived)
│   └── diffusion_generate.py # NEW — adapter for diffusion model
│
├── training/                 # our classifier + dataset tools (keep)
│   ├── classifier.py
│   ├── dataset.py
│   ├── gan.py                # deprioritized
│   └── ...
│
├── third_party/
│   └── diffusion_hw/         # cloned Diffusion-Handwriting-Generation repo
│       ├── inference.py
│       ├── nn.py
│       ├── utils.py
│       ├── preprocessing.py
│       └── weights/
│           └── model_weights.h5  (38.6MB, pre-trained)
│
├── inkmimic/                 # React web UI
│   └── inkmimic/
│       └── src/packages/
│           ├── ai-core/      # ← wire diffusion_generate.py here
│           └── ai-prototype/ # Anthropic API stand-in
│
├── data/                     # raw handwriting photos
├── dataset/                  # labeled character crops
├── PRD.md
├── plan.md                   # this file
└── README.md
```

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| TF 2.3 won't install on our Python/system | High | Blocks everything | Try TF 2.10-2.15; port model if needed (small codebase) |
| Style extraction doesn't capture our user's handwriting well | Medium | Poor output quality | Test with multiple reference images; try different line crops |
| Diffusion inference is too slow for demo (>60s) | Medium | Bad demo experience | Use Colab GPU; or reduce diffusion steps (30 instead of 60, lower quality but faster) |
| The rendered strokes look too "digital" | Low | Aesthetic issue | Custom renderer with variable stroke width, ink effects |
| Professor/FYP panel questions why we didn't build our own model | Medium | Perception issue | Frame it honestly: we built the preprocessing + segmentation from scratch, and chose a pre-trained generation backbone because training a GAN from scratch on 70 images is not viable. This is standard practice in ML — transfer learning. |

---

## 10. Final Verdict

### Why Diffusion > HiGAN+ for us

1. **It actually ships working weights.** HiGAN+ technically has weights but
   the inference pipeline may still need IAM data paths to initialize.
   Diffusion gives you `git clone` → `python inference.py` → done.

2. **Full text generation.** HiGAN+ does one word at a time and we'd have to
   compose them. Diffusion generates the full string.

3. **MIT license.** No ambiguity about usage.

4. **Simpler code.** 5 files vs a maze of configs, networks, lib, metrics.

5. **Stroke output.** Resolution-independent, composable, and more useful for
   downstream processing than a fixed 64px image.

### Why Diffusion > Our own GAN

1. **70 images ≠ viable GAN training.** We need 1,200+ minimum. That's weeks
   of data collection and labeling.

2. **Diffusion quality is competitive with GANs** for handwriting specifically
   (see the paper's results vs prior GAN work).

3. **Time.** Getting a working demo in 2-3 days vs 4-6 weeks of data
   collection + GAN training + debugging mode collapse.

### What we keep from our own work

Everything except `gan.py` and `generate.py` remains relevant:
- **Preprocessing** — feeds style reference extraction
- **Segmentation** — extracts line-level crops for style conditioning
- **Classifier + auto-labeling** — still useful independently (e.g. if we want
  to identify characters in the output to verify accuracy)
- **Web UI** — the frontend is framework-agnostic; it just needs an API

### Action items

1. `git clone` the diffusion repo into `third_party/`
2. Get `inference.py` running with the included weights
3. Test with our own style reference images from `data/`
4. Write `diffusion_generate.py` adapter
5. Build the page composition layer
6. Wire into the inkmimic web UI's `ai-core/` package
