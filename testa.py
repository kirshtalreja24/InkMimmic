# # import argparse
# # import csv
# # import os

# # import cv2
# # import numpy as np
# # from skimage.filters import threshold_sauvola


# # # ---------------------------------------------------------------------------
# # # 1. Preprocessing
# # # ---------------------------------------------------------------------------

# # def preprocess(image_path: str) -> np.ndarray:
# #     """Load image, denoise, and binarize so ink = white(255), background = black(0).

# #     A *photographed* ruled page (vs. a flatbed scan) usually has an uneven
# #     light/shadow gradient across it. A single global threshold -- whether
# #     on grayscale or on color saturation -- can't separate "ink" from
# #     "shadow" and "paper" everywhere at once, because what counts as "dark"
# #     or "background-colored" varies from one part of the page to another.

# #     Sauvola thresholding solves this properly: for every pixel it compares
# #     local brightness against the mean/std-dev of a window around it, so
# #     the effective threshold adapts as lighting changes across the page.
# #     It's the standard technique for binarizing photographed/scanned
# #     documents with uneven illumination.
# #     """
# #     img = cv2.imread(image_path)
# #     if img is None:
# #         raise FileNotFoundError(f"Could not read image: {image_path}")

# #     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# #     gray = cv2.GaussianBlur(gray, (3, 3), 0)

# #     # window_size should be a few times the stroke width; k controls how far
# #     # below the local mean a pixel must be to count as ink (higher = stricter).
# #     local_thresh = threshold_sauvola(gray, window_size=51, k=0.2)
# #     binary = ((gray < local_thresh).astype(np.uint8)) * 255

# #     # Remove small speckle noise (dust, scan artifacts)
# #     kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
# #     binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

# #     # Ruled notebook lines are long, (near-)horizontal strokes, but a
# #     # photographed page is rarely perfectly flat -- it usually has a
# #     # gentle curve/warp, so the lines aren't perfectly straight across
# #     # the whole width. A single wide morphological kernel assumes a
# #     # dead-straight run and misses curved lines (and can leave a letter
# #     # fused to the fragment of line it happens to touch). The probabilistic
# #     # Hough transform instead finds many short straight *segments*, which
# #     # together trace a gently curved line just fine, so it copes with the
# #     # warp and still leaves individual letters alone.
# #     line_segments = cv2.HoughLinesP(
# #         binary, 1, np.pi / 360, threshold=80, minLineLength=200, maxLineGap=30
# #     )
# #     if line_segments is not None:
# #         line_mask = np.zeros_like(binary)
# #         for seg in line_segments:
# #             pts = np.asarray(seg).reshape(-1)
# #             if len(pts) < 4:
# #                 continue
# #             x1, y1, x2, y2 = map(int, pts[:4])
# #             angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
# #             if angle < 10 or angle > 170:  # keep only near-horizontal segments
# #                 cv2.line(line_mask, (x1, y1), (x2, y2), 255, thickness=6)
# #         binary = cv2.subtract(binary, line_mask)

# #     # Subtracting the ruled lines can leave tiny notches where a letter
# #     # stroke crossed a line; close them back up so characters stay whole.
# #     close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
# #     binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel)

# #     return binary


# # # ---------------------------------------------------------------------------
# # # 2. Character-shaped component detection (contour-based, with diacritic merge)
# # # ---------------------------------------------------------------------------

# # def find_char_boxes(binary: np.ndarray, min_char_area: int = 20,
# #                      max_flat_aspect: float = 3.0):
# #     """
# #     Find individual character-shaped components anywhere in the (whole-page)
# #     binary image. Merges small blobs (dots on i/j, crossbars) into the
# #     nearest stem below/above them so they don't get saved as orphan
# #     fragments.

# #     Also rejects "flat" blobs that are much wider than they are tall
# #     (width > max_flat_aspect * height). Real letters (even wide ones like
# #     'm' or 'w') don't get anywhere near that flat; leftover fragments of
# #     ruled notebook lines do, so this filters them out without needing
# #     line-removal in preprocess() to be pixel-perfect.
# #     """
# #     contours, _ = cv2.findContours(
# #         binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
# #     )

# #     boxes = []
# #     for c in contours:
# #         x, y, w, h = cv2.boundingRect(c)
# #         if w * h < min_char_area:
# #             continue
# #         if h > 0 and w > max_flat_aspect * h:
# #             continue
# #         boxes.append([x, y, w, h])

# #     if not boxes:
# #         return []

# #     boxes.sort(key=lambda b: b[0])  # left to right

# #     heights = [b[3] for b in boxes]
# #     median_h = np.median(heights) if heights else 0

# #     merged = []
# #     used = [False] * len(boxes)

# #     for i, box in enumerate(boxes):
# #         if used[i]:
# #             continue
# #         x, y, w, h = box
# #         is_small = h < median_h * 0.45 and w < median_h * 0.6

# #         if is_small:
# #             best_j, best_dist = None, float("inf")
# #             for j, other in enumerate(boxes):
# #                 if i == j or used[j]:
# #                     continue
# #                 ox, oy, ow, oh = other
# #                 overlap = min(x + w, ox + ow) - max(x, ox)
# #                 if overlap > 0:
# #                     dist = abs(y - oy)
# #                     if dist < best_dist:
# #                         best_dist = dist
# #                         best_j = j

