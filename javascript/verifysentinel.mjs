// A small client for Sentinel, the AI image check at https://verifysentinel.com. One file, no dependencies.
// Node 18 or later (it uses the built-in fetch, FormData and Blob).
//
//   import { Sentinel } from './verifysentinel.mjs';
//   const s = new Sentinel();                       // no key: the free check, 6 every 3 hours, nothing kept
//   const r = await s.check('photo.jpg');           // a path, a Buffer/Uint8Array, or a Blob
//   console.log(r.headline, r.answered, r.receiptUrl);
//   const s2 = new Sentinel({ apiKey: process.env.SENTINEL_API_KEY });   // your plan's limits
//
// Browsers cannot call the API from other websites (only verifysentinel.com and its Hugging Face demo may),
// so run this on a server.

export const VERSION = '0.1.0';
export const ANSWERED = ['likely_ai', 'likely_authentic'];
export const WORDS = {
  likely_ai: 'Likely made by AI',
  likely_authentic: 'Likely a real photo',
  uncertain: 'No answer for this one',
  evidence_compromised: "Can't verify",
  insufficient_evidence: 'Too little to read',
};
const TYPES = { 'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp' };

export class SentinelError extends Error {
  /** @param {number} status HTTP status, 0 when the service could not be reached */
  constructor(status, message) {
    super(status ? `${status}: ${message}` : message);
    this.name = 'SentinelError';
    this.status = status;
  }
}

export class Sentinel {
  /** @param {{apiKey?: string, baseUrl?: string, timeoutMs?: number}} [opts] */
  constructor(opts = {}) {
    const env = typeof process !== 'undefined' && process.env ? process.env : {};
    this.apiKey = opts.apiKey || env.SENTINEL_API_KEY || null;
    this.baseUrl = (opts.baseUrl || 'https://verifysentinel.com').replace(/\/+$/, '');
    this.timeoutMs = opts.timeoutMs || 60000;
  }

  /**
   * Check one picture (JPEG, PNG or WebP). Without a key this is the free check: 6 every 3 hours, up to 5 MB,
   * nothing kept, and a receipt with every answer. With a key it counts against your plan.
   * @param {string|Uint8Array|ArrayBuffer|Blob} file
   * @param {{screenshot?: boolean}} [opts]
   */
  async check(file, opts = {}) {
    const { bytes, name, type } = await read(file);
    const form = new FormData();
    form.append('file', new Blob([bytes], { type }), name);
    let path = '/api/detect/demo';
    const headers = {};
    if (this.apiKey) {
      path = '/api/detect/upload';
      headers['X-API-Key'] = this.apiKey;
    } else {
      form.append('via', 'javascript');
      if (opts.screenshot) form.append('screenshot', 'true');
    }
    const d = await this.#request(path, { method: 'POST', body: form, headers });
    const verdict = String(d.verdict || '');
    const answer = d.answer && typeof d.answer === 'object' ? d.answer : {};
    const decision = d.final_decision && typeof d.final_decision === 'object' ? d.final_decision : {};
    const left = d.demo_left && typeof d.demo_left.remaining === 'number' ? d.demo_left.remaining : null;
    return {
      verdict,
      headline: answer.headline || WORDS[verdict] || verdict,
      text: answer.text || decision.reasoning || '',
      answered: ANSWERED.includes(verdict) && !d.abstained,
      receipt: d.receipt || null,
      receiptUrl: d.receipt ? `${this.baseUrl}/r/#${d.receipt}` : null,
      checksLeft: left,
      raw: d,
    };
  }

  /** Is a receipt (the token, or its full /r/#... link) genuine, and what does it say? */
  async verifyReceipt(receipt) {
    const token = String(receipt).includes('#') ? String(receipt).split('#')[1] : String(receipt);
    const d = await this.#request('/api/public/receipt', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: token.trim() }),
    });
    if (!d.valid) return { valid: false };
    const out = { valid: true, verdict: d.verdict, sha256: d.sha256, checkedAt: d.checked_at, modelVersion: d.model_version };
    /** True if `file` is the exact file this receipt describes. */
    out.matches = async (file) => (await sha256Hex((await read(file)).bytes)) === out.sha256;
    return out;
  }

  async #request(path, init) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    let r;
    try {
      r = await fetch(this.baseUrl + path, {
        ...init, signal: ctrl.signal,
        headers: { Accept: 'application/json', 'User-Agent': `verifysentinel-js/${VERSION}`, ...(init.headers || {}) },
      });
    } catch (e) {
      throw new SentinelError(0, `could not reach ${this.baseUrl} (${e && e.name === 'AbortError' ? 'timed out' : e && e.message})`);
    } finally {
      clearTimeout(timer);
    }
    const d = await r.json().catch(() => ({}));
    if (r.ok) return d;
    if (r.status === 429) throw new SentinelError(429, 'limit reached: the free check allows 6 every 3 hours; try later, or use an API key');
    if (r.status === 401 || r.status === 403) throw new SentinelError(r.status, 'the API key was not accepted');
    throw new SentinelError(r.status, typeof d.detail === 'string' ? d.detail : (d.error || r.statusText || 'request failed'));
  }
}

async function read(file) {
  let bytes, name = 'picture';
  if (typeof file === 'string') {
    const { readFile } = await import('node:fs/promises');
    const { basename, extname } = await import('node:path');
    bytes = new Uint8Array(await readFile(file));
    name = basename(file, extname(file)) || 'picture';
  } else if (typeof Blob !== 'undefined' && file instanceof Blob) {
    bytes = new Uint8Array(await file.arrayBuffer());
    if (file.name) name = String(file.name).replace(/\.[^.]*$/, '') || 'picture';
  } else if (file instanceof ArrayBuffer) {
    bytes = new Uint8Array(file);
  } else if (file instanceof Uint8Array) {
    bytes = file;
  } else {
    throw new SentinelError(0, 'pass a file path, a Buffer/Uint8Array, an ArrayBuffer or a Blob');
  }
  const type = sniff(bytes);
  if (!type) throw new SentinelError(0, 'not a JPEG, PNG or WebP picture');
  name = name.replace(/[^\w\- .]/g, '').slice(0, 80) || 'picture';
  return { bytes, name: name + TYPES[type], type };     // the server refuses a name that does not match the content
}

function sniff(b) {
  if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'image/jpeg';
  if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return 'image/png';
  const ascii = (i, n) => String.fromCharCode(...b.slice(i, i + n));
  if (ascii(0, 4) === 'RIFF' && ascii(8, 4) === 'WEBP') return 'image/webp';
  return null;
}

async function sha256Hex(bytes) {
  // Node 18 has no global `crypto` without a flag; its own module has the same Web Crypto.
  const subtle = (globalThis.crypto && globalThis.crypto.subtle) || (await import('node:crypto')).webcrypto.subtle;
  const h = await subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(h), (x) => x.toString(16).padStart(2, '0')).join('');
}
