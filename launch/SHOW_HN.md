# Show HN draft — ShortSmash

**Title:** Show HN: ShortSmash – prompt-to-published short videos, 50-language dubbing, open source

**URL:** https://github.com/hydope/shortsmash

**Body:**

Hey HN. I built ShortSmash because every "AI shorts" tool I tried assembled clips blindly — whatever the stock API returned first went into the video. The result is the infamous stock-footage look: a burger in a biryani video, a robin in a cooking tutorial.

ShortSmash is a prompt-to-published pipeline for vertical shorts:

- LLM writes the script + a shot-by-shot edit plan (pydantic-validated)
- Neural TTS narrates it — 50 languages, native voices, not translationese
- Every footage clip passes a **two-stage vision gate** (local CLIP ViT-B/32 + Gemini vision) before it ships. This is the part nobody else does.
- Karaoke captions (per-word timed; Urdu renders in proper Nastaliq calligraphy with RTL-correct highlighting)
- FFmpeg renders 1080×1920 with a cinematic treatment (Ken Burns + film grade)
- One-click publish to 10 platforms via official APIs: YouTube, TikTok, Instagram, X, Threads, Bluesky, LinkedIn, Pinterest, Facebook

Visual providers: Pixabay stock (free), Agnes AI (free tier), and as of v0.3.0, Google Veo 3.1 and Kling AI (paid, bring-your-own-key). There's also a `visual_command` shell escape hatch — point it at ComfyUI, Replicate, whatever you already pay for.

There's a web Studio (`shortsmash serve`), a lyrics-video mode, an Auto tab that goes trend → video → scheduled publish with API quota budgeting, and an MCP server.

One-command install: `curl -fsSL https://raw.githubusercontent.com/hydope/shortsmash/main/install.sh | bash`

MIT licensed. The demo in the README ("How Goats Made You Addicted to Coffee") was made end-to-end by the tool — including the Mandarin re-voice. Happy to answer anything about the pipeline, the vision gate, or why Urdu karaoke was the hardest caption problem I've ever solved.
