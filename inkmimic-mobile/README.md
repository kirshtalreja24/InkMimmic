# Inkmimic (mobile)

The mobile counterpart to the Inkmimic webapp — same product, same visual
identity, same modular architecture, built with Expo + React Native
instead of Vite + React.

Royal blue + gold "ink and paper" identity, Supabase for auth/storage, and
the same AI boundary pattern (`ai-core` left empty, `ai-prototype` backed
by Gemini for testing).

## Stack

- **Expo + React Native** — app shell (works on iOS, Android, and web via
  Expo)
- **NativeWind** — Tailwind-style utility classes for React Native
- **React Navigation** (native stack) — Landing → About → Auth → Workspace
- **Supabase** — same backend the webapp uses; email/password auth,
  session persistence via AsyncStorage, file storage for handwriting
  samples
- **@expo-google-fonts** — Fraunces, Manrope, Caveat, matching the webapp's
  type system exactly

## Getting started

```bash
npm install
cp .env.example .env   # then fill in your keys
npx expo start
```

Scan the QR code with the **Expo Go** app on your phone, or press `i` / `a`
in the terminal to open an iOS/Android simulator if you have one set up.

### Supabase

You can reuse the exact same Supabase project as the webapp — same URL,
same anon key, same `handwriting-samples` bucket. If it's a fresh project,
run `supabase/setup.sql` in the SQL editor first.

### AI integration

Same split as the webapp:

- **`src/packages/ai-core/`** — empty on purpose. Implement your real
  handwriting-generation model here.
- **`src/packages/ai-prototype/`** — a working Gemini-backed stand-in so
  the chat screen can be tested today. Add `EXPO_PUBLIC_GEMINI_API_KEY` to
  `.env` to try it. **Not safe for a released build** — see
  `src/packages/README.md` for the migration path.

## Differences from the webapp (by necessity, not by choice)

| Webapp | Mobile | Why |
|---|---|---|
| Drag-and-drop file zone | Take photo / photo library / browse files buttons | No drag-and-drop on a touchscreen |
| CSS `clip-path` ink-reveal wordmark | `Animated` width-reveal wordmark | RN has no `clip-path` |
| `localStorage`-backed Supabase session | `AsyncStorage`-backed Supabase session | No browser storage on native |
| `File` objects | Picker "asset" objects (`{ uri, mimeType, fileName }`) | RN has no browser File API |
| Tailwind + Vite | NativeWind + Expo | Different renderer (DOM vs native views) |

Every screen, state name, and the file/folder layout otherwise mirror the
webapp 1:1, so working on one should feel familiar coming from the other.

## Project structure

```
App.js                  entry point, loads fonts, wraps providers
src/
  screens/              LandingScreen, AboutScreen, AuthScreen, ChatWorkspaceScreen
  navigation/            RootNavigator (stack, gates Workspace behind auth)
  components/
    ui/                  Button, Card, InkDivider, InkWordmark
    auth/                LoginForm, RegisterForm
    workspace/           SamplePicker, ChatPanel, ArtifactPreview, SessionHeader
  context/               AuthContext
  hooks/                 useAuth, useSamplePicker
  lib/supabase/          client.js, auth.js, storage.js
  packages/
    ai-core/             <- implement your real AI integration here
    ai-prototype/        <- Gemini-backed stand-in, for testing only
  config/                env.js
  types/                 shared JSDoc typedefs for AI request/response shapes
supabase/
  setup.sql              storage bucket + RLS policies (same as webapp)
```
