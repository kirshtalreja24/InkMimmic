"""
generate_handwriting.py

Lives inside Diffusion-Handwriting-Generation/, run as a sibling folder to
your ai_handwriter project. Ties together:

    ai_handwriter/segment.py             -> segments a scanned page into lines + char crops
    ai_handwriter/training/classifier.py -> scores each line's legibility (confidence)
    (this repo) nn.py / utils.py / preprocessing.py -> generates handwriting via diffusion

Pipeline: scanned page -> segment -> pick cleanest line by classifier confidence
          -> use that line as style reference -> generate typed text in that style.

BEFORE RUNNING: fix AI_HANDWRITER_ROOT and AI_HANDWRITER_TRAINING_DIR below if your
folder layout differs from ~/Desktop/ai_handwriter with classifier.py inside training/.
"""

import argparse
import csv
import os
import sys
import textwrap
from collections import defaultdict

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import tensorflow as tf

# ---------------------------------------------------------------------------
# Path setup -- adjust these two if your layout differs
# ---------------------------------------------------------------------------
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
AI_HANDWRITER_ROOT = os.path.abspath(os.path.join(THIS_DIR, '..'))  # ai_handwriter itself
AI_HANDWRITER_TRAINING_DIR = os.path.join(AI_HANDWRITER_ROOT, 'training')

# IMPORTANT: ai_handwriter's segment.py does its own `import preprocessing`
# internally, and THIS repo also has a preprocessing.py -- same module name,
# completely different code. Python only keeps one module cached under a given
# name process-wide, so a normal `import preprocessing` here would collide
# with segment.py's own import (whichever runs first "wins" and the other
# breaks). Loading this repo's copy under a private alias avoids ever
# registering the plain name "preprocessing", leaving it free for segment.py.
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("diffusion_preprocessing", os.path.join(THIS_DIR, "preprocessing.py"))
diffusion_preprocessing = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(diffusion_preprocessing)

import nn                                        # noqa: E402  (this repo)
import utils                                     # noqa: E402

sys.path.insert(0, AI_HANDWRITER_ROOT)          # for segment.py
sys.path.insert(0, AI_HANDWRITER_TRAINING_DIR)  # for classifier.py, dataset.py

import segment                                   # noqa: E402  (ai_handwriter/segment.py; owns the "preprocessing" name)
from classifier import SmallCNN                  # noqa: E402  (ai_handwriter/training/classifier.py)
from dataset import _load_as_grayscale, pad_to_square  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Segment the page and build one flattened style-reference image per line
# ---------------------------------------------------------------------------
def get_candidate_lines(page_path, work_dir, mode='auto'):
    os.makedirs(work_dir, exist_ok=True)
    segment.segment_handwriting(page_path, work_dir, mode=mode)

    binary = segment.preprocess(page_path)  # re-run: cheap, and gives us the array directly

    manifest_path = os.path.join(work_dir, 'manifest.csv')
    with open(manifest_path, newline='') as f:
        rows = list(csv.DictReader(f))

    by_line = defaultdict(list)
    for r in rows:
        by_line[int(r['line'])].append(r)

    candidates = []
    for line_num, line_rows in sorted(by_line.items()):
        xs0 = min(int(r['x']) for r in line_rows)
        ys0 = min(int(r['y']) for r in line_rows)
        xs1 = max(int(r['x']) + int(r['width']) for r in line_rows)
        ys1 = max(int(r['y']) + int(r['height']) for r in line_rows)

        line_img_path = os.path.join(work_dir, f'line{line_num:02d}_style_ref.png')
        _save_line_image_for_diffusion(binary, (xs0, ys0, xs1 - xs0, ys1 - ys0), line_img_path)

        char_paths = [os.path.join(work_dir, r['filename']) for r in line_rows]
        candidates.append({'line_image_path': line_img_path, 'char_crop_paths': char_paths})

    return candidates


