"""A small client for Sentinel, the AI image check at https://verifysentinel.com. No dependencies.

    from verifysentinel import Sentinel

    s = Sentinel()                        # no key: the free check, 6 every 3 hours, nothing kept
    r = s.check("photo.jpg")
    print(r.headline)                     # "Likely made by AI", "Likely a real photo", "No answer for this one", ...
    print(r.answered)                     # False when Sentinel declined to call it
    print(r.receipt_url)                  # a sealed record of this answer; Sentinel keeps no copy

    s = Sentinel(api_key="...")           # or set SENTINEL_API_KEY; a key from verifysentinel.com -> API keys
    r = s.check("photo.jpg")

    receipt = s.verify_receipt(r.receipt_url)
    print(receipt.valid, receipt.matches("photo.jpg"))
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Optional, Union

__version__ = "0.1.0"
__all__ = ["Sentinel", "Result", "Receipt", "SentinelError", "ANSWERED"]

DEFAULT_BASE_URL = "https://verifysentinel.com"
ANSWERED = ("likely_ai", "likely_authentic")
WORDS = {
    "likely_ai": "Likely made by AI",
    "likely_authentic": "Likely a real photo",
    "uncertain": "No answer for this one",
    "evidence_compromised": "Can't verify",
    "insufficient_evidence": "Too little to read",
}
_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

FileLike = Union[str, "os.PathLike[str]", bytes, bytearray, BinaryIO]


class SentinelError(Exception):
    """The service said no: `status` is the HTTP status (0 when it could not be reached)."""

    def __init__(self, status: int, message: str):
        super().__init__("%s: %s" % (status, message) if status else message)
        self.status = status
        self.message = message


@dataclass
class Result:
    verdict: str                 # likely_ai | likely_authentic | uncertain | evidence_compromised | insufficient_evidence
    headline: str                # the answer in words
    text: str                    # one or two plain sentences about it
    answered: bool               # False when Sentinel declined to call it
    receipt: Optional[str]       # free check only: the sealed receipt token
    receipt_url: Optional[str]
    checks_left: Optional[int]   # free check only: checks left in this window
    raw: dict = field(repr=False, default_factory=dict)


@dataclass
class Receipt:
    valid: bool                  # issued by Sentinel and unchanged
    verdict: Optional[str] = None
    sha256: Optional[str] = None
    checked_at: Optional[int] = None
    model_version: Optional[str] = None

    def matches(self, file: FileLike) -> bool:
        """True if `file` is the exact file this receipt describes (same bytes, same SHA-256)."""
        return bool(self.valid and self.sha256 == hashlib.sha256(_read(file)[0]).hexdigest())


class Sentinel:
    def __init__(self, api_key: Optional[str] = None, base_url: str = DEFAULT_BASE_URL, timeout: float = 60.0):
        self.api_key = api_key or os.environ.get("SENTINEL_API_KEY") or None
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def check(self, file: FileLike, screenshot: bool = False) -> Result:
        """Check one picture (JPEG, PNG or WebP): a path, bytes or an open binary file.

        Without a key this is the free check (6 every 3 hours, up to 5 MB, nothing kept, a receipt with every
        answer). With a key it counts against your plan, and `raw` holds the full result."""
        data, name, ctype = _read(file)
        fields = {"via": "python"}
        if screenshot:
            fields["screenshot"] = "true"
        if self.api_key:
            d = self._post_file("/api/detect/upload", fields={}, data=data, name=name, ctype=ctype,
                                headers={"X-API-Key": self.api_key})
        else:
            d = self._post_file("/api/detect/demo", fields=fields, data=data, name=name, ctype=ctype, headers={})
        verdict = str(d.get("verdict") or "")
        answer = d.get("answer") if isinstance(d.get("answer"), dict) else {}
        decision = d.get("final_decision") if isinstance(d.get("final_decision"), dict) else {}
        answered = verdict in ANSWERED and not d.get("abstained")
        token = d.get("receipt")
        left = (d.get("demo_left") or {}).get("remaining") if isinstance(d.get("demo_left"), dict) else None
        return Result(
            verdict=verdict,
            headline=answer.get("headline") or WORDS.get(verdict, verdict),
            text=answer.get("text") or decision.get("reasoning") or "",
            answered=answered,
            receipt=token,
            receipt_url=(self.base_url + "/r/#" + token) if token else None,
            checks_left=left if isinstance(left, int) else None,
            raw=d,
        )

    def verify_receipt(self, receipt: str) -> Receipt:
        """Ask Sentinel whether a receipt (the token, or its full /r/#... link) is genuine, and what it says."""
        token = receipt.split("#", 1)[1] if "#" in receipt else receipt
        d = self._request("POST", "/api/public/receipt", body=json.dumps({"token": token.strip()}).encode("utf-8"),
                          headers={"Content-Type": "application/json"})
        if not d.get("valid"):
            return Receipt(valid=False)
        return Receipt(valid=True, verdict=d.get("verdict"), sha256=d.get("sha256"),
                       checked_at=d.get("checked_at"), model_version=d.get("model_version"))

    # -- plumbing ------------------------------------------------------------------------------------------------

    def _post_file(self, path, fields, data, name, ctype, headers):
        boundary = "verifysentinel-" + uuid.uuid4().hex
        parts = []
        for k, v in fields.items():
            parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, k, v)).encode())
        parts.append(('--%s\r\nContent-Disposition: form-data; name="file"; filename="%s"\r\nContent-Type: %s\r\n\r\n'
                      % (boundary, name, ctype)).encode() + data + b"\r\n")
        parts.append(("--%s--\r\n" % boundary).encode())
        h = dict(headers)
        h["Content-Type"] = "multipart/form-data; boundary=" + boundary
        return self._request("POST", path, body=b"".join(parts), headers=h)

    def _request(self, method, path, body=None, headers=None) -> dict:
        h = {"User-Agent": "verifysentinel-python/" + __version__, "Accept": "application/json"}
        h.update(headers or {})
        req = urllib.request.Request(self.base_url + path, data=body, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            raise SentinelError(e.code, _message(e)) from None
        except urllib.error.URLError as e:
            raise SentinelError(0, "could not reach %s (%s)" % (self.base_url, e.reason)) from None


def _message(e: "urllib.error.HTTPError") -> str:
    try:
        d = json.loads(e.read().decode("utf-8"))
    except Exception:
        d = {}
    if e.code == 429:
        return "limit reached: the free check allows 6 every 3 hours; try later, or use an API key"
    if e.code in (401, 403):
        return "the API key was not accepted"
    detail = d.get("detail") if isinstance(d, dict) else None
    if isinstance(detail, str):
        return detail
    return (d.get("error") if isinstance(d, dict) else None) or (e.reason or "request failed")


def _read(file: FileLike):
    """(bytes, a filename whose extension matches the content, the content type)."""
    if isinstance(file, (bytes, bytearray)):
        data, name = bytes(file), "picture"
    elif hasattr(file, "read"):
        n = getattr(file, "name", None)             # an int for a file opened from a descriptor
        data, name = file.read(), os.path.basename(n) if isinstance(n, str) else "picture"
    else:
        with open(file, "rb") as f:
            data = f.read()
        name = os.path.basename(os.fspath(file))
    ctype = _sniff(data)
    if ctype is None:
        raise SentinelError(0, "not a JPEG, PNG or WebP picture")
    stem = os.path.splitext(name)[0] or "picture"
    stem = "".join(c for c in stem if c.isalnum() or c in "-_ .")[:80] or "picture"
    return data, stem + _TYPES[ctype], ctype      # the server refuses a name that does not match the content


def _sniff(data: bytes) -> Optional[str]:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
