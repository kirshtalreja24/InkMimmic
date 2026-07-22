"""
dataset.py — shared PyTorch Dataset for the labeled character folders.

Both classifier.py and gan.py read the same on-disk layout:

    dataset/
      A/  0001.png  0002.png  ...
      B/  ...
      a/  ...
      0/  ...
      _junk/   <- ignored, see label_app.py

Each PNG is expected to be the transparent-alpha-mask format segment.py
produces (RGBA, ink = alpha channel), but this also works fine on plain
grayscale/RGB crops if you're feeding it something else.
"""

from __future__ import annotations

from pathlib import Path

import torch
from PIL import Image, ImageOps
from torch.utils.data import Dataset
from torchvision import transforms

IGNORED_DIRS = {"_junk"}

# All A-Z / a-z / 0-9, in a fixed order so label<->index mapping is stable
# across separate classifier.py and gan.py runs/checkpoints.
DEFAULT_CLASSES = list(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
)


def _load_as_grayscale(path: Path) -> Image.Image:
    """Composite transparent ink-mask PNGs onto white, then grayscale.
    Falls back gracefully if the image has no alpha channel at all."""
    img = Image.open(path)
    if img.mode == "RGBA":
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img).convert("L")
    else:
        img = img.convert("L")
    return img


def pad_to_square(img: Image.Image, size: int, fill: int = 255) -> Image.Image:
    """Resize+pad an image to a square (size x size) WITHOUT stretching it.
    Preserves the original aspect ratio, padding the shorter side with
    white so characters don't get squashed/stretched into odd proportions.

    This matters because your segmented character crops are naturally
    non-square (e.g. 71x74, 94x117, 76x61) -- a plain Resize((32,32))
    stretches each one differently, distorting shapes in ways EMNIST's
    already-square training images never had. That mismatch can make a
    real, correctly-labeled image look unfamiliar to the model.
    """
    return ImageOps.pad(img, (size, size), color=fill, method=Image.LANCZOS)


class CharacterDataset(Dataset):
    def __init__(self, dataset_dir: str, image_size: int = 32,
                 classes: list[str] | None = None):
        self.dataset_dir = Path(dataset_dir)
        self.image_size = image_size

        found = sorted(
            d.name for d in self.dataset_dir.iterdir()
            if d.is_dir() and d.name not in IGNORED_DIRS
        ) if self.dataset_dir.exists() else []

        # Use the full fixed 62-class vocabulary by default (even if you
        # don't have samples for every class yet) so class indices stay
        # stable as you label more data over time -- retraining later
        # won't silently renumber classes out from under an old checkpoint.
        self.classes = classes if classes is not None else DEFAULT_CLASSES
        self.class_to_idx = {c: i for i, c in enumerate(self.classes)}

        self.samples: list[tuple[Path, int]] = []
        for cls in found:
            if cls not in self.class_to_idx:
                continue  # unexpected folder name, e.g. a typo -- skip, don't crash
            idx = self.class_to_idx[cls]
            for f in (self.dataset_dir / cls).glob("*.png"):
                self.samples.append((f, idx))

        if not self.samples:
            raise FileNotFoundError(
                f"No labeled images found under {dataset_dir}. "
                f"Run label_app.py first."
            )

        self.transform = transforms.Compose([
            transforms.Lambda(lambda img: pad_to_square(img, image_size)),
            transforms.Lambda(lambda img: ImageOps.invert(img)),  # match EMNIST's
            # white-ink-on-black convention (our images are dark ink on white)
            transforms.ToTensor(),          # -> [0, 1]
            transforms.Normalize((0.5,), (0.5,)),  # -> [-1, 1]
        ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, label = self.samples[i]
        img = _load_as_grayscale(path)
        img = self.transform(img)
        return img, label

    def class_counts(self) -> dict[str, int]:
        counts = {c: 0 for c in self.classes}
        for _, label in self.samples:
            counts[self.classes[label]] += 1
        return counts
