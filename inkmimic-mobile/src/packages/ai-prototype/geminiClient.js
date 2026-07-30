import * as FileSystem from 'expo-file-system';
import { env, isAiPrototypeConfigured } from '../../config/env.js';

// -----------------------------------------------------------------------
// PROTOTYPE ONLY. Do not ship this to production.
//
// This calls the Gemini API directly from the app using
// EXPO_PUBLIC_GEMINI_API_KEY, which means the key ships inside your app
// bundle and can be extracted by anyone with the built app. It's here
// purely so the chat UI has something real to talk to while
// src/packages/ai-core is being built.
//
// Before shipping: move this call behind a server (a Supabase Edge
// Function is the natural fit here, since Supabase is already wired up)
// so the API key never reaches the client, then swap ChatPanel over to
// src/packages/ai-core instead of this file.
// -----------------------------------------------------------------------

const GEMINI_ENDPOINT = (model) =>
  `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;

/**
 * Sends a chat-style prompt to Gemini and returns the text response.
 * Optionally attaches an image (the handwriting sample) for the model to
 * look at, so responses can reference what was uploaded.
 *
 * @param {object} params
 * @param {string} params.prompt
 * @param {{ base64: string, mimeType: string }} [params.image]
 * @param {AbortSignal} [params.signal]
 */
export async function sendPrototypeMessage({ prompt, image, signal }) {
  if (!isAiPrototypeConfigured) {
    throw new Error(
      'Set EXPO_PUBLIC_GEMINI_API_KEY in .env to test the chat box against the real Gemini API.'
    );
  }

  const parts = [{ text: prompt }];
  if (image) {
    parts.push({ inline_data: { mime_type: image.mimeType, data: image.base64 } });
  }

  const response = await fetch(`${GEMINI_ENDPOINT(env.geminiModel)}?key=${env.geminiApiKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ role: 'user', parts }],
    }),
    signal,
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`Gemini API error (${response.status}): ${detail || response.statusText}`);
  }

  const data = await response.json();
  const text = data.candidates?.[0]?.content?.parts?.map((p) => p.text ?? '').join('') ?? '';
  return text;
}

/**
 * Reads a local asset (from expo-image-picker / expo-document-picker) into
 * base64, the format Gemini's inline_data expects.
 */
export async function assetToBase64(asset) {
  return FileSystem.readAsStringAsync(asset.uri, { encoding: FileSystem.EncodingType.Base64 });
}
