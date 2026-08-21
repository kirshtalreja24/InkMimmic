// AI-core client shared by the Inkmimic web and mobile apps — talks to the
// FastAPI handwriting model backend (api/server.py)'s /api/generate and
// /api/analyze-style endpoints.
//
// Both apps hand-implemented the same request/response logic; the only
// real difference was how a sample gets attached to FormData (a File/Blob
// on web, a { uri, mimeType, fileName } asset object on mobile). That
// platform-specific step is the one thing callers inject here.

/**
 * @param {object} params
 * @param {string} params.apiUrl - base URL of api/server.py.
 * @param {(sample: any) => any} params.buildSamplePart - turns the platform's
 *   sample shape into whatever FormData.append() should receive for it.
 * @param {() => string} [params.genId] - fallback id generator when the
 *   server doesn't return one.
 */
export function createAiCoreClient({ apiUrl, buildSamplePart, genId = () => `${Date.now()}` }) {
  /**
   * @param {object} params
   * @param {any} [params.sample] - the user's handwriting sample, in whatever
   *   shape this platform's buildSamplePart expects.
   * @param {string} params.prompt - what the user asked for in chat.
   * @param {string} [params.inkColor] - ink hex code (default #1a1a2e).
   * @param {string} [params.paper] - paper style ('white' | 'ruled' | 'graph').
   * @param {AbortSignal} [params.signal] - to support cancellation.
   * @returns {Promise<import('../../inkmimic/inkmimic/src/types/ai.js').AiArtifactResult>}
   */
  async function generateHandwrittenArtifact({ sample, prompt, inkColor = '#1a1a2e', paper = 'white', signal }) {
    if (!prompt || !prompt.trim()) {
      throw new Error('Please enter some text to write.');
    }

    const formData = new FormData();
    formData.append('prompt', prompt.trim());
    formData.append('ink_color', inkColor);
    formData.append('paper', paper);
    formData.append('tries', '5');

    const samplePart = sample ? buildSamplePart(sample) : null;
    if (samplePart) {
      formData.append('sample_file', samplePart);
    }

    const response = await fetch(`${apiUrl}/api/generate`, {
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
      id: result.id || genId(),
      kind: result.kind || 'image',
      content: result.content,
      note: result.note || 'Generated handwriting page.',
    };
  }

  /**
   * @param {any} sample
   * @param {AbortSignal} [signal]
   */
  async function analyzeHandwritingStyle(sample, signal) {
    const samplePart = sample ? buildSamplePart(sample) : null;
    if (!samplePart) {
      throw new Error('A handwriting sample is required for style analysis.');
    }

    const formData = new FormData();
    formData.append('sample_file', samplePart);

    const response = await fetch(`${apiUrl}/api/analyze-style`, {
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

  return { generateHandwrittenArtifact, analyzeHandwritingStyle };
}
