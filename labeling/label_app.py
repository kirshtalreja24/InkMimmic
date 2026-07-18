"""
label_app.py — interactive labeling tool.

This is the missing piece between segment.py's output and a trainable
dataset. segment.py produces flat files like line03_word01_char01.png
with no idea *which letter* each one is -- this app shows you each
cropped character one at a time and lets you type its label, then
automatically sorts it into dataset/<label>/<file>.png (the folder
structure training/dataset.py and training/gan.py both expect).

USAGE
-----
    streamlit run label_app.py -- --chars_dir ../chars --dataset_dir ../dataset

Then open the local URL Streamlit prints (usually http://localhost:8501).

WORKFLOW
--------
- One character image shown at a time, scaled up so it's actually legible.
- Type the label (a single character: A-Z, a-z, or 0-9) and hit Enter,
  or click a quick-pick button for common ambiguous cases.
- The file is copied (not moved -- your original chars/ folder is left
  intact) into dataset/<label>/<original_filename>.
- Already-labeled files (found in ANY dataset/<label>/ folder) are
  skipped automatically, so you can safely close and reopen this app
  across multiple sessions without re-labeling anything or losing
  progress -- there's no separate progress file to keep in sync.
- A "skip / not a real character" button exists for genuine junk crops
  (stray noise that slipped through segmentation) so you don't have to
  force a label onto something that isn't actually a letter.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import streamlit as st
from PIL import Image

VALID_LABELS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")


def parse_args():
    # Streamlit swallows argv itself, so custom args must come after `--`
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]
    else:
        argv = []
    p = argparse.ArgumentParser()
    p.add_argument("--chars_dir", default="../chars", help="Folder of segment.py's raw output PNGs.")
    p.add_argument("--dataset_dir", default="../dataset", help="Output folder, organized as dataset/<label>/*.png")
    return p.parse_args(argv)


def already_labeled_filenames(dataset_dir: Path) -> set[str]:
    """Every original filename that's already been sorted into some
    dataset/<label>/ folder, so we never show it again."""
    done = set()
    if not dataset_dir.exists():
        return done
    for label_dir in dataset_dir.iterdir():
        if label_dir.is_dir():
            for f in label_dir.glob("*.png"):
                done.add(f.name)
    return done


def main():
    args = parse_args()
    chars_dir = Path(args.chars_dir)
    dataset_dir = Path(args.dataset_dir)
    dataset_dir.mkdir(parents=True, exist_ok=True)

    st.set_page_config(page_title="Handwriting Labeler", layout="centered")
    st.title("Character labeling")

    if not chars_dir.exists():
        st.error(f"chars_dir not found: {chars_dir}. Run segment.py first.")
        return

    all_files = sorted(chars_dir.glob("*.png"))
    done = already_labeled_filenames(dataset_dir)
    remaining = [f for f in all_files if f.name not in done]

    st.progress(0 if not all_files else (len(all_files) - len(remaining)) / len(all_files))
    st.caption(f"{len(all_files) - len(remaining)} / {len(all_files)} labeled")

    if not remaining:
        st.success("Nothing left to label — every crop in chars_dir has a label.")
        return

    current = remaining[0]

    # Show the crop, scaled up (these are small, tight character crops)
    img = Image.open(current)
    # Composite the transparent PNG onto white so faint strokes are visible
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(bg, img.convert("RGBA")).convert("RGB")
    display_img = composited.resize((composited.width * 4, composited.height * 4), Image.NEAREST)
    st.image(display_img)
    st.caption(current.name)

    def commit_label(label: str):
        label_dir = dataset_dir / label
        label_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(current, label_dir / current.name)
        st.rerun()

    with st.form(key="label_form", clear_on_submit=True):
        label = st.text_input("Label (single character)", max_chars=1)
        submitted = st.form_submit_button("Save & next")
        if submitted:
            if label in VALID_LABELS:
                commit_label(label)
            elif label:
                st.warning(f"'{label}' isn't A-Z, a-z, or 0-9 — not saved.")

    if st.button("Skip (not a real character / junk crop)"):
        # Recorded in its own bucket rather than silently discarded, so
        # you can spot-check later whether segmentation is leaking noise.
        junk_dir = dataset_dir / "_junk"
        junk_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(current, junk_dir / current.name)
        st.rerun()

    st.divider()
    st.caption(
        "Tip: keep this window + a reference alphabet image side by side if "
        "handwriting is ambiguous (e.g. 0/O, 1/l/I, 5/S)."
    )


if __name__ == "__main__":
    main()
