# AI packages (mobile)

Same split as the webapp, on purpose:

### `ai-core/`
The real integration. Left empty. Implement `generateHandwrittenArtifact`
and `analyzeHandwritingStyle` here. Nothing in `screens/` or `components/`
should import an AI SDK directly — only these two functions.

### `ai-prototype/`
A working stand-in that calls the Gemini API directly from the app, so the
chat screen, sample picker, and end-to-end flow can be tested before
`ai-core` exists. Exports the same function shape as `ai-core`.

**Not production-safe.** It ships your Gemini API key inside the app
bundle. Before release:

1. Move the Gemini (or your production model) call into a Supabase Edge
   Function or other server-side endpoint.
2. Implement `ai-core/index.js` to call that endpoint instead.
3. In `src/components/workspace/ChatPanel.jsx`, change the import from
   `../../packages/ai-prototype` to `../../packages/ai-core`.
4. Remove `EXPO_PUBLIC_GEMINI_API_KEY` from your `.env` / EAS secrets.

### Switching later

```js
// current (prototype)
import { generateHandwrittenArtifact } from '../../packages/ai-prototype';

// after ai-core is implemented
import { generateHandwrittenArtifact } from '../../packages/ai-core';
```
