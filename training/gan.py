"""
gan.py — class-conditional GAN for generating new instances of YOUR
handwritten characters.

This is Phase 1 from the roadmap ("Character-level Conditional GAN").
Conditioning on class label (which letter/digit) means one single model
learns all 62 classes together, and at generation time you tell it which
character you want:

    z (random noise) + class label  --Generator-->  new character image
    (image, class label)            --Discriminator--> real or fake?

Personalization is implicit here, not a separate mechanism: every
training image comes from your own handwriting samples, so everything
the model learns to generate is drawn from your style specifically --
unlike a model pretrained on many different people's handwriting.

This is a DCGAN-style architecture (standard, well-documented, known to
train reasonably stably at small image sizes like the 32x32 used here).
GANs are notoriously fussier to train than a straightforward classifier
-- expect to babysit this more, and see the troubleshooting notes at the
bottom of this file if generated images collapse to noise or to one
repeated pattern (mode collapse).

USAGE
-----
    python gan.py --dataset_dir ../dataset --epochs 200 --out generator.pt

Strongly recommended to run this in Colab with a GPU (same as the
DiffusionPen work) rather than locally -- even this small a GAN benefits
a lot from GPU, and 200+ epochs on CPU will be slow.
"""

from __future__ import annotations

import argparse
import os

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision.utils import save_image

from dataset import CharacterDataset

IMAGE_SIZE = 32
NOISE_DIM = 100
EMBED_DIM = 32


class Generator(nn.Module):
    def __init__(self, num_classes: int, noise_dim: int = NOISE_DIM, embed_dim: int = EMBED_DIM):
        super().__init__()
        self.label_embed = nn.Embedding(num_classes, embed_dim)
        in_dim = noise_dim + embed_dim

        # Project to a small spatial feature map, then upsample via
        # transposed convolutions: 4x4 -> 8x8 -> 16x16 -> 32x32
        self.project = nn.Sequential(
            nn.Linear(in_dim, 256 * 4 * 4),
            nn.BatchNorm1d(256 * 4 * 4),
            nn.ReLU(True),
        )
        self.net = nn.Sequential(
            nn.ConvTranspose2d(256, 128, 4, 2, 1), nn.BatchNorm2d(128), nn.ReLU(True),  # 4->8
            nn.ConvTranspose2d(128, 64, 4, 2, 1), nn.BatchNorm2d(64), nn.ReLU(True),    # 8->16
            nn.ConvTranspose2d(64, 1, 4, 2, 1),                                          # 16->32
            nn.Tanh(),  # matches dataset.py's [-1, 1] normalization
        )

    def forward(self, z, labels):
        c = self.label_embed(labels)
        x = torch.cat([z, c], dim=1)
        x = self.project(x).view(-1, 256, 4, 4)
        return self.net(x)


class Discriminator(nn.Module):
    def __init__(self, num_classes: int, embed_dim: int = EMBED_DIM):
        super().__init__()
        self.label_embed = nn.Embedding(num_classes, embed_dim)
        self.label_proj = nn.Linear(embed_dim, IMAGE_SIZE * IMAGE_SIZE)

        self.net = nn.Sequential(
            nn.Conv2d(2, 64, 4, 2, 1), nn.LeakyReLU(0.2, True),        # 32->16
            nn.Conv2d(64, 128, 4, 2, 1), nn.BatchNorm2d(128), nn.LeakyReLU(0.2, True),  # 16->8
            nn.Conv2d(128, 256, 4, 2, 1), nn.BatchNorm2d(256), nn.LeakyReLU(0.2, True), # 8->4
            nn.Conv2d(256, 1, 4, 1, 0),  # 4->1
        )

    def forward(self, img, labels):
        c = self.label_embed(labels)
        c_map = self.label_proj(c).view(-1, 1, IMAGE_SIZE, IMAGE_SIZE)
        x = torch.cat([img, c_map], dim=1)
        return self.net(x).view(-1)


