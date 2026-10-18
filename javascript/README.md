# verifysentinel (JavaScript)

**Is this picture made by AI?** This is a small client for [Sentinel](https://verifysentinel.com). It is one
file, [`verifysentinel.mjs`](verifysentinel.mjs). It needs Node 18 or later and has no dependencies.

```js
import { Sentinel, SentinelError } from './verifysentinel.mjs';

const s = new Sentinel();                    // no key: the free check, 6 every 3 hours, nothing kept
const r = await s.check('photo.jpg');        // a path, a Buffer/Uint8Array, an ArrayBuffer or a Blob
console.log(r.headline);                     // "Likely made by AI" / "Likely a real photo" / "No answer for this one" / ...
console.log(r.answered, r.verdict);          // answered is false when Sentinel declined to call it
console.log(r.receiptUrl);                   // a sealed record of this answer; Sentinel keeps no copy

const receipt = await s.verifyReceipt(r.receiptUrl);
console.log(receipt.valid, await receipt.matches('photo.jpg'));
```

With an API key from [verifysentinel.com](https://verifysentinel.com) (under API keys), use
`new Sentinel({ apiKey })` or set `SENTINEL_API_KEY`. Checks then count against your plan, and `r.raw` holds the
full result.

Browsers can't call the API from other websites. Only verifysentinel.com and its Hugging Face demo may, so
run this on a server.

Every answer is an estimate, not proof of how a picture was made. Please never use one to accuse a person.
