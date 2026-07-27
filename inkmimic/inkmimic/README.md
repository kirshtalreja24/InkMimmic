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

This is the part left for you to build. Two packages live in
`src/packages/`:

- **`ai-core/`** — empty on purpose. This is where your production
  handwriting-generation model gets wired in.
- **`ai-prototype/`** — a working stand-in that calls the Anthropic API
  directly from the browser, so the chat box, drag-and-drop, and full
  request/response loop can be tested right now. It is **not** safe to
  ship — see `src/packages/README.md` for the migration path to `ai-core`.

To test the prototype chat, add `VITE_ANTHROPIC_API_KEY` to `.env`.

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
    ai-core/        <- implement your real AI integration here
    ai-prototype/   <- Anthropic-backed stand-in, for testing only
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
