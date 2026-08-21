# Ship the stateless style-transfer flow; shelve per-writer fine-tuning

Status: accepted

Two independent generation workflows exist (`docs/adr/workflow.md`): Workflow A (`app/app.py`, Streamlit) builds a genuinely fine-tuned per-writer model — multi-page upload, manual per-line transcription, stroke reconstruction, a real fine-tuning run. Workflow B (`api/server.py` + Inkmimic web/mobile) is stateless one-shot style transfer off the base IAM weights — one sample photo, one prompt, one request.

**Decision: Workflow B is the product.** Workflow A is not wired into it today (the API never loads a fine-tuned `.h5` file) and stays that way — kept only as a research/FYP-demo artifact, not a target for further engineering investment.

**Why:** Workflow A's onboarding — manually typing out what every line of a multi-page upload says — is not something a real user will do; it's a data-labeling chore, not a signup flow. Its stroke reconstruction is admittedly approximate (ADR 0003), and the style extractor is frozen either way (ADR 0002), so the fidelity ceiling is the same for both paths — the extra effort doesn't buy a proportionally better result. This matches this project's own prior conclusion (`summary.txt`): *"the style-ref-only path is live today and is the most credible story with the data you have."*

**Consequences:** `app/app.py`'s Streamlit-callback/orchestration entanglement (the deferred, optional Phase 6 cleanup candidate) is not worth fixing — don't invest further engineering time there. Going live means closing Workflow B's real gaps.

**Update:** two of those gaps are now closed. Login is mandatory (the "Continue as Guest" bypass was removed from both apps' auth screens) and persistence is wired up — Samples and Artifacts now save to Supabase Storage plus a `public.artifacts` row per Account, via `packages/inkmimic-core/src/persistence.js` (see `CONTEXT.md`'s Sample/Artifact entries and `supabase/setup.sql` in each app). Remaining gaps: open CORS (`allow_origins=["*"]` in `api/server.py`), no real deployment target, and no rate limiting on a public generation endpoint.
