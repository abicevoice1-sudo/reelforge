# Reddit drafts — ShortSmash (tailored per subreddit)

Post each from an established account with real history in that subreddit. Never post the same text twice. Space them out — one per day minimum.

---

## r/Python

**Title:** I built a prompt-to-published video pipeline in Python — every stock clip is verified by CLIP + Gemini before it ships

**Body:**

https://github.com/hydope/shortsmash

The architecture, since this is r/Python:

- **LLM layer** (`shortsmash/llm.py`) — script + shot-by-shot edit plan as pydantic-validated JSON; providers: NVIDIA, Gemini, Grok, OpenAI-compatible, template fallback
- **Async pipeline** — footage fetch, TTS, and caption timing run concurrently with asyncio; per-stage retries with backoff
- **Vision gate** (`shortsmash/vision.py`) — every stock clip is scored by local CLIP ViT-B/32, then confirmed by Gemini vision. Both must pass. This kills the classic "burger in the cooking video" failure of every other tool in this space
- **Captions** — per-word timed ASS subtitles, including proper Urdu Nastaliq with RTL-correct karaoke highlighting (the hardest text-rendering problem I've ever solved)
- **Publishers** (`shortsmash/platforms/`) — 10 official API adapters (YouTube, TikTok, Instagram, X, Threads, Bluesky, LinkedIn, Pinterest, Facebook), each with its own OAuth flow and setup guide in docs/
- **Scheduler** — SQLite-backed queue, natural-language times ("Friday 6pm"), background worker
- **MCP server** — AI agents can drive the whole factory

52 tests, CI green, MIT. The README demo videos were generated end-to-end by the tool itself. Would love code review — especially on the vision gate and the publisher adapters.

---

## r/SelfHosted

**Title:** ShortSmash — self-hosted AI short video factory: prompt in, published short out, your keys, your machine

**Body:**

https://github.com/hydope/shortsmash

If you're allergic to SaaS video tools that charge per render: this runs entirely on your hardware.

- **Your keys, your control** — Pixabay (free), Agnes AI (free tier) for footage; Veo 3.1 / Kling are bring-your-own-key and optional. LLM via NVIDIA/Gemini/Grok or any OpenAI-compatible endpoint (points at your local Ollama/vLLM just fine)
- **Local-first where it counts** — CLIP verification runs on your GPU/CPU, Piper TTS is fully offline, FFmpeg render is local, SQLite queue, no phone-home
- **Docker** — compose file included; `shortsmash serve` also gives you a web Studio UI on localhost:8000
- **Secrets** — everything lives in your own `.env`, never leaves the box
- **10-platform publishing** from one box via official APIs, with a natural-language scheduler

MIT licensed. The demo videos in the README were made by the tool running on a plain VM. Happy to help anyone self-hosting it — issues on GitHub get answered.

---

## r/OpenSource

**Title:** ShortSmash — MIT-licensed prompt-to-published short video pipeline; looking for contributors

**Body:**

https://github.com/hydope/shortsmash

I built this as MIT from day one because the SaaS versions of this idea charge per video for what is, under the hood, blind stock assembly with a markup. The interesting parts — the vision gate, the 50-language dubbing engine, the publishing adapters — deserve to be inspectable and forkable.

Where contributors would help most:
- **New publishers** — the adapter interface is small; Snapchat and more are on the roadmap
- **TTS providers** — Edge/Piper/gTTS are in; more voices welcome
- **Vision gate** — better local models, smarter rejection heuristics
- **Docs/translations** — setup guides for the 10 platforms exist; more languages for the README

Roadmap is in the README. PRs get reviewed fast, issues get answered, and there's a real test suite (52 tests) so you won't break things blind. If you've ever wanted to learn how the sausage gets made in AI video tooling, this is a good codebase to start.
