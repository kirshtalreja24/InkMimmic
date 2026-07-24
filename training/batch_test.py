"""
batch_test.py -- test the model against one sample from each labeled class folder.
"""
import argparse
from pathlib import Path
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import ImageOps
from dataset import _load_as_grayscale, pad_to_square, IGNORED_DIRS, folder_to_label
from classifier import SmallCNN
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", default="classifier_emnist.pt")
    p.add_argument("--dataset_dir", default="../dataset")
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
    dataset_dir = Path(args.dataset_dir)
    correct = 0
    total = 0
    wrong = []
    for cls_dir in sorted(dataset_dir.iterdir()):
        if not cls_dir.is_dir() or cls_dir.name in IGNORED_DIRS:
            continue
        pngs = sorted(cls_dir.glob("*.png"))
        if not pngs:
            continue
        img_path = pngs[0]
        true_label = folder_to_label(cls_dir.name)
        img = _load_as_grayscale(img_path)
        x = tfm(img).unsqueeze(0).to(device)
        with torch.no_grad():
            probs = F.softmax(model(x), dim=1)[0]
        top_idx = probs.argmax().item()
        pred_label = classes[top_idx]
        conf = probs[top_idx].item()
        total += 1
        if pred_label == true_label:
            correct += 1
            status = "OK"
        else:
            status = "WRONG"
            wrong.append((true_label, pred_label, conf, img_path.name))
        print(f"[{status}] true={true_label!r}  pred={pred_label!r}  conf={conf:.3f}  ({img_path.name})")
    print(f"\n{correct}/{total} correct = {correct/max(total,1):.1%} accuracy on this quick spot-check")
    if wrong:
        print("\nMissed these:")
        for true_l, pred_l, conf, fname in wrong:
            print(f"  true={true_l!r} -> predicted={pred_l!r} (conf={conf:.3f}, file={fname})")
if __name__ == "__main__":
    main()
