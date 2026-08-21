# Mobile app tech stack: Expo + React Native + Supabase

Status: accepted

The Inkmimic mobile app (`inkmimic-mobile/`) is a separate Expo / React Native codebase — not React Native Web reusing the web app's components. It uses React Navigation (native-stack) for routing, NativeWind/Tailwind for styling, `@supabase/supabase-js` with an `AsyncStorage`-backed session adapter (mirroring the web app's `localStorage` adapter — see the session-module deepening candidate from the architecture review), and Expo's image/document pickers to build the platform-specific "asset" shape `ai-core` sends to `api/server.py`.

**Consequences:** every screen exists twice, hand-mirrored — `inkmimic-mobile/README.md`'s own "Differences from the webapp" table frames this as necessity (no DOM, no `File`/`Blob`, no `localStorage` on native), not preference. The session/auth logic and the `api/server.py` client no longer are: both now come from the shared `packages/inkmimic-core/` workspace package (npm workspaces, added alongside this ADR), with each app supplying only its platform-specific storage adapter or FormData sample-attachment. See `docs/adr/workflow.md`'s Dev environment section.

**Note:** nothing in the repo documents *why* this is two hand-mirrored UI codebases instead of one React Native Web codebase serving both targets. No alternative appears to have been evaluated. This is recorded here as the current, working state, not as a considered trade-off — worth revisiting explicitly before adding a third platform or a fifth duplicated screen.