# #             if best_j is not None:
# #                 ox, oy, ow, oh = boxes[best_j]
# #                 nx = min(x, ox)
# #                 ny = min(y, oy)
# #                 nx2 = max(x + w, ox + ow)
# #                 ny2 = max(y + h, oy + oh)
# #                 merged.append([nx, ny, nx2 - nx, ny2 - ny])
# #                 used[i] = True
# #                 used[best_j] = True
# #                 continue

# #         merged.append(box)
# #         used[i] = True

# #     return merged


# # # ---------------------------------------------------------------------------
# # # 3. Group character boxes into text lines and words by position
# # # ---------------------------------------------------------------------------

# # def group_into_lines(boxes, gap_factor: float = 1.2):
# #     """
# #     Cluster character boxes into text lines by their vertical position.

# #     This works directly off the character-shaped components found by
# #     find_char_boxes() rather than a raw row-by-row ink projection. That
# #     matters on photographed (not scanned) pages: a handful of stray noise
# #     pixels surviving in a heavily-shadowed row can keep a naive row
# #     projection from ever seeing a "gap", silently merging several real
# #     lines into one. Clustering the already-filtered character boxes
# #     instead is robust to that, since the noise was already screened out
# #     by find_char_boxes()'s size/shape filters.

# #     Boxes are sorted by vertical center, then a new line starts whenever
# #     the gap to the next box's vertical center exceeds gap_factor times the
# #     median character height (so the threshold scales with handwriting
# #     size instead of being a fixed pixel count).
# #     """
# #     if not boxes:
# #         return []

# #     heights = [b[3] for b in boxes]
# #     median_h = np.median(heights)
# #     gap_threshold = max(median_h * gap_factor, 10)

# #     by_y = sorted(boxes, key=lambda b: b[1] + b[3] / 2)

# #     lines = [[by_y[0]]]
# #     prev_center = by_y[0][1] + by_y[0][3] / 2
# #     for box in by_y[1:]:
# #         center = box[1] + box[3] / 2
# #         if center - prev_center > gap_threshold:
# #             lines.append([])
# #         lines[-1].append(box)
# #         prev_center = center

# #     # Within each line, order left to right and split into words by x-gap.
# #     result = []
# #     for line_boxes in lines:
# #         line_boxes.sort(key=lambda b: b[0])
# #         widths = [b[2] for b in line_boxes]
# #         median_w = np.median(widths)
# #         word_gap = max(median_w * 1.5, 15)

# #         words = [[line_boxes[0]]]
# #         prev_right = line_boxes[0][0] + line_boxes[0][2]
# #         for box in line_boxes[1:]:
# #             if box[0] - prev_right > word_gap:
# #                 words.append([])
# #             words[-1].append(box)
# #             prev_right = box[0] + box[2]

# #         result.append(words)

# #     return result


# # # ---------------------------------------------------------------------------
# # # 5. Cropping + saving as transparent PNG
# # # ---------------------------------------------------------------------------

# # def save_character_png(binary_full: np.ndarray, box, out_path: str, padding: int = 4):
# #     """Crop a character from the binary (ink=white) image and save as a
# #     transparent PNG (alpha channel = ink mask), ready for compositing later."""
# #     x, y, w, h = box
# #     x0 = max(x - padding, 0)
# #     y0 = max(y - padding, 0)
# #     x1 = min(x + w + padding, binary_full.shape[1])
# #     y1 = min(y + h + padding, binary_full.shape[0])

# #     crop = binary_full[y0:y1, x0:x1]

# #     rgba = np.zeros((crop.shape[0], crop.shape[1], 4), dtype=np.uint8)
# #     rgba[..., 0] = 20   # R
# #     rgba[..., 1] = 20   # G
# #     rgba[..., 2] = 20   # B  (near-black ink; tweak per pen color later)
# #     rgba[..., 3] = crop  # alpha channel follows the ink mask

# #     cv2.imwrite(out_path, rgba)


# # # ---------------------------------------------------------------------------
# # # 6. Full pipeline
# # # ---------------------------------------------------------------------------

# # def segment_handwriting(image_path: str, output_dir: str):
# #     os.makedirs(output_dir, exist_ok=True)
# #     binary = preprocess(image_path)

# #     char_boxes = find_char_boxes(binary)
# #     lines = group_into_lines(char_boxes)
# #     print(f"Detected {len(lines)} line(s) of text.")

# #     manifest_rows = []

# #     for line_idx, words in enumerate(lines, start=1):
# #         for word_idx, word_boxes in enumerate(words, start=1):
# #             for char_idx, (cx, cy, cw, ch) in enumerate(word_boxes, start=1):
# #                 abs_box = (cx, cy, cw, ch)

# #                 filename = f"line{line_idx:02d}_word{word_idx:02d}_char{char_idx:02d}.png"
# #                 out_path = os.path.join(output_dir, filename)

# #                 save_character_png(binary, abs_box, out_path)

