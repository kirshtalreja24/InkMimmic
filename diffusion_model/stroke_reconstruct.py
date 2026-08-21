"""

stroke_reconstruct.py — Reconstruct approximate online stroke data from offline
handwriting line images.

Takes a binarized line crop (ink-dark on white background) and produces an
approximate stroke sequence: (dx, dy, pen_up) triplets in the exact format
the HANDWRITER diffusion model expects for training.

Pipeline per line:
  1. Skeletonize (1px medial axis)
  2. Build pixel-adjacency graph → endpoints + junctions
  3. Decompose into chains (edge-paths between junctions/endpoints)
  4. Order chains left→right, assign pen-up between disconnected chains
  5. Resample to ≤480 points (model's MAX_SEQ_LEN)
  6. Normalize: differential (dx, dy), pen-up flag, /= std, combine_strokes

The output matches diffusion_model/preprocessing.py::parse_stroke_xml's format
so it can be fed directly into train.py / finetune.py.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from skimage.morphology import skeletonize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Add diffusion_model/ to path for combine_strokes / show
THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(THIS_DIR))

from utils import show  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Skeletonize a binary line image
# ---------------------------------------------------------------------------
def binarize_and_skeletonize(img_path: str, ink_dark: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Load a line image, binarize, and skeletonize.

    Parameters
    ----------
    img_path : path to a grayscale or RGB line crop.
    ink_dark : if True (default), ink pixels are dark (< 128).  If False
               (e.g. segment.py's convention: ink=255, bg=0), we invert.

    Returns
    -------
    binary : H×W bool array, True = ink
    skeleton : H×W bool array, True = skeleton pixel
    """
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {img_path}")

    # Ensure binary: ink=True
    if ink_dark:
        binary = img < 128
    else:
        binary = img > 128

    # Remove tiny noise blobs (< 8 px connected components)
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary.astype(np.uint8), connectivity=8
    )
    for i in range(1, n_labels):
        if stats[i, cv2.CC_STAT_AREA] < 8:
            binary[labels == i] = False

    skeleton = skeletonize(binary)
    return binary, skeleton


# ---------------------------------------------------------------------------
# 2. Build adjacency graph from skeleton pixels
# ---------------------------------------------------------------------------
_NEIGHBORS_8 = [(-1, -1), (-1, 0), (-1, 1),
                (0, -1),           (0, 1),
                (1, -1),  (1, 0),  (1, 1)]


def _neighbor_count(skel: np.ndarray, r: int, c: int) -> int:
    """Count 8-connected skeleton neighbors of pixel (r, c)."""
    count = 0
    H, W = skel.shape
    for dr, dc in _NEIGHBORS_8:
        nr, nc = r + dr, c + dc
        if 0 <= nr < H and 0 <= nc < W and skel[nr, nc]:
            count += 1
    return count


def _classify_pixels(skel: np.ndarray):
    """Classify skeleton pixels into endpoints (deg 1), junctions (deg >= 3), and midpoints."""
    points = np.argwhere(skel)  # (N, 2) — row, col
    endpoints = []
    junctions = []
    midpoints = []
    for r, c in points:
        deg = _neighbor_count(skel, r, c)
        if deg == 1:
            endpoints.append((r, c))
        elif deg >= 3:
            junctions.append((r, c))
        else:
            midpoints.append((r, c))
    return set(endpoints), set(junctions), set(midpoints)


