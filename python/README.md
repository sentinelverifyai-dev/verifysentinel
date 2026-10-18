# verifysentinel (Python)

**Is this picture made by AI?** This is a small client for [Sentinel](https://verifysentinel.com). It needs
Python 3.9 or later and has no dependencies.

```bash
pip install "git+https://github.com/sentinelverifyai-dev/verifysentinel#subdirectory=python"
```

```python
from verifysentinel import Sentinel, SentinelError

s = Sentinel()                         # no key: the free check, 6 every 3 hours, nothing kept
r = s.check("photo.jpg")               # a path, bytes, or an open binary file (JPEG, PNG, WebP)
print(r.headline)                      # "Likely made by AI" / "Likely a real photo" / "No answer for this one" / ...
print(r.text)                          # one or two plain sentences
print(r.answered, r.verdict)           # answered is False when Sentinel declined to call it
print(r.receipt_url)                   # a sealed record of this answer; Sentinel keeps no copy

receipt = s.verify_receipt(r.receipt_url)
print(receipt.valid, receipt.matches("photo.jpg"))
```

You get an API key from [verifysentinel.com](https://verifysentinel.com) under API keys. Pass it as
`Sentinel(api_key="...")` or set `SENTINEL_API_KEY`. Checks then count against your plan, and `r.raw` holds the
full result.

Errors raise `SentinelError`. Its `status` is the HTTP status, 429 when the limit is reached, and `message` says
what to do.

Every answer is an estimate, not proof of how a picture was made. Please never use one to accuse a person.
