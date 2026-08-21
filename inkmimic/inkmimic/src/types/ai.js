// Shared shape definitions for anything crossing the boundary into the AI
// package (ai-core). Kept as plain JSDoc typedefs (not TypeScript) so the
// project stays a plain JS + Vite setup, but still gives editor
// autocomplete and a single source of truth for the request/response
// contract.

/**
 * @typedef {Object} AiStyleProfile
 * @property {string} slantDescription
 * @property {string} strokeWeightDescription
 * @property {number} confidence - 0 to 1
 */

/**
 * @typedef {Object} AiArtifactResult
 * @property {string} id
 * @property {'image' | 'text'} kind
 * @property {string} content - image URL/base64, or generated text
 * @property {string} [note] - short model commentary, shown in chat
 */

export {};