def _save_line_image_for_diffusion(binary, box, out_path, padding=6):
    """
    segment.py's save_character_png() writes transparent PNGs (uniform dark
    RGB fill + ink stored in the alpha channel), which is NOT what the
    diffusion model's preprocessing.read_img() expects (it loads as flat
    grayscale and needs a normal white-background/dark-ink image). This
    builds that directly from the binarized page instead, inverted so ink
    is dark (~0) and background is white (~255), matching what
    read_img()'s whitespace-removal threshold assumes.
    """
    x, y, w, h = box
    x0, y0 = max(x - padding, 0), max(y - padding, 0)
    x1 = min(x + w + padding, binary.shape[1])
    y1 = min(y + h + padding, binary.shape[0])
    crop = binary[y0:y1, x0:x1]          # ink=255, background=0 (segment.py's convention)
    inverted = 255 - crop                # -> ink=dark, background=white
    cv2.imwrite(out_path, inverted)


# ---------------------------------------------------------------------------
# 2. Score each line's legibility using the trained classifier
# ---------------------------------------------------------------------------
_classifier_cache = {}


def _load_classifier(checkpoint_path):
    if checkpoint_path not in _classifier_cache:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        ckpt = torch.load(checkpoint_path, map_location=device)
        model = SmallCNN(num_classes=len(ckpt["classes"])).to(device)
        model.load_state_dict(ckpt["model_state"])
        model.eval()
        _classifier_cache[checkpoint_path] = (model, device)
    return _classifier_cache[checkpoint_path]


def score_line_confidence(char_crop_paths, checkpoint_path):
    model, device = _load_classifier(checkpoint_path)
    tfm = transforms.Compose([
        transforms.Lambda(lambda img: pad_to_square(img, 32, fill=0)),
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,)),
    ])
    scores = []
    with torch.no_grad():
        for p in char_crop_paths:
            img = _load_as_grayscale(p)
            x = tfm(img).unsqueeze(0).to(device)
            probs = F.softmax(model(x), dim=1)[0]
            scores.append(probs.max().item())
    return sum(scores) / len(scores) if scores else 0.0


def pick_best_line(page_path, work_dir, checkpoint_path, mode='auto'):
    candidates = get_candidate_lines(page_path, work_dir, mode=mode)
    if not candidates:
        raise ValueError(f"No lines detected on page: {page_path}")

    scored = []
    for c in candidates:
        score = score_line_confidence(c['char_crop_paths'], checkpoint_path)
        scored.append((score, c['line_image_path']))
        print(f"  {os.path.basename(c['line_image_path'])}: avg confidence {score:.3f}")

    scored.sort(reverse=True, key=lambda x: x[0])
    best_score, best_path = scored[0]
    print(f"Selected '{best_path}' (confidence {best_score:.3f}) out of {len(scored)} lines.")
    return best_path


