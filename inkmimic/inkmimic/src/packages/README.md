# AI packages

Two packages live here, on purpose:

### `ai-core/`
The real integration. Left empty. This is where handwriting-synthesis
generation should be implemented, behind the `generateHandwrittenArtifact`
and `analyzeHandwritingStyle` exports already stubbed out in `index.js`.
Nothing in `pages/` or `components/` should ever import an AI SDK directly —
they should only ever import from `ai-core` (or, during development,
`ai-prototype`).

### `ai-prototype/`
A working stand-in that calls the Anthropic API directly from the browser,
so the chat box, drag-and-drop, and end-to-end flow can be tested before
`ai-core` exists. It exports the exact same function shape as `ai-core`.

**This is not production-safe.** It ships your Anthropic API key inside the
client bundle (via `anthropic-dangerous-direct-browser-access`). Before
launch:

1. Move the Anthropic (or your production model) call into a Supabase Edge
   Function or other server-side endpoint.
2. Implement `ai-core/index.js` to call that endpoint instead.
3. In `src/components/workspace/ChatPanel.jsx`, change the import from
   `../../packages/ai-prototype` to `../../packages/ai-core`.
4. Remove `VITE_ANTHROPIC_API_KEY` from any client-side `.env`.

### Switching today

Everything is wired through `ChatPanel.jsx`'s single import line — swap it
whenever `ai-core` is ready:

```js
// current (prototype)
import { generateHandwrittenArtifact } from '../../packages/ai-prototype';

// after ai-core is implemented
import { generateHandwrittenArtifact } from '../../packages/ai-core';
```