# #                 manifest_rows.append({
# #                     "filename": filename,
# #                     "line": line_idx,
# #                     "word": word_idx,
# #                     "char_index_in_word": char_idx,
# #                     "x": abs_box[0],
# #                     "y": abs_box[1],
# #                     "width": abs_box[2],
# #                     "height": abs_box[3],
# #                 })

# #     manifest_path = os.path.join(output_dir, "manifest.csv")
# #     with open(manifest_path, "w", newline="") as f:
# #         writer = csv.DictWriter(
# #             f,
# #             fieldnames=["filename", "line", "word", "char_index_in_word",
# #                         "x", "y", "width", "height"],
# #         )
# #         writer.writeheader()
# #         writer.writerows(manifest_rows)

# #     print(f"Saved {len(manifest_rows)} character images to '{output_dir}'.")
# #     print(f"Manifest written to '{manifest_path}'.")


# # # ---------------------------------------------------------------------------
# # # CLI entry point
# # # ---------------------------------------------------------------------------

# # if __name__ == "__main__":
# #     parser = argparse.ArgumentParser(description="Segment handwriting image into character PNGs.")
# #     parser.add_argument("--input", required=True, help="Path to the handwriting image.")
# #     parser.add_argument("--output_dir", default="./chars", help="Directory to save character PNGs + manifest.")
# #     args = parser.parse_args()

# #     segment_handwriting(args.input, args.output_dir)

# import argparse
# import csv
# import os

# import cv2
# import numpy as np
# from skimage.filters import threshold_sauvola


# # ---------------------------------------------------------------------------
# # 1. Preprocessing
# # ---------------------------------------------------------------------------

# def preprocess(image_path: str, remove_ruled_lines: str = "auto"):
#     """Load image, denoise, and binarize so ink = white(255), background = black(0).

#     Two fixes vs. the previous version:

#     1. Ruled-line removal no longer eats handwriting. The old code used
#        minLineLength=200px on a ~2600px-wide photo -- about 7% of the
#        image width. On UNRULED paper, cursive baseline connectors between
#        letters ("th", "ov", "wn"...) are easily 200px long and dead
#        straight, so HoughLinesP was flagging them as "ruled lines" and
#        cv2.subtract() was cutting the very strokes that join letters --
#        actively causing the touching/broken-fragment mess. Ruled-line
#        segments must span most of the page width to be real notebook
#        rules, so the length threshold now scales with image width
#        (40%), and the whole step is skipped unless ruled lines are
#        actually detected (remove_ruled_lines="auto").
#     2. No blind morphological opening. A (2,2) MORPH_OPEN on the whole
#        page erodes thin pen strokes before dilating them back, which
#        reliably punches gaps in fine ballpoint ink and fragments single
#        letters into 2-3 pieces (this is what was happening to "quick").
#        Noise removal is deferred to the component-filtering stage below,
#        where it can be done by connected-component area instead of by
#        eroding every stroke on the page.
#     """
#     img = cv2.imread(image_path)
#     if img is None:
#         raise FileNotFoundError(f"Could not read image: {image_path}")

#     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     gray = cv2.bilateralFilter(gray, 5, 50, 50)  # denoise, keeps stroke edges sharp

#     local_thresh = threshold_sauvola(gray, window_size=35, k=0.18)
#     binary = ((gray < local_thresh).astype(np.uint8)) * 255

#     # Close 1px anti-aliasing gaps WITHOUT eroding first (closing only
#     # ever adds pixels, so it can't fragment a stroke the way open did).
#     close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
#     binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel)

#     img_w = binary.shape[1]
#     min_line_len = int(img_w * 0.4)

#     line_segments = cv2.HoughLinesP(
#         binary, 1, np.pi / 360, threshold=200,
#         minLineLength=min_line_len, maxLineGap=20,
#     )

#     has_ruled_lines = False
#     if line_segments is not None:
#         horiz = 0
#         for seg in line_segments:
#             x1, y1, x2, y2 = map(int, np.asarray(seg).reshape(-1)[:4])
#             angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
#             if angle < 3 or angle > 177:
#                 horiz += 1
#         has_ruled_lines = horiz >= 2  # a couple of full-width straight rules

#     do_remove = (remove_ruled_lines == "always") or (
#         remove_ruled_lines == "auto" and has_ruled_lines
#     )

#     if do_remove and line_segments is not None:
#         line_mask = np.zeros_like(binary)
#         for seg in line_segments:
#             x1, y1, x2, y2 = map(int, np.asarray(seg).reshape(-1)[:4])
#             angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
#             if angle < 3 or angle > 177:
#                 cv2.line(line_mask, (x1, y1), (x2, y2), 255, thickness=4)
#         binary = cv2.subtract(binary, line_mask)
#         binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel)

#     return binary


# # ---------------------------------------------------------------------------
# # 2. Blob detection + diacritic merge (word/ligature-level, not yet chars)
# # ---------------------------------------------------------------------------

# def find_blobs(binary: np.ndarray, min_area: int = 12):
#     """Connected components on the page. On handwriting where letters
#     within a word are pen-joined, one blob here can span several
#     characters ("The", "ow" in "brown") -- that's expected and is what
#     split_into_characters() below is for. This stage only removes
#     speckle noise and re-attaches small marks (dots on i/j, crossbars on
#     t) to the nearest stroke below/above them.
#     """
#     n, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

