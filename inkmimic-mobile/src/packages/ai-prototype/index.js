import { sendPrototypeMessage, assetToBase64 } from './geminiClient.js';

/**
 * Stand-in for ai-core's generateHandwrittenArtifact(), shaped the same
 * way, so swapping the import in ChatPanel later is a one-line change.
 *
 * Works with or without a sample attached — with no file, it just answers
 * the prompt as text, which is enough to verify the chat wiring end to end.
 *
 * @param {object} params
 * @param {{ uri: string, mimeType: string }} [params.sampleAsset]
 * @param {string} params.prompt
 * @param {AbortSignal} [params.signal]
 * @returns {Promise<{ id: string, kind: 'text', content: string }>}
 */
export async function generateHandwrittenArtifact({ sampleAsset, prompt, signal }) {
  let image;
  if (sampleAsset && sampleAsset.mimeType?.startsWith('image/')) {
    image = { base64: await assetToBase64(sampleAsset), mimeType: sampleAsset.mimeType };
  }

  const instruction = sampleAsset
    ? `A user attached a handwriting sample ("${sampleAsset.fileName ?? 'sample'}") and asked: "${prompt}". ` +
      `Describe, in a warm and concrete way, what a regenerated handwritten page would look like ` +
      `for this request, as if reporting back the result. This is a prototype response standing in ` +
      `for real handwriting-synthesis output.`
    : prompt;

  const text = await sendPrototypeMessage({ prompt: instruction, image, signal });

  return {
    id: `${Date.now()}`,
    kind: 'text',
    content: text,
  };
}
