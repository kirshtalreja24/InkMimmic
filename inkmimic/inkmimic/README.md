# Inkmimic

An AI handwriting tool: upload a sample of your handwriting, describe what
you want, and get back a new page written in the same hand.

Royal blue + gold "ink and paper" visual identity, built with React + Vite +
Tailwind, Supabase for auth/storage, and a modular AI boundary so the real
model integration can be dropped in without touching any UI code.

## Stack

- **React 18 + Vite** — app shell
- **Tailwind CSS** — theming (see `tailwind.config.js` for the full color/
  type/animation token system)
- **React Router** — routes for landing, about, auth, and the protected
  workspace
- **Supabase** — email/password auth, session persistence, and file storage
  for uploaded handwriting samples

## Getting started

```bash
npm install
cp .env.example .env   # then fill in your keys
npm run dev
```

### Supabase

1. Create a project at supabase.com.
2. Copy the Project URL and anon public key into `.env`.
3. Run `supabase/setup.sql` in the SQL editor to create the storage bucket
   and its row-level security policies.
4. Email/password auth is on by default in a new Supabase project — nothing
   else to enable for this to work.

Without a `.env`, the app still runs: the auth page will show a notice, and
`/workspace` is reachable directly for UI/prototype testing.

### AI integration

- **`src/packages/ai-core/`** — the real AI integration. Calls the FastAPI
  handwriting model backend (`api/server.py`)'s `/api/generate` and
  `/api/analyze-style` endpoints — see `src/packages/README.md`. The
  request/response logic itself lives in the shared `inkmimic-core`
  workspace package (`packages/inkmimic-core/`, also used by the mobile
  app); this package only supplies the web-specific FormData sample
  attachment.

## Project structure

```
src/
  pages/            LandingPage, AboutUsPage, AuthPage, ChatWorkspace
  components/
    layout/         Navbar, Footer, ProtectedRoute
    ui/             Button, Card, InkDivider, InkWordmark
    auth/           LoginForm, RegisterForm
    workspace/      FileDropZone, ChatPanel, ArtifactPreview, SessionHeader
  context/          AuthContext (session state, app-wide)
  hooks/            useAuth, useFileDrop
  lib/supabase/     client.js, auth.js, storage.js
  packages/
    ai-core/        <- FastAPI handwriting model client
  config/           env.js — single source of truth for env vars
  types/            shared JSDoc typedefs for AI request/response shapes
supabase/
  setup.sql         storage bucket + RLS policies
```

## Flow

Routing and workspace state follow the app's state diagram:
`Landing → About (optional) → Auth (login/register, with a validating
state on submit) → Workspace (idle → file dropped → sending → awaiting
response → regenerated, looping back to idle) → close session → Landing`.
