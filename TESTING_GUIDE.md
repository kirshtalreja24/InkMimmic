# Testing Guide — Handwriting Generation Pipeline

This covers how to run/test the handwriting generation pipeline as it
currently stands (PDF export added, blank-page bug fixed), and how it
connects to the Streamlit web app.

---

## 1. Setup (one time)

From the project root (`ai_handwriter/`):

```bash
py -3.12 -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements-app.txt
```

If TensorFlow complains about numpy:
```bash
pip install "numpy<2"
```

Verify the environment:
```bash
python -c "import tensorflow, torch, cv2, streamlit, skimage; print('env OK')"
```

---

## 2. Quick smoke test (no training required)

Uses the IAM base weights — style-transfer only, not per-user identical.

```bash
cd diffusion_model
python inference.py --textstring "The quick brown fox" --name smoke
```

Check `smoke.png` was created and has visible ink (not blank).

---

## 3. Generate a page — single line

Run from inside `diffusion_model/`:

```bash
python generate_page.py \
    --text "HELLO WORLD" \
    --weights weights/model_weights.h5 \
    --style ../data/alizeh/s.png \
    --out ./out
```

By default this now outputs **PDF only** (`./out/page_output.pdf`).

To get PNG instead of/as well as PDF:
```bash
--format png     # PNG only
--format both     # both PNG and PDF
--format pdf      # PDF only (default, same as omitting --format)
```

Open the result (macOS):
```bash
open ./out/page_output.pdf
```

---

## 4. Generate a page — multiple lines

`generate_page.py` auto-wraps long text into multiple lines and stacks
them into one page — no separate command needed, just pass longer text:

```bash
python generate_page.py \
    --text "This is a longer sentence that should wrap across several lines once it goes past the max characters per line setting, so you can see how a full paragraph looks." \
    --weights weights/model_weights.h5 \
    --style ../data/alizeh/s.png \
    --out ./out \
    --max_chars 40 \
    --tries 5
```

Flags that affect wrapping/quality:

| Flag | Meaning |
|---|---|
| `--max_chars` | Characters per line before it wraps (lower = shorter lines, more of them) |
| `--tries` | Best-of-N stochastic retries per line (higher = better odds of a clean result, slower) |
| `--height` | Line height in px |
| `--ink` | Ink color (hex) |
| `--paper` | `white` \| `ruled` \| `graph` |
| `--no_gate` | Disable the legibility-gate scoring (use if the classifier/segment step is unavailable or misbehaving) |

**Note:** `--text` is wrapped as one continuous paragraph
(`textwrap.wrap`). Literal `\n` line breaks in your input are **not**
preserved as separate lines — they get collapsed and re-wrapped by
`--max_chars` instead.

---

## 5. Debug output (added while fixing the blank-page bug)

Every run now prints, per line:
```
[DEBUG] line 00 strokes shape=... min=... max=... mean=... pen_up_frac=...
```
and saves the model's raw, unprocessed stroke preview separately from the
final rendered image:
```
./out/_try{N}_line{NN}_raw.png     ← straight from the model (matplotlib)
./out/_try{N}_line{NN}.png         ← after renderer.py (PIL, styled ink)
```

If you ever see a blank page again, check `_raw.png` first — if that's
also blank, the problem is upstream (model/weights), not in the renderer.

---

## 6. Verification checklist

Run in order — each gate should pass before moving to the next:

1. `python -c "import tensorflow, torch, cv2, streamlit, skimage"` → no errors
2. `inference.py --textstring "..." --name smoke` → `smoke.png` has visible ink
3. `generate_page.py` single-line test (§3) → `page_output.pdf` has visible ink, not blank
4. `generate_page.py` multi-line test (§4) → all lines render, page composes correctly

---

## 7. How this connects to the web app (`app/app.py`)

The Streamlit app (Step 6 of its flow) calls the same `PageGenerator`
class from `generate_page.py` under the hood — it's the same generation
code, just wired into a UI instead of the CLI.

**To expose the PDF as a downloadable file in the app**, Step 6 needs to:

```python
page_path = generator.generate_page(text, style_image_path, out_dir, ...)

with open(page_path, "rb") as f:
    pdf_bytes = f.read()

st.download_button(
    label="Download handwritten page (PDF)",
    data=pdf_bytes,
    file_name="my_handwriting.pdf",
    mime="application/pdf",
)
```

Notes:
- Since `generate_page()`'s default `export_format` is `'pdf'`, `page_path`
  will already point at a `.pdf` file — no extra conversion needed.
- Streamlit can't preview PDFs inline natively. If you want an on-screen
  preview before the user downloads, generate with `export_format='both'`
  instead, show the `.png` inline with `st.image(...)`, and offer the
  `.pdf` as the actual download via `st.download_button` as above.
- This change lives in `app/app.py`, not in `generate_page.py` — the
  backend already produces the file; the app just needs to read it and
  hand it to the user.

---

## 8. Known bugs fixed in this pass (for reference)

| Bug | File | Fix |
|---|---|---|
| `IndexError` in `compute_velocities` — `pen_up` shape `(N,1)` instead of `(N,)` | `renderer.py` | Flatten `pen_up` with `.reshape(-1)` |
| `IndexError` — `pen_up` length didn't match `points` length | `renderer.py` | Align lengths (truncate/pad) right after unpacking in `render_strokes()` |
| Blank page — `run_batch_inference()` returns a batched `(1, T, 3)` array, but renderer expected `(T, 3)` | `generate_page.py` | Unwrap with `[0]` right where strokes come out of the model |
| `NameError: _load_as_grayscale not defined` | `generate_page.py` | Function was imported only inside `_load_classifier()`'s local scope; now stored in the `gate` dict and read back in `score_generation()` |
| No PDF export | `generate_page.py` | `_compose_page()` now saves PDF (default) and/or PNG via `--format` |
