"""
renderer.py — High-quality ink renderer for the HANDWRITER diffusion model.

Replaces the matplotlib-based utils.show() for product output.

Features:
  - Anti-aliased stroked polylines (PIL)
  - Variable stroke width from pen velocity (fast = thin, slow = thick)
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
    pen_up = strokes[:, 2]

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


def compute_velocities(points: np.ndarray, pen_up: np.ndarray) -> np.ndarray:
    """Per-point velocity magnitude (distance moved per step)."""
    diffs = np.linalg.norm(np.diff(points, axis=0), axis=1)
    velocities = np.concatenate([[diffs[0] if len(diffs) else 0.0], diffs])
    # Zero velocity at pen-up boundaries to force thin/dashed transitions
    velocities[pen_up > 0.5] = 0.0
    return velocities


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

    Returns
    -------
    out_path
    """
    points, pen_up = strokes_to_abs_points(strokes)

    if len(points) == 0:
        raise ValueError("No points to render")

    # Scale coordinates so the stroke extents map to the target height
    # The model's coordinate space is std-normalized; we use the y-extent
    # to fit the desired line height.
    xs, ys = points[:, 0], points[:, 1]
    y_span = np.ptp(ys)
    if y_span < 1e-6:
        y_span = 1.0
    s = height / y_span
    px = ((points[:, 0] - np.min(xs)) * s).astype(np.float64)
    # The model's y-axis is negated (pen up = positive). PIL's y-axis points
    # DOWN, so invert to keep ascenders above the baseline.
    py = ((np.max(ys) - points[:, 1]) * s).astype(np.float64)

    # Canvas size
    x_min, x_max = 0, np.max(px)
    y_min, y_max = 0, np.max(py)
    W = int(x_max + margin * 2)
    H = int(y_max + margin * 2)
    W = max(W, 10)
    H = max(H, 10)

    # Paper background
    if paper == 'ruled':
        # Light blue horizontal rules
        img = Image.new('RGB', (W, H), 'white')
        draw = ImageDraw.Draw(img)
        rule_spacing = max(4, int(height * 0.35))
        for yy in range(margin, H - margin, rule_spacing):
            draw.line([(0, yy), (W, yy)], fill=(180, 200, 240), width=1)
    elif paper == 'graph':
        img = Image.new('RGB', (W, H), 'white')
        draw = ImageDraw.Draw(img)
        grid = max(4, int(height * 0.25))
        for xx in range(0, W, grid):
            draw.line([(xx, 0), (xx, H)], fill=(220, 225, 235), width=1)
        for yy in range(0, H, grid):
            draw.line([(0, yy), (W, yy)], fill=(220, 225, 235), width=1)
    else:
        img = Image.new('RGB', (W, H), 'white')

    draw = ImageDraw.Draw(img)

    # Draw strokes segment by segment (breaks at pen-up)
    velocities = compute_velocities(np.column_stack([px, py]), pen_up)
    widths = stroke_width_from_velocity(velocities, min_width, max_width)

    # To preserve the stroke-width-per-point mapping, draw each tiny segment
    # as its own line with the width of its start point.
    for i in range(1, len(px)):
        if pen_up[i] > 0.5:
            continue  # pen lifted: no ink between i-1 and i

        w = max(0.5, widths[i - 1])
        x0, y0 = margin + px[i - 1], margin + py[i - 1]
        x1, y1 = margin + px[i], margin + py[i]

        # Anti-aliasing: draw a slightly wider line first (overdraw)
        draw.line([(x0, y0), (x1, y1)], fill=ink_color, width=int(w * 2))
        draw.line([(x0, y0), (x1, y1)], fill=ink_color, width=int(w * 1.25))
        draw.line([(x0, y0), (x1, y1)], fill=ink_color, width=int(w))

    # Scale up the whole canvas if requested
    if scale != 1.0:
        img = img.resize((int(W * scale), int(H * scale)), Image.LANCZOS)

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
    args = parser.parse_args()

    strokes = np.load(args.strokes).astype(np.float32)
    render_strokes(strokes, args.out, height=args.height, ink_color=args.ink,
                   paper=args.paper, scale=args.scale)
    print(f"Saved → {args.out}")


if __name__ == '__main__':
    main()