# ---------------------------------------------------------------------------
# 3. Trace chains between junctions / endpoints
# ---------------------------------------------------------------------------
def _trace_chains(skel: np.ndarray, endpoints: set, junctions: set) -> list[list[tuple[int, int]]]:
    """Walk the skeleton, producing chains (ordered pixel paths).

    Each chain starts at an endpoint or junction and continues until it hits
    another endpoint/junction or a dead end (already visited).
    """
    H, W = skel.shape
    visited = np.zeros_like(skel, dtype=bool)
    chains = []

    # Mark junction pixels as "split points" — we'll start/stop at them
    # but not mark them visited globally (so multiple chains can share a junction).
    start_points = list(endpoints) + list(junctions)
    # Sort left→right, top→bottom for deterministic ordering
    start_points.sort(key=lambda p: (p[1], p[0]))

    def _walk(start_r, start_c):
        """Walk from (start_r, start_c) along unvisited skeleton pixels."""
        chain = [(start_r, start_c)]
        visited[start_r, start_c] = True
        r, c = start_r, start_c

        while True:
            found_next = False
            for dr, dc in _NEIGHBORS_8:
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and skel[nr, nc] and not visited[nr, nc]:
                    chain.append((nr, nc))
                    visited[nr, nc] = True
                    # If we reach a junction or endpoint (other than start), stop
                    if (nr, nc) in junctions or (nr, nc) in endpoints:
                        return chain
                    r, c = nr, nc
                    found_next = True
                    break
            if not found_next:
                break
        return chain

    for sr, sc in start_points:
        if visited[sr, sc] and (sr, sc) not in junctions:
            continue
        # For junctions, try each unvisited neighbor direction
        for dr, dc in _NEIGHBORS_8:
            nr, nc = sr + dr, sc + dc
            if 0 <= nr < H and 0 <= nc < W and skel[nr, nc] and not visited[nr, nc]:
                chain = [(sr, sc)]
                visited[nr, nc] = True
                chain.append((nr, nc))
                if (nr, nc) not in junctions and (nr, nc) not in endpoints:
                    rest = _walk(nr, nc)
                    chain.extend(rest[1:])  # rest[0] is (nr, nc) again
                if len(chain) >= 2:
                    chains.append(chain)

    # Catch any remaining unvisited skeleton pixels (isolated loops, etc.)
    remaining = np.argwhere(skel & ~visited)
    if len(remaining) > 0:
        for r, c in remaining:
            if not visited[r, c]:
                chain = _walk(r, c)
                if len(chain) >= 2:
                    chains.append(chain)

    return chains


# ---------------------------------------------------------------------------
# 4. Order chains left→right and build a single stroke sequence
# ---------------------------------------------------------------------------
def _chain_centroid_x(chain: list[tuple[int, int]]) -> float:
    return np.mean([c for _, c in chain])


def _chains_to_strokes(chains: list[list[tuple[int, int]]]) -> np.ndarray:
    """Convert ordered chains into an absolute (x, y) stroke sequence with pen-up flags.

    Returns shape (N, 3): columns are (x, y, pen_up).
    pen_up = 1.0 means the pen lifts AFTER this point (before the next one).
    """
    if not chains:
        return np.zeros((0, 3), dtype=np.float64)

    # Sort chains by centroid x (left→right reading order)
    chains_sorted = sorted(chains, key=_chain_centroid_x)

    # Decide chain direction: each chain should flow left→right
    oriented = []
    for chain in chains_sorted:
        if chain[-1][1] < chain[0][1]:  # last point is further left → reverse
            chain = list(reversed(chain))
        oriented.append(chain)

    # Concatenate with pen-up between chains
    all_points = []
    for i, chain in enumerate(oriented):
        for j, (r, c) in enumerate(chain):
            # pen is UP at the last point of each chain (except the very last chain's very last point)
            is_last_in_chain = (j == len(chain) - 1) and (i < len(oriented) - 1)
            all_points.append((float(c), float(-r), 1.0 if is_last_in_chain else 0.0))
            # Note: y is negated so "up on screen" = positive y (pen convention)

    return np.array(all_points, dtype=np.float64)


