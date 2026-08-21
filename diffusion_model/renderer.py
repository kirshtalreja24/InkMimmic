"""

renderer.py — High-quality ink renderer for the HANDWRITER diffusion model.

Replaces the matplotlib-based utils.show() for product output.

Features:
  - Catmull-Rom spline smoothing between the model's raw points, so curves
    read as flowing pen strokes instead of the straight-edged polygon you
    get from connecting ~16 points/character with straight lines
  - Supersampled rendering (draw at N x resolution, downsample with
    LANCZOS) for real anti-aliased edges, replacing the old same-color
    overdraw trick which fattened lines without actually softening them
  - Variable stroke width from pen velocity (fast = thin, slow = thick),
    with rounded joints so width changes don't leave gaps at sharp turns
  - Configurable ink color + paper background (blank / ruled / graph)
  - Margins + DPI control
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(THIS_DIR))


def strokes_to_abs_points(strokes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert differential (dx, dy, pen_up) strokes to absolute (x, y) points.

    Returns (points [N,2], pen_up [N]).
    """
    coords = strokes[:, :2]
    pen_up = np.asarray(strokes[:, 2]).reshape(-1)

    # Cumulative sum — but reset at pen-up boundaries so "pen in air" jumps
    # don't produce one long connected line.
    points = np.zeros_like(coords, dtype=np.float64)
    points[0] = coords[0]
    for i in range(1, len(coords)):
        points[i] = points[i - 1] + coords[i]

    # Normalize to a reasonable pixel scale: the model's coordinate space is
    # roughly unit-scale (std-normalized), so map to line height in pixels.
    # We keep a constant scale here and let the caller set line height.
    return points, pen_up


def stroke_width_from_velocity(
    velocities: np.ndarray,
    min_width: float = 1.0,
    max_width: float = 3.5,
) -> np.ndarray:
    """Map velocities to stroke widths (fast = thin, slow = thick)."""
    v_safe = velocities.copy()
    v_range = np.percentile(v_safe[v_safe > 0], 90) if np.any(v_safe > 0) else 1.0
    v_range = max(v_range, 1e-6)

    # Normalize so 0 → thick, high velocity → thin
    widths = max_width - (max_width - min_width) * (v_safe / v_range)
    widths = np.clip(widths, min_width, max_width)
    return widths


def _split_pen_down_segments(pen_up: np.ndarray) -> list[tuple[int, int]]:
    """Group point indices into contiguous pen-down runs (end exclusive),
    dropping single-point runs (nothing to draw a line between)."""
    n = len(pen_up)
    segments = []
    start = 0
    for i in range(1, n):
        if pen_up[i] > 0.5:
            if i - start >= 2:
                segments.append((start, i))
            start = i
    if n - start >= 2:
        segments.append((start, n))
    return segments


def _catmull_rom_smooth(points: np.ndarray, samples_per_span: int = 8) -> np.ndarray:
    """Densify one pen-down segment via Catmull-Rom spline interpolation.

    The model outputs roughly one point per ~1/16th of a character, which
    is sparse enough that connecting them with straight lines produces
    visibly faceted, robotic-looking letters. Interpolating a smooth curve
    through the same points (rather than just adding more straight
    segments) is what makes the rendered ink look hand-drawn.
    """
    n = len(points)
    if n < 3:
        return points.astype(np.float64)

    # Duplicate the endpoints so the spline has a defined tangent there.
    ext = np.vstack([points[0], points, points[-1]])  # length n + 2

    out = [points[0].astype(np.float64)]
    for i in range(n - 1):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for t in np.linspace(0, 1, samples_per_span, endpoint=True)[1:]:
            t2, t3 = t * t, t * t * t
            pt = 0.5 * (
                (2 * p1)
                + (-p0 + p2) * t
                + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
            )
            out.append(pt)
    return np.array(out)


