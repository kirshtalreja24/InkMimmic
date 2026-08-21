# Handwriting Synthesis FYP — Roadmap & Next Steps

> Consolidated from prior discussion analyzing `PRD.md` and `testa.py`.

## Current Status

`testa.py` is **not** the AI model — it's the preprocessing + segmentation pipeline. It already handles:

**✅ Preprocessing**
- Grayscale conversion
- Adaptive thresholding (Sauvola)
- Noise reduction
- Optional ruled-line removal

**✅ Segmentation**
- Connected component analysis
- Word grouping
- Character splitting (touching-letter handling)
- Per-character PNG export
- Manifest generation

This corresponds to **Steps 2–3** of the PRD. The ML/generation stage hasn't started yet.

---

## Next Steps

### Step 1 — Verify Segmentation Quality
```bash
python testa.py --input handwriting.jpg --output_dir dataset --debug_overlay
```
Check that:
- Every character has its own PNG
- No letters are merged
- No letters are broken
- The `_debug_overlay.png` looks correct

**Do not proceed until this is solid** — garbage dataset → garbage model.

### Step 2 — Label the Characters
Reorganize flat output into class-labeled folders:
```
dataset/
  A/
    001.png
    002.png
  B/
    001.png
  a/
    001.png
  0/
    001.png
```

### Step 3 — Collect Samples
Target ~30 images per class × 62 classes (A–Z, a–z, 0–9) ≈ **1,860 images**. More is better.

### Step 4 — Choose & Train a Generative Model
A CNN classifier is **not** sufficient — need a generative architecture:
- **Phase 1 (recommended start):** Character-level Conditional GAN — simpler, faster to demonstrate
- **Phase 2 (stretch goal):** Diffusion Model — higher quality, more realistic

Pipeline:
```
Character PNG → Encoder → Latent style → Generator → New handwritten character
```

### Step 5 — Learn Handwriting Style
Model should capture, not memorize:
- Stroke thickness
- Slant
- Curvature
- Spacing
- Approximate pen pressure
- Overall style

### Step 6 — Generate Full Text
```
"Hello World" → split into chars → generate each char → join → styled output
```

### Step 7 — Improve Realism
Beyond simple concatenation:
- Variable spacing
- Baseline movement
- Slight rotation per character
- Character scaling
- Ligatures between letters

---

## Suggested Project Structure
```
project/
  preprocessing/
    preprocess.py
  segmentation/
    segment.py
  dataset/
    A/ B/ ... a/ b/ ... 0/ 1/ ...
  training/
    train.py
    model.py
    dataset.py
  generation/
    generate.py
    compose.py
  outputs/
```

## Roadmap Summary
- [x] Finish segmentation
- [ ] Verify with multiple pages
- [ ] Label every extracted character
- [ ] Build dataset folders
- [ ] Train generation model (GAN → Diffusion)
- [ ] Generate individual characters
- [ ] Compose full words/sentences
- [ ] Add spacing, ligatures, style refinement

---

## Key Open Decision
PRD currently says "train a handwriting generation model" without specifying architecture. This is the biggest missing piece — decide before writing training code:

**Recommended progression:** Phase 1 (Conditional GAN) → Phase 2 (Diffusion Model upgrade).

---

## Preprocessing/Segmentation Rewrite Plan (In Progress, Paused)

Goal: rewrite `testa.py` into two clean, production-quality modules:

- `preprocessing/preprocess.py`
- `segmentation/segment.py`

### Anomalies to Handle
| Problem | Solution |
|---|---|
| Phone camera images | Perspective correction |
| Rotated pages | Automatic deskew |
| Uneven lighting | Illumination normalization |
| Shadows | Background estimation & subtraction |
| Blank pages | Standard thresholding |
| Lined notebooks | Automatic ruled-line detection/removal |
| Graph paper | Horizontal & vertical line suppression |
| Different pen colors | Grayscale + adaptive threshold |
| Thick/thin pens | Stroke-preserving filtering |
| Salt & pepper noise | Connected-component cleanup |
| JPEG artifacts | Bilateral/median filtering |
| Dark borders | Automatic border cropping |
| Low contrast scans | CLAHE |
| Different image sizes | Resolution normalization |

### Planned Pipeline
```
Load Image → Resize → Detect document → Perspective correction → Deskew
→ Border removal → CLAHE → Shadow removal → Noise reduction
→ Adaptive threshold (Sauvola) → Detect page type (blank/ruled/grid)
→ Remove notebook/grid lines if needed → Stroke repair → Final binary image
```

### Proposed Output Structure
```python
@dataclass
class PreprocessResult:
    original: np.ndarray
    corrected: np.ndarray
    gray: np.ndarray
    binary: np.ndarray
    page_type: str      # blank / ruled / grid
    skew_angle: float
    debug_images: dict
```

### Build Plan (was in progress, not completed)
- **Part 1:** Imports, config dataclasses, utilities, document detection, perspective correction
- **Part 2:** Deskew, illumination correction, CLAHE, shadow removal, denoising
- **Part 3:** Sauvola thresholding, page-type detection, line removal, stroke repair
- **Part 4:** Final orchestration, debug outputs, CLI, documentation

Then repeat the same staged build for `segmentation/segment.py`.

**Status:** conversation was cut off before Part 1 code was delivered (message limit reached on prior session). Full code generation for `preprocess.py` and `segment.py` still needs to be done.
