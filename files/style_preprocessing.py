"""
style_preprocessing.py — Phase 2

Turns a folder of arbitrary handwriting photos into the exact tensor shape
DiffusionPen's style encoder expects. This is the "feed YOUR photo into the
style encoder" step from the pipeline doc (Phase 2), implementing the recipe
verified in Section 5.2 of InkMimic_DiffusionPen_Pipeline.docx by reading
train.py + utils/auxilary_functions.py directly.

Recipe (per reference image):
    1. Open as RGB
    2. Resize so height == 64px, preserving aspect ratio
    3. If width < 256px: pad with white to exactly 256x64
    4. If width > 256px: shrink in 20px steps, then center-pad to 256x64
    5. ToTensor() + Normalize((0.5,0.5,0.5), (0.5,0.5,0.5))  <- matches
       train.py's `transform` exactly (line ~595-598 of the source)

This module has ZERO dependency on the DiffusionPen repo itself — it only
needs PIL/torchvision — so you can unit-test it in isolation before wiring
it into inference.py.
"""

from __future__ import annotations

import glob
import os
from typing import List

import torch
from PIL import Image, ImageOps
from torchvision import transforms

TARGET_H = 64
TARGET_W = 256

# Identical to the `transform` object built in train.py — do not change
# these normalization constants, they must match what the pretrained style
# encoder was trained on.
STYLE_TRANSFORM = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
])


def _shrink_to_width(img: Image.Image, max_width: int = TARGET_W, step: int = 20) -> Image.Image:
    """Shrink in 20px steps until width <= max_width (mirrors the while-loop
    in train.py's sampling(), which calls image_resize_PIL repeatedly rather
    than resizing directly to the target in one shot)."""
    w, h = img.size
    while w > max_width:
        w = max(w - step, 1)
        scale = w / img.size[0]
        new_h = int(img.size[1] * scale)
        img = img.resize((w, new_h))
        w, h = img.size
    return img


def preprocess_style_image(path: str) -> Image.Image:
    """Implements Section 5.2 steps 1-4. Returns a PIL Image, exactly
    256x64, white-padded, RGB."""
    img = Image.open(path).convert("RGB")
    w, h = img.size

    # Step 2: resize so height == 64, preserving aspect ratio
    new_w = max(int(w * TARGET_H / h), 1)
    img = img.resize((new_w, TARGET_H))
    w, _ = img.size

    if w < TARGET_W:
        # Step 3: pad with white to exactly 256x64
        img = ImageOps.pad(img, size=(TARGET_W, TARGET_H), color="white")
    else:
        # Step 4: shrink in 20px steps, then center-pad
        img = _shrink_to_width(img, TARGET_W)
        img = ImageOps.pad(img, size=(TARGET_W, TARGET_H), color="white", centering=(0.5, 0.5))

    return img


def load_style_batch(image_dir: str, num_samples: int = 5, seed: int | None = None) -> torch.Tensor:
    """
    Loads every image in `image_dir`, preprocesses each with
    preprocess_style_image(), and returns a tensor of shape (num_samples, 3, 64, 256)
    ready to hand to the style encoder.

    - If image_dir has >= num_samples images, `num_samples` are sampled.
    - If it has fewer (down to 1), images are repeated to fill num_samples —
      the model architecture hard-expects exactly 5 (see unet.py's
      `y.reshape(b, 5, -1)`), so this always returns exactly num_samples.

    Raises FileNotFoundError if the directory has zero usable images.
    """
    import random

    exts = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.webp")
    paths: List[str] = []
    for ext in exts:
        paths.extend(glob.glob(os.path.join(image_dir, ext)))
        paths.extend(glob.glob(os.path.join(image_dir, ext.upper())))
    paths = sorted(set(paths))

    if not paths:
        raise FileNotFoundError(
            f"No images found in {image_dir!r}. Expected .png/.jpg/.jpeg/.bmp/.webp files."
        )

    rng = random.Random(seed)
    if len(paths) >= num_samples:
        chosen = rng.sample(paths, num_samples)
    else:
        # repeat-with-wraparound so we always end up with exactly num_samples
        chosen = [paths[i % len(paths)] for i in range(num_samples)]

    tensors = []
    for p in chosen:
        pil_img = preprocess_style_image(p)
        tensors.append(STYLE_TRANSFORM(pil_img))

    batch = torch.stack(tensors, dim=0)  # (num_samples, 3, 64, 256)
    assert batch.shape == (num_samples, 3, TARGET_H, TARGET_W), batch.shape
    return batch


if __name__ == "__main__":
    # Quick standalone smoke test — run this BEFORE touching inference.py.
    # Usage: python style_preprocessing.py /path/to/folder/of/handwriting/photos
    import sys

    if len(sys.argv) != 2:
        print("Usage: python style_preprocessing.py <image_dir>")
        raise SystemExit(1)

    batch = load_style_batch(sys.argv[1], num_samples=5, seed=0)
    print(f"OK — produced batch of shape {tuple(batch.shape)}, "
          f"dtype={batch.dtype}, range=[{batch.min():.3f}, {batch.max():.3f}]")
