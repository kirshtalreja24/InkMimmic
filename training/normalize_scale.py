"""
normalize_scale.py -- fixes a real accuracy problem: telling lowercase
from uppercase for letters that are nearly the same SHAPE.
"""

from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path

from PIL import Image

CANVAS_SIZE = 64
TARGET_REF_HEIGHT = 48


def normalize_folder(chars_dir: Path, output_dir: Path,
                      canvas_size: int = CANVAS_SIZE,
                      target_ref_height: int = TARGET_REF_HEIGHT) -> None:
    manifest_path = chars_dir / "manifest.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"No manifest.csv in {chars_dir} -- this must be a raw segment.py "
            f"output folder, not something already merged into dataset/."
        )

    with open(manifest_path, newline="") as f:
        rows = list(csv.DictReader(f))

    heights = [int(r["height"]) for r in rows if r["height"]]
    if not heights:
        raise ValueError(f"manifest.csv in {chars_dir} has no height data.")

    page_ref_height = statistics.median(heights)
    scale = target_ref_height / page_ref_height
    print(f"{chars_dir}: {len(rows)} crops, page reference height={page_ref_height:.1f}px, "
          f"scale factor={scale:.3f}")

    output_dir.mkdir(parents=True, exist_ok=True)
    n_done = 0
    n_missing = 0

    actual_files = {f.name: f for f in chars_dir.glob("*.png")}
    suffix_lookup: dict[str, Path] = {}
    for name, path in actual_files.items():
        suffix_lookup.setdefault(name, path)
    for name, path in actual_files.items():
        for r in rows:
            if name.endswith(r["filename"]) and r["filename"] not in suffix_lookup:
                suffix_lookup[r["filename"]] = path

    for r in rows:
        src_path = actual_files.get(r["filename"]) or suffix_lookup.get(r["filename"])
        if src_path is None or not src_path.exists():
            n_missing += 1
            continue

        img = Image.open(src_path)
        w, h = img.size
        new_w = max(1, round(w * scale))
        new_h = max(1, round(h * scale))
        new_w = min(new_w, canvas_size)
        new_h = min(new_h, canvas_size)

        resized = img.resize((new_w, new_h), Image.LANCZOS)

        if resized.mode == "RGBA":
            canvas = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
        else:
            canvas = Image.new("RGB", (canvas_size, canvas_size), (255, 255, 255))
        offset = ((canvas_size - new_w) // 2, (canvas_size - new_h) // 2)
        canvas.paste(resized, offset, resized if resized.mode == "RGBA" else None)

        canvas.save(output_dir / src_path.name)
        n_done += 1

    if n_missing:
        print(f"WARNING: {n_missing} manifest entries had no matching file on disk -- skipped.")

    import shutil
    shutil.copy(manifest_path, output_dir / "manifest.csv")

    print(f"Wrote {n_done} scale-normalized crops to {output_dir}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--chars_dir", required=True)
    p.add_argument("--output_dir", required=True)
    p.add_argument("--canvas_size", type=int, default=CANVAS_SIZE)
    p.add_argument("--target_ref_height", type=int, default=TARGET_REF_HEIGHT)
    args = p.parse_args()

    normalize_folder(
        Path(args.chars_dir), Path(args.output_dir),
        canvas_size=args.canvas_size, target_ref_height=args.target_ref_height,
    )


if __name__ == "__main__":
    main()
