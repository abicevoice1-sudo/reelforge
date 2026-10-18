# Reddit Pack — ReelForge

## r/SideProject — "I built an AI video pipeline that rejects its own bad footage"

Title: **I built an open-source text-to-video pipeline with a vision gate — it looks at every clip and rejects the wrong ones**

Body:

I kept getting garbage from AI video tools — my biryani video had a burger, a robin, and a houseplant in it. Every pipeline pulls stock footage blindly and ships whatever the API returns.

So I built ReelForge: prompt → script → neural voice → *visually verified* footage → karaoke captions → music → render → publish to YouTube/TikTok/IG/X via official APIs.

The differentiator is a two-stage vision gate: a local CLIP model (offline, free) checks every clip against confuser categories, then Gemini vision double-checks. It also has an audio safety gate (silent renders fail instead of shipping).

Also in there: `reelforge trends` (free trend harvesting, no keys), `reelforge batch` (unattended multi-video production), an MCP server for agent control, and resume-from-failure.

MIT, Python, 37 tests. Demo video in the README was generated end-to-end by the tool.

https://github.com/abicevoice1-sudo/reelforge

Happy to answer anything — especially skeptical questions about the vision gate's accuracy.

---

## r/selfhosted — angle: the self-hosted / $0-to-run angle (FULL COPY, rewritten — not the r/SideProject post)

Title: **ReelForge — self-hosted AI video studio: prompt → viral short, all local-first**

Body:

Full disclosure: I built this.

I wanted an AI video pipeline that costs $0 to run and doesn't need a SaaS account, so I built ReelForge to be self-hosted first:

- Runs on your own hardware or a cheap VPS — `pip install`, SQLite queue, no account, no subscription
- Local LLM support (Ollama) — script + edit-plan generation for $0
- Local neural TTS (Piper), karaoke captions, music bed, render — all local
- A local CLIP model (offline, free) acts as a QA gate: every stock clip is checked against confuser labels before it lands in the render. It caught a burger in my biryani video, and a houseplant. Calibrated 11/11 on real render frames.
- Audio gate: a silent render fails instead of shipping
- Publish to 8 platforms (YouTube, TikTok, Instagram, X, Threads, Bluesky, LinkedIn, Pinterest) through their official APIs
- `reelforge trends` (trend harvesting, no keys), `reelforge batch` (unattended overnight runs), an MCP server if you want to drive it from an agent

The only external calls are the stock-footage API and whichever LLM provider you pick — everything else runs local. MIT, Python, 37 tests, Docker-friendly. The demo video in the README was generated end-to-end by the tool itself.

https://github.com/abicevoice1-sudo/reelforge

Happy to help anyone getting it running on their homelab — setup questions welcome.

Rules check (2026-10-17): r/selfhosted has a strong open-source preference (~800K members); MIT + self-hostable + local-first fits the sub's ethos. Disclosure first line; no vote-begging. Before posting: read the live r/selfhosted sidebar/wiki rules (stricter than r/SideProject); consider modmail heads-up; new/low-karma accounts get AutoMod scrutiny — if removed, don't repost.

---

## r/artificial — angle: the CLIP QA angle (FULL COPY)

Title: **Using CLIP as a QA gate in a text-to-video pipeline — it rejects bad stock footage automatically**

Body:

Full disclosure: I built this.

Text-to-video pipelines that pull stock footage usually ship whatever the API returns. My biryani video rendered with a burger, a robin, and a houseplant in it. So I put a vision gate between footage selection and the render.

Design (MIT, Python, pointer: `reelforge/vision_local.py`):
- Local CLIP ViT-B/32 (605MB, fully offline, no quota) does zero-shot classification of each clip against per-scene confuser labels — e.g. "steaming pot of biryani" vs "burger", "robin", "houseplant", "empty pan"
- Two-stage: CLIP always runs; Gemini vision double-checks when quota allows; both must pass
- Fail-open on API errors (a vision-API outage never blocks the pipeline); fail-closed on CLIP
- Calibration: 11/11 on real render frames — accepts steaming pot/chai/bhatura; rejects oranges, burger, robin, plant, milk, empty pan
- Known break point: visually adjacent categories (rice paddy vs rice dish) — confuser labels need hand-tuning per scene type

https://github.com/abicevoice1-sudo/reelforge

Would love critique of the calibration approach — where would you expect this to break at scale?

---

## Posting rules (all subreddits)

- [ ] Read each sub's self-promo rules first; r/SideProject allows with context
- [ ] Post on different days, not all at once
- [ ] Reply to every comment in the first hours
- [ ] Never ask for stars/upvotes — Reddit buries vote-begging