# ---------------------------------------------------------------------------
# 3. Diffusion model wrapper
# ---------------------------------------------------------------------------
class HandwritingGenerator:
    def __init__(self, weights_path, channels=128, num_attlayers=2):
        self.style_extractor = nn.StyleExtractor()
        self.model = nn.DiffusionWriter(num_layers=num_attlayers, c1=channels, c2=channels * 3 // 2, c3=channels * 2)
        _ = self.model(
            tf.random.normal([1, 400, 2]),
            tf.random.uniform([1, 40], dtype=tf.int32, maxval=50),
            tf.random.uniform([1, 1]),
            tf.random.normal([1, 14, 1280]),
        )
        self.model.load_weights(weights_path)
        self.tokenizer = utils.Tokenizer()
        self.beta_set = utils.get_beta_set()

    def generate(self, text, style_image_path, out_path, diffusion_mode='new'):
        img = tf.expand_dims(diffusion_preprocessing.read_img(style_image_path, 96), 0)
        style_vector = self.style_extractor(img)

        timesteps = len(text) * 16
        timesteps = timesteps - (timesteps % 8) + 8

        utils.run_batch_inference(
            self.model, self.beta_set, text, style_vector,
            tokenizer=self.tokenizer, time_steps=timesteps,
            diffusion_mode=diffusion_mode, show_samples=False, path=out_path,
        )
        print(f"Saved generated handwriting to ./{out_path}.png")

    def generate_paragraph(self, text, style_image_path, out_dir, max_chars_per_line=45, diffusion_mode='new'):
        """
        The model was trained with max text length 50 chars and max sequence
        length 480 (see train.py's --textlen/--seqlen defaults) -- roughly
        one sentence. It also has no concept of line breaks; a raw long
        string would render as one continuous, ever-thinner strip. This
        splits text into word-wrapped chunks, generates each as its own
        line (reusing one style vector so they all match), then stitches
        them vertically into a single paragraph image.
        """
        os.makedirs(out_dir, exist_ok=True)
        img = tf.expand_dims(diffusion_preprocessing.read_img(style_image_path, 96), 0)
        style_vector = self.style_extractor(img)  # computed once, reused for every line

        lines = textwrap.wrap(text, width=max_chars_per_line, break_long_words=False)
        if not lines:
            raise ValueError("No text to generate.")

        line_paths = []
        for i, line in enumerate(lines):
            timesteps = len(line) * 16
            timesteps = timesteps - (timesteps % 8) + 8
            name = os.path.join(out_dir, f'para_line_{i:02d}')
            print(f"Generating line {i+1}/{len(lines)}: \"{line}\"")
            utils.run_batch_inference(
                self.model, self.beta_set, line, style_vector,
                tokenizer=self.tokenizer, time_steps=timesteps,
                diffusion_mode=diffusion_mode, show_samples=False, path=name,
            )
            line_paths.append(name + '.png')

        imgs = [Image.open(p).convert('RGBA') for p in line_paths]
        max_w = max(im.width for im in imgs)
        line_gap = 10
        total_h = sum(im.height for im in imgs) + line_gap * (len(imgs) - 1)

        canvas = Image.new('RGBA', (max_w, total_h), (255, 255, 255, 255))
        y = 0
        for im in imgs:
            canvas.paste(im, (0, y), im)
            y += im.height + line_gap

        final_path = os.path.join(out_dir, 'paragraph_output.png')
        canvas.convert('RGB').save(final_path)
        print(f"Saved stitched paragraph ({len(lines)} lines) to {final_path}")
        return final_path


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------
def generate_from_page(page_path, text, out_path, work_dir, checkpoint_path, weights_path, mode='auto', paragraph=False):
    print("Segmenting page and scoring lines...")
    best_line_path = pick_best_line(page_path, work_dir, checkpoint_path, mode=mode)

    print("Loading diffusion model and generating...")
    generator = HandwritingGenerator(weights_path=weights_path)
    if paragraph:
        generator.generate_paragraph(text, best_line_path, out_path)  # out_path used as a directory here
    else:
        generator.generate(text, best_line_path, out_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--page', required=True, help='path to a scanned page of your handwriting')
    parser.add_argument('--text', required=True, help='text to generate in your handwriting style')
    parser.add_argument('--out', default='generated_output',
                         help='output filename (no extension) for single-line mode, '
                              'or output DIRECTORY for --paragraph mode')
    parser.add_argument('--work_dir', default='./_line_candidates')
    parser.add_argument('--checkpoint', default=os.path.join(AI_HANDWRITER_TRAINING_DIR, 'classifier_final2.pt'))
    parser.add_argument('--weights', default='./weights/model_weights.h5')
    parser.add_argument('--mode', choices=['auto', 'prose', 'isolated'], default='auto')
    parser.add_argument('--paragraph', action='store_true',
                         help='split long text into wrapped lines and stitch into one paragraph image')
    args = parser.parse_args()

    generate_from_page(args.page, args.text, args.out, args.work_dir, args.checkpoint, args.weights,
                        args.mode, args.paragraph)