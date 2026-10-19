# Show HN — ShortSmash (ready to submit)

**URL:** https://github.com/hydope/shortsmash
**Guidelines check:** This is my own open-source project, first public Show HN. Post on a weekday morning US time for max visibility. Do NOT post from a fresh same-day account (gets flagged) — use an established account. One submission only; don't repost if it flops.

---

## Title options (pick ONE)

1. **Show HN: ShortSmash – prompt-to-published short videos, 50-language dubbing, MIT-licensed**
2. **Show HN: I built an open-source pipeline that turns one prompt into a published short**
3. **Show HN: ShortSmash – every AI shorts tool assembles clips blindly, so I added a vision gate**

---

## Body

Hey HN. I built ShortSmash because every "AI shorts" tool I tried assembled clips blindly — whatever the stock API returned first went into the video. The result is the infamous stock-footage look: a burger in a cooking tutorial, a parrot in a recipe video.

ShortSmash is a prompt-to-published pipeline for vertical shorts:

- **LLM writes the script + a shot-by-shot edit plan** (pydantic-validated JSON, not vibes)
- **Neural TTS narrates it** — 50 languages with native voices, not translationese. Urdu captions render in proper Nastaliq calligraphy with RTL-correct karaoke highlighting
- **Every footage clip passes a two-stage vision gate** (local CLIP ViT-B/32 + Gemini vision) before it ships. This is the part nobody else does — it's why the coffee video shows actual coffee and goats, not a burger
- **Karaoke captions**, per-word timed; **cinematic treatment** (Ken Burns + film grade); **ducked music bed**
- **One-click publish to 10 platforms via official APIs**: YouTube Shorts, TikTok, Instagram, X, Threads, Bluesky, LinkedIn, Pinterest, Facebook (profiles + Pages)

Visual providers: Pixabay stock (free), Agnes AI (free tier), plus Google Veo 3.1 and Kling AI (paid, bring-your-own-key). There's also a `visual_command` shell escape hatch — point it at ComfyUI, Replicate, whatever you already pay for. And a `shortsmash dub` command that re-voices any finished video into any of 50 languages.

There's a natural-language scheduler ("post it Friday at 6pm"), a trends harvester, batch production, comment-reply drafts (human-approved only — no bot engagement), and an MCP server so AI agents can drive the whole thing.

### Run it

```bash
git clone https://github.com/hydope/shortsmash && cd shortsmash
./install.sh          # or install.ps1 on Windows
shortsmash "why you can't tickle yourself"
```

The repo has 4 real demo videos generated end-to-end by the pipeline (plus the same video dubbed into Spanish, Urdu, and Mandarin).

### Why MIT, not SaaS

I looked at what the SaaS versions charge per video and what they actually do under the hood — blind stock assembly with a markup. The interesting engineering here (the vision gate, the dubbing engine, the publishing adapters) deserves to be inspectable and forkable. If this gets traction I'd rather have 500 contributors than 500 subscribers.

Happy to answer anything about the pipeline, the vision gate, or why publishing to 10 official APIs was the worst part. Bug reports and PRs very welcome.
