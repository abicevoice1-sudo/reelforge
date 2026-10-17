# ReelForge ⚒️

[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

**Prompt in. Viral short out.**

ReelForge is an AI video studio that takes one sentence — or today's trends — and ships a finished, captioned 9:16 short, then publishes it to YouTube, TikTok, Instagram and X through their **official APIs**. Script, voiceover, *verified* stock footage, karaoke captions, music ducking, trend harvesting, batch production, scheduling and comment-reply drafts, all in one CLI. And an MCP server, so AI agents can drive the whole factory.

```bash
reelforge trends food                    # what's hot right now (free, no keys)
reelforge batch food --count 5           # turn the top 5 trends into 5 videos
reelforge agent "make a 30s reel about hyderabadi biryani and post it Friday at 6pm"
```

## 🎬 Demo

*Made end-to-end by ReelForge — Gemini script, Piper neural voice, CLIP-verified Pixabay footage, karaoke captions, ducked music bed.*

<video src="demo/biryani-v3.mp4" width="270" controls></video>

## Why ReelForge

Most text-to-video tools assemble clips blindly — whatever the stock API returns first goes in. That's why automated shorts have the infamous "stock-footage look": a burger in a biryani video, a robin in a cooking tutorial.

ReelForge is the first open-source pipeline with **eyes**:

- **Two-stage vision gate.** Every candidate clip's middle frame is checked by a local CLIP model (offline, no quota, no cost) against 15 confuser categories — burgers, birds, houseplants, empty pans, citrus fruit — then by Gemini vision when quota allows. Wrong footage never ships.
- **Audible gate.** Renders with dead or missing audio fail instead of shipping.
- **Never ships silent.** A CC-licensed music library auto-downloads on first run; music is ducked under narration with a real FFmpeg sidechain.

## The pipeline

```
prompt ──▶ script ──▶ voice ──▶ visuals ──▶ captions ──▶ render ──▶ publish
           NVIDIA     Edge-TTS   Pixabay      faster-     FFmpeg      official
           Gemini     Piper      CLIP         whisper     1080x1920   APIs only
           OpenAI-    (offline   verified     karaoke     +faststart
           compat     neural)
```

- **Script** — NVIDIA NIM (free) → Gemini (free) → any OpenAI-compatible endpoint (OpenRouter, DeepSeek, local Ollama) → offline template. Writes a scroll-stopping script *and* a strict JSON edit plan, validated by pydantic. Second-person, punchy, 3–4s scenes.
- **Voice** — Edge-TTS → Piper offline neural → gTTS fallback chain. Urdu/Hindi/Arabic voices included.
- **Visuals** — free Pixabay footage, every clip verified by the vision gate. Prefer AI generation? Set `visual_provider: custom` with your own command (ComfyUI, Replicate, MiniMax…) — the gate still checks the result.
- **Captions** — faster-whisper word timestamps → burned-in **karaoke captions**.
- **Render** — FFmpeg: 9:16 smart reframe, transitions, hook + CTA overlays, ducked music, H.264/AAC faststart.
- **Publish** — YouTube Data API v3, TikTok Content Posting API, Instagram Graph API, X API v2. Official APIs only — no Selenium, no scraping, nothing that gets accounts banned.
- **Trends** — `reelforge trends <niche>` harvests Google News + Hacker News (free, no keys). `reelforge batch` turns the top trends into videos unattended.
- **Schedule** — natural language ("Friday 6pm"), durable SQLite queue, retrying worker.
- **Engage** — pulls recent comments, drafts warm replies, **you approve each one with a tap**. Nothing posts itself.
- **MCP server** — `python -m reelforge.mcp_server` exposes `generate_video`, `get_trends`, `list_projects`, `project_status` to Claude Code, Cursor, and any MCP client.
- **Resume** — `reelforge resume <slug>` picks up failed projects from the first incomplete stage instead of redoing everything.

## How ReelForge compares

| | ReelForge | MoneyPrinterTurbo | OpenPost | Postiz | ShortGPT |
|---|---|---|---|---|---|
| Prompt → finished short | ✅ | ✅ | ❌ (manual editor) | ❌ | ✅ |
| Footage verification | ✅ CLIP + Gemini | ❌ | n/a | n/a | ❌ |
| Offline neural voice fallback | ✅ Piper | ❌ | n/a | n/a | ❌ |
| Audio safety gate | ✅ | ❌ | n/a | n/a | ❌ |
| Trend harvesting (free, no keys) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Batch production | ✅ | ✅ | ❌ | ❌ | ❌ |
| Karaoke word-level captions | ✅ | ✅ | ✅ | ❌ | ✅ |
| Official publishing APIs | ✅ | ⚠️ Selenium for YT | ✅ | ✅ | ⚠️ |
| MCP server | ✅ | ❌ | ✅ | ✅ | ❌ |
| Comment-reply drafts (human-approved) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Resume failed projects | ✅ | ❌ | n/a | n/a | ❌ |
| License | MIT | MIT | AGPL/Commercial | MIT | MIT |
| $0 to run | ✅ | ✅ | self-host | ✅ | ✅ |

*MoneyPrinterTurbo (129K★) is the most mature; OpenPost is the best manual workspace. ReelForge is the most engineered AI-native pipeline — the only one that checks its own work.*

## What ReelForge will never do

No fake likes, comments, follows, shares, or stars. No botting, no "human-like" evasion of platform detection, no scraping or unofficial endpoints. That violates every platform's rules and gets accounts banned — and it doesn't work for real growth anyway. This boundary is architectural, not a policy note: the capability simply isn't in the codebase.

## Quickstart

```bash
pip install 'reelforge[ai,voice,captions,trends,vision,mcp,youtube,x,schedule]'
reelforge init          # guided setup: keys, voice, defaults
reelforge doctor        # verify every dependency

# Your first video (needs a free Pixabay key + any LLM key)
reelforge new "hyderabadi biryani" --duration 30

# Ride the trends
reelforge trends ai --limit 5
reelforge batch ai --count 3

# Hands-free
reelforge agent "make a 30s reel about the top AI trend and post it Friday at 6pm"
```

Free keys: [Pixabay](https://pixabay.com/api/docs/) (footage) · [Google AI Studio](https://aistudio.google.com/) (Gemini LLM) · [NVIDIA NIM](https://build.nvidia.com/) (LLM). Or point `openai_base_url` at local Ollama and pay nothing at all.

## Docs

- `docs/setup-youtube.md`, `setup-tiktok.md`, `setup-instagram.md`, `setup-x.md` — per-platform OAuth
- `docs/trends.md` — trend sources and scoring
- `docs/mcp.md` — MCP server setup for Claude Code / Cursor
- `docs/visual-providers.md` — plugging in AI visual generation

## License

MIT — build whatever you want.
