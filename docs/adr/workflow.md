# Project Workflow

Two independent workflows share the same generation core (`diffusion_model/generate_page.py`'s `PageGenerator`), but nothing else connects them at runtime — no shared database, no shared identity between the two. See `CONTEXT.md` for the terms used below (Writer, Account, Session, Artifact, etc).

**Workflow B is the product** (ADR 0007) — that's what's live for real users. Workflow A is kept as a research/FYP-demo artifact only; it is not wired into the product and isn't a target for further engineering investment.

## Workflow A — Building a per-writer model (research pipeline, not part of the live product)

Run via `app/app.py` (Streamlit) or its CLI equivalents (`README.md`). Produces a fine-tuned model for one Writer. Nothing in Workflow B ever loads this output.

1. **Create/select a writer** — `app/users/<name>/` is created with `photos/ lines/ strokes/ overlays/ data/ weights/ outputs/`.
2. **Upload** 1–3 page photos → `photos/`.
3. **Segment** — `segment.py` (via `preprocessing.py`) turns each photo into line crops → `lines/lineNN.png`, with an approve/reject step over the detected lines.
4. **Transcribe** — type what each line says → `transcript.json`.
5. **Reconstruct strokes** — `stroke_reconstruct.py` turns each line crop into approximate online stroke data (ADR 0003) → `strokes/lineNN.npy` + a validation overlay image.
6. **Build + fine-tune** — `build_train_data.py` assembles `data/train_strokes.p` (80/20 train/holdout split), then `finetune.py` runs decoder-only fine-tuning from IAM base weights (ADR 0002) → `weights/model_<name>.h5`.
7. **Generate** — pick a style-reference line and weights (base or fine-tuned); `PageGenerator.generate_page()` runs best-of-N generation scored by the classifier legibility gate → a page in `outputs/`.

## Workflow B — Product generation (Inkmimic, stateless) — the live product

Run via `api/server.py` (FastAPI) plus either `inkmimic/` (web) or `inkmimic-mobile/`. No per-writer fine-tuning happens here, and no Writer identity or state from Workflow A carries over — the API only ever uses the base IAM weights, style-transferred against whatever single Sample image the current request supplies (or a default IAM style line if none is given).

1. Start the backend: `uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload`.
2. Start the web app (`npm run dev` in `inkmimic/inkmimic/`) or the mobile app (`expo start` in `inkmimic-mobile/`).
3. A signed-in Account opens the Workspace, attaches a Sample (optional) and a prompt, and submits.
4. `ai-core` POSTs to `/api/generate`; the server extracts a usable style line from the Sample (`extract_style_reference`), then calls `PageGenerator.generate_page(..., gate=get_gate())` — scored with the same classifier legibility gate Workflow A uses (loaded once at server startup). Returns a base64 PNG as an Artifact.
5. The Artifact renders in the Workspace and is not persisted anywhere — no DB row, no Supabase Storage write, despite `lib/supabase/storage.js` existing on both apps for exactly this purpose and never being called. This is the top go-live gap (ADR 0007).

**Other go-live gaps (ADR 0007):** `api/server.py` currently allows CORS from any origin (`allow_origins=["*"]`), has no real deployment target, and has no rate limiting on a public generation endpoint.

## Dev environment

- **Python** — one shared venv for the whole pipeline + API (`requirements-app.txt`). See ADR 0004 for why PyTorch and TensorFlow share one interpreter.
- **Web** — Node + npm, `inkmimic/inkmimic/package.json` (Vite). See ADR 0005.
- **Mobile** — Node + npm, `inkmimic-mobile/package.json` (Expo). See ADR 0006.

`inkmimic/inkmimic/` and `inkmimic-mobile/` are npm workspace members (root `package.json`), alongside `packages/inkmimic-core/` — the module shared between them (session/auth logic and the `api/server.py` client; see the architecture-review candidates that motivated it). Each app still has its own `.env` and its own platform-specific dependencies; only the workspace-linked code and hoistable shared dependencies are common.
