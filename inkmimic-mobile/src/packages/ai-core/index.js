// packages/ai-core
// -----------------------------------------------------------------------
// This is the dedicated home for Inkmimic's real AI integration — same
// role as src/packages/ai-core in the webapp. It is intentionally left
// unimplemented. Wire up your production model (handwriting synthesis,
// style transfer, etc.) behind the interface below.
//
// Nothing else in the app should import an AI provider's SDK directly.
// Screens and components call the functions exported from here, so the
// implementation can change without touching UI code.
//
// src/packages/ai-prototype is a separate, throwaway package that stands
// in for this one so the chat UI has something to talk to during
// development. Once this package is implemented, point ChatPanel at
// `generateHandwrittenArtifact` from here instead.
// -----------------------------------------------------------------------

import '../../types/ai.js'; // JSDoc typedefs only, no runtime code

/**
 * Turn a handwriting sample + instructions into a newly generated artifact.
 *
 * @param {object} params
 * @param {{ uri: string, mimeType: string }} [params.sampleAsset] - the user's handwriting sample.
 * @param {string} params.prompt - what the user asked for in chat.
 * @param {AbortSignal} [params.signal] - to support cancellation.
 * @returns {Promise<AiArtifactResult>}
 */
export async function generateHandwrittenArtifact(/* { sampleAsset, prompt, signal } */) {
  throw new Error(
    'ai-core is not implemented yet. Implement generateHandwrittenArtifact() here, ' +
      'or use src/packages/ai-prototype for local testing.'
  );
}

/**
 * @param {{ uri: string, mimeType: string }} sampleAsset
 * @returns {Promise<AiStyleProfile>}
 */
export async function analyzeHandwritingStyle(/* sampleAsset */) {
  throw new Error('ai-core is not implemented yet. Implement analyzeHandwritingStyle() here.');
}
