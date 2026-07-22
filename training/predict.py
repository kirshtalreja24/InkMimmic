"""
predict.py — run the trained classifier on a single image, print top-3 guesses.

Usage:
    python predict.py --checkpoint classifier.pt --image path/to/char.png
"""

import argparse
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import ImageOps

from dataset import _load_as_grayscale, pad_to_square
from classifier import SmallCNN


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", default="classifier.pt")
    p.add_argument("--image", required=True)
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.checkpoint, map_location=device)
    classes = ckpt["classes"]

    model = SmallCNN(num_classes=len(classes)).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    tfm = transforms.Compose([
        transforms.Lambda(lambda img: pad_to_square(img, 32)),
        transforms.Lambda(lambda img: ImageOps.invert(img)),  # match EMNIST's
        # white-ink-on-black convention (our images are dark ink on white)
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,)),
    ])

    img = _load_as_grayscale(args.image)
    x = tfm(img).unsqueeze(0).to(device)

    with torch.no_grad():
        probs = F.softmax(model(x), dim=1)[0]

    top3 = torch.topk(probs, k=3)
    print(f"Predictions for {args.image}:")
    for prob, idx in zip(top3.values, top3.indices):
        print(f"  {classes[idx.item()]!r}: {prob.item():.3f}")


if __name__ == "__main__":
    main()
