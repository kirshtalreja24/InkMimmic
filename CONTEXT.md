# AI Handwriter

Turns photographs of a person's handwriting into a per-writer generative model, then renders new typed text as pages in that handwriting. Two connected parts: a Python ML pipeline (preprocessing → segmentation → classifier → diffusion generation, rooted at the repo root and `diffusion_model/`) and Inkmimic, a product front end (web + mobile) that calls a FastAPI backend for stateless style-transfer generation.

## Language

### Handwriting synthesis pipeline

**Writer**:
The person whose handwriting is being captured and modeled. Identified only by name — raw photos live under `data/<writer>/`, the full per-writer pipeline (crops, strokes, transcript, fine-tuned weights) lives under `app/users/<writer>/`.
_Avoid_: user (reserved for Inkmimic's Account below — a different concept)

**Page photo**:
A raw phone photo of a handwritten page — the pipeline's input.

**Binary image**:
The cleaned black-and-white output of preprocessing (perspective correction, deskew, shadow removal, Sauvola thresholding) — the direct input to segmentation.

**Page type**:
Preprocessing's classification of a page as blank, ruled, or grid — determines whether ruled/grid-line removal runs.

**Blob**:
A raw connected component found in a binary image, before it's grouped into lines, words, and characters. May span multiple pen-joined letters or be a single letter.

**Line / Word / Character crop**:
The three nesting levels segmentation groups blobs into; each character crop is saved as `lineNN_wordNN_charNN.png` with a matching row in a manifest.

**Manifest**:
The `manifest.csv` a segmentation run writes alongside its crops — one row per character crop, with its line/word/char index and bounding box.

**Prose mode / Isolated mode**:
Segmentation's two splitting behaviors. Prose assumes pen-joined letters and runs valley-based splitting to cut them apart; isolated assumes deliberately spaced glyphs (e.g. an alphabet practice sheet) and skips splitting entirely. Auto-detected per line by default.

**Segmentation run**:
One raw, unlabeled output of running segmentation on a page (e.g. `chars9/`) — flat crops plus a manifest, no ground-truth label yet.
_Avoid_: dataset (reserved for the labeled set below)

**Labeled dataset**:
`dataset/<label>/` — character crops sorted by confirmed ground-truth label, built by hand-labeling or auto-labeling a segmentation run. What the classifier actually trains on.

**Checkpoint**:
A saved classifier weights file paired with its class list, so the label-to-index mapping can never silently drift between training runs.

**Stroke**:
One online-format sample point — a differential `(dx, dy, pen_up)` offset from the previous point. What the diffusion model consumes and produces, as opposed to raw pixels.

**Stroke reconstruction**:
Approximating online stroke data from an offline (photographed) handwriting line, since no real pen-tablet capture exists in this project. Lossy — pen order, timing, and loops are inferred, not recorded.

**Style reference (line)**:
The one line-crop image of a writer's real handwriting fed into the frozen style extractor to condition a generation run.

**Style vector**:
The style extractor's output for a given style reference — computed once per run and reused across every line of a page so the output stays visually consistent.

**Per-writer fine-tuning**:
Training the diffusion decoder (never the style extractor) on one writer's reconstructed strokes, starting from IAM-pretrained weights, to shift generation closer to that writer's actual hand.

**IAM weights / base weights**:
The pretrained starting checkpoint (from the public IAM handwriting database), always kept and never overwritten by a per-writer fine-tune.

**Best-of-N / legibility gate**:
Since generation starts from random noise, several attempts are generated per page and the most legible one is kept — scored either by a trained classifier's read-back or a cheaper ink-density heuristic.

**Transcript**:
The typed ground-truth text for a line, keyed by line name — required to build fine-tuning training pairs.

### Inkmimic product

**Account**:
A registered (or local-mode) Inkmimic identity, authenticated via a Session.
_Avoid_: user (this repo has two unrelated "user" concepts — see Writer above)

**Session**:
The signed-in Account's Supabase authentication session — signing in, staying signed in, signing out.

**Local mode**:
A dev/demo fallback that activates when Supabase isn't configured — auth calls accept any email/password and fabricate a Session stored on-device, so the product can be exercised without real credentials.

**Guest access**:
The "Continue as Guest" button — signs in with one shared hardcoded demo credential. Not a real anonymous-account feature.

**Workspace**:
The screen where a signed-in Account submits a prompt and Sample and views the resulting Artifact.

**Sample**:
The user's uploaded or captured handwriting reference image, attached to a generation request.

**Artifact**:
The generated result of one request — `{ id, kind: 'image'|'text', content, note }`. Ephemeral: held only in memory for the current Workspace visit, never persisted.
