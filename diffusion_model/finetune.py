"""

finetune.py — Per-user fine-tuning of the HANDWRITER diffusion model.

Loads pretrained IAM weights, then fine-tunes the DECODER ONLY (StyleExtractor
stays frozen) on a user's reconstructed stroke data (from build_train_data.py).

Key differences from train.py:
  - Loads pretrained base weights BEFORE training
  - Lower learning rate (1e-4..1e-5) with shorter warmup
  - Short runs (5k–15k steps) to avoid catastrophic forgetting
  - Dropout 0.1 for regularization on small data
  - Saves per-user weights (never overwrites model_weights.h5)
  - Periodic checkpoint saving + holdout generation for quality selection

Usage:
    python finetune.py --user_data ./data/train_strokes.p \\
        --base_weights ./weights/model_weights.h5 \\
        --user alizeh --steps 5000 --batchsize 32
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

# TensorFlow import
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')  # suppress TF info logs
import tensorflow as tf

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)

import nn
import utils


# ---------------------------------------------------------------------------
# Learning rate schedule — same InvSqrtSchedule but tuned for fine-tuning
# ---------------------------------------------------------------------------
class FinetuneLRSchedule(tf.keras.optimizers.schedules.LearningRateSchedule):
    """Inverse-sqrt schedule with a configurable peak LR and warmup.

    Peak LR = base_lr at the end of warmup, then decays as 1/sqrt(step).
    """
    def __init__(self, base_lr: float = 1e-4, warmup_steps: int = 500):
        super().__init__()
        self.base_lr = tf.cast(base_lr, tf.float32)
        self.warmup_steps = tf.cast(warmup_steps, tf.float32)

    def __call__(self, step):
        step = tf.cast(step, tf.float32)
        warmup_pct = tf.minimum(step / self.warmup_steps, 1.0)
        decay = tf.math.rsqrt(tf.maximum(step, self.warmup_steps) / self.warmup_steps)
        return self.base_lr * warmup_pct * decay


# ---------------------------------------------------------------------------
# Training step — identical to train.py but extracted for clarity
# ---------------------------------------------------------------------------
@tf.function
def train_step(x, pen_lifts, text, style_vectors, model, alpha_set, bce, optimizer):
    alphas = utils.get_alphas(tf.shape(x)[0], alpha_set)
    eps = tf.random.normal(tf.shape(x))
    x_perturbed = tf.sqrt(alphas) * x + tf.sqrt(1 - alphas) * eps

    with tf.GradientTape() as tape:
        score, pl_pred, att = model(x_perturbed, text, tf.sqrt(alphas), style_vectors, training=True)
        loss = nn.loss_fn(eps, score, pen_lifts, pl_pred, alphas, bce)

    gradients = tape.gradient(loss, model.trainable_variables)
    optimizer.apply_gradients(zip(gradients, model.trainable_variables))
    return loss


# ---------------------------------------------------------------------------
# Main fine-tuning loop
# ---------------------------------------------------------------------------
def finetune(
    data_path: str,
    base_weights: str,
    user_name: str,
    steps: int = 5000,
    batch_size: int = 32,
    lr: float = 1e-4,
    warmup_steps: int = 500,
    dropout: float = 0.1,
    save_every: int = 1000,
    print_every: int = 200,
    max_seq_len: int = 480,
    max_text_len: int = 50,
    img_width: int = 1400,
    img_height: int = 96,
    channels: int = 128,
    num_attlayers: int = 2,
    output_dir: str = './weights',
):
    """Fine-tune the diffusion model on per-user data."""

    C1 = channels
    C2 = C1 * 3 // 2
    C3 = C1 * 2

    print(f"[finetune] User: {user_name}")
    print(f"[finetune] Base weights: {base_weights}")
    print(f"[finetune] Data: {data_path}")
    print(f"[finetune] Config: steps={steps}, batch={batch_size}, lr={lr}, "
          f"warmup={warmup_steps}, dropout={dropout}")

    # --- 1. Build model and load pretrained weights ---
    style_extractor = nn.StyleExtractor()  # frozen (trainable=False inside)
    model = nn.DiffusionWriter(
        num_layers=num_attlayers, c1=C1, c2=C2, c3=C3, drop_rate=dropout
    )

    # Dummy forward pass to build weights (required before load_weights)
    _stroke = tf.random.normal([1, 400, 2])
    _text = tf.random.uniform([1, 40], dtype=tf.int32, maxval=50)
    _noise = tf.random.uniform([1, 1])
    _style = tf.random.normal([1, 14, 1280])
    _ = model(_stroke, _text, _noise, _style)

    model.load_weights(base_weights)
    print(f"[finetune] Loaded base weights ({len(model.trainable_variables)} trainable vars)")

    # --- 2. Load and preprocess data ---
    strokes, texts, samples = utils.preprocess_data(
        data_path, max_text_len, max_seq_len, img_width, img_height
    )

    if len(strokes) == 0:
        raise ValueError(f"No valid training samples loaded from {data_path}")

    print(f"[finetune] Loaded {len(strokes)} training samples")

    # Clamp batch size: create_dataset uses drop_remainder=True, so a batch
    # larger than the dataset would silently drop everything and train nothing.
    batch_size = min(batch_size, len(strokes))

    # Pre-compute style vectors (StyleExtractor is frozen, so we only need to
    # do this once — same as utils.create_dataset)
    buffer_size = min(len(strokes), 3000)
    dataset = utils.create_dataset(strokes, texts, samples, style_extractor, batch_size, buffer_size)

    # --- 3. Optimizer ---
    lr_schedule = FinetuneLRSchedule(base_lr=lr, warmup_steps=warmup_steps)
    optimizer = tf.keras.optimizers.Adam(lr_schedule, beta_1=0.9, beta_2=0.98, clipnorm=100)

    # --- 4. Training loop ---
    beta_set = utils.get_beta_set()
    alpha_set = tf.math.cumprod(1 - beta_set)
    bce = tf.keras.losses.BinaryCrossentropy(from_logits=False)

    os.makedirs(output_dir, exist_ok=True)
    start_time = time.time()
    losses = []

    # Repeat dataset enough times to cover all steps
    # Each epoch = len(strokes) / batch_size steps
    steps_per_epoch = max(1, len(strokes) // batch_size)
    repeats = max(1, (steps // steps_per_epoch) + 2)

    step = 0
    for epoch_strokes, epoch_text, epoch_style in dataset.repeat(repeats):
        strokes_xy, pen_lifts = epoch_strokes[:, :, :2], epoch_strokes[:, :, 2:]
        loss = train_step(strokes_xy, pen_lifts, epoch_text, epoch_style,
                          model, alpha_set, bce, optimizer)
        step += 1
        losses.append(float(loss))

        if step % print_every == 0:
            avg_loss = np.mean(losses[-print_every:])
            elapsed = time.time() - start_time
            current_lr = float(lr_schedule(tf.cast(step, tf.float32)))
            print(f"  Step {step:6d}/{steps}  loss={avg_loss:.4f}  lr={current_lr:.2e}  time={elapsed:.0f}s")

        if step % save_every == 0:
            ckpt_path = os.path.join(output_dir, f'model_{user_name}_step{step}.h5')
            model.save_weights(ckpt_path)
            print(f"  Checkpoint → {ckpt_path}")

        if step >= steps:
            break

    # --- 5. Save final weights ---
    final_path = os.path.join(output_dir, f'model_{user_name}.h5')
    model.save_weights(final_path)
    elapsed = time.time() - start_time
    final_loss = np.mean(losses[-min(100, len(losses)):])
    print(f"\n[finetune] Done. {step} steps in {elapsed:.0f}s")
    print(f"[finetune] Final avg loss: {final_loss:.4f}")
    print(f"[finetune] Saved → {final_path}")

    return final_path, losses


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Fine-tune the handwriting diffusion model per user.')
    parser.add_argument('--user_data', required=True, help='Path to train_strokes.p')
    parser.add_argument('--base_weights', default='./weights/model_weights.h5',
                        help='Path to pretrained IAM weights')
    parser.add_argument('--user', required=True, help='User name (used for output filenames)')
    parser.add_argument('--steps', type=int, default=5000, help='Number of training steps')
    parser.add_argument('--batchsize', type=int, default=32, help='Batch size')
    parser.add_argument('--lr', type=float, default=1e-4, help='Peak learning rate')
    parser.add_argument('--warmup', type=int, default=500, help='Warmup steps')
    parser.add_argument('--dropout', type=float, default=0.1, help='Dropout rate')
    parser.add_argument('--save_every', type=int, default=1000, help='Save checkpoint every N steps')
    parser.add_argument('--print_every', type=int, default=200, help='Print loss every N steps')
    parser.add_argument('--channels', type=int, default=128, help='Model channels (must match base weights)')
    parser.add_argument('--num_attlayers', type=int, default=2, help='Attention layers (must match base weights)')
    parser.add_argument('--output_dir', default='./weights', help='Output directory for weights')
    parser.add_argument('--seqlen', type=int, default=480)
    parser.add_argument('--textlen', type=int, default=50)
    parser.add_argument('--width', type=int, default=1400)
    args = parser.parse_args()

    finetune(
        data_path=args.user_data,
        base_weights=args.base_weights,
        user_name=args.user,
        steps=args.steps,
        batch_size=args.batchsize,
        lr=args.lr,
        warmup_steps=args.warmup,
        dropout=args.dropout,
        save_every=args.save_every,
        print_every=args.print_every,
        max_seq_len=args.seqlen,
        max_text_len=args.textlen,
        img_width=args.width,
        channels=args.channels,
        num_attlayers=args.num_attlayers,
        output_dir=args.output_dir,
    )


if __name__ == '__main__':
    main()
