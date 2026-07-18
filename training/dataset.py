"""
dataset.py -- shared PyTorch Dataset for the labeled character folders.
"""

from __future__ import annotations

from pathlib import Path

import torch
from PIL import Image, ImageOps
from torch.utils.data import Dataset
from torchvision import transforms

IGNORED_DIRS = {"_junk"}

DEFAULT_CLASSES = list(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
)


def _load_as_grayscale(path: Path) -> Image.Image:
    img = Image.open(path)
    if img.mode == "RGBA":
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img).convert("L")
    else:
        img = img.convert("L")
    return img


def pad_to_square(img: Image.Image, size: int, fill: int = 255) -> Image.Image:
    """Resize+pad to a square WITHOUT stretching -- preserves aspect ratio,
    padding the shorter side with white so characters aren't distorted."""
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

        self.classes = classes if classes is not None else DEFAULT_CLASSES
        self.class_to_idx = {c: i for i, c in enumerate(self.classes)}

        self.samples: list[tuple[Path, int]] = []
        for cls in found:
            if cls not in self.class_to_idx:
                continue
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
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,)),
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
