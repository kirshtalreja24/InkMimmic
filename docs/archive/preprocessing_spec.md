# Image Preprocessing Module — `preprocessing/preprocess.py`

## Purpose
Take a raw handwriting image (phone photo or scan) and produce a clean, normalized binary image ready for segmentation. This is the first stage of the handwriting synthesis pipeline (PRD Step 2).

## Input
- Raw image: phone camera photo or scanned page
- May be: blank page, ruled notebook, grid/graph paper
- May have: skew, shadows, uneven lighting, noise, borders

## Output — `PreprocessResult`
```python
@dataclass
class PreprocessResult:
    original: np.ndarray       # untouched input
    corrected: np.ndarray      # after perspective + deskew
    gray: np.ndarray           # grayscale version
    binary: np.ndarray         # final clean binary image (input to segmentation)
    page_type: str             # "blank" | "ruled" | "grid"
    skew_angle: float          # degrees corrected
    debug_images: dict         # intermediate stages, keyed by step name
```

## Anomalies to Handle

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

## Pipeline (Order of Operations)
```
1. Load image
2. Resize (normalize resolution)
3. Detect document boundary
4. Perspective correction
5. Deskew
6. Border removal
7. CLAHE (contrast enhancement)
8. Shadow removal
9. Noise reduction (bilateral/median filter)
10. Adaptive threshold (Sauvola)
11. Detect page type (blank / ruled / grid)
12. Remove ruled/grid lines if detected
13. Stroke repair (fill gaps, preserve thickness)
14. Output final binary image
```

## Functions to Implement

| Function | Responsibility |
|---|---|
| `load_image(path)` | Read image from disk, validate |
| `resize_image(img, target)` | Normalize resolution |
| `detect_document(img)` | Find page edges/contour |
| `correct_perspective(img, corners)` | Warp to top-down view |
| `deskew(img)` | Estimate & correct rotation angle |
| `remove_borders(img)` | Crop dark/scanner-edge borders |
| `apply_clahe(img)` | Local contrast enhancement |
| `remove_shadows(img)` | Background estimation & subtraction |
| `denoise(img)` | Bilateral/median filtering |
| `sauvola_threshold(img)` | Adaptive binarization |
| `detect_page_type(img)` | Classify blank / ruled / grid |
| `remove_ruled_lines(img)` | Detect & erase horizontal ruling |
| `remove_grid_lines(img)` | Detect & erase grid lines |
| `repair_strokes(img)` | Morphological cleanup of broken strokes |
| `preprocess(path, config) -> PreprocessResult` | Orchestrates full pipeline |

## Configuration Object (proposed)
```python
@dataclass
class PreprocessConfig:
    target_width: int = 2000
    apply_perspective_correction: bool = True
    apply_deskew: bool = True
    apply_clahe: bool = True
    clahe_clip_limit: float = 2.0
    denoise_strength: int = 9
    sauvola_window: int = 25
    sauvola_k: float = 0.2
    auto_detect_lines: bool = True
    save_debug_images: bool = False
```

## CLI (proposed)
```bash
python preprocess.py --input page.jpg --output_dir processed --debug
```

## Acceptance Criteria
- Works on both phone photos and flat scans
- Correctly detects and removes ruled/grid lines without erasing strokes
- Output binary image has clean, continuous character strokes
- No false-positive line removal on blank pages
- Debug images available for every stage when `--debug` is passed

## Status
Design spec only — implementation not yet written. Next step: implement `preprocess.py` following this spec, section by section (document detection → deskew/illumination → thresholding/line removal → orchestration/CLI).
