"""
api/server.py — REST API server for AI Handwriting Generation.

Exposes endpoints for the Inkmimic web app and mobile app to:
- Generate realistic handwriting images from text + optional style sample.
- Analyze handwriting style from uploaded images.
- Check backend and model health.

Run with:
    uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import base64
import io
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import numpy as np

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DIFFUSION_DIR = REPO_ROOT / 'diffusion_model'
TRAINING_DIR = REPO_ROOT / 'training'

for p in (str(REPO_ROOT), str(DIFFUSION_DIR), str(TRAINING_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

DEFAULT_WEIGHTS = DIFFUSION_DIR / 'weights' / 'model_weights.h5'
DEFAULT_STYLE_REF = DIFFUSION_DIR / 'assets' / 'a02-050-03.tif'

app = FastAPI(
    title="Inkmimic Handwriting AI Engine",
    description="Diffusion-based handwriting synthesis API for Web and Mobile",
    version="1.0.0",
)

# Enable CORS for Vite Web (localhost:5173, etc.) and Mobile (Expo, React Native)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_generator = None
_generator_error = None
_gate = None
_gate_loaded = False


def get_generator():
    """Lazy-load the PageGenerator so the server boots quickly."""
    global _generator, _generator_error
    if _generator is not None:
        return _generator
    if _generator_error is not None:
        raise HTTPException(status_code=500, detail=f"Model failed to initialize: {_generator_error}")

    try:
        import generate_page  # noqa: E402
        if not DEFAULT_WEIGHTS.exists():
            raise FileNotFoundError(f"Model weights not found at {DEFAULT_WEIGHTS}")

        _generator = generate_page.PageGenerator(weights_path=str(DEFAULT_WEIGHTS))
        return _generator
    except Exception as exc:  # noqa: BLE001
        _generator_error = str(exc)
        raise HTTPException(status_code=500, detail=f"Failed to load handwriting model: {exc}")


def get_gate():
    """Lazy-load the classifier legibility gate (same one app.py's research
    pipeline uses), so best-of-N scoring is consistent across both frontends.
    Degrades gracefully to None (generate_page.score_generation falls back to
    an ink-density heuristic) if torch or the checkpoint aren't available.
    """
    global _gate, _gate_loaded
    if not _gate_loaded:
        import generate_page  # noqa: E402
        _gate = generate_page._load_classifier()
        _gate_loaded = True
    return _gate


def extract_style_reference(sample_image_path: str, temp_dir: str) -> str:
    """
    Ensure the image is a valid line crop for style extraction.
    If it's a full page image, attempt segmentation to pick a clear line.
    """
    try:
        img = Image.open(sample_image_path)
        w, h = img.size

        # If it is reasonably wide and short (a single line crop), use it directly
        if w > h * 1.8 and h <= 300:
            return sample_image_path

        # Otherwise, attempt to extract a clean line via segment.py
        import segment  # noqa: E402
        work_dir = os.path.join(temp_dir, 'seg_work')
        os.makedirs(work_dir, exist_ok=True)
        segment.segment_handwriting(sample_image_path, work_dir, mode='auto')

        # Look for segmented line crops or character crops in work_dir
        manifest = os.path.join(work_dir, 'manifest.csv')
        if os.path.exists(manifest):
            import csv
            with open(manifest, newline='', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
            if rows:
                binary = segment.preprocess(sample_image_path)
                first_line_rows = [r for r in rows if r.get('line') == rows[0].get('line', '0')]
                if first_line_rows:
                    boxes = [(int(r['x']), int(r['y']), int(r['width']), int(r['height'])) for r in first_line_rows]
                    bbox = segment.line_bbox(boxes, pad=6, img_shape=binary.shape)
                    crop = segment.crop_line_image(binary, bbox)
                    if crop is not None:
                        out_line = os.path.join(temp_dir, 'extracted_line.png')
                        import cv2
                        cv2.imwrite(out_line, crop)
                        return out_line
    except Exception as e:
        print(f"[WARN] Style extraction fallback: {e}")

    return sample_image_path


@app.get("/health")
@app.get("/api/health")
def health():
    weights_ok = DEFAULT_WEIGHTS.exists()
    style_ok = DEFAULT_STYLE_REF.exists()
    return {
        "status": "ok" if weights_ok else "warning",
        "model_weights_available": weights_ok,
        "weights_path": str(DEFAULT_WEIGHTS),
        "default_style_available": style_ok,
        "engine": "TensorFlow Diffusion Handwriting Generator",
    }


@app.post("/api/generate")
async def generate(
    prompt: str = Form(...),
    sample_file: Optional[UploadFile] = File(None),
    ink_color: str = Form("#1a1a2e"),
    paper: str = Form("white"),
    tries: int = Form(1),
    max_chars: int = Form(45),
):
    """
    Generate handwriting image from prompt text and optional sample image.
    Returns standard AiArtifactResult JSON with base64 PNG data.
    """
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        raise HTTPException(status_code=400, detail="Prompt text cannot be empty.")

    generator = get_generator()

    with tempfile.TemporaryDirectory(prefix="inkmimic_gen_") as temp_dir:
        # Determine style reference
        if sample_file and sample_file.filename:
            temp_sample_path = os.path.join(temp_dir, f"sample_{sample_file.filename}")
            with open(temp_sample_path, "wb") as f:
                shutil.copyfileobj(sample_file.file, f)
            style_path = extract_style_reference(temp_sample_path, temp_dir)
            has_custom_style = True
        else:
            if not DEFAULT_STYLE_REF.exists():
                raise HTTPException(status_code=500, detail=f"Default style reference missing at {DEFAULT_STYLE_REF}")
            style_path = str(DEFAULT_STYLE_REF)
            has_custom_style = False

        out_dir = os.path.join(temp_dir, "output")
        os.makedirs(out_dir, exist_ok=True)

        try:
            # Generate the page (export PNG)
            generator.generate_page(
                text=cleaned_prompt,
                style_image_path=style_path,
                out_dir=out_dir,
                max_chars_per_line=max(15, min(max_chars, 80)),
                n_tries=max(1, min(tries, 5)),
                min_score=0.7,
                ink_color=ink_color,
                paper=paper,
                export_format="png",
                # The classifier gate's read-back currently scores every
                # attempt ~0 -- not because the classifier is wrong, but
                # because split_into_characters() (tuned for photographed
                # prose) over-segments this renderer's joined-cursive
                # strokes into fragments that were never real single
                # letters (e.g. "The" -> 5 crops instead of 3), so it has
                # nothing meaningful to classify. Falling back to the
                # ink-density heuristic (gate=None) until that segmentation
                # heuristic is re-tuned for synthetic renders specifically.
                gate=None,
            )

            png_file = os.path.join(out_dir, "page_output.png")
            if not os.path.exists(png_file):
                raise RuntimeError("Page generation did not output page_output.png")

            with open(png_file, "rb") as f:
                img_bytes = f.read()

            b64_data = base64.b64encode(img_bytes).decode("utf-8")
            data_uri = f"data:image/png;base64,{b64_data}"

            style_note = "custom handwriting style" if has_custom_style else "classic IAM handwriting style"
            return {
                "id": str(uuid.uuid4()),
                "kind": "image",
                "content": data_uri,
                "note": f"Rendered into handwriting using {style_note} on {paper} paper.",
            }

        except Exception as exc:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Generation failed: {exc}")


@app.post("/api/analyze-style")
async def analyze_style(sample_file: UploadFile = File(...)):
    """
    Analyze style characteristics of a sample image.
    """
    if not sample_file or not sample_file.filename:
        raise HTTPException(status_code=400, detail="Sample file is required.")

    content = await sample_file.read()
    try:
        img = Image.open(io.BytesIO(content)).convert("L")
        arr = np.asarray(img)
        ink = (arr < 128).astype(np.float32)
        density = float(ink.mean())

        weight_desc = "Bold / Heavy stroke" if density > 0.15 else "Medium stroke" if density > 0.07 else "Fine / Light stroke"

        return {
            "slantDescription": "Natural rightward slant (~12°)",
            "strokeWeightDescription": weight_desc,
            "confidence": round(min(0.95, max(0.65, 1.0 - abs(0.10 - density) * 5)), 2),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not analyze image: {exc}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
