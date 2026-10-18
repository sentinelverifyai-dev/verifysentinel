---
title: Sentinel AI Image Check
emoji: 🛡️
colorFrom: gray
colorTo: indigo
sdk: static
pinned: false
license: mit
short_description: Is this picture made by AI? Free check, nothing kept.
tags:
  - ai-image-detection
  - ai-generated-images
  - deepfake-detection
  - image-forensics
---

# Sentinel AI Image Check

Drop a picture and Sentinel says whether it was likely made by AI, in plain words. When the evidence is too
thin to call, it says so instead of guessing.

**How this Space works.** This is a plain web page. It runs in your browser and sends the picture straight to
Sentinel's free check at [verifysentinel.com](https://verifysentinel.com). The detector runs on Sentinel's own
server. The picture is checked in memory and discarded: nothing is kept.

**Receipts.** Each answer comes with a receipt link: a sealed record of what Sentinel answered, when, and a
fingerprint (SHA-256) of the exact file. Anyone holding the original file can open the receipt and confirm it
is the same picture. The comparison happens on their own device.

**What we have measured.** These figures come from our own test sets:
- On 560 pictures, with AI ones from 7 generators it was never trained on, it declined about 1 in 4. It got every one of the 413 it answered right.
- Of the real photos it judged in a 2,800-picture test set, it wrongly called 0.1% AI.

New image generators may behave differently. Every answer is an estimate, not proof of how a picture was
made.

**Free.** This Space gives 6 checks every 3 hours. A free account on the site gives 10 checks every 3 hours,
up to 100 a month. There are also [Android and Windows apps](https://verifysentinel.com/apps/) and a
[Telegram bot](https://t.me/VerifySentinelbot).

Made by Small Room.