#     raw = []
#     for i in range(1, n):
#         x, y, w, h, area = stats[i]
#         if area < min_area:
#             continue
#         raw.append([x, y, w, h])

#     if not raw:
#         return []

#     heights = [b[3] for b in raw]
#     median_h = np.median(heights)

#     merged = []
#     used = [False] * len(raw)
#     for i, box in enumerate(raw):
#         if used[i]:
#             continue
#         x, y, w, h = box
#         is_small = h < median_h * 0.45 and w < median_h * 0.6
#         if is_small:
#             best_j, best_dist = None, float("inf")
#             for j, other in enumerate(raw):
#                 if i == j or used[j]:
#                     continue
#                 ox, oy, ow, oh = other
#                 overlap = min(x + w, ox + ow) - max(x, ox)
#                 if overlap > 0:
#                     dist = abs((y + h / 2) - (oy + oh / 2))
#                     if dist < best_dist:
#                         best_dist, best_j = dist, j
#             if best_j is not None:
#                 ox, oy, ow, oh = raw[best_j]
#                 nx, ny = min(x, ox), min(y, oy)
#                 nx2, ny2 = max(x + w, ox + ow), max(y + h, oy + oh)
#                 merged.append([nx, ny, nx2 - nx, ny2 - ny])
#                 used[i] = used[best_j] = True
#                 continue
#         merged.append(box)
#         used[i] = True

#     return merged


# # ---------------------------------------------------------------------------
# # 3. Lines -> words (same clustering idea as before, kept because it works)
# # ---------------------------------------------------------------------------

# def group_into_lines(blobs, gap_factor: float = 1.2):
#     if not blobs:
#         return []

#     heights = [b[3] for b in blobs]
#     median_h = np.median(heights)
#     gap_threshold = max(median_h * gap_factor, 10)

#     by_y = sorted(blobs, key=lambda b: b[1] + b[3] / 2)
#     lines = [[by_y[0]]]
#     prev_center = by_y[0][1] + by_y[0][3] / 2
#     for box in by_y[1:]:
#         center = box[1] + box[3] / 2
#         if center - prev_center > gap_threshold:
#             lines.append([])
#         lines[-1].append(box)
#         prev_center = center

#     result = []
#     for line_boxes in lines:
#         line_boxes.sort(key=lambda b: b[0])
#         widths = [b[2] for b in line_boxes]
#         median_w = np.median(widths)
#         word_gap = max(median_w * 1.3, 15)

#         words = [[line_boxes[0]]]
#         prev_right = line_boxes[0][0] + line_boxes[0][2]
#         for box in line_boxes[1:]:
#             if box[0] - prev_right > word_gap:
#                 words.append([])
#             words[-1].append(box)
#             prev_right = box[0] + box[2]

#         result.append(words)

#     return result


# # ---------------------------------------------------------------------------
# # 4. THE MISSING STEP: split touching/ligature-joined blobs into characters
# # ---------------------------------------------------------------------------
# #
# # This is what the old pipeline never did. find_char_boxes() only ever
# # merged blobs together (for diacritics); nothing ever cut a blob apart.
# # So the moment two letters were pen-joined -- which happens constantly
# # in ordinary handwriting, even print-style -- they were saved as a
# # single "character" image forever. Splitting connected handwritten
# # glyphs with 100% accuracy is an open problem (that's why production
# # handwriting recognition, CRNN+CTC etc., avoids doing it explicitly at
# # all -- see the note at the bottom). What we CAN do reliably is the
# # classic vertical-projection-profile cut: within a word blob, ink
# # density per column dips at the "neck" between two letters even when
# # they're technically touching, and a smoothed local-minimum finder can
# # locate those necks.

# def _typical_char_width(blobs, median_h):
#     """Estimate a single character's width from blobs in this line that
#     are NOT unusually wide (i.e. likely already single letters), so the
#     splitter has a real per-line calibration instead of a fixed guess."""
#     plausible = [b[2] for b in blobs if b[2] <= median_h * 1.1]
#     if plausible:
#         return max(np.median(plausible), median_h * 0.35)
#     return median_h * 0.6


# def split_into_characters(binary_full, blob, typical_char_width, min_char_width):
#     """Slice one word/ligature blob into character-candidate sub-boxes."""
#     x, y, w, h = blob
#     if w <= typical_char_width * 1.35:
#         return [blob]  # already one character's worth of width

#     n_chars = max(1, round(w / typical_char_width))
#     if n_chars <= 1:
#         return [blob]

#     crop = binary_full[y:y + h, x:x + w]
#     profile = (crop > 0).sum(axis=0).astype(np.float32)

#     # Smooth so single-pixel dips inside a letter (e.g. the counter of an
#     # 'o') don't get mistaken for a neck between two letters.
#     k = max(3, int(typical_char_width * 0.12) | 1)  # odd kernel
#     kernel = np.ones(k, dtype=np.float32) / k
#     smooth = np.convolve(profile, kernel, mode="same")

