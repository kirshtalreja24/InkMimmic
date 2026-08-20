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
import { env } from '../../config/env.js';

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
export async function generateHandwrittenArtifact({
  sampleFile,
  prompt,
  inkColor = '#1a1a2e',
  paper = 'white',
  signal,
}) {
  if (!prompt || !prompt.trim()) {
    throw new Error('Please enter some text to write.');
  }

  const formData = new FormData();
  formData.append('prompt', prompt.trim());
  formData.append('ink_color', inkColor);
  formData.append('paper', paper);
  formData.append('tries', '1');

  if (sampleFile) {
    formData.append('sample_file', sampleFile);
  }

  const response = await fetch(`${env.apiUrl}/api/generate`, {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const message = errData.detail || `Server error (${response.status}): ${response.statusText}`;
    throw new Error(message);
  }

  const result = await response.json();
  return {
    id: result.id || crypto.randomUUID(),
    kind: result.kind || 'image',
    content: result.content,
    note: result.note || 'Generated handwriting page.',
  };
}

/**
 * Analyze an uploaded handwriting sample (stroke width, slant, confidence).
 *
 * @param {File|Blob} sampleFile
 * @param {AbortSignal} [signal]
 * @returns {Promise<AiStyleProfile>}
 */
export async function analyzeHandwritingStyle(sampleFile, signal) {
  if (!sampleFile) {
    throw new Error('A handwriting sample file is required for style analysis.');
  }

  const formData = new FormData();
  formData.append('sample_file', sampleFile);

  const response = await fetch(`${env.apiUrl}/api/analyze-style`, {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || 'Style analysis failed.');
  }

  return response.json();
}

