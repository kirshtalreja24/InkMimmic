import argparse
import csv
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preprocessing as _pp  # noqa: E402  -- must sit in the same folder as this file


# ---------------------------------------------------------------------------
# 1. Preprocessing -- delegates to preprocess.py (must be in this same folder)
# ---------------------------------------------------------------------------
#
# This used to be an inline Sauvola+Hough implementation here. It's now a
# thin wrapper around the dedicated preprocessing module (see preprocess.py),
# which additionally handles deskew, CLAHE, shadow-gradient removal, and
# page-type-aware ruled/grid line removal -- see that file's docstrings for
# why each of those matters for real phone photos (shadow gradients breaking
# a single threshold, curved ruled lines on a photographed rather than
# flat-scanned notebook, etc).

def preprocess(image_path: str, remove_ruled_lines: str = "auto") -> np.ndarray:
    cfg = _pp.PreprocessConfig()
    result = _pp.preprocess(image_path, cfg)
    binary = result.binary

    if remove_ruled_lines == "never" and result.page_type in ("ruled", "grid"):
        # Caller explicitly opted out of line removal even though the page
        # has ruling -- re-run without it. (Re-threshold is cheap enough
        # not to bother threading a flag through the whole module for
        # this one case.)
        cfg2 = _pp.PreprocessConfig(auto_detect_lines=False)
        binary = _pp.preprocess(image_path, cfg2).binary
    elif remove_ruled_lines == "always" and result.page_type == "blank":
        # Force line removal even though auto-detection found nothing --
        # rare (e.g. very faint ruling), but keep the escape hatch.
        n, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        heights = [stats[i][3] for i in range(1, n) if stats[i][4] >= 15]
        mh = float(np.median(heights)) if heights else None
        binary = _pp.remove_ruled_lines(binary, mh)
        binary = _pp.repair_strokes(binary)

    return binary


# ---------------------------------------------------------------------------
# 2. Blob detection + diacritic merge (word/ligature-level, not yet chars)
# ---------------------------------------------------------------------------

def find_blobs(binary: np.ndarray, min_area: int = 8):
    """Connected components on the page. On handwriting where letters
    within a word are pen-joined, one blob here can span several
    characters ("The", "ow" in "brown") -- that's expected and is what
    split_into_characters() below is for. This stage only removes
    speckle noise and re-attaches small marks (dots on i/j, crossbars on
    t) to the nearest stroke below/above them.

    A fixed min_area alone isn't enough on real phone photos: paper
    grain, JPEG artifacts, and short surviving fragments of a removed
    ruled line all produce components a few pixels tall that comfortably
    clear a tiny area cutoff (e.g. a 20x2 sliver has area 40). At high
    photo resolutions there can be *thousands* of these, heavily
    outnumbering actual letters -- which is a problem beyond just
    clutter: if median blob height is computed across that mixed pool,
    the noise majority drags it down to near-nothing, which then breaks
    every downstream heuristic calibrated off it (line clustering,
    word-gap, character-split width) even for the real letters.

    So this uses a two-population split instead of one flat threshold:
    Otsu's method applied to the *heights* of surviving blobs (not pixel
    intensities, but the same "find the valley between two clusters"
    idea) separates real ink-sized components from noise-sized ones for
    THIS image, rather than assuming a fixed pixel count that only holds
    at one resolution. Small blobs are then either merged onto a nearby
    real blob (genuine diacritics: dots, crossbars) or dropped entirely
    (no real neighbor = noise, not a stray "character").
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

    heights = np.array([b[3] for b in raw])

    # Auto-split into "real ink" vs "noise/fragment" populations. Only
    # meaningful with enough samples and actual spread; degrades safely
    # to "treat everything as real" otherwise (small/clean pages).
    real_thresh = 0
    if len(heights) >= 20 and heights.max() > heights.min():
        h_u8 = np.clip(heights, 0, 255).astype(np.uint8)
        otsu_val, _ = cv2.threshold(h_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Only trust the split if it leaves a real "ink-sized" population on
        # the tall side. Noise can legitimately be the overwhelming majority
        # of components on a grainy high-res photo (paper texture alone can
        # outnumber actual letters 10:1+), so the guard here is "did we keep
        # a plausible number of real components", not "is noise a minority".
        above = np.sum(heights > otsu_val)
        if above >= min(15, max(3, len(heights) * 0.02)):
            real_thresh = otsu_val

    real_boxes = [b for b in raw if b[3] > real_thresh]
    small_boxes = [b for b in raw if b[3] <= real_thresh]

    median_h = np.median([b[3] for b in real_boxes]) if real_boxes else np.median(heights)

    merged = list(real_boxes)
    for x, y, w, h in small_boxes:
        best_j, best_dist = None, float("inf")
        for j, (ox, oy, ow, oh) in enumerate(merged):
            overlap = min(x + w, ox + ow) - max(x, ox)
            if overlap > 0:
                dist = abs((y + h / 2) - (oy + oh / 2))
                if dist < best_dist:
                    best_dist, best_j = dist, j
        # Only merge if genuinely close (a dot sits right above its stem;
        # unrelated noise elsewhere on the line shouldn't glom on).
        if best_j is not None and best_dist < median_h * 0.9:
            ox, oy, ow, oh = merged[best_j]
            nx, ny = min(x, ox), min(y, oy)
            nx2, ny2 = max(x + w, ox + ow), max(y + h, oy + oh)
            merged[best_j] = [nx, ny, nx2 - nx, ny2 - ny]
        # else: no real neighbor nearby -> noise/line-fragment, drop it.

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

def _line_is_isolated(line_blobs, median_w):
    """Heuristic for mode="auto": on a specimen/reference sheet every blob
    is its own letter with deliberate whitespace, so the gap between
    consecutive blobs is consistently large relative to letter width. In
    prose, most gaps are the tight spacing *within* a word (letters
    touching or nearly so) with only occasional wider word-breaks, so the
    per-line median gap stays small. Needs a few blobs to be a meaningful
    sample; with fewer, default to prose (the safer assumption for the
    common case of a short line of writing)."""
    if len(line_blobs) < 4:
        return False
    by_x = sorted(line_blobs, key=lambda b: b[0])
    gaps = [by_x[i + 1][0] - (by_x[i][0] + by_x[i][2]) for i in range(len(by_x) - 1)]
    return float(np.median(gaps)) > median_w * 0.55


def segment_handwriting(image_path: str, output_dir: str, remove_ruled_lines: str = "auto",
                         debug_overlay: bool = False, mode: str = "auto"):
    """
    mode="auto"     -- (default) decides per line of text using the gap
                        between letters relative to their width. You
                        shouldn't need to touch this for a normal photo;
                        it's here mainly as an override for borderline
                        cases.
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

        line_mode = mode
        if line_mode == "auto":
            line_mode = "isolated" if _line_is_isolated(line_blobs, typical_w) else "prose"

        if line_mode == "isolated":
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
    parser.add_argument("--mode", choices=["auto", "prose", "isolated"], default="auto",
                         help="'auto' (default) decides per line. 'prose' forces the "
                              "touching-letter split heuristic (sentences/paragraphs). "
                              "'isolated' forces no splitting (reference/specimen sheets "
                              "where each glyph already has its own whitespace, e.g. an "
                              "alphabet practice sheet).")
    args = parser.parse_args()

    segment_handwriting(args.input, args.output_dir, args.remove_ruled_lines,
                         args.debug_overlay, args.mode)