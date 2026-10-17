# Reddit Pack — ReelForge

## r/SideProject — "I built an AI video pipeline that rejects its own bad footage"

Title: **I built an open-source text-to-video pipeline with a vision gate — it looks at every clip and rejects the wrong ones**

Body:

I kept getting garbage from AI video tools — my biryani video had a burger, a robin, and a houseplant in it. Every pipeline pulls stock footage blindly and ships whatever the API returns.

So I built ReelForge: prompt → script → neural voice → *visually verified* footage → karaoke captions → music → render → publish to YouTube/TikTok/IG/X via official APIs.

The differentiator is a two-stage vision gate: a local CLIP model (offline, free) checks every clip against confuser categories, then Gemini vision double-checks. It also has an audio safety gate (silent renders fail instead of shipping).

Also in there: `reelforge trends` (free trend harvesting, no keys), `reelforge batch` (unattended multi-video production), an MCP server for agent control, and resume-from-failure.

MIT, Python, 32 tests. Demo video in the README was generated end-to-end by the tool.

https://github.com/abicevoice1-sudo/reelforge

Happy to answer anything — especially skeptical questions about the vision gate's accuracy.

---

## r/selfhosted — angle: the self-hosted angle

Title: **ReelForge — self-hosted AI video studio: trends → script → verified footage → publish, all local-first**

Body: same core, emphasize: runs on your hardware, local Ollama support (zero API cost), local CLIP model, local Piper TTS, SQLite queue. Only external calls: stock footage API + whatever LLM you choose. Docker-friendly Python.

---

## r/artificial — angle: the CLIP QA angle

Title: **Using CLIP as a QA gate in a text-to-video pipeline — it rejects bad stock footage automatically**

Body: technical deep-dive on the vision gate: zero-shot classification against confuser labels, calibration results (11/11 on real render frames), fail-open design on API errors, where CLIP's judgment breaks (rice paddy vs rice dish). Code pointers to vision_local.py.

---

## Posting rules (all subreddits)

- [ ] Read each sub's self-promo rules first; r/SideProject allows with context
- [ ] Post on different days, not all at once
- [ ] Reply to every comment in the first hours
- [ ] Never ask for stars/upvotes — Reddit buries vote-begging
