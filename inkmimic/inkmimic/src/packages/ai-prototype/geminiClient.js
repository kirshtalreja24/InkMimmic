import { env, isAiPrototypeConfigured } from '../../config/env.js';

const GEMINI_ENDPOINT = (model) =>
  `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;

export async function sendPrototypeMessage({ prompt, image, signal }) {
  if (!isAiPrototypeConfigured) {
    throw new Error(
      'Set VITE_GEMINI_API_KEY in .env to test the chat box against the real Gemini API.'
    );
  }

  const parts = [{ text: prompt }];
  if (image) {
    parts.push({ inline_data: { mime_type: image.mediaType, data: image.base64 } });
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

export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',')[1]);
    reader.onerror = () => reject(new Error('Could not read file.'));
    reader.readAsDataURL(file);
  });
}