def render_strokes(
    strokes: np.ndarray,
    out_path: str,
    height: int = 128,
    ink_color: str = '#1a1a2e',
    paper: str = 'white',
    scale: float = 1.0,
    min_width: float = 1.0,
    max_width: float = 3.5,
    margin: int = 8,
    line_spacing: float = 1.6,
    smooth: bool = True,
    supersample: int = 3,
) -> str:
    """Render a stroke sequence to a PNG using PIL.

    Parameters
    ----------
    strokes : (N, 3) float32 — (dx, dy, pen_up)
    out_path : where to save the PNG
    height : line height in px (render scale)
    ink_color : hex color for ink
    paper : 'white' | 'ruled' | 'graph'
    scale : additional output scale multiplier
    min_width / max_width : stroke width bounds in px
    margin : page margin in px
    line_spacing : line spacing as multiple of height (for multi-line pages)
    smooth : apply Catmull-Rom curve smoothing (set False to get the old
        straight-segment look, e.g. for debugging raw model output)
    supersample : draw at this many times the target resolution, then
        downsample with LANCZOS for anti-aliased edges (1 disables it)

    Returns
    -------
    out_path
    """
    points, pen_up = strokes_to_abs_points(strokes)

    if len(points) == 0:
        raise ValueError("No points to render")

    # Guard against pen_up not having exactly one entry per point (seen with
    # some short/edge-case stroke sequences from the model).
    pen_up = np.asarray(pen_up).reshape(-1)
    if pen_up.shape[0] != points.shape[0]:
        n = points.shape[0]
        if pen_up.shape[0] > n:
            pen_up = pen_up[:n]
        else:
            pen_up = np.concatenate([pen_up, np.zeros(n - pen_up.shape[0], dtype=pen_up.dtype)])

    # Scale coordinates so the stroke extents map to the target height
    xs, ys = points[:, 0], points[:, 1]
    y_span = np.ptp(ys)
    if y_span < 1e-6:
        y_span = 1.0
    s = height / y_span
    px = ((points[:, 0] - np.min(xs)) * s).astype(np.float64)
    # The model's y-axis is negated (pen up = positive). PIL's y-axis points
    # DOWN, so invert to keep ascenders above the baseline.
    py = ((np.max(ys) - points[:, 1]) * s).astype(np.float64)

    # Canvas size, at the FINAL (post-scale) resolution
    W = max(int(np.max(px) + margin * 2), 10)
    H = max(int(np.max(py) + margin * 2), 10)

    SS = max(1, int(supersample))
    cW, cH = W * SS, H * SS

    # Paper background, drawn at the supersampled resolution
    if paper == 'ruled':
        img = Image.new('RGB', (cW, cH), 'white')
        draw = ImageDraw.Draw(img)
        rule_spacing = max(4, int(height * 0.35)) * SS
        for yy in range(margin * SS, cH - margin * SS, rule_spacing):
            draw.line([(0, yy), (cW, yy)], fill=(180, 200, 240), width=max(1, SS))
    elif paper == 'graph':
        img = Image.new('RGB', (cW, cH), 'white')
        draw = ImageDraw.Draw(img)
        grid = max(4, int(height * 0.25)) * SS
        for xx in range(0, cW, grid):
            draw.line([(xx, 0), (xx, cH)], fill=(220, 225, 235), width=max(1, SS))
        for yy in range(0, cH, grid):
            draw.line([(0, yy), (cW, yy)], fill=(220, 225, 235), width=max(1, SS))
    else:
        img = Image.new('RGB', (cW, cH), 'white')

    draw = ImageDraw.Draw(img)

    for start, end in _split_pen_down_segments(pen_up):
        seg = np.column_stack([px[start:end], py[start:end]]) * SS

        if smooth and len(seg) >= 3:
            seg = _catmull_rom_smooth(seg)

        diffs = np.diff(seg, axis=0)
        velocities = np.linalg.norm(diffs, axis=1)
        velocities = np.concatenate([[velocities[0] if len(velocities) else 0.0], velocities])
        widths = stroke_width_from_velocity(velocities, min_width * SS, max_width * SS)

        for i in range(1, len(seg)):
            w = max(1.0, widths[i - 1])
            x0, y0 = margin * SS + seg[i - 1]
            x1, y1 = margin * SS + seg[i]
            draw.line([(x0, y0), (x1, y1)], fill=ink_color, width=int(round(w)))
            # Round the joint so variable width doesn't leave visible gaps
            # at sharp turns between adjacent segments.
            r = w / 2
            draw.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=ink_color)

    final_W, final_H = max(1, int(W * scale)), max(1, int(H * scale))
    img = img.resize((final_W, final_H), Image.LANCZOS)

    img.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Render stroke sequences to PNG.')
    parser.add_argument('--strokes', required=True, help='Path to .npy stroke file (N,3)')
    parser.add_argument('--out', default='rendered.png')
    parser.add_argument('--height', type=int, default=128, help='Line height in px')
    parser.add_argument('--ink', default='#1a1a2e', help='Ink color (hex)')
    parser.add_argument('--paper', choices=['white', 'ruled', 'graph'], default='white')
    parser.add_argument('--scale', type=float, default=1.0)
    parser.add_argument('--no-smooth', action='store_true', help='Disable Catmull-Rom smoothing')
    parser.add_argument('--supersample', type=int, default=3, help='Anti-aliasing supersample factor')
    args = parser.parse_args()

    strokes = np.load(args.strokes).astype(np.float32)
    render_strokes(strokes, args.out, height=args.height, ink_color=args.ink,
                   paper=args.paper, scale=args.scale, smooth=not args.no_smooth,
                   supersample=args.supersample)
    print(f"Saved -> {args.out}")


if __name__ == '__main__':
    main()
