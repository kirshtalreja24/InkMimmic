"""
train_emnist.py -- train the SAME SmallCNN architecture from classifier.py,
but on the EMNIST ByClass dataset (700k+ real handwritten samples, 62
classes: 0-9, A-Z, a-z) instead of your small hand-labeled dataset/.
"""

from __future__ import annotations

import argparse
import gzip
import struct

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from torchvision import transforms

from classifier import SmallCNN
from dataset import DEFAULT_CLASSES, CharacterDataset

EMNIST_BYCLASS_ORDER = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")


def _parse_idx_images(path: str) -> np.ndarray:
    with gzip.open(path, "rb") as f:
        magic, num, rows, cols = struct.unpack(">IIII", f.read(16))
        assert magic == 2051, f"Bad magic number for images file: {magic} (expected 2051)"
        data = np.frombuffer(f.read(), dtype=np.uint8)
        return data.reshape(num, rows, cols)


def _parse_idx_labels(path: str) -> np.ndarray:
    with gzip.open(path, "rb") as f:
        magic, num = struct.unpack(">II", f.read(8))
        assert magic == 2049, f"Bad magic number for labels file: {magic} (expected 2049)"
        return np.frombuffer(f.read(), dtype=np.uint8)


def _download_emnist_raw_files(repo_id: str = "Royc30ne/emnist-byclass") -> dict:
    from huggingface_hub import hf_hub_download

    filenames = {
        "train_images": "emnist-byclass-train-images-idx3-ubyte.gz",
        "train_labels": "emnist-byclass-train-labels-idx1-ubyte.gz",
        "test_images": "emnist-byclass-test-images-idx3-ubyte.gz",
        "test_labels": "emnist-byclass-test-labels-idx1-ubyte.gz",
    }
    paths = {}
    for key, filename in filenames.items():
        print(f"  fetching {filename} ...")
        paths[key] = hf_hub_download(repo_id=repo_id, filename=filename, repo_type="dataset")
    return paths


class EMNISTAsCharacterDataset(Dataset):
    def __init__(self, images, labels, image_size=32):
        self.images = images
        char_to_default_idx = {c: i for i, c in enumerate(DEFAULT_CLASSES)}
        self.labels = np.array(
            [char_to_default_idx[EMNIST_BYCLASS_ORDER[l]] for l in labels],
            dtype=np.int64,
        )
        self.transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,)),
        ])

    def __len__(self):
        return len(self.images)

    def __getitem__(self, i):
        img = self.images[i]
        img = np.transpose(img)
        img = Image.fromarray(img, mode="L")
        img = self.transform(img)
        return img, self.labels[i]


def train_on_emnist(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    print("Downloading EMNIST ByClass raw files via huggingface_hub...")
    paths = _download_emnist_raw_files()

    print("Parsing IDX files...")
    X_train = _parse_idx_images(paths["train_images"])
    y_train = _parse_idx_labels(paths["train_labels"])
    X_test = _parse_idx_images(paths["test_images"])
    y_test = _parse_idx_labels(paths["test_labels"])

    if args.max_train_samples and args.max_train_samples < len(X_train):
        rng = np.random.default_rng(0)
        idx = rng.choice(len(X_train), size=args.max_train_samples, replace=False)
        X_train, y_train = X_train[idx], y_train[idx]
    if args.max_test_samples and args.max_test_samples < len(X_test):
        rng = np.random.default_rng(0)
        idx = rng.choice(len(X_test), size=args.max_test_samples, replace=False)
        X_test, y_test = X_test[idx], y_test[idx]
    print(f"EMNIST train: {len(X_train)} images, test: {len(X_test)} images, 62 classes")

    sample_std = X_train[:1000].astype(np.float32).std()
    print(f"Sanity check -- pixel std-dev on a 1000-image sample: {sample_std:.2f} "
          f"(expect roughly 60-90 for real EMNIST; a value near 0 means corrupted/blank data)")
    if sample_std < 10:
        raise RuntimeError(
            "Downloaded EMNIST data looks corrupted or blank (near-zero pixel "
            "variance). Do not proceed with training on this."
        )

    sample_path = "emnist_sample_check.png"
    Image.fromarray(np.transpose(X_train[0]), mode="L").save(sample_path)
    print(f"Saved a sample training image to {sample_path} -- open it now and confirm "
          f"it's a legible, correctly-oriented character before waiting through full "
          f"training. (label for this sample: {EMNIST_BYCLASS_ORDER[y_train[0]]!r})")

    train_ds = EMNISTAsCharacterDataset(X_train, y_train)
    test_ds = EMNISTAsCharacterDataset(X_test, y_test)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=2)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, num_workers=2)

    model = SmallCNN(num_classes=len(DEFAULT_CLASSES)).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        n_seen = 0
        n_batches = len(train_loader)
        for batch_i, (imgs, labels) in enumerate(train_loader, start=1):
            imgs, labels = imgs.to(device), labels.to(device)
            opt.zero_grad()
            logits = model(imgs)
            loss = F.cross_entropy(logits, labels)
            loss.backward()
            opt.step()
            total_loss += loss.item() * imgs.size(0)
            n_seen += imgs.size(0)
            if batch_i % 20 == 0 or batch_i == n_batches:
                print(f"  epoch {epoch}/{args.epochs}  batch {batch_i}/{n_batches}  running_loss={total_loss/n_seen:.4f}", flush=True)

        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for imgs, labels in test_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                preds = model(imgs).argmax(dim=1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)
        val_acc = correct / max(total, 1)
        print(f"epoch {epoch:3d}/{args.epochs}  train_loss={total_loss/n_seen:.4f}  test_acc={val_acc:.3f}")

    torch.save({"model_state": model.state_dict(), "classes": DEFAULT_CLASSES}, args.out)
    print(f"Saved EMNIST-trained checkpoint to {args.out}")
    return model, device


