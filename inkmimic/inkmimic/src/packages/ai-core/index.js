// packages/ai-core
// -----------------------------------------------------------------------
// The real AI integration: a client for the FastAPI handwriting model
// backend (api/server.py), calling /api/generate and /api/analyze-style.
//
// Nothing else in the app should import an AI provider's SDK directly.
// Pages and components call the functions exported from here, so the
// implementation can change (self-hosted model, different vendor, a
// Supabase Edge Function proxy, etc.) without touching UI code.
//
// The request/response logic itself lives in the shared `inkmimic-core`
// package (identical on mobile) — this file only supplies the one thing
// that's genuinely platform-specific: how a sample attaches to FormData.
// -----------------------------------------------------------------------

import '../../types/ai.js'; // JSDoc typedefs only, no runtime code
import { createAiCoreClient } from 'inkmimic-core';
import { env } from '../../config/env.js';

const client = createAiCoreClient({
  apiUrl: env.apiUrl,
  buildSamplePart: (sampleFile) => sampleFile, // File/Blob passed straight through
  genId: () => crypto.randomUUID(),
});

/**
 * Turn a handwriting sample + instructions into a newly generated handwriting artifact.
 *
 * @param {object} params
 * @param {File|Blob} [params.sampleFile] - the user's handwriting sample.
 * @param {string} params.prompt - what the user asked for in chat.
 * @param {string} [params.inkColor] - ink hex code (default #1a1a2e).
 * @param {string} [params.paper] - paper style ('white' | 'ruled' | 'graph').
 * @param {AbortSignal} [params.signal] - to support cancellation.
 * @returns {Promise<AiArtifactResult>}
 */
export async function generateHandwrittenArtifact({ sampleFile, prompt, inkColor, paper, signal }) {
  return client.generateHandwrittenArtifact({ sample: sampleFile, prompt, inkColor, paper, signal });
}

/**
 * Analyze an uploaded handwriting sample (stroke width, slant, confidence).
 *
 * @param {File|Blob} sampleFile
 * @param {AbortSignal} [signal]
 * @returns {Promise<AiStyleProfile>}
 */
export async function analyzeHandwritingStyle(sampleFile, signal) {
  return client.analyzeHandwritingStyle(sampleFile, signal);
}
