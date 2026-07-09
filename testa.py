import argparse
import csv
import os

import cv2
import numpy as np
from skimage.filters import threshold_sauvola


# ---------------------------------------------------------------------------
# 1. Preprocessing
# ---------------------------------------------------------------------------

def preprocess(image_path: str) -> np.ndarray:
    """Load image, denoise, and binarize so ink = white(255), background = black(0).

    A *photographed* ruled page (vs. a flatbed scan) usually has an uneven
    light/shadow gradient across it. A single global threshold -- whether
    on grayscale or on color saturation -- can't separate "ink" from
    "shadow" and "paper" everywhere at once, because what counts as "dark"
    or "background-colored" varies from one part of the page to another.

    Sauvola thresholding solves this properly: for every pixel it compares
    local brightness against the mean/std-dev of a window around it, so
    the effective threshold adapts as lighting changes across the page.
    It's the standard technique for binarizing photographed/scanned
    documents with uneven illumination.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # window_size should be a few times the stroke width; k controls how far
    # below the local mean a pixel must be to count as ink (higher = stricter).
    local_thresh = threshold_sauvola(gray, window_size=51, k=0.2)
    binary = ((gray < local_thresh).astype(np.uint8)) * 255

    # Remove small speckle noise (dust, scan artifacts)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    # Ruled notebook lines are long, (near-)horizontal strokes, but a
    # photographed page is rarely perfectly flat -- it usually has a
    # gentle curve/warp, so the lines aren't perfectly straight across
    # the whole width. A single wide morphological kernel assumes a
    # dead-straight run and misses curved lines (and can leave a letter
    # fused to the fragment of line it happens to touch). The probabilistic
    # Hough transform instead finds many short straight *segments*, which
    # together trace a gently curved line just fine, so it copes with the
    # warp and still leaves individual letters alone.
    line_segments = cv2.HoughLinesP(
        binary, 1, np.pi / 360, threshold=80, minLineLength=200, maxLineGap=30
    )
    if line_segments is not None:
        line_mask = np.zeros_like(binary)
        for seg in line_segments:
            x1, y1, x2, y2 = seg[0]
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if angle < 10 or angle > 170:  # keep only near-horizontal segments
                cv2.line(line_mask, (x1, y1), (x2, y2), 255, thickness=6)
        binary = cv2.subtract(binary, line_mask)

    # Subtracting the ruled lines can leave tiny notches where a letter
    # stroke crossed a line; close them back up so characters stay whole.
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel)

    return binary


# ---------------------------------------------------------------------------
# 2. Character-shaped component detection (contour-based, with diacritic merge)
# ---------------------------------------------------------------------------

def find_char_boxes(binary: np.ndarray, min_char_area: int = 20,
                     max_flat_aspect: float = 3.0):
    """
    Find individual character-shaped components anywhere in the (whole-page)
    binary image. Merges small blobs (dots on i/j, crossbars) into the
    nearest stem below/above them so they don't get saved as orphan
    fragments.

    Also rejects "flat" blobs that are much wider than they are tall
    (width > max_flat_aspect * height). Real letters (even wide ones like
    'm' or 'w') don't get anywhere near that flat; leftover fragments of
    ruled notebook lines do, so this filters them out without needing
    line-removal in preprocess() to be pixel-perfect.
    """
    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w * h < min_char_area:
            continue
        if h > 0 and w > max_flat_aspect * h:
            continue
        boxes.append([x, y, w, h])

    if not boxes:
        return []

    boxes.sort(key=lambda b: b[0])  # left to right

    heights = [b[3] for b in boxes]
    median_h = np.median(heights) if heights else 0

    merged = []
    used = [False] * len(boxes)

    for i, box in enumerate(boxes):
        if used[i]:
            continue
        x, y, w, h = box
        is_small = h < median_h * 0.45 and w < median_h * 0.6

        if is_small:
            best_j, best_dist = None, float("inf")
            for j, other in enumerate(boxes):
                if i == j or used[j]:
                    continue
                ox, oy, ow, oh = other
                overlap = min(x + w, ox + ow) - max(x, ox)
                if overlap > 0:
                    dist = abs(y - oy)
                    if dist < best_dist:
                        best_dist = dist
                        best_j = j

            if best_j is not None:
                ox, oy, ow, oh = boxes[best_j]
                nx = min(x, ox)
                ny = min(y, oy)
                nx2 = max(x + w, ox + ow)
                ny2 = max(y + h, oy + oh)
                merged.append([nx, ny, nx2 - nx, ny2 - ny])
                used[i] = True
                used[best_j] = True
                continue

        merged.append(box)
        used[i] = True

    return merged


# ---------------------------------------------------------------------------
# 3. Group character boxes into text lines and words by position
# ---------------------------------------------------------------------------

def group_into_lines(boxes, gap_factor: float = 1.2):
    """
    Cluster character boxes into text lines by their vertical position.

    This works directly off the character-shaped components found by
    find_char_boxes() rather than a raw row-by-row ink projection. That
    matters on photographed (not scanned) pages: a handful of stray noise
    pixels surviving in a heavily-shadowed row can keep a naive row
    projection from ever seeing a "gap", silently merging several real
    lines into one. Clustering the already-filtered character boxes
    instead is robust to that, since the noise was already screened out
    by find_char_boxes()'s size/shape filters.

    Boxes are sorted by vertical center, then a new line starts whenever
    the gap to the next box's vertical center exceeds gap_factor times the
    median character height (so the threshold scales with handwriting
    size instead of being a fixed pixel count).
    """
    if not boxes:
        return []

    heights = [b[3] for b in boxes]
    median_h = np.median(heights)
    gap_threshold = max(median_h * gap_factor, 10)

    by_y = sorted(boxes, key=lambda b: b[1] + b[3] / 2)

    lines = [[by_y[0]]]
    prev_center = by_y[0][1] + by_y[0][3] / 2
    for box in by_y[1:]:
        center = box[1] + box[3] / 2
        if center - prev_center > gap_threshold:
            lines.append([])
        lines[-1].append(box)
        prev_center = center

    # Within each line, order left to right and split into words by x-gap.
    result = []
    for line_boxes in lines:
        line_boxes.sort(key=lambda b: b[0])
        widths = [b[2] for b in line_boxes]
        median_w = np.median(widths)
        word_gap = max(median_w * 1.5, 15)

        words = [[line_boxes[0]]]
        prev_right = line_boxes[0][0] + line_boxes[0][2]
        for box in line_boxes[1:]:
            if box[0] - prev_right > word_gap:
                words.append([])
            words[-1].append(box)
            prev_right = box[0] + box[2]

        result.append(words)

    return result


# ---------------------------------------------------------------------------
# 5. Cropping + saving as transparent PNG
# ---------------------------------------------------------------------------

def save_character_png(binary_full: np.ndarray, box, out_path: str, padding: int = 4):
    """Crop a character from the binary (ink=white) image and save as a
    transparent PNG (alpha channel = ink mask), ready for compositing later."""
    x, y, w, h = box
    x0 = max(x - padding, 0)
    y0 = max(y - padding, 0)
    x1 = min(x + w + padding, binary_full.shape[1])
    y1 = min(y + h + padding, binary_full.shape[0])

    crop = binary_full[y0:y1, x0:x1]

    rgba = np.zeros((crop.shape[0], crop.shape[1], 4), dtype=np.uint8)
    rgba[..., 0] = 20   # R
    rgba[..., 1] = 20   # G
    rgba[..., 2] = 20   # B  (near-black ink; tweak per pen color later)
    rgba[..., 3] = crop  # alpha channel follows the ink mask

    cv2.imwrite(out_path, rgba)


# ---------------------------------------------------------------------------
# 6. Full pipeline
# ---------------------------------------------------------------------------

def segment_handwriting(image_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    binary = preprocess(image_path)

    char_boxes = find_char_boxes(binary)
    lines = group_into_lines(char_boxes)
    print(f"Detected {len(lines)} line(s) of text.")

    manifest_rows = []

    for line_idx, words in enumerate(lines, start=1):
        for word_idx, word_boxes in enumerate(words, start=1):
            for char_idx, (cx, cy, cw, ch) in enumerate(word_boxes, start=1):
                abs_box = (cx, cy, cw, ch)

                filename = f"line{line_idx:02d}_word{word_idx:02d}_char{char_idx:02d}.png"
                out_path = os.path.join(output_dir, filename)

                save_character_png(binary, abs_box, out_path)

                manifest_rows.append({
                    "filename": filename,
                    "line": line_idx,
                    "word": word_idx,
                    "char_index_in_word": char_idx,
                    "x": abs_box[0],
                    "y": abs_box[1],
                    "width": abs_box[2],
                    "height": abs_box[3],
                })

    manifest_path = os.path.join(output_dir, "manifest.csv")
    with open(manifest_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["filename", "line", "word", "char_index_in_word",
                        "x", "y", "width", "height"],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Saved {len(manifest_rows)} character images to '{output_dir}'.")
    print(f"Manifest written to '{manifest_path}'.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Segment handwriting image into character PNGs.")
    parser.add_argument("--input", required=True, help="Path to the handwriting image.")
    parser.add_argument("--output_dir", default="./chars", help="Directory to save character PNGs + manifest.")
    args = parser.parse_args()

    segment_handwriting(args.input, args.output_dir)