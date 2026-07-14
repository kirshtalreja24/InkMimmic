"""
inference.py — Phase 3: the custom script that doesn't exist in the
upstream repo.

Takes (folder of YOUR handwriting photos, arbitrary text string) and
produces a PNG of that text rendered in your handwriting style.

This is NOT a guess at the model's API — every call signature below
(ImageEncoder(...), UNetModel(...), the forward() kwargs, the sampling
loop, the vae decode math) was copied from reading koninik/DiffusionPen's
actual train.py::Diffusion.sampling() and unet.py::UNetModel.forward()
source directly, then stripped of everything that only exists to fetch
IAM benchmark images (writers_dict_train.json lookups, writer-ID sampling,
etc.) per Section 5 of the pipeline doc.

USAGE
-----
    # Run this FROM INSIDE your cloned DiffusionPen repo directory (so
    # `import unet` / `import feature_extractor` resolve), or pass
    # --repo_dir pointing at it.

    python inference.py \\
        --style_dir /path/to/your/handwriting/photos \\
        --text "hello world" \\
        --output out.png \\
        --repo_dir /path/to/cloned/DiffusionPen \\
        --save_path /path/to/cloned/DiffusionPen/diffusionpen_iam_model_path \\
        --style_path /path/to/cloned/DiffusionPen/style_models/iam_style_diffusionpen.pth \\
        --stable_dif_path /path/to/cloned/DiffusionPen/stable-diffusion-v1-5

PREREQUISITE: Phase 0 must already work — i.e. the documented
`python train.py --train_mode sampling --sampling_mode single_sampling`
command produces an image on your machine using the paths above. This
script reuses those exact same downloaded weights; it only changes WHERE
the 5 style images come from (your photos, not IAM).
"""

from __future__ import annotations

import argparse
import os
import sys


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="InkMimic custom DiffusionPen inference")
    p.add_argument("--style_dir", required=True,
                    help="Folder of your handwriting photos (5-10 recommended, JPEG/PNG).")
    p.add_argument("--text", required=True,
                    help="Text to render. Must use only DiffusionPen's trained vocabulary: "
                         "_!\"#&'()*+,-./0123456789:;?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz "
                         "(space included, 80 chars total). No accents, no @/%, no newlines.")
    p.add_argument("--output", default="output.png", help="Where to save the generated PNG.")
    p.add_argument("--num_style_images", type=int, default=5,
                    help="Architecture hard-expects 5 (unet.py reshapes to (batch, 5, -1)). "
                         "Leave this at 5 unless you've verified otherwise.")
    p.add_argument("--seed", type=int, default=None, help="Random seed for style-image sampling + generation.")

    # --- paths to the pretrained assets (Phase 0 downloads) ---
    p.add_argument("--repo_dir", default=".",
                    help="Path to your cloned koninik/DiffusionPen checkout (needs unet.py, "
                         "feature_extractor.py on the Python path).")
    p.add_argument("--save_path", default="./diffusionpen_iam_model_path",
                    help="Folder containing models/ckpt.pt and models/ema_ckpt.pt (from HF).")
    p.add_argument("--style_path", default="./style_models/iam_style_diffusionpen.pth",
                    help="Style encoder weights (from HF style_models/).")
    p.add_argument("--stable_dif_path", default="./stable-diffusion-v1-5",
                    help="Local stable-diffusion-v1-5 checkout (for the VAE + DDIM scheduler config).")
    p.add_argument("--use_ema", action="store_true", default=True,
                    help="Use ema_ckpt.pt instead of ckpt.pt (the paper/repo sample with EMA weights).")

    # --- fixed model hyperparameters (must match how the checkpoint was trained — do not change) ---
    p.add_argument("--emb_dim", type=int, default=320)
    p.add_argument("--num_heads", type=int, default=4)
    p.add_argument("--num_res_blocks", type=int, default=1)
    p.add_argument("--channels", type=int, default=4)
    p.add_argument("--style_classes", type=int, default=339,
                    help="IAM writer-class count. Only affects an unused nn.Embedding layer's "
                         "shape (needed so load_state_dict matches the checkpoint) — irrelevant "
                         "to output quality since we always pass style_extractor, which makes the "
                         "UNet ignore this embedding entirely (see unet.py forward()).")
    p.add_argument("--vocab_size", type=int, default=80)
    p.add_argument("--ddim_steps", type=int, default=50)

    p.add_argument("--device", default="cuda:0" if _cuda_available() else "cpu")
    return p