# ---------------------------------------------------------------------------
# 5. Resample to a target point count
# ---------------------------------------------------------------------------
def _arc_length_resample(points: np.ndarray, target_n: int) -> np.ndarray:
    """Resample an (N, 3) absolute stroke array to `target_n` points via arc-length interpolation.

    pen_up flags are preserved: if the original segment between two points
    had a pen-up, the resampled point inherits it.
    """
    if len(points) <= 1:
        return points

    xy = points[:, :2]
    pen_up = points[:, 2]

    # Compute cumulative arc length
    diffs = np.diff(xy, axis=0)
    seg_lengths = np.linalg.norm(diffs, axis=1)
    cum_len = np.concatenate([[0], np.cumsum(seg_lengths)])
    total_len = cum_len[-1]

    if total_len < 1e-8:
        return points[:1]

    # Desired sample positions along the arc
    sample_positions = np.linspace(0, total_len, target_n)

    resampled = np.zeros((target_n, 3), dtype=np.float64)
    seg_idx = 0
    for i, s in enumerate(sample_positions):
        # Find the segment containing position s
        while seg_idx < len(cum_len) - 2 and cum_len[seg_idx + 1] < s:
            seg_idx += 1
        # Interpolate within segment
        seg_start = cum_len[seg_idx]
        seg_end = cum_len[min(seg_idx + 1, len(cum_len) - 1)]
        if seg_end - seg_start > 1e-8:
            t = (s - seg_start) / (seg_end - seg_start)
        else:
            t = 0.0
        idx_a = seg_idx
        idx_b = min(seg_idx + 1, len(xy) - 1)
        resampled[i, :2] = (1 - t) * xy[idx_a] + t * xy[idx_b]
        # Pen-up: if either endpoint of this segment has pen_up, carry it
        resampled[i, 2] = pen_up[idx_a] if t < 0.5 else pen_up[idx_b]

    return resampled


# ---------------------------------------------------------------------------
# 6. Normalize to differential (dx, dy) format — matches parse_stroke_xml
# ---------------------------------------------------------------------------
def _combine_strokes_copy(x: np.ndarray, n: int) -> np.ndarray:
    """Replicate diffusion_model/preprocessing.py::combine_strokes exactly.

    Consecutive stroke vectors who point in similar directions are summed.
    If the pen was picked up in either of the strokes, we pick up the pen
    for the combined stroke.
    """
    s, s_neighbors = x[::2, :2], x[1::2, :2]
    if len(x) % 2 != 0:
        s = s[:-1]
    if len(s) == 0 or len(s_neighbors) == 0:
        return x
    norms_s = np.linalg.norm(s, axis=-1)
    norms_n = np.linalg.norm(s_neighbors, axis=-1)
    norms_sum = np.linalg.norm(s + s_neighbors, axis=-1)
    values = norms_s + norms_n - norms_sum
    n = min(n, len(values))
    ind = np.argsort(values)[:n]
    x[ind * 2] += x[ind * 2 + 1]
    x[ind * 2, 2] = np.greater(x[ind * 2, 2], 0).astype(float)
    x = np.delete(x, ind * 2 + 1, axis=0)
    x[:, :2] /= np.std(x[:, :2]) if np.std(x[:, :2]) > 1e-8 else 1.0
    return x


def absolute_to_differential(abs_points: np.ndarray) -> np.ndarray:
    """Convert absolute (x, y, pen_up) to differential (dx, dy, pen_up).

    Matches the convention in parse_stroke_xml:
    - Each row is (dx, dy, pen_up) where dx/dy are offsets from previous point.
    - pen_up flags are shifted (np.roll by 1): a stroke that is NOT drawn has 1.
    - Normalized by std of (dx, dy).
    - combine_strokes applied 3x to merge similar-direction consecutive strokes.
    """
    if len(abs_points) < 2:
        return abs_points

    # Differential: each point is the offset from the previous
    diffs = np.diff(abs_points[:, :2], axis=0)
    pen_up = abs_points[1:, 2]  # pen_up associated with the destination point

    strokes = np.column_stack([diffs, pen_up])  # (N-1, 3)

    # Shift pen_up by 1 (same as parse_stroke_xml line 99)
    strokes[:, 2] = np.roll(strokes[:, 2], 1)

    # Normalize by std
    std = np.std(strokes[:, :2])
    if std > 1e-8:
        strokes[:, :2] /= std

    # combine_strokes 3x (same as parse_stroke_xml lines 103)
    for _ in range(3):
        strokes = _combine_strokes_copy(strokes, int(len(strokes) * 0.2))

    return strokes.astype(np.float32)


