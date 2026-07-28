import { sendPrototypeMessage, fileToBase64 } from './geminiClient.js';
/**
 * Stand-in for ai-core's generateHandwrittenArtifact(), shaped the same
 * way, so swapping the import in ChatPanel later is a one-line change.
 *
 * Since real handwriting synthesis lives in ai-core (not built yet), this
 * just asks Claude to describe/transform the text so the end-to-end wiring
 * — upload, prompt, request, response, render — can be verified now.
 *
 * @param {object} params
 * @param {File} [params.sampleFile]
 * @param {string} params.prompt
 * @param {AbortSignal} [params.signal]
 * @returns {Promise<{ id: string, kind: 'text', content: string }>}
 */
export async function generateHandwrittenArtifact({ sampleFile, prompt, signal }) {
  let image;
  if (sampleFile && sampleFile.type.startsWith('image/')) {
    image = { base64: await fileToBase64(sampleFile), mediaType: sampleFile.type };
  }

  const instruction = sampleFile
    ? `A user uploaded a handwriting sample ("${sampleFile.name}") and asked: "${prompt}". ` +
      `Describe, in a warm and concrete way, what a regenerated handwritten page would look like ` +
      `for this request, as if reporting back the result. This is a prototype response standing in ` +
      `for real handwriting-synthesis output.`
    : prompt;

  const text = await sendPrototypeMessage({ prompt: instruction, image, signal });

  return {
    id: crypto.randomUUID(),
    kind: 'text',
    content: text,
  };
}
