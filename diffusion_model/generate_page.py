"""
generate_page.py — Generate a full page of handwriting in a per-user style.

Loads a fine-tuned per-user model (or the IAM base), generates each wrapped
line with one reused style vector, renders via renderer.py, retries a few
times stochastically, and keeps the best (scored by classifier read-back if
available, else a cheap heuristic).

Usage:
    python generate_page.py --text "Your assignment text here..." \\
        --weights ./weights/model_alizeh.h5 \\
        --style ./assets/<user line>.png \\
        --out ./out --paragraph
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path

import numpy as np

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
import tensorflow as tf

THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(THIS_DIR))

import nn
import utils
import renderer

# Load the diffusion preprocessing module under a private alias to avoid the
# module-name collision with the project's own preprocessing.py (same trick
# as generate_handwriting.py).
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("diffusion_preprocessing", os.path.join(THIS_DIR, "preprocessing.py"))
diffusion_preprocessing = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(diffusion_preprocessing)


# ---------------------------------------------------------------------------
# Optional legibility gate: SmallCNN read-back (degrades gracefully)
# ---------------------------------------------------------------------------
def _load_classifier():
    """Load the SmallCNN classifier if torch + checkpoint are available."""
    try:
        import torch
        import torch.nn.functional as F
        from torchvision import transforms
        project_root = THIS_DIR.parent
        training_dir = project_root / 'training'
        sys.path.insert(0, str(training_dir))

        from classifier import SmallCNN  # noqa: E402
        from dataset import _load_as_grayscale, pad_to_square  # noqa: E402

        ckpt_path = training_dir / 'classifier_final4.pt'
        if not ckpt_path.exists():
            return None

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        ckpt = torch.load(str(ckpt_path), map_location=device)
        model = SmallCNN(num_classes=len(ckpt['classes'])).to(device)
        model.load_state_dict(ckpt['model_state'])
        model.eval()
        return {'model': model, 'device': device, 'classes': ckpt['classes'],
                'torch': torch, 'F': F, 'tfm': transforms.Compose([
                    transforms.Lambda(lambda img: pad_to_square(img, 32, fill=0)),
                    transforms.ToTensor(),
                    transforms.Normalize((0.5,), (0.5,)),
                ])}
    except Exception as e:  # noqa: BLE001
        print(f"[gate] Classifier unavailable, using heuristic scoring: {e}")
        return None


def score_generation(gate, image_path, expected_text):
    """Score a generated line image against the intended text.

    With the classifier: fraction of expected characters that the classifier
    reads back correctly.  Without it: ink-density heuristic (more balanced
    ink coverage is a weak proxy for legibility).
    """
    if gate is None:
        from PIL import Image
        img = Image.open(image_path).convert('L')
        arr = np.asarray(img)
        ink = (arr < 128).astype(np.float32)
        if ink.sum() == 0:
            return 0.0
        # Coverage ratio in the central band — a rough legibility proxy
        h, w = arr.shape
        band = arr[h // 3: 2 * h // 3, :]
        coverage = (band < 128).mean()
        return float(min(coverage * 8.0, 1.0))  # penalize both too little and too much ink

    # Classifier read-back path
    torch, F = gate['torch'], gate['F']
    model, device, classes = gate['model'], gate['device'], gate['classes']
    tfm = gate['tfm']

    label_to_char = {classes[i]: classes[i] for i in range(len(classes))}
    # folder names are like 'AA', 'a', '9' → take first char for single-char labels
    char_map = {}
    for c in classes:
        key = c[0] if c and c[0].isalnum() else c
        char_map[c] = key

    # Segment the generated line back into characters using the project's segment.py
    project_root = THIS_DIR.parent
    sys.path.insert(0, str(project_root))
    try:
        import segment
        work_dir = image_path + '_seg'
        segment.segment_handwriting(image_path, work_dir, mode='auto')
        import csv
        manifest = os.path.join(work_dir, 'manifest.csv')
        if not os.path.exists(manifest):
            return 0.0
        with open(manifest, newline='') as f:
            rows = list(csv.DictReader(f))
        crops = [os.path.join(work_dir, r['filename']) for r in rows]
    except Exception:  # noqa: BLE001
        return 0.0

    if not crops:
        return 0.0

    with torch.no_grad():
        preds = []
        for p in crops:
            img = _load_as_grayscale(p)
            x = tfm(img).unsqueeze(0).to(device)
            probs = F.softmax(model(x), dim=1)[0]
            conf, idx = probs.max(dim=0)
            if conf.item() < 0.4:
                preds.append('_')
            else:
                preds.append(char_map.get(classes[idx.item()], '_'))

    expected = expected_text.replace(' ', '')
    readback = ''.join(preds).replace('_', '').replace(' ', '')
    if not expected:
        return 0.0

    # Character-level accuracy (allow order-ish match)
    n_match = sum(1 for a, b in zip(expected[:len(readback)], readback) if a == b)
    score = n_match / len(expected)
    return float(score)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
class PageGenerator:
    """Generate full pages in a user's style using a (possibly fine-tuned) model."""

    def __init__(self, weights_path, channels=128, num_attlayers=2):
        self.style_extractor = nn.StyleExtractor()
        self.model = nn.DiffusionWriter(
            num_layers=num_attlayers, c1=channels, c2=channels * 3 // 2, c3=channels * 2
        )
        # Build graph + load weights
        _ = self.model(
            tf.random.normal([1, 400, 2]),
            tf.random.uniform([1, 40], dtype=tf.int32, maxval=50),
            tf.random.uniform([1, 1]),
            tf.random.normal([1, 14, 1280]),
        )
        self.model.load_weights(weights_path)
        self.tokenizer = utils.Tokenizer()
        self.beta_set = utils.get_beta_set()

    def _style_vector(self, style_image_path):
        img = tf.expand_dims(diffusion_preprocessing.read_img(style_image_path, 96), 0)
        return self.style_extractor(img)

    def generate_page(
        self,
        text,
        style_image_path,
        out_dir,
        max_chars_per_line=45,
        n_tries=3,
        ink_color='#1a1a2e',
        paper='white',
        line_height=128,
        gate=None,
    ):
        """Generate a full page (word-wrapped, best-of-N) and return the path."""
        os.makedirs(out_dir, exist_ok=True)
        style_vector = self._style_vector(style_image_path)

        lines = textwrap.wrap(text, width=max_chars_per_line, break_long_words=False)
        if not lines:
            raise ValueError('No text to generate.')

        best_score = -1.0
        best_lines = None
        best_strokes = None

        for attempt in range(n_tries):
            line_images = []
            line_strokes = []
            for i, line in enumerate(lines):
                strokes = utils.run_batch_inference(
                    self.model, self.beta_set, line, style_vector,
                    tokenizer=self.tokenizer, time_steps=len(line) * 16 - (len(line) * 16 % 8) + 8,
                    diffusion_mode='new', show_samples=False,
                    path=os.path.join(out_dir, f'_try{attempt}_line{i:02d}'),
                )
                img_path = os.path.join(out_dir, f'_try{attempt}_line{i:02d}.png')
                renderer.render_strokes(strokes, img_path, height=line_height,
                                        ink_color=ink_color, paper=paper)
                line_images.append(img_path)
                line_strokes.append(strokes)

            # Score the whole page: average per-line read-back
            scores = []
            for i, line in enumerate(lines):
                scores.append(score_generation(gate, line_images[i], line))
            page_score = float(np.mean(scores)) if scores else 0.0
            print(f"  Attempt {attempt + 1}/{n_tries}: score {page_score:.3f}")

            if page_score > best_score:
                best_score = page_score
                best_lines = list(line_images)
                best_strokes = list(line_strokes)

        # Compose the best attempt into a single page image
        from PIL import Image
        page_path = self._compose_page(best_lines, best_strokes, out_dir, line_height, paper)
        print(f"  Best score: {best_score:.3f}")
        print(f"  Page → {page_path}")
        return page_path

    def _compose_page(self, line_images, line_strokes, out_dir, line_height, paper):
        """Stack rendered lines into a single page image with spacing."""
        imgs = [Image.open(p).convert('RGB') for p in line_images]
        max_w = max(im.width for im in imgs)
        line_gap = max(8, int(line_height * 0.35))
        total_h = sum(im.height for im in imgs) + line_gap * (len(imgs) - 1)

        page = Image.new('RGB', (max_w, total_h), 'white')
        y = 0
        for im in imgs:
            page.paste(im, (0, y))
            y += im.height + line_gap

        final_path = os.path.join(out_dir, 'page_output.png')
        page.save(final_path)
        return final_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Generate a page of handwriting in a user style.')
    parser.add_argument('--text', required=True, help='Text to generate')
    parser.add_argument('--weights', required=True, help='Model weights (.h5) — per-user or IAM base')
    parser.add_argument('--style', required=True, help='Style reference line image')
    parser.add_argument('--out', default='./generated_pages')
    parser.add_argument('--max_chars', type=int, default=45, help='Max chars per line')
    parser.add_argument('--tries', type=int, default=3, help='Best-of-N stochastic retries')
    parser.add_argument('--ink', default='#1a1a2e')
    parser.add_argument('--paper', choices=['white', 'ruled', 'graph'], default='white')
    parser.add_argument('--height', type=int, default=128, help='Line height in px')
    parser.add_argument('--no_gate', action='store_true', help='Disable the legibility gate')
    args = parser.parse_args()

    gate = None if args.no_gate else _load_classifier()
    generator = PageGenerator(weights_path=args.weights)
    generator.generate_page(
        args.text, args.style, args.out,
        max_chars_per_line=args.max_chars, n_tries=args.tries,
        ink_color=args.ink, paper=args.paper, line_height=args.height, gate=gate,
    )


if __name__ == '__main__':
    main()