#     # Candidate cut columns: local minima of the smoothed profile.
#     candidates = []
#     for i in range(2, len(smooth) - 2):
#         if smooth[i] <= smooth[i - 1] and smooth[i] <= smooth[i + 1] \
#                 and smooth[i] < smooth.max() * 0.55:
#             candidates.append((smooth[i], i))
#     candidates.sort()  # lowest ink first = most likely a real gap

#     needed_cuts = n_chars - 1
#     chosen = []
#     for val, pos in candidates:
#         if len(chosen) >= needed_cuts:
#             break
#         if all(abs(pos - c) >= min_char_width for c in chosen):
#             if pos >= min_char_width and pos <= w - min_char_width:
#                 chosen.append(pos)
#     chosen.sort()

#     if not chosen:
#         return [blob]

#     bounds = [0] + chosen + [w]
#     pieces = []
#     for i in range(len(bounds) - 1):
#         seg_w = bounds[i + 1] - bounds[i]
#         if seg_w < 2:
#             continue
#         pieces.append([x + bounds[i], y, seg_w, h])
#     return pieces if pieces else [blob]


# # ---------------------------------------------------------------------------
# # 5. Cropping + saving as transparent PNG
# # ---------------------------------------------------------------------------

# def save_character_png(binary_full, box, out_path, padding: int = 4):
#     x, y, w, h = box
#     x0 = max(x - padding, 0)
#     y0 = max(y - padding, 0)
#     x1 = min(x + w + padding, binary_full.shape[1])
#     y1 = min(y + h + padding, binary_full.shape[0])

#     crop = binary_full[y0:y1, x0:x1]
#     rgba = np.zeros((crop.shape[0], crop.shape[1], 4), dtype=np.uint8)
#     rgba[..., 0] = 20
#     rgba[..., 1] = 20
#     rgba[..., 2] = 20
#     rgba[..., 3] = crop
#     cv2.imwrite(out_path, rgba)


# # ---------------------------------------------------------------------------
# # 6. Full pipeline
# # ---------------------------------------------------------------------------

# def segment_handwriting(image_path: str, output_dir: str, remove_ruled_lines: str = "auto",
#                          debug_overlay: bool = False):
#     os.makedirs(output_dir, exist_ok=True)
#     binary = preprocess(image_path, remove_ruled_lines=remove_ruled_lines)

#     blobs = find_blobs(binary)
#     lines = group_into_lines(blobs)
#     print(f"Detected {len(lines)} line(s) of text.")

#     manifest_rows = []
#     overlay = cv2.imread(image_path) if debug_overlay else None

#     for line_idx, words in enumerate(lines, start=1):
#         line_blobs = [b for word in words for b in word]
#         median_h = np.median([b[3] for b in line_blobs]) if line_blobs else 0
#         typical_w = _typical_char_width(line_blobs, median_h)
#         min_char_w = max(typical_w * 0.45, 6)

#         for word_idx, word_blobs in enumerate(words, start=1):
#             char_boxes = []
#             for blob in word_blobs:
#                 char_boxes.extend(
#                     split_into_characters(binary, blob, typical_w, min_char_w)
#                 )
#             char_boxes.sort(key=lambda b: b[0])

#             for char_idx, (cx, cy, cw, ch) in enumerate(char_boxes, start=1):
#                 abs_box = (cx, cy, cw, ch)
#                 filename = f"line{line_idx:02d}_word{word_idx:02d}_char{char_idx:02d}.png"
#                 out_path = os.path.join(output_dir, filename)
#                 save_character_png(binary, abs_box, out_path)

#                 if overlay is not None:
#                     cv2.rectangle(overlay, (cx, cy), (cx + cw, cy + ch), (0, 0, 255), 1)

#                 manifest_rows.append({
#                     "filename": filename, "line": line_idx, "word": word_idx,
#                     "char_index_in_word": char_idx,
#                     "x": abs_box[0], "y": abs_box[1], "width": abs_box[2], "height": abs_box[3],
#                 })

#     manifest_path = os.path.join(output_dir, "manifest.csv")
#     with open(manifest_path, "w", newline="") as f:
#         writer = csv.DictWriter(f, fieldnames=[
#             "filename", "line", "word", "char_index_in_word", "x", "y", "width", "height"])
#         writer.writeheader()
#         writer.writerows(manifest_rows)

#     if overlay is not None:
#         cv2.imwrite(os.path.join(output_dir, "_debug_overlay.png"), overlay)

#     print(f"Saved {len(manifest_rows)} character images to '{output_dir}'.")
#     print(f"Manifest written to '{manifest_path}'.")


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Segment handwriting image into character PNGs.")
#     parser.add_argument("--input", required=True)
#     parser.add_argument("--output_dir", default="./chars")
#     parser.add_argument("--remove_ruled_lines", choices=["auto", "always", "never"], default="auto")
#     parser.add_argument("--debug_overlay", action="store_true")
#     args = parser.parse_args()

#     segment_handwriting(args.input, args.output_dir, args.remove_ruled_lines, args.debug_overlay)





import argparse
import csv
import os

import cv2
import numpy as np
from skimage.filters import threshold_sauvola


# ---------------------------------------------------------------------------
# 1. Preprocessing
# ---------------------------------------------------------------------------

