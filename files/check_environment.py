"""
check_environment.py — Phase 0 sanity check.

Run this BEFORE trying the documented single_sampling command, and BEFORE
touching inference.py. It just confirms your environment has everything
importable and reports your GPU situation, so if something's missing you
find out in 5 seconds instead of after a 10-minute model download.

Usage:
    python check_environment.py
"""

import importlib
import sys

REQUIRED = [
    "torch", "torchvision", "diffusers", "transformers",
    "timm", "einops", "omegaconf", "PIL", "numpy", "tqdm",
]


def main() -> int:
    print(f"Python: {sys.version}\n")
    missing = []
    for mod in REQUIRED:
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "unknown")
            print(f"  OK   {mod:<15} {ver}")
        except ImportError:
            print(f"  MISS {mod:<15} (pip install this)")
            missing.append(mod)

    print()
    try:
        import torch
        cuda = torch.cuda.is_available()
        print(f"CUDA available: {cuda}")
        if cuda:
            print(f"  Device: {torch.cuda.get_device_name(0)}")
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            print(f"  VRAM:   {vram_gb:.1f} GB")
            if vram_gb < 8:
                print("  NOTE: DiffusionPen's SD-VAE + UNet DDIM sampling is heavier than an "
                      "LSTM-based model. <8GB VRAM may need smaller batch/resolution or Colab/Kaggle instead.")
        else:
            print("  NOTE: No CUDA GPU detected. CPU inference will work but each image may take "
                  "minutes rather than seconds (50 DDIM steps through a UNet + VAE decode). "
                  "Colab (free T4) or Kaggle GPU runtime is recommended for Phase 0-3.")
    except ImportError:
        print("torch not installed — install requirements.txt first.")

    print()
    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print(f"Fix with: pip install {' '.join(missing)}")
        return 1

    print("Environment looks good. Next: clone the repo and download the HF weights (see README.md Phase 0).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