def _cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def main() -> None:
    args = build_arg_parser().parse_args()

    # Make the cloned repo importable (unet.py, feature_extractor.py live there).
    sys.path.insert(0, os.path.abspath(args.repo_dir))
    try:
        from unet import UNetModel
        from feature_extractor import ImageEncoder
    except ImportError as e:
        raise SystemExit(
            f"Could not import unet.py / feature_extractor.py from --repo_dir={args.repo_dir!r}.\n"
            f"Make sure you've cloned https://github.com/koninik/DiffusionPen and pointed "
            f"--repo_dir at it. Original error: {e}"
        )

    import torch
    from diffusers import AutoencoderKL, DDIMScheduler
    from transformers import CanineModel, CanineTokenizer

    from style_preprocessing import load_style_batch  # our Phase 2 module, same folder as this script

    if args.seed is not None:
        torch.manual_seed(args.seed)

    device = torch.device(args.device)
    print(f"[1/6] Using device: {device}")

    # ---- 1. Style images: YOUR photos, not IAM --------------------------
    print(f"[2/6] Loading + preprocessing {args.num_style_images} style images from {args.style_dir}")
    style_images = load_style_batch(args.style_dir, num_samples=args.num_style_images, seed=args.seed)
    style_images = style_images.to(device)  # (5, 3, 64, 256)

    # ---- 2. Text conditioning: CANINE, not letter2index.json ------------
    print("[3/6] Tokenizing text with CanineTokenizer('google/canine-c')")
    _validate_vocab(args.text)
    tokenizer = CanineTokenizer.from_pretrained("google/canine-c")
    text_encoder = CanineModel.from_pretrained("google/canine-c").to(device)
    text_encoder.eval()
    text_features = tokenizer(
        args.text, padding="max_length", truncation=True, return_tensors="pt", max_length=40
    ).to(device)
    # NOTE: we pass this raw tokenizer output dict straight into the UNet as
    # `context` — UNetModel.forward() calls self.text_encoder(**context)
    # internally, so text_encoder is wired into the UNet constructor below,
    # not called separately here.

    # ---- 3. Style encoder (pretrained mobilenetv2_100) -------------------
    print(f"[4/6] Loading style encoder weights from {args.style_path}")
    style_extractor = ImageEncoder(model_name="mobilenetv2_100", num_classes=0,
                                    pretrained=True, trainable=False).to(device)
    style_state = torch.load(args.style_path, map_location=device)
    # Some checkpoints save {"model_state_dict": ...} instead of a raw state_dict;
    # handle both so this doesn't silently fail on a KeyError deep in torch internals.
    if isinstance(style_state, dict) and "model_state_dict" in style_state:
        style_state = style_state["model_state_dict"]
    style_extractor.load_state_dict(style_state, strict=False)
    style_extractor.eval()

    with torch.no_grad():
        style_feats = style_extractor(style_images)  # (5, 1280)

    # ---- 4. UNet (pretrained diffusion backbone) --------------------------
    print(f"[5/6] Loading UNet weights from {args.save_path}")
    unet = UNetModel(
        image_size=(64, 256),
        in_channels=args.channels,
        model_channels=args.emb_dim,
        out_channels=args.channels,
        num_res_blocks=args.num_res_blocks,
        attention_resolutions=(1, 1),
        channel_mult=(1, 1),
        num_heads=args.num_heads,
        num_classes=args.style_classes,   # unused at inference, see arg help above
        context_dim=args.emb_dim,
        vocab_size=args.vocab_size,
        text_encoder=text_encoder,
        args=args,
    ).to(device)

    ckpt_name = "ema_ckpt.pt" if args.use_ema else "ckpt.pt"
    ckpt_path = os.path.join(args.save_path, "models", ckpt_name)
    unet.load_state_dict(torch.load(ckpt_path, map_location=device))
    unet.eval()

    # ---- 5. VAE + DDIM scheduler (stable-diffusion-v1-5) -------------------
    vae = AutoencoderKL.from_pretrained(args.stable_dif_path, subfolder="vae").to(device)
    vae.requires_grad_(False)
    vae.eval()
    noise_scheduler = DDIMScheduler.from_pretrained(args.stable_dif_path, subfolder="scheduler")

    # ---- 6. DDIM sampling loop (mirrors Diffusion.sampling() in train.py) --
    print(f"[6/6] Running {args.ddim_steps}-step DDIM sampling...")
    n = 1  # generating one image
    latent_h, latent_w = 64 // 8, 256 // 8
    x = torch.randn((n, args.channels, latent_h, latent_w), device=device)

    noise_scheduler.set_timesteps(args.ddim_steps)
    with torch.no_grad():
        for t in noise_scheduler.timesteps:
            t_batch = torch.full((n,), t.item(), device=device, dtype=torch.long)
            noise_pred = unet(
                x,
                timesteps=t_batch,
                context=text_features,   # dict -> unet calls text_encoder(**context) internally
                y=None,                  # ignored: style_extractor below overrides the label path
                mix_rate=None,
                style_extractor=style_feats,
            )
            x = noise_scheduler.step(noise_pred, t, x).prev_sample

    # ---- Decode latent -> pixel-space image --------------------------------
    latents = 1 / 0.18215 * x
    with torch.no_grad():
        image = vae.decode(latents).sample
    image = (image / 2 + 0.5).clamp(0, 1)

    from torchvision.utils import save_image
    save_image(image, args.output)
    print(f"Done. Saved {args.output}")


def _validate_vocab(text: str) -> None:
    """Warn (don't crash) if text uses characters outside the trained
    80-char vocabulary — per Section 5.3's 'practical implication'."""
    vocab = set('_!"#&\'()*+,-./0123456789:;?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ')
    bad = sorted(set(text) - vocab)
    if bad:
        print(f"WARNING: text contains characters outside DiffusionPen's trained vocabulary: {bad!r}. "
              f"Output quality for these characters is unverified — consider substituting them.")


if __name__ == "__main__":
    main()