def preprocess(image_path: str, remove_ruled_lines: str = "auto"):
    """Load image, denoise, and binarize so ink = white(255), background = black(0).

    Two fixes vs. the previous version:

    1. Ruled-line removal no longer eats handwriting. The old code used
       minLineLength=200px on a ~2600px-wide photo -- about 7% of the
       image width. On UNRULED paper, cursive baseline connectors between
       letters ("th", "ov", "wn"...) are easily 200px long and dead
       straight, so HoughLinesP was flagging them as "ruled lines" and
       cv2.subtract() was cutting the very strokes that join letters --
       actively causing the touching/broken-fragment mess. Ruled-line
       segments must span most of the page width to be real notebook
       rules, so the length threshold now scales with image width
       (40%), and the whole step is skipped unless ruled lines are
       actually detected (remove_ruled_lines="auto").
    2. No blind morphological opening. A (2,2) MORPH_OPEN on the whole
       page erodes thin pen strokes before dilating them back, which
       reliably punches gaps in fine ballpoint ink and fragments single
       letters into 2-3 pieces (this is what was happening to "quick").
       Noise removal is deferred to the component-filtering stage below,
       where it can be done by connected-component area instead of by
       eroding every stroke on the page.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 5, 50, 50)  # denoise, keeps stroke edges sharp

    local_thresh = threshold_sauvola(gray, window_size=35, k=0.18)
    binary = ((gray < local_thresh).astype(np.uint8)) * 255

    # Close 1px anti-aliasing gaps WITHOUT eroding first (closing only
    # ever adds pixels, so it can't fragment a stroke the way open did).
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel)

    img_w = binary.shape[1]
    min_line_len = int(img_w * 0.4)

    line_segments = cv2.HoughLinesP(
        binary, 1, np.pi / 360, threshold=200,
        minLineLength=min_line_len, maxLineGap=20,
    )

    has_ruled_lines = False
    if line_segments is not None:
        horiz = 0
        for seg in line_segments:
            x1, y1, x2, y2 = map(int, np.asarray(seg).reshape(-1)[:4])
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if angle < 3 or angle > 177:
                horiz += 1
        has_ruled_lines = horiz >= 2  # a couple of full-width straight rules

    do_remove = (remove_ruled_lines == "always") or (
        remove_ruled_lines == "auto" and has_ruled_lines
    )

    if do_remove and line_segments is not None:
        line_mask = np.zeros_like(binary)
        for seg in line_segments:
            x1, y1, x2, y2 = map(int, np.asarray(seg).reshape(-1)[:4])
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if angle < 3 or angle > 177:
                cv2.line(line_mask, (x1, y1), (x2, y2), 255, thickness=4)
        binary = cv2.subtract(binary, line_mask)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel)

    return binary


# ---------------------------------------------------------------------------
# 2. Blob detection + diacritic merge (word/ligature-level, not yet chars)
# ---------------------------------------------------------------------------

def find_blobs(binary: np.ndarray, min_area: int = 12):
    """Connected components on the page. On handwriting where letters
    within a word are pen-joined, one blob here can span several
    characters ("The", "ow" in "brown") -- that's expected and is what
    split_into_characters() below is for. This stage only removes
    speckle noise and re-attaches small marks (dots on i/j, crossbars on
    t) to the nearest stroke below/above them.
    """
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

    raw = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < min_area:
            continue
        raw.append([x, y, w, h])

    if not raw:
        return []

    heights = [b[3] for b in raw]
    median_h = np.median(heights)

    merged = []
    used = [False] * len(raw)
    for i, box in enumerate(raw):
        if used[i]:
            continue
        x, y, w, h = box
        is_small = h < median_h * 0.45 and w < median_h * 0.6
        if is_small:
            best_j, best_dist = None, float("inf")
            for j, other in enumerate(raw):
                if i == j or used[j]:
                    continue
                ox, oy, ow, oh = other
                overlap = min(x + w, ox + ow) - max(x, ox)
                if overlap > 0:
                    dist = abs((y + h / 2) - (oy + oh / 2))
                    if dist < best_dist:
                        best_dist, best_j = dist, j
            if best_j is not None:
                ox, oy, ow, oh = raw[best_j]
                nx, ny = min(x, ox), min(y, oy)
                nx2, ny2 = max(x + w, ox + ow), max(y + h, oy + oh)
                merged.append([nx, ny, nx2 - nx, ny2 - ny])
                used[i] = used[best_j] = True
                continue
        merged.append(box)
        used[i] = True

    return merged


# ---------------------------------------------------------------------------
# 3. Lines -> words (same clustering idea as before, kept because it works)
# ---------------------------------------------------------------------------

def group_into_lines(blobs, gap_factor: float = 1.2):
    if not blobs:
        return []

    heights = [b[3] for b in blobs]
    median_h = np.median(heights)
    gap_threshold = max(median_h * gap_factor, 10)

    by_y = sorted(blobs, key=lambda b: b[1] + b[3] / 2)
    lines = [[by_y[0]]]
    prev_center = by_y[0][1] + by_y[0][3] / 2
    for box in by_y[1:]:
        center = box[1] + box[3] / 2
        if center - prev_center > gap_threshold:
            lines.append([])
        lines[-1].append(box)
        prev_center = center

    result = []
    for line_boxes in lines:
        line_boxes.sort(key=lambda b: b[0])
        widths = [b[2] for b in line_boxes]
        median_w = np.median(widths)
        word_gap = max(median_w * 1.3, 15)

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
# 4. THE MISSING STEP: split touching/ligature-joined blobs into characters
# ---------------------------------------------------------------------------
#
# This is what the old pipeline never did. find_char_boxes() only ever
# merged blobs together (for diacritics); nothing ever cut a blob apart.
# So the moment two letters were pen-joined -- which happens constantly
# in ordinary handwriting, even print-style -- they were saved as a
# single "character" image forever. Splitting connected handwritten
# glyphs with 100% accuracy is an open problem (that's why production
# handwriting recognition, CRNN+CTC etc., avoids doing it explicitly at
# all -- see the note at the bottom). What we CAN do reliably is the
# classic vertical-projection-profile cut: within a word blob, ink
# density per column dips at the "neck" between two letters even when
# they're technically touching, and a smoothed local-minimum finder can
# locate those necks.

def _typical_char_width(blobs, median_h):
    """Estimate a single character's width from blobs in this line that
    are NOT unusually wide (i.e. likely already single letters), so the
    splitter has a real per-line calibration instead of a fixed guess."""
    plausible = [b[2] for b in blobs if b[2] <= median_h * 1.1]
    if plausible:
        return max(np.median(plausible), median_h * 0.35)
    return median_h * 0.6


def group_isolated_glyphs(line_blobs, median_h):
    """For isolated/specimen mode: reconstruct each glyph directly from the
    line's blobs, independent of the word_gap clustering used for prose.

    Word_gap clustering is deliberately loose (it has to be, to keep prose
    words together across normal letter-spacing), which means it can lump
    two genuinely separate letters that just happen to sit a bit close
    together (e.g. 'y' and 'z' at the end of a row) into one "word". That's
    fine for prose grouping but wrong here, where every letter is meant to
    stand alone.

    What we actually want to bridge is much narrower: a single glyph whose
    pen stroke has a tiny gap in it from thresholding (the hook of a 'G',
    the corner of a 'K'). Those fragments sit right against each other --
    touching or overlapping in x -- unlike two distinct letters, which even
    when "close" are still separated by real whitespace. So here we cluster
    by a small fragment-gap threshold instead of the word-level one.
    """
    if not line_blobs:
        return []
    fragment_gap = max(median_h * 0.18, 6)
    by_x = sorted(line_blobs, key=lambda b: b[0])
    glyphs = [[by_x[0]]]
    prev_right = by_x[0][0] + by_x[0][2]
    for b in by_x[1:]:
        if b[0] - prev_right > fragment_gap:
            glyphs.append([])
        glyphs[-1].append(b)
        prev_right = max(prev_right, b[0] + b[2])

    boxes = []
    for g in glyphs:
        x0 = min(b[0] for b in g)
        y0 = min(b[1] for b in g)
        x1 = max(b[0] + b[2] for b in g)
        y1 = max(b[1] + b[3] for b in g)
        h = y1 - y0
        if median_h and h < median_h * 0.3:
            continue  # debris (stray marks), not a real glyph
        boxes.append([x0, y0, x1 - x0, h])
    return boxes


def split_into_characters(binary_full, blob, typical_char_width, min_char_width):
    """Slice one word/ligature blob into character-candidate sub-boxes."""
    x, y, w, h = blob
    if w <= typical_char_width * 1.35:
        return [blob]  # already one character's worth of width

    n_chars = max(1, round(w / typical_char_width))
    if n_chars <= 1:
        return [blob]

    crop = binary_full[y:y + h, x:x + w]
    profile = (crop > 0).sum(axis=0).astype(np.float32)

    # Smooth so single-pixel dips inside a letter (e.g. the counter of an
    # 'o') don't get mistaken for a neck between two letters.
    k = max(3, int(typical_char_width * 0.12) | 1)  # odd kernel
    kernel = np.ones(k, dtype=np.float32) / k
    smooth = np.convolve(profile, kernel, mode="same")

    # Candidate cut columns: local minima of the smoothed profile.
    candidates = []
    for i in range(2, len(smooth) - 2):
        if smooth[i] <= smooth[i - 1] and smooth[i] <= smooth[i + 1] \
                and smooth[i] < smooth.max() * 0.55:
            candidates.append((smooth[i], i))
    candidates.sort()  # lowest ink first = most likely a real gap

    needed_cuts = n_chars - 1
    chosen = []
    for val, pos in candidates:
        if len(chosen) >= needed_cuts:
            break
        if all(abs(pos - c) >= min_char_width for c in chosen):
            if pos >= min_char_width and pos <= w - min_char_width:
                chosen.append(pos)
    chosen.sort()

    if not chosen:
        return [blob]

    bounds = [0] + chosen + [w]
    pieces = []
    for i in range(len(bounds) - 1):
        seg_w = bounds[i + 1] - bounds[i]
        if seg_w < 2:
            continue
        pieces.append([x + bounds[i], y, seg_w, h])
    return pieces if pieces else [blob]


# ---------------------------------------------------------------------------
# 5. Cropping + saving as transparent PNG
# ---------------------------------------------------------------------------

def save_character_png(binary_full, box, out_path, padding: int = 4):
    x, y, w, h = box
    x0 = max(x - padding, 0)
    y0 = max(y - padding, 0)
    x1 = min(x + w + padding, binary_full.shape[1])
    y1 = min(y + h + padding, binary_full.shape[0])

    crop = binary_full[y0:y1, x0:x1]
    rgba = np.zeros((crop.shape[0], crop.shape[1], 4), dtype=np.uint8)
    rgba[..., 0] = 20
    rgba[..., 1] = 20
    rgba[..., 2] = 20
    rgba[..., 3] = crop
    cv2.imwrite(out_path, rgba)


# ---------------------------------------------------------------------------
# 6. Full pipeline
# ---------------------------------------------------------------------------

def segment_handwriting(image_path: str, output_dir: str, remove_ruled_lines: str = "auto",
                         debug_overlay: bool = False, mode: str = "prose"):
    """
    mode="prose"    -- continuous handwriting (sentences, paragraphs) where
                        letters are routinely pen-joined within a word.
                        Runs the width/valley character-splitting heuristic.
    mode="isolated" -- reference/specimen sheets where each glyph is already
                        written with deliberate whitespace around it (e.g. an
                        alphabet practice sheet, or one-letter-per-box capture
                        UI). Skips splitting entirely and saves each blob as
                        one character. See the note above split_into_characters
                        for why this matters: wide-but-single letters like
                        m/w/H/K/z produce the exact same "wide blob + internal
                        low-ink valley" signature as two touching letters do,
                        so the same heuristic that correctly separates joined
                        cursive will incorrectly slice these apart when nothing
                        was ever touching in the first place. If your capture
                        flow already guarantees one glyph per blob, isolated
                        mode is strictly more correct.
    """
    os.makedirs(output_dir, exist_ok=True)
    binary = preprocess(image_path, remove_ruled_lines=remove_ruled_lines)

    blobs = find_blobs(binary)
    lines = group_into_lines(blobs)
    print(f"Detected {len(lines)} line(s) of text.")

    manifest_rows = []
    overlay = cv2.imread(image_path) if debug_overlay else None

    for line_idx, words in enumerate(lines, start=1):
        line_blobs = [b for word in words for b in word]
        median_h = np.median([b[3] for b in line_blobs]) if line_blobs else 0
        typical_w = _typical_char_width(line_blobs, median_h)
        min_char_w = max(typical_w * 0.45, 6)

        if mode == "isolated":
            # Rebuild glyphs straight from the line's blobs (see
            # group_isolated_glyphs for why word-level clustering isn't
            # used here), then present each as its own single-character
            # "word" so the output/manifest shape matches prose mode.
            glyph_boxes = group_isolated_glyphs(line_blobs, median_h)
            glyph_boxes.sort(key=lambda b: b[0])
            word_char_lists = [(i + 1, [box]) for i, box in enumerate(glyph_boxes)]
        else:
            word_char_lists = []
            for word_idx, word_blobs in enumerate(words, start=1):
                char_boxes = []
                for blob in word_blobs:
                    char_boxes.extend(
                        split_into_characters(binary, blob, typical_w, min_char_w)
                    )
                char_boxes.sort(key=lambda b: b[0])
                word_char_lists.append((word_idx, char_boxes))

        for word_idx, char_boxes in word_char_lists:
            for char_idx, (cx, cy, cw, ch) in enumerate(char_boxes, start=1):
                abs_box = (cx, cy, cw, ch)
                filename = f"line{line_idx:02d}_word{word_idx:02d}_char{char_idx:02d}.png"
                out_path = os.path.join(output_dir, filename)
                save_character_png(binary, abs_box, out_path)

                if overlay is not None:
                    cv2.rectangle(overlay, (cx, cy), (cx + cw, cy + ch), (0, 0, 255), 1)

                manifest_rows.append({
                    "filename": filename, "line": line_idx, "word": word_idx,
                    "char_index_in_word": char_idx,
                    "x": abs_box[0], "y": abs_box[1], "width": abs_box[2], "height": abs_box[3],
                })

    manifest_path = os.path.join(output_dir, "manifest.csv")
    with open(manifest_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "filename", "line", "word", "char_index_in_word", "x", "y", "width", "height"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    if overlay is not None:
        cv2.imwrite(os.path.join(output_dir, "_debug_overlay.png"), overlay)

    print(f"Saved {len(manifest_rows)} character images to '{output_dir}'.")
    print(f"Manifest written to '{manifest_path}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Segment handwriting image into character PNGs.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output_dir", default="./chars")
    parser.add_argument("--remove_ruled_lines", choices=["auto", "always", "never"], default="auto")
    parser.add_argument("--debug_overlay", action="store_true")
    parser.add_argument("--mode", choices=["prose", "isolated"], default="prose",
                         help="'prose' splits touching letters within joined handwriting "
                              "(sentences/paragraphs). 'isolated' skips splitting -- use for "
                              "reference/specimen sheets where each glyph already has its own "
                              "whitespace (e.g. an alphabet practice sheet).")
    args = parser.parse_args()

    segment_handwriting(args.input, args.output_dir, args.remove_ruled_lines,
                         args.debug_overlay, args.mode)