def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    if device.type == "cpu":
        print("WARNING: no GPU detected. This will be slow -- Colab is strongly recommended, "
              "same as we used for DiffusionPen.")

    ds = CharacterDataset(args.dataset_dir, image_size=IMAGE_SIZE)
    print(f"Training on {len(ds)} labeled images across {len(ds.classes)} possible classes.")
    counts = ds.class_counts()
    empty = [c for c, n in counts.items() if n == 0]
    if empty:
        print(f"NOTE: {len(empty)} classes have zero samples ({''.join(empty)}). "
              f"The GAN can still train on the rest, but you won't be able to "
              f"generate those characters until you label some.")

    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=True, drop_last=True)

    num_classes = len(ds.classes)
    G = Generator(num_classes).to(device)
    D = Discriminator(num_classes).to(device)

    opt_g = torch.optim.Adam(G.parameters(), lr=args.lr, betas=(0.5, 0.999))
    opt_d = torch.optim.Adam(D.parameters(), lr=args.lr, betas=(0.5, 0.999))
    criterion = nn.BCEWithLogitsLoss()

    os.makedirs(args.sample_dir, exist_ok=True)
    fixed_z = torch.randn(num_classes, NOISE_DIM, device=device)
    fixed_labels = torch.arange(num_classes, device=device)

    for epoch in range(1, args.epochs + 1):
        d_loss_total, g_loss_total = 0.0, 0.0
        for real_imgs, labels in loader:
            real_imgs, labels = real_imgs.to(device), labels.to(device)
            bs = real_imgs.size(0)
            real_targets = torch.ones(bs, device=device)
            fake_targets = torch.zeros(bs, device=device)

            # --- Discriminator step ---
            opt_d.zero_grad()
            d_real = D(real_imgs, labels)
            loss_real = criterion(d_real, real_targets)

            z = torch.randn(bs, NOISE_DIM, device=device)
            fake_imgs = G(z, labels).detach()
            d_fake = D(fake_imgs, labels)
            loss_fake = criterion(d_fake, fake_targets)

            d_loss = loss_real + loss_fake
            d_loss.backward()
            opt_d.step()

            # --- Generator step ---
            opt_g.zero_grad()
            z = torch.randn(bs, NOISE_DIM, device=device)
            fake_imgs = G(z, labels)
            d_out = D(fake_imgs, labels)
            g_loss = criterion(d_out, real_targets)  # wants D to think these are real
            g_loss.backward()
            opt_g.step()

            d_loss_total += d_loss.item() * bs
            g_loss_total += g_loss.item() * bs

        print(f"epoch {epoch:4d}/{args.epochs}  d_loss={d_loss_total/len(ds):.4f}  g_loss={g_loss_total/len(ds):.4f}")

        if epoch % args.sample_every == 0 or epoch == args.epochs:
            G.eval()
            with torch.no_grad():
                samples = G(fixed_z, fixed_labels)
            save_image(samples, f"{args.sample_dir}/epoch_{epoch:04d}.png",
                       nrow=10, normalize=True, value_range=(-1, 1))
            G.train()

        if epoch % args.checkpoint_every == 0 or epoch == args.epochs:
            torch.save({
                "generator_state": G.state_dict(),
                "classes": ds.classes,
                "noise_dim": NOISE_DIM,
                "embed_dim": EMBED_DIM,
                "image_size": IMAGE_SIZE,
            }, args.out)

    print(f"Done. Final generator checkpoint saved to {args.out}")
    print(f"Sample grids (one per class, per checkpoint interval) are in {args.sample_dir} "
          f"-- look through these to judge training progress, not just the loss numbers.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset_dir", default="../dataset")
    p.add_argument("--epochs", type=int, default=200)
    p.add_argument("--batch_size", type=int, default=32)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--out", default="generator.pt")
    p.add_argument("--sample_dir", default="samples")
    p.add_argument("--sample_every", type=int, default=10)
    p.add_argument("--checkpoint_every", type=int, default=20)
    args = p.parse_args()
    train(args)


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# Troubleshooting notes (read this before assuming something's broken)
# ---------------------------------------------------------------------------
#
# GANs are genuinely harder to get good results from than a classifier --
# this is expected, not a sign your setup is wrong. Common symptoms and
# what they mean:
#
# - Generated samples look like pure noise even after 100+ epochs:
#   check your dataset actually has enough samples per class (see the
#   class_counts() warning in classifier.py -- fewer than ~15-20 images
#   per class is thin for a GAN, even a small one like this).
#
# - All generated images for a class look nearly identical ("mode
#   collapse"): classic GAN failure mode, more likely with very small
#   per-class datasets. Try: more data per class, a lower generator
#   learning rate relative to the discriminator, or reducing epochs
#   between generator updates.
#
# - d_loss goes to ~0 while g_loss keeps climbing: the discriminator is
#   "winning" too easily and stops giving the generator useful signal.
#   Try lowering the discriminator's learning rate, or adding label
#   smoothing (use real_targets of 0.9 instead of 1.0 in criterion calls).
#
# - Loss numbers look fine but the sample grids in --sample_dir look bad:
#   trust the sample images over the loss numbers -- GAN losses don't
#   correlate with visual quality nearly as reliably as in a classifier.