def finetune_on_own_data(model, device, args):
    print(f"\nFine-tuning on your own data: {args.finetune_dir}")
    full_ds = CharacterDataset(args.finetune_dir, image_size=32)
    print(f"Loaded {len(full_ds)} of your own labeled samples for fine-tuning.")

    from collections import Counter
    label_counts = Counter(label for _, label in full_ds.samples)
    print("Fine-tune set class balance (top 5 largest):",
          sorted(label_counts.items(), key=lambda x: -x[1])[:5])

    num_classes = len(full_ds.classes)
    class_weights = torch.ones(num_classes)
    for cls_idx, count in label_counts.items():
        class_weights[cls_idx] = 1.0 / count
    class_weights = class_weights / class_weights.sum() * num_classes
    class_weights = class_weights.to(device)

    val_size = max(1, int(len(full_ds) * 0.15))
    train_size = len(full_ds) - val_size
    from torch.utils.data import random_split
    train_ds, val_ds = random_split(full_ds, [train_size, val_size])

    loader = DataLoader(train_ds, batch_size=min(args.batch_size, len(train_ds)), shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=min(args.batch_size, len(val_ds)))
    opt = torch.optim.Adam(model.parameters(), lr=args.finetune_lr)

    best_val_acc = 0.0
    for epoch in range(1, args.finetune_epochs + 1):
        model.train()
        total_loss = 0.0
        for imgs, labels in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            opt.zero_grad()
            logits = model(imgs)
            loss = F.cross_entropy(logits, labels, weight=class_weights)
            loss.backward()
            opt.step()
            total_loss += loss.item() * imgs.size(0)

        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                preds = model(imgs).argmax(dim=1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)
        val_acc = correct / max(total, 1)
        best_val_acc = max(best_val_acc, val_acc)
        print(f"finetune epoch {epoch:3d}/{args.finetune_epochs}  "
              f"train_loss={total_loss/len(train_ds):.4f}  val_acc={val_acc:.3f}")

    print(f"Best val_acc during fine-tuning: {best_val_acc:.3f} "
          f"(if this is low/near-random, more/more-balanced data is needed "
          f"before fine-tuning helps -- see the class balance line above)")

    torch.save({"model_state": model.state_dict(), "classes": DEFAULT_CLASSES}, args.out)
    print(f"Saved fine-tuned checkpoint to {args.out}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--batch_size", type=int, default=128)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--out", default="classifier_emnist.pt")
    p.add_argument("--max_train_samples", type=int, default=None)
    p.add_argument("--max_test_samples", type=int, default=None)
    p.add_argument("--finetune_dir", default=None)
    p.add_argument("--finetune_epochs", type=int, default=10)
    p.add_argument("--finetune_lr", type=float, default=1e-4)

    args = p.parse_args()
    model, device = train_on_emnist(args)
    if args.finetune_dir:
        finetune_on_own_data(model, device, args)


if __name__ == "__main__":
    main()