# ---------------------------------------------------------------------------
# 7. End-to-end reconstruction
# ---------------------------------------------------------------------------
def reconstruct_strokes(
    img_path: str,
    target_points: int = 450,
    ink_dark: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reconstruct online stroke data from an offline line image.

    Parameters
    ----------
    img_path : path to a line crop (grayscale, ink on white or ink on black).
    target_points : target number of points after resampling (≤480 for model).
    ink_dark : True if ink pixels are dark (< 128).

    Returns
    -------
    strokes : (N, 3) float32 differential strokes — ready for training.
    abs_points : (M, 3) absolute stroke points — for visualization.
    skeleton : the binary skeleton image — for validation overlay.
    """
    binary, skeleton = binarize_and_skeletonize(img_path, ink_dark=ink_dark)

    if skeleton.sum() < 5:
        raise ValueError(f"Skeleton too sparse ({skeleton.sum()} pixels) — check image: {img_path}")

    endpoints, junctions, _ = _classify_pixels(skeleton)
    chains = _trace_chains(skeleton, endpoints, junctions)

    if not chains:
        raise ValueError(f"No chains extracted from skeleton: {img_path}")

    abs_points = _chains_to_strokes(chains)

    # Resample to target
    target_n = min(target_points, len(abs_points))
    if target_n < len(abs_points):
        abs_points = _arc_length_resample(abs_points, target_n)

    # Convert to differential format
    strokes = absolute_to_differential(abs_points)

    return strokes, abs_points, skeleton


# ---------------------------------------------------------------------------
# 8. Validation overlay — render reconstructed strokes beside original
# ---------------------------------------------------------------------------
def save_validation_overlay(
    original_path: str,
    abs_points: np.ndarray,
    skeleton: np.ndarray,
    out_path: str,
):
    """Save a side-by-side: original | skeleton | reconstructed rendering."""
    original = cv2.imread(original_path, cv2.IMREAD_GRAYSCALE)
    if original is None:
        return

    fig, axes = plt.subplots(1, 3, figsize=(18, 4))

    # Original
    axes[0].imshow(original, cmap='gray')
    axes[0].set_title('Original line')
    axes[0].axis('off')

    # Skeleton
    axes[1].imshow(skeleton, cmap='gray')
    axes[1].set_title(f'Skeleton ({skeleton.sum()} px)')
    axes[1].axis('off')

    # Reconstructed strokes
    xy = abs_points[:, :2].copy()
    pen_up = abs_points[:, 2]
    ax = axes[2]
    prev_i = 0
    for i in range(len(pen_up)):
        if pen_up[i] > 0.5 or i == len(pen_up) - 1:
            seg = xy[prev_i:i + 1]
            if len(seg) >= 2:
                ax.plot(seg[:, 0], seg[:, 1], 'k-', linewidth=1.0)
            prev_i = i + 1
    ax.set_title(f'Reconstructed ({len(abs_points)} pts)')
    ax.set_aspect('equal')
    ax.invert_yaxis()
    ax.axis('off')

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()


# ---------------------------------------------------------------------------
# 9. Batch: reconstruct all lines from a page via segment.py
# ---------------------------------------------------------------------------
def reconstruct_page(
    page_path: str,
    output_dir: str,
    target_points: int = 450,
    segment_mode: str = 'auto',
) -> list[dict]:
    """Reconstruct strokes for every line detected on a page.

    Uses the project's segment.py to extract line crops, then reconstructs
    each one.

    Returns a list of dicts per line:
        {'line_num': int, 'line_image': str, 'strokes_path': str,
         'abs_points': ndarray, 'overlay': str}

    Output layout (mirrors the web app's per-user dirs):
        output_dir/lines/lineNN.png        — line crop (ink-dark on white)
        output_dir/strokes/lineNN.npy      — reconstructed strokes
        output_dir/overlays/lineNN_overlay.png — validation overlay
    """
    # Import segment from the project root
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    import segment  # noqa: E402

    lines_dir = os.path.join(output_dir, 'lines')
    strokes_dir = os.path.join(output_dir, 'strokes')
    overlays_dir = os.path.join(output_dir, 'overlays')
    for d in (lines_dir, strokes_dir, overlays_dir):
        os.makedirs(d, exist_ok=True)

    # Segment the page
    work_dir = os.path.join(output_dir, '_segment_work')
    os.makedirs(work_dir, exist_ok=True)
    segment.segment_handwriting(page_path, work_dir, mode=segment_mode)
    binary = segment.preprocess(page_path)

    # Read manifest to find lines
    import csv
    from collections import defaultdict
    manifest_path = os.path.join(work_dir, 'manifest.csv')
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Segmentation produced no manifest: {manifest_path}")

    with open(manifest_path, newline='') as f:
        rows = list(csv.DictReader(f))

    by_line = defaultdict(list)
    for r in rows:
        by_line[int(r['line'])].append(r)

    results = []
    for line_num, line_rows in sorted(by_line.items()):
        # Compute line bounding box
        boxes = [(int(r['x']), int(r['y']), int(r['width']), int(r['height'])) for r in line_rows]
        bbox = segment.line_bbox(boxes, pad=6, img_shape=binary.shape)
        # binary from segment.py: ink=255, bg=0 → crop_line_image inverts to ink=dark, bg=white
        line_crop = segment.crop_line_image(binary, bbox)
        if line_crop is None:
            continue
        line_img_path = os.path.join(lines_dir, f'line{line_num:02d}.png')
        cv2.imwrite(line_img_path, line_crop)

        try:
            strokes, abs_points, skeleton = reconstruct_strokes(
                line_img_path, target_points=target_points, ink_dark=True
            )
            overlay_path = os.path.join(overlays_dir, f'line{line_num:02d}_overlay.png')
            save_validation_overlay(line_img_path, abs_points, skeleton, overlay_path)
            strokes_path = os.path.join(strokes_dir, f'line{line_num:02d}.npy')
            np.save(strokes_path, strokes)

            results.append({
                'line_num': line_num,
                'line_image': line_img_path,
                'strokes_path': strokes_path,
                'strokes': strokes,
                'abs_points': abs_points,
                'overlay': overlay_path,
            })
            print(f"  Line {line_num}: {len(strokes)} stroke points, {len(abs_points)} abs points")
        except ValueError as e:
            print(f"  Line {line_num}: SKIPPED — {e}")

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Reconstruct online strokes from offline handwriting images.')
    parser.add_argument('--input', required=True, help='Path to a line crop image OR a full page image with --page flag')
    parser.add_argument('--output_dir', default='./stroke_output', help='Directory for output files')
    parser.add_argument('--page', action='store_true', help='If set, --input is a full page; segment it first')
    parser.add_argument('--target_points', type=int, default=450, help='Target stroke points per line (≤480)')
    parser.add_argument('--mode', choices=['auto', 'prose', 'isolated'], default='auto', help='Segmentation mode')
    parser.add_argument('--ink_dark', action='store_true', default=True, help='Ink pixels are dark (default)')
    parser.add_argument('--ink_light', action='store_true', help='Ink pixels are light (inverted image)')
    args = parser.parse_args()

    ink_dark = not args.ink_light

    if args.page:
        print(f"Reconstructing strokes from page: {args.input}")
        results = reconstruct_page(args.input, args.output_dir, args.target_points, args.mode)
        print(f"\nDone. {len(results)} lines reconstructed → {args.output_dir}/")
    else:
        print(f"Reconstructing strokes from line image: {args.input}")
        os.makedirs(args.output_dir, exist_ok=True)
        strokes, abs_points, skeleton = reconstruct_strokes(
            args.input, target_points=args.target_points, ink_dark=ink_dark
        )
        overlay_path = os.path.join(args.output_dir, 'overlay.png')
        save_validation_overlay(args.input, abs_points, skeleton, overlay_path)

        # Save strokes as .npy
        npy_path = os.path.join(args.output_dir, 'strokes.npy')
        np.save(npy_path, strokes)
        print(f"  {len(strokes)} stroke points → {npy_path}")
        print(f"  Validation overlay → {overlay_path}")


if __name__ == '__main__':
    main()
