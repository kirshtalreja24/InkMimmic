"""
classifier.py — CNN classifier for handwritten characters.

Two jobs, both useful before you get to the GAN:

1. TRAIN on whatever you've hand-labeled so far with label_app.py. Even a
   small hand-labeled set is enough to get this working -- it doesn't
   need your full 1,860-image target to be useful.

2. AUTO-LABEL a new batch of raw segment.py crops using that trained
   classifier, sorting its *predictions* into dataset_auto/<label>/ for
   you to quickly eyeball and correct, rather than labeling every new
   page from scratch by hand. This is the practical way to scale up to
   a bigger dataset without linearly scaling your own labeling time.

Architecture is intentionally small (this is 32x32 grayscale glyphs, not
ImageNet) -- a few conv blocks is plenty and trains fast even on CPU.

USAGE
-----
    # Train on your hand-labeled dataset/
    python classifier.py train --dataset_dir ../dataset --epochs 15 --out classifier.pt

    # Use the trained classifier to auto-label a new folder of raw crops
    python classifier.py auto_label --checkpoint classifier.pt \\
        --chars_dir ../chars_new_page --out_dir ../dataset_auto --min_confidence 0.6
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, random_split

from dataset import CharacterDataset, DEFAULT_CLASSES, _load_as_grayscale, pad_to_square, label_to_folder
from torchvision import transforms


class SmallCNN(nn.Module):
    def __init__(self, num_classes: int = 62):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(2),  # 32 -> 16

            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2),  # 16 -> 8

            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.features(x)
        x = torch.flatten(x, 1)
        return self.classifier(x)


def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    full_ds = CharacterDataset(args.dataset_dir, image_size=32)
    print(f"Loaded {len(full_ds)} labeled samples across {len(full_ds.classes)} possible classes.")
    counts = full_ds.class_counts()
    populated = {c: n for c, n in counts.items() if n > 0}
    print(f"Classes with at least 1 sample: {len(populated)} / {len(full_ds.classes)}")
    sparse = {c: n for c, n in populated.items() if n < 5}
    if sparse:
        print(f"WARNING: these classes have <5 samples, accuracy on them will be unreliable: {sparse}")

    val_size = max(1, int(len(full_ds) * 0.15))
    train_size = len(full_ds) - val_size
    train_ds, val_ds = random_split(full_ds, [train_size, val_size])

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size)

    model = SmallCNN(num_classes=len(full_ds.classes)).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)

    best_val_acc = 0.0
    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            opt.zero_grad()
            logits = model(imgs)
            loss = F.cross_entropy(logits, labels)
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
        print(f"epoch {epoch:3d}/{args.epochs}  train_loss={total_loss/len(train_ds):.4f}  val_acc={val_acc:.3f}")

    torch.save({"model_state": model.state_dict(), "classes": full_ds.classes}, args.out)
    print(f"Saved checkpoint to {args.out} (best val_acc during training: {best_val_acc:.3f})")


def auto_label(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.checkpoint, map_location=device)
    classes = ckpt["classes"]
    model = SmallCNN(num_classes=len(classes)).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    tfm = transforms.Compose([
        transforms.Lambda(lambda img: pad_to_square(img, 32, fill=0)),
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,)),
    ])

    chars_dir = Path(args.chars_dir)
    out_dir = Path(args.out_dir)
    low_conf_dir = out_dir / "_low_confidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    low_conf_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(chars_dir.glob("*.png"))
    print(f"Auto-labeling {len(files)} crops from {chars_dir} ...")

    n_confident = 0
    with torch.no_grad():
        for f in files:
            img = _load_as_grayscale(f)
            x = tfm(img).unsqueeze(0).to(device)
            probs = F.softmax(model(x), dim=1)[0]
            conf, pred_idx = probs.max(dim=0)
            conf = conf.item()
            label = classes[pred_idx.item()]

            if conf >= args.min_confidence:
                dest = out_dir / label_to_folder(label)
                n_confident += 1
            else:
                # Uncertain predictions go in their own bucket for manual
                # review rather than silently mislabeling your dataset.
                dest = low_conf_dir
            dest.mkdir(parents=True, exist_ok=True)
            img.save(dest / f.name)

    print(f"Done. {n_confident}/{len(files)} labeled with confidence >= {args.min_confidence}.")
    print(f"The rest are in {low_conf_dir} for manual review -- "
          f"open label_app.py pointed at that folder to sort them by hand.")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)

    p_train = sub.add_parser("train")
    p_train.add_argument("--dataset_dir", default="../dataset")
    p_train.add_argument("--epochs", type=int, default=15)
    p_train.add_argument("--batch_size", type=int, default=32)
    p_train.add_argument("--lr", type=float, default=1e-3)
    p_train.add_argument("--out", default="classifier.pt")

    p_auto = sub.add_parser("auto_label")
    p_auto.add_argument("--checkpoint", default="classifier.pt")
    p_auto.add_argument("--chars_dir", required=True)
    p_auto.add_argument("--out_dir", default="../dataset_auto")
    p_auto.add_argument("--min_confidence", type=float, default=0.6)

    args = p.parse_args()
    if args.command == "train":
        train(args)
    else:
        auto_label(args)


if __name__ == "__main__":
    main()
