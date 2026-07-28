// packages/ai-core
// -----------------------------------------------------------------------
// This is the dedicated home for Inkmimic's real AI integration. It is
// intentionally left unimplemented — wire up your production model
// (handwriting synthesis, style transfer, whatever the backend ends up
// being) behind the interface below.
//
// Nothing else in the app should import an AI provider's SDK directly.
// Pages and components call the functions exported from here, so the
// implementation can change (self-hosted model, different vendor, a
// Supabase Edge Function proxy, etc.) without touching UI code.
//
// src/packages/ai-prototype is a separate, throwaway package that
// currently stands in for this one so the chat UI has something to talk
// to during development. Once this package is implemented, point
// ChatPanel at `generateHandwrittenArtifact` from here instead.
// -----------------------------------------------------------------------

import '../../types/ai.js'; // JSDoc typedefs only, no runtime code

/**
 * Turn a handwriting sample + instructions into a newly generated artifact.
 *
 * @param {object} params
 * @param {File|Blob} params.sampleFile - the user's handwriting sample.
 * @param {string} params.prompt - what the user asked for in chat.
 * @param {AbortSignal} [params.signal] - to support cancellation.
 * @returns {Promise<AiArtifactResult>}
 */
export async function generateHandwrittenArtifact(/* { sampleFile, prompt, signal } */) {
  throw new Error(
    'ai-core is not implemented yet. Implement generateHandwrittenArtifact() here, ' +
      'or use src/packages/ai-prototype for local testing.'
  );
}

/**
 * Optional: analyze an uploaded sample up front (stroke width, slant,
 * spacing) before generation. Left as a stub for the same reason as above.
 *
 * @param {File|Blob} sampleFile
 * @returns {Promise<AiStyleProfile>}
 */
export async function analyzeHandwritingStyle(/* sampleFile */) {
  throw new Error('ai-core is not implemented yet. Implement analyzeHandwritingStyle() here.');
}
