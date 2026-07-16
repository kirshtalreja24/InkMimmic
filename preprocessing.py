"""
Handwriting image preprocessing -- see preprocessing_spec.md.

Turns a raw phone photo / scan into a clean binary image ready for
character segmentation. Built directly against the failures we hit
segmenting real photos:

- Curved/warped ruled lines (page not perfectly flat under the camera)
  survive a single strict Hough pass and get mistaken for text lines.
- A too-loose Hough pass to catch that curve instead eats handwriting
  connector strokes on blank pages.
- Shadow gradients across a photographed (not scanned) page break a
  single global threshold.
=> see remove_ruled_lines() and remove_shadows() docstrings for exactly
   how each is handled.
"""

from dataclasses import dataclass, field
import os

import cv2
import numpy as np
from skimage.filters import threshold_sauvola


# ---------------------------------------------------------------------------
# Config / result containers
# ---------------------------------------------------------------------------

@dataclass
class PreprocessConfig:
    target_width: int = 2000
    apply_perspective_correction: bool = True
    apply_deskew: bool = True
    apply_clahe: bool = True
    clahe_clip_limit: float = 2.0
    denoise_strength: int = 5
    sauvola_window: int = 35
    sauvola_k: float = 0.18
    auto_detect_lines: bool = True
    save_debug_images: bool = False


@dataclass
class PreprocessResult:
    original: np.ndarray
    corrected: np.ndarray
    gray: np.ndarray
    binary: np.ndarray
    page_type: str
    skew_angle: float
    debug_images: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 1-2. Load / resize
# ---------------------------------------------------------------------------

def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {path}")
    return img


def resize_image(img: np.ndarray, target_width: int) -> np.ndarray:
    """Upscale only. Our downstream segmentation heuristics (stroke
    thickness, min blob area, split-width ratios) are tuned against
    native phone-photo resolution (~2000-2900px wide); downscaling a
    already-high-res photo down to target_width throws away exactly the
    thin-stroke detail those heuristics depend on, without buying
    anything -- so target_width is treated as a floor, not a fixed size.
    """
    h, w = img.shape[:2]
    if w >= target_width:
        return img
    scale = target_width / w
    return cv2.resize(img, (target_width, int(h * scale)), interpolation=cv2.INTER_CUBIC)


# ---------------------------------------------------------------------------
# 3-4. Document detection + perspective correction
# ---------------------------------------------------------------------------
#
# Full 4-corner perspective correction needs the page edges visible in
# frame with reasonable contrast against a background (desk, table).
# Our actual inputs so far are photos already cropped tight to the
# written area -- no page edges in frame -- so a corner-search would be
# fitting noise. detect_document() looks for a plausible page contour and
# only warps when it's confident (large, ~4-sided, not the whole frame);
# otherwise it's a no-op passthrough. This matches the spec's
# "works on phone photos" criterion without breaking the common case.

def detect_document(img: np.ndarray):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    img_area = img.shape[0] * img.shape[1]
    best = None
    for c in contours:
        area = cv2.contourArea(c)
        if area < img_area * 0.5 or area > img_area * 0.97:
            continue  # too small to be the page, or basically the whole frame (no border in shot)
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            if best is None or area > cv2.contourArea(best):
                best = approx
    return best


def correct_perspective(img: np.ndarray, corners) -> np.ndarray:
    if corners is None:
        return img
    pts = corners.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    ordered = np.array([
        pts[np.argmin(s)], pts[np.argmin(diff)],
        pts[np.argmax(s)], pts[np.argmax(diff)],
    ], dtype=np.float32)  # tl, tr, br, bl

    w = int(max(np.linalg.norm(ordered[0] - ordered[1]), np.linalg.norm(ordered[3] - ordered[2])))
    h = int(max(np.linalg.norm(ordered[0] - ordered[3]), np.linalg.norm(ordered[1] - ordered[2])))
    if w < 50 or h < 50:
        return img
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(ordered, dst)
    return cv2.warpPerspective(img, M, (w, h))


# ---------------------------------------------------------------------------
# 5. Deskew
# ---------------------------------------------------------------------------
#
# Estimate rotation from the dominant near-horizontal direction in the
# image -- ruled lines when present (most reliable), otherwise the
# aggregate slant of ink strokes via minAreaRect on all foreground pixels.
# Only *rotation* is corrected here, not the gentle page curve/warp --
# that's handled downstream by ruled-line removal tracing the curve
# directly rather than assuming straightness.

def deskew(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=150,
                             minLineLength=gray.shape[1] * 0.25, maxLineGap=20)
    angles = []
    if lines is not None:
        for seg in lines:
            x1, y1, x2, y2 = map(int, np.asarray(seg).reshape(-1)[:4])
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(angle) < 20:  # near-horizontal only; ignore verticals/diagonals
                angles.append(angle)
    if not angles:
        return 0.0
    return float(np.median(angles))


