# Web app tech stack: Vite + React + Tailwind + Supabase

Status: accepted

The Inkmimic web app (`inkmimic/inkmimic/`) is a Vite-bundled React 18 SPA: `react-router-dom` for routing, Tailwind for styling, `@supabase/supabase-js` for auth (with a `localStorage`-backed local-mode fallback — see Local mode in `CONTEXT.md`). It talks to the handwriting generation model only over HTTP, through the FastAPI backend in `api/server.py` — it never imports Python model code directly.

**Consequences:** deployment is a static SPA build plus a separately-hosted API, and auth/session storage is tied to Supabase specifically; swapping either touches `src/lib/supabase/*` and `src/packages/ai-core/` and nowhere else, by design (see the ai-core deepening candidate from the architecture review).

**Note:** no rationale for choosing Vite/React/Tailwind specifically (over, say, Next.js) is recorded anywhere in the repo. This ADR documents the stack that was built, not a deliberated choice between named alternatives — flagging that honestly rather than inventing a trade-off that isn't there.
