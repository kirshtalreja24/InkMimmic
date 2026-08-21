// packages/ai-core
// -----------------------------------------------------------------------
// The real AI integration — same role as src/packages/ai-core in the
// webapp: a client for the FastAPI handwriting model backend
// (api/server.py), calling /api/generate and /api/analyze-style.
//
// Nothing else in the app should import an AI provider's SDK directly.
// Screens and components call the functions exported from here, so the
// implementation can change without touching UI code.
//
// The request/response logic itself lives in the shared `inkmimic-core`
// package (identical on web) — this file only supplies the one thing
// that's genuinely platform-specific: how a sample attaches to FormData.
// -----------------------------------------------------------------------

import '../../types/ai.js'; // JSDoc typedefs only, no runtime code
import { createAiCoreClient } from 'inkmimic-core';
import { env } from '../../config/env.js';

const client = createAiCoreClient({
  apiUrl: env.apiUrl,
  buildSamplePart: (sampleAsset) => ({
    uri: sampleAsset.uri,
    name: sampleAsset.fileName || 'sample.jpg',
    type: sampleAsset.mimeType || 'image/jpeg',
  }),
});

/**
 * Turn a handwriting sample + instructions into a newly generated handwriting artifact.
 *
 * @param {object} params
 * @param {{ uri: string, mimeType?: string, fileName?: string }} [params.sampleAsset] - the user's handwriting sample.
 * @param {string} params.prompt - what the user asked for in chat.
 * @param {string} [params.inkColor] - ink hex code (default #1a1a2e).
 * @param {string} [params.paper] - paper style ('white' | 'ruled' | 'graph').
 * @param {AbortSignal} [params.signal] - to support cancellation.
 * @returns {Promise<AiArtifactResult>}
 */
export async function generateHandwrittenArtifact({ sampleAsset, prompt, inkColor, paper, signal }) {
  return client.generateHandwrittenArtifact({
    sample: sampleAsset?.uri ? sampleAsset : null,
    prompt,
    inkColor,
    paper,
    signal,
  });
}

/**
 * @param {{ uri: string, mimeType?: string, fileName?: string }} sampleAsset
 * @param {AbortSignal} [signal]
 * @returns {Promise<AiStyleProfile>}
 */
export async function analyzeHandwritingStyle(sampleAsset, signal) {
  return client.analyzeHandwritingStyle(sampleAsset?.uri ? sampleAsset : null, signal);
}
