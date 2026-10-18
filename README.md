# Sentinel

**Is this picture made by AI?** Sentinel answers in plain words. When it can't tell, it says so instead of guessing.

Try it: [verifysentinel.com](https://verifysentinel.com) · [Hugging Face demo](https://huggingface.co/spaces/verifysentinel/ai-image-detector) · [Telegram bot](https://t.me/VerifySentinelbot) · [Android and Windows apps](https://verifysentinel.com/apps/)

**Think you can fool it? [Prove it wrong](CHALLENGE.md).**

This repository holds the open parts of Sentinel:
- small clients for its API, in [Python](python/) and [JavaScript](javascript/);
- the page behind the [Hugging Face demo](demo/);
- the rules of the challenge.

The detector itself runs on Sentinel's own server and is not published here.

## What it answers

| Answer | What it means |
|---|---|
| **Likely made by AI** | An estimate from the picture itself, not proof. |
| **Likely a real photo** | An estimate, not proof. A real photo can still come with a false story. |
| **No answer for this one** | It can't tell either way, and says so rather than guess. This is by design. |
| **Can't verify** | The picture was altered in a way that hides the evidence (added noise or grain). |
| **Too little to read** | Blank, tiny or mostly flat colour. |

A file that carries signed Content Credentials (C2PA) can be answered from its own signed record, and Sentinel says so when it does.

## What we have measured

These figures are for images, on our own test sets, with the current engine (v6.0):
- **The 560-picture set.** Its AI pictures come from 7 generators the engine was never trained on, alongside real photos.
  - It declined about 1 in 4 on purpose.
  - It answered the other 413 and got **every one right**. Made to answer all 560, it would have been wrong 15 times.
  - After one JPEG re-save, which is how most shared pictures arrive, its AUC on those pictures is **0.995**. The previous engine's was 0.907.
- **The 2,800-picture test set** (older generators and edited photos):
  - Its AUC is **0.984**.
  - It declines more here, about 1 in 3.
  - When it answers, it is wrong **0.6%** of the time, against 6.5% if it had to answer everything.
  - It called **0.1%** of the real photos it judged AI.

New image generators may behave differently. Every answer is an estimate, not proof of how a picture was made. Please never use one to accuse a person.

## Use it from code

**No key.** This is the free check: 6 every 3 hours, and nothing is kept.
```bash
curl -F "file=@photo.jpg" https://verifysentinel.com/api/detect/demo
```

**With an API key.** Make one on [verifysentinel.com](https://verifysentinel.com) under API keys.
```bash
curl -H "X-API-Key: $SENTINEL_API_KEY" -F "file=@photo.jpg" https://verifysentinel.com/api/detect/upload
```

**Python** (3.9 or later, no dependencies). It isn't on PyPI yet, so install it from this repository:
```bash
pip install "git+https://github.com/sentinelverifyai-dev/verifysentinel#subdirectory=python"
```
```python
from verifysentinel import Sentinel

result = Sentinel().check("photo.jpg")          # Sentinel(api_key="...") for your plan's limits
print(result.headline)                          # "Likely made by AI"
print(result.answered)                          # False when Sentinel declined to call it
print(result.receipt_url)                       # proof of this answer: see Receipts
```

**JavaScript** (Node 18 or later). It is one file, [`javascript/verifysentinel.mjs`](javascript/verifysentinel.mjs):
```js
import { Sentinel } from './verifysentinel.mjs';

const result = await new Sentinel().check('photo.jpg');
console.log(result.headline, result.receiptUrl);
```

Browsers can't call the API from other websites: it only answers pages on verifysentinel.com and the Hugging Face demo. Call it from your server instead.

## Receipts

Each free check returns a **receipt**: a short, sealed record of what Sentinel answered, when, and a fingerprint (SHA-256) of the exact file. Open it at `https://verifysentinel.com/r/#…`. Anyone holding the original file can drop it there to confirm it is the same picture. The comparison runs on their device.

Receipts cannot be edited without breaking the seal. Sentinel keeps no copy of the picture or of the receipt: the link is the only record, and it belongs to whoever checked the picture.

```python
receipt = Sentinel().verify_receipt(result.receipt_url)
print(receipt.valid, receipt.verdict, receipt.matches("photo.jpg"))
```

## Privacy

The free check keeps nothing. The picture is checked in memory and then discarded. The full policy is at [verifysentinel.com/#/privacy](https://verifysentinel.com/#/privacy).

## Contact

Write to sentinelverifyai@gmail.com. To report a security problem, see [SECURITY.md](SECURITY.md).

## License

Everything in this repository is under the [MIT license](LICENSE). The Sentinel service and its detector are not part of it.

Sentinel is made by Small Room.
