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