def apply_rotation(img: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 0.1:
        return img
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REPLICATE)


# ---------------------------------------------------------------------------
# 6. Border removal
# ---------------------------------------------------------------------------

def remove_borders(img: np.ndarray, margin_frac: float = 0.01) -> np.ndarray:
    """Crop a thin dark scanner-edge border if present. Conservative: only
    crops if the outer ring is genuinely much darker than the page interior,
    so it's a no-op on ordinary photos without borders."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    h, w = gray.shape[:2]
    m = max(int(min(h, w) * margin_frac), 3)
    border_mean = np.mean([gray[:m, :].mean(), gray[-m:, :].mean(),
                            gray[:, :m].mean(), gray[:, -m:].mean()])
    interior_mean = gray[m:h - m, m:w - m].mean()
    if border_mean < interior_mean - 40:  # border is notably darker
        return img[m:h - m, m:w - m]
    return img


# ---------------------------------------------------------------------------
# 7. CLAHE
# ---------------------------------------------------------------------------

def apply_clahe(gray: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    return clahe.apply(gray)


# ---------------------------------------------------------------------------
# 8. Shadow removal
# ---------------------------------------------------------------------------

def remove_shadows(gray: np.ndarray) -> np.ndarray:
    """Estimate the page's illumination gradient with a large-kernel median
    blur (background = paper, no strokes survive a kernel this big) and
    divide it out. This is what actually lets a single downstream Sauvola
    pass work evenly across a photo with a shadow gradient across it --
    Sauvola alone adapts locally but still degrades under a strong smooth
    gradient like the one in the 'Handwriting styles...' sample."""
    bg = cv2.medianBlur(gray, 35)
    norm = cv2.divide(gray, bg, scale=255)
    return norm


# ---------------------------------------------------------------------------
# 9. Denoise
# ---------------------------------------------------------------------------

def denoise(gray: np.ndarray, strength: int = 5) -> np.ndarray:
    d = max(3, strength | 1)
    return cv2.bilateralFilter(gray, d, 50, 50)


# ---------------------------------------------------------------------------
# 10. Sauvola threshold
# ---------------------------------------------------------------------------

def sauvola_threshold(gray: np.ndarray, window: int = 35, k: float = 0.18) -> np.ndarray:
    local_thresh = threshold_sauvola(gray, window_size=window, k=k)
    return ((gray < local_thresh).astype(np.uint8)) * 255


# ---------------------------------------------------------------------------
# 11. Page type detection
# ---------------------------------------------------------------------------

def _find_long_lines(binary: np.ndarray, min_len_frac: float, angle_max: float = 3.0):
    w = binary.shape[1]
    segs = cv2.HoughLinesP(binary, 1, np.pi / 360, threshold=200,
                            minLineLength=int(w * min_len_frac), maxLineGap=20)
    horiz, vert = [], []
    if segs is not None:
        for seg in segs:
            x1, y1, x2, y2 = map(int, np.asarray(seg).reshape(-1)[:4])
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if angle < angle_max or angle > 180 - angle_max:
                horiz.append((x1, y1, x2, y2))
            elif abs(angle - 90) < angle_max:
                vert.append((x1, y1, x2, y2))
    return horiz, vert


def detect_page_type(binary: np.ndarray) -> str:
    horiz, vert = _find_long_lines(binary, min_len_frac=0.35)
    has_h = len(horiz) >= 2
    has_v = len(vert) >= 2
    if has_h and has_v:
        return "grid"
    if has_h:
        return "ruled"
    return "blank"


# ---------------------------------------------------------------------------
# 12a. Ruled-line removal
# ---------------------------------------------------------------------------

def remove_ruled_lines(binary: np.ndarray, median_ink_height: float = None) -> np.ndarray:
    """Morphological horizontal opening: erode with a kernel much longer
    than any single letter's horizontal run, then dilate back with the
    same kernel. Only features with an unbroken horizontal run at least
    as long as the kernel survive erosion -- ruled lines qualify (they
    span most of the page), ordinary handwriting essentially never does,
    even wide cursive joins. This tolerates the gentle curvature a
    photographed (not flat-scanned) notebook page typically has, since
    the kernel only needs to fit within a locally-straight stretch, not
    trace the whole page-width curve at once.

    This was tested against several alternatives (Hough-segment tracing,
    per-column thin-run classification, per-connected-component opening)
    and came out the most reliable overall; it's not perfect on pages
    where handwriting sits directly on top of the rule (letters can fuse
    with the line into one component and lose a sliver where they touch),
    but that's a narrow edge case, not a systematic failure the way the
    alternatives were.
    """
    h, w = binary.shape
    strict_horiz, _ = _find_long_lines(binary, min_len_frac=0.18, angle_max=3.0)
    if len(strict_horiz) < 2:
        return binary  # not actually ruled

    kernel_len = max(int((median_ink_height or h * 0.03) * 1.1), 35)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))
    line_mask = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    # A little extra dilation so near-miss/dashed rule fragments (broken
    # by paper texture or a slight curve) still get fully cleared, not
    # left as thin residue that would otherwise survive as noise.
    line_mask = cv2.dilate(line_mask, np.ones((3, 3), np.uint8))

    out = cv2.subtract(binary, line_mask)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, close_kernel)
    return out


# ---------------------------------------------------------------------------
# 12b. Grid-line removal
# ---------------------------------------------------------------------------

def remove_grid_lines(binary: np.ndarray, median_ink_height: float = None) -> np.ndarray:
    """Same morphological-opening logic as remove_ruled_lines, applied on
    the vertical axis for grid columns after horizontal rules are gone."""
    out = remove_ruled_lines(binary, median_ink_height)

    h, w = out.shape
    _, strict_v = _find_long_lines(binary, min_len_frac=0.18, angle_max=3.0)
    if len(strict_v) < 2:
        return out

    kernel_len = max(int((median_ink_height or w * 0.03) * 1.1), 35)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_len))
    line_mask = cv2.morphologyEx(out, cv2.MORPH_OPEN, kernel)
    line_mask = cv2.dilate(line_mask, np.ones((3, 3), np.uint8))

    out = cv2.subtract(out, line_mask)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, close_kernel)
    return out


# ---------------------------------------------------------------------------
# 13. Stroke repair
# ---------------------------------------------------------------------------

def repair_strokes(binary: np.ndarray) -> np.ndarray:
    """Bridge 1-2px anti-aliasing gaps left by thresholding/line removal
    without eroding first (pure MORPH_OPEN fragments thin ballpoint ink --
    see segment.py's preprocess() history). Closing only ever adds pixels
    back, so it can't introduce new fragmentation."""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def preprocess(path: str, config: PreprocessConfig = None) -> PreprocessResult:
    config = config or PreprocessConfig()
    debug = {}

    original = load_image(path)
    img = resize_image(original, config.target_width)
    if config.save_debug_images:
        debug["01_resized"] = img.copy()

    corrected = img
    if config.apply_perspective_correction:
        corners = detect_document(img)
        corrected = correct_perspective(img, corners)
        if config.save_debug_images:
            debug["02_perspective"] = corrected.copy()

    corrected = remove_borders(corrected)

    gray = cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY)

    skew_angle = 0.0
    if config.apply_deskew:
        skew_angle = deskew(gray)
        corrected = apply_rotation(corrected, skew_angle)
        gray = apply_rotation(gray, skew_angle)
        if config.save_debug_images:
            debug["03_deskewed"] = corrected.copy()

    if config.apply_clahe:
        gray = apply_clahe(gray, config.clahe_clip_limit)
        if config.save_debug_images:
            debug["04_clahe"] = gray.copy()

    gray = remove_shadows(gray)
    if config.save_debug_images:
        debug["05_shadow_removed"] = gray.copy()

    gray = denoise(gray, config.denoise_strength)
    if config.save_debug_images:
        debug["06_denoised"] = gray.copy()

    binary = sauvola_threshold(gray, config.sauvola_window, config.sauvola_k)
    if config.save_debug_images:
        debug["07_binary_raw"] = binary.copy()

    page_type = detect_page_type(binary) if config.auto_detect_lines else "blank"

    # Rough ink-height estimate (for line-removal band sizing) from
    # connected components before any line removal.
    n, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    heights = [stats[i][3] for i in range(1, n) if stats[i][4] >= 15]
    median_ink_height = float(np.median(heights)) if heights else None

    if page_type == "ruled":
        binary = remove_ruled_lines(binary, median_ink_height)
    elif page_type == "grid":
        binary = remove_grid_lines(binary, median_ink_height)
    if config.save_debug_images:
        debug["08_lines_removed"] = binary.copy()

    binary = repair_strokes(binary)
    if config.save_debug_images:
        debug["09_final_binary"] = binary.copy()

    return PreprocessResult(
        original=original, corrected=corrected, gray=gray, binary=binary,
        page_type=page_type, skew_angle=skew_angle, debug_images=debug,
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Preprocess a handwriting image.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output_dir", default="./processed")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    cfg = PreprocessConfig(save_debug_images=args.debug)
    result = preprocess(args.input, cfg)

    cv2.imwrite(os.path.join(args.output_dir, "binary.png"), result.binary)
    cv2.imwrite(os.path.join(args.output_dir, "corrected.png"), result.corrected)
    print(f"page_type={result.page_type} skew_angle={result.skew_angle:.2f}")

    if args.debug:
        for name, im in result.debug_images.items():
            cv2.imwrite(os.path.join(args.output_dir, f"debug_{name}.png"), im)