

import argparse
import csv
import os

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# 1. Preprocessing
# ---------------------------------------------------------------------------

def preprocess(image_path: str) -> np.ndarray:
    """Load image, denoise, and binarize so ink = white(255), background = black(0)."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # Otsu's threshold, inverted so ink is white on a black background
    _, binary = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    # Remove small speckle noise (dust, scan artifacts)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    return binary


# ---------------------------------------------------------------------------
# 2. Line segmentation (horizontal projection profile)
# ---------------------------------------------------------------------------

def segment_lines(binary: np.ndarray, min_line_height: int = 8, gap_tolerance: int = 3):
    """Return list of (y_start, y_end) for each detected line of text."""
    row_has_ink = np.sum(binary, axis=1) > 0

    lines = []
    in_line = False
    start = 0
    gap_count = 0

    for y, has_ink in enumerate(row_has_ink):
        if has_ink:
            if not in_line:
                start = y
                in_line = True
            gap_count = 0
        else:
            if in_line:
                gap_count += 1
                if gap_count > gap_tolerance:
                    end = y - gap_count + 1
                    if end - start >= min_line_height:
                        lines.append((max(start - 2, 0), min(end + 2, binary.shape[0])))
                    in_line = False
                    gap_count = 0

    if in_line:
        end = len(row_has_ink)
        if end - start >= min_line_height:
            lines.append((max(start - 2, 0), min(end + 2, binary.shape[0])))

    return lines


# ---------------------------------------------------------------------------
# 3. Word segmentation within a line (vertical projection, bigger gaps = word break)
# ---------------------------------------------------------------------------

def segment_words(line_img: np.ndarray, word_gap_threshold: int = 15):
    """Return list of (x_start, x_end) for each word in a line image."""
    col_has_ink = np.sum(line_img, axis=0) > 0

    runs = []
    in_run = False
    start = 0
    for x, has_ink in enumerate(col_has_ink):
        if has_ink and not in_run:
            start = x
            in_run = True
        elif not has_ink and in_run:
            runs.append((start, x))
            in_run = False
    if in_run:
        runs.append((start, len(col_has_ink)))

    if not runs:
        return []

    # Merge runs into words based on gap size
    words = [list(runs[0])]
    for (s, e) in runs[1:]:
        prev_end = words[-1][1]
        if s - prev_end <= word_gap_threshold:
            words[-1][1] = e
        else:
            words.append([s, e])

    return [tuple(w) for w in words]


# ---------------------------------------------------------------------------
# 4. Character segmentation within a word (contour-based, with diacritic merge)
# ---------------------------------------------------------------------------

def segment_characters(word_img: np.ndarray, min_char_area: int = 20):
    """
    Find individual character contours within a word image.
    Merges small blobs (dots on i/j, crossbars) into the nearest stem below/above
    them so they don't get saved as orphan fragments.
    """
    contours, _ = cv2.findContours(
        word_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w * h >= min_char_area:
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

    merged.sort(key=lambda b: b[0])
    return merged


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

    lines = segment_lines(binary)
    print(f"Detected {len(lines)} line(s) of text.")

    manifest_rows = []

    for line_idx, (y0, y1) in enumerate(lines, start=1):
        line_img = binary[y0:y1, :]
        words = segment_words(line_img)

        for word_idx, (x0, x1) in enumerate(words, start=1):
            word_img = line_img[:, x0:x1]
            chars = segment_characters(word_img)

            for char_idx, (cx, cy, cw, ch) in enumerate(chars, start=1):
                abs_box = (x0 + cx, y0 + cy, cw, ch)

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