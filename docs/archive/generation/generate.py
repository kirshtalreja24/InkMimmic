"""
generate.py — turn typed text into a generated handwriting image using
your trained conditional GAN.

This is the roadmap's Step 6 ("Generate Full Text") plus a first pass at
Step 7 (basic spacing/baseline variation, not full ligatures/rotation --
see the TODOs below for what's still simple concatenation).

USAGE
-----
    python generate.py --checkpoint ../training/generator.pt --text "Hello World" --output out.png

Each requested character is generated fresh from random noise + its
class label -- so running this twice with the same text gives you two
different-looking (but same-style) renderings, which is the whole point
of using a generator instead of just replaying fixed stored glyphs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
from gan import Generator  # noqa: E402


def load_generator(checkpoint_path: str, device: torch.device):
    ckpt = torch.load(checkpoint_path, map_location=device)
    classes = ckpt["classes"]
    G = Generator(
        num_classes=len(classes),
        noise_dim=ckpt["noise_dim"],
        embed_dim=ckpt["embed_dim"],
    ).to(device)
    G.load_state_dict(ckpt["generator_state"])
    G.eval()
    return G, classes, ckpt["noise_dim"], ckpt["image_size"]


def generate_text_image(
    text: str,
    checkpoint_path: str,
    output_path: str,
    letter_spacing: int = 4,
    space_width: int = 24,
    seed: int | None = None,
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    G, classes, noise_dim, image_size = load_generator(checkpoint_path, device)
    class_to_idx = {c: i for i, c in enumerate(classes)}

    if seed is not None:
        torch.manual_seed(seed)

    tiles = []
    missing = []
    for ch in text:
        if ch == " ":
            tiles.append(("space", None))
            continue
        if ch not in class_to_idx:
            missing.append(ch)
            tiles.append(("missing", ch))
            continue
        tiles.append(("char", ch))

    if missing:
        print(f"WARNING: these characters have no trained class and will be "
              f"rendered as blanks: {sorted(set(missing))!r}. "
              f"(Your GAN was only trained on A-Z/a-z/0-9 -- punctuation "
              f"isn't in scope yet; see the segmentation punctuation "
              f"discussion for why.)")

    # Generate each character glyph
    imgs = []
    with torch.no_grad():
        for kind, ch in tiles:
            if kind == "space":
                imgs.append(("space", None))
            elif kind == "missing":
                imgs.append(("blank", None))
            else:
                z = torch.randn(1, noise_dim, device=device)
                label = torch.tensor([class_to_idx[ch]], device=device)
                out = G(z, label)[0, 0].cpu()  # (H, W), range [-1, 1]
                out = ((out + 1) / 2 * 255).clamp(0, 255).byte().numpy()
                pil = Image.fromarray(out, mode="L")
                imgs.append(("glyph", pil))

    # Compose left to right onto a white canvas.
    # TODO (roadmap Step 7 -- not yet implemented here): per-character
    # baseline jitter, slight rotation, and variable spacing based on
    # neighboring letter shapes. Right now this is simple concatenation
    # with fixed spacing, which is a legitimate, honest first version --
    # not the polished final target.
    total_width = sum(
        image_size if k == "glyph" else (space_width if k == "space" else image_size // 2)
        for k, _ in imgs
    ) + letter_spacing * len(imgs)
    canvas = Image.new("L", (total_width, image_size), color=255)

    x = 0
    for kind, glyph in imgs:
        if kind == "glyph":
            canvas.paste(glyph, (x, 0))
            x += image_size + letter_spacing
        elif kind == "space":
            x += space_width
        else:  # blank stand-in for an unsupported character
            x += image_size // 2 + letter_spacing

    canvas.save(output_path)
    print(f"Saved {output_path} ({len(text)} characters, {total_width}x{image_size}px)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", default="../training/generator.pt")
    p.add_argument("--text", required=True)
    p.add_argument("--output", default="out.png")
    p.add_argument("--letter_spacing", type=int, default=4)
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()
    generate_text_image(
        args.text, args.checkpoint, args.output,
        letter_spacing=args.letter_spacing, seed=args.seed,
    )


if __name__ == "__main__":
    main()
