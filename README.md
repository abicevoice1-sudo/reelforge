# ReelForge ⚒️

**Prompt in. Viral short out.**

ReelForge is an AI video studio that takes one sentence and ships a finished,
captioned 9:16 short — then publishes it to YouTube, TikTok, Instagram and X
through their **official APIs**. Script, voiceover, stock footage, karaoke
captions, music ducking, scheduling and comment-reply drafts, all in one CLI.

```
reelforge agent "make a 30s reel about hyderabadi biryani and post it Friday at 6pm"
```

## Why "ReelForge"?

A forge is where raw material becomes something sharp. You bring the raw
material — a prompt — and ReelForge hammers it into a finished reel:
scripted, voiced, cut, captioned, scored, and shipped. Short, memorable,
and honest about what it does.

## The pipeline

```
  prompt ──▶ script ──▶ voice ──▶ stock ──▶ captions ──▶ render ──▶ publish
             NVIDIA    Edge-TTS  Pixabay/   faster-     FFmpeg      official
             (free)    (free,    Pexels*    whisper     1080x1920   APIs only
                       no key)   (free)     karaoke     +faststart
```

- **Script** — Gemini (free tier) writes a scroll-stopping script *and* a strict
  JSON edit plan (scenes, hooks, transitions, hashtags), validated by pydantic.
  No key? A built-in template keeps the pipeline running offline.
- **Voice** — Edge-TTS neural voices, free, no API key. Urdu/Hindi/Arabic voices included.
- **Stock** — Pixabay/Pexels* free APIs (portrait video). No key? Cinematic generated
  placeholders keep everything testable.
  \*Pexels paused new API key issuance 2026-09-30; Pixabay is the default.
- **Captions** — faster-whisper word timestamps → burned-in **karaoke captions**,
  the word-pop style top shorts use.
- **Render** — FFmpeg: 9:16 smart reframe, xfade transitions (cut/fade/slide/zoom),
  hook + CTA overlays, music ducked under narration, H.264/AAC faststart.
- **Publish** — YouTube Data API v3, TikTok Content Posting API, Instagram Graph
  API (Reels), X API v2. Uploads only. Nothing else.
- **Schedule** — render now, publish later: timezone-aware natural language
  ("Friday 6pm"), durable SQLite queue, retrying worker.
- **Engage** — pulls your recent comments, drafts warm replies, **you approve
  each one with a tap**. Nothing posts itself. Ever.

## What ReelForge will never do

No fake likes, comments, follows or shares. No botting, no "human-like"
evasion of platform detection, no scraping or unofficial endpoints. That stuff
violates every platform's rules and gets accounts banned — and it doesn't work
for real growth anyway. This boundary is architectural, not a policy note:
the capability simply isn't in the codebase.

## Quickstart

```bash
pip install 'reelforge[ai,voice,captions,youtube,x,schedule]'
reelforge init
reelforge doctor        # checks ffmpeg, keys, everything

# One command, end to end:
reelforge agent "make a 30s reel about morning routines and post it Friday at 6pm"

# Or stage by stage:
reelforge new "why hyderabadi biryani hits different" --duration 30
reelforge publish 20261016-193000-why-hyderabadi-biryani-hits-d --platforms youtube,tiktok --dry-run
reelforge schedule "matchday vlog" --at "tomorrow 9am" --platforms instagram,x
reelforge worker        # processes the queue
reelforge engage --platform youtube   # approve comment replies, one tap each
```

Copy `.env.example` → `.env` and add keys. Only three matter for the core:
`GEMINI_API_KEY` (free), `PIXABAY_API_KEY` (free) — and Edge-TTS needs no key at all.
(Script LLM prefers NVIDIA NIM free tier, falls back to Gemini.)
Publisher setup guides live in `docs/` (one per platform, ~5 min each).

## Project layout

```
reelforge/
  script.py     Gemini script + edit-plan JSON (pydantic-validated)
  voice.py      Edge-TTS narration (Piper for offline)
  stock.py      Pixabay / Pexels* / generated placeholders (*existing keys only)
  captions.py   faster-whisper → karaoke .ass subtitles
  music.py      royalty-free bed + speech-aware ducking
  edit.py       FFmpeg 1080x1920 render pipeline
  publish/      youtube.py  tiktok.py  instagram.py  x.py  (official APIs)
  schedule.py   SQLite queue + natural-language times + worker
  engage.py     comment fetchers + drafts (human-approved posting)
  agent.py      natural-language → AgentJob → confirm → run
  pipeline.py   orchestration + ~/.reelforge/projects/<slug>/ artifacts
```

Every stage writes inspectable artifacts (`plan.json`, `voiceover.mp3`,
`clips/`, `captions.ass`, `final.mp4`) — re-run or hand-tweak any stage.

## Config

`~/.reelforge/config.yaml` (created by `reelforge init`): voice, caption style,
resolution, music bed level, timezone. Secrets stay in the environment —
ReelForge never writes keys to disk.

## Roadmap

- Face-aware 9:16 reframe (subject tracking instead of center crop)
- Auto chapters + multi-language caption tracks
- A/B hook testing: render 3 hook variants, publish the winner
- Web dashboard for the queue and approvals

MIT — forge freely.
