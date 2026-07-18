"""
train_emnist.py -- train the SAME SmallCNN architecture from classifier.py,
but on the EMNIST ByClass dataset (700k+ real handwritten samples, 62
classes: 0-9, A-Z, a-z) instead of your small hand-labeled dataset/.
"""

from __future__ import annotations

import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from torchvision import transforms

from classifier import SmallCNN
from dataset import DEFAULT_CLASSES, CharacterDataset

EMNIST_BYCLASS_ORDER = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")


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
    from torchvision.datasets import EMNIST

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    print("Loading EMNIST ByClass (cached locally if already downloaded)...")
    raw_train = EMNIST(root=args.emnist_root, split="byclass", train=True, download=True)
    raw_test = EMNIST(root=args.emnist_root, split="byclass", train=False, download=True)

    X_train = raw_train.data.numpy()
    y_train = raw_train.targets.numpy()
    X_test = raw_test.data.numpy()
    y_test = raw_test.targets.numpy()

    if args.max_train_samples and args.max_train_samples < len(X_train):
        rng = np.random.default_rng(0)
        idx = rng.choice(len(X_train), size=args.max_train_samples, replace=False)
        X_train, y_train = X_train[idx], y_train[idx]
    if args.max_test_samples and args.max_test_samples < len(X_test):
        rng = np.random.default_rng(0)
        idx = rng.choice(len(X_test), size=args.max_test_samples, replace=False)
        X_test, y_test = X_test[idx], y_test[idx]
    print(f"EMNIST train: {len(X_train)} images, test: {len(X_test)} images, 62 classes")

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
    own_ds = CharacterDataset(args.finetune_dir, image_size=32)
    print(f"Loaded {len(own_ds)} of your own labeled samples for fine-tuning.")

    loader = DataLoader(own_ds, batch_size=min(args.batch_size, len(own_ds)), shuffle=True)
    opt = torch.optim.Adam(model.parameters(), lr=args.finetune_lr)

    model.train()
    for epoch in range(1, args.finetune_epochs + 1):
        total_loss = 0.0
        for imgs, labels in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            opt.zero_grad()
            logits = model(imgs)
            loss = F.cross_entropy(logits, labels)
            loss.backward()
            opt.step()
            total_loss += loss.item() * imgs.size(0)
        print(f"finetune epoch {epoch:3d}/{args.finetune_epochs}  train_loss={total_loss/len(own_ds):.4f}")

    torch.save({"model_state": model.state_dict(), "classes": DEFAULT_CLASSES}, args.out)
    print(f"Saved fine-tuned checkpoint to {args.out}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--batch_size", type=int, default=128)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--out", default="classifier_emnist.pt")
    p.add_argument("--emnist_root", default="./emnist_data")
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
