# Show HN Submission Pack — ReelForge

## Title options (pick one)

1. **Show HN: ReelForge – the AI video pipeline with eyes (it rejects its own bad footage)** ← recommended
2. Show HN: I built a text-to-video CLI that visually verifies every clip before shipping
3. Show HN: ReelForge – prompt in, viral short out, with a local CLIP model as QA

## Post body (~250 words)

Hey HN. Every open-source text-to-video pipeline I've tried assembles clips blindly — whatever the stock API returns first goes in the video. That's the "stock-footage look": a burger in a biryani video, a robin in a cooking tutorial. The tools don't look at what they ship.

So I built ReelForge, a prompt-to-short pipeline with eyes. Every candidate clip's middle frame goes through a two-stage vision gate: a local CLIP model (offline, no quota, no cost) scores it against 15 confuser categories — burgers, birds, houseplants, empty pans, citrus fruit — then Gemini vision double-checks when quota allows. Wrong footage never ships. There's also an audible gate: renders with dead audio fail instead of shipping silently.

```
reelforge trends food                  # what's hot (free, no keys)
reelforge batch food --count 5         # 5 trends → 5 videos, unattended
reelforge agent "make a 30s reel about biryani, post Friday 6pm"
```

The rest of the pipeline: NVIDIA/Gemini/Ollama script writing (strict JSON edit plans, pydantic-validated), Edge-TTS → offline Piper neural → gTTS voice chain, faster-whisper karaoke captions, FFmpeg 1080×1920 with ducked music, and publishing through official YouTube/TikTok/Instagram/X APIs — no Selenium, no scraping. Plus an MCP server so agents can drive it, and `resume` to pick up failed renders mid-pipeline.

Honest scope: it's a CLI, not a web app. The vision gate is only as good as CLIP's zero-shot judgment — it occasionally prefers a rice paddy over a rice dish. 32 tests, MIT, ~4K lines of Python. Demo video in the README was made end-to-end by the tool itself.

Repo: https://github.com/abicevoice1-sudo/reelforge

I'd love teardowns of the vision gate especially — where does CLIP's judgment break for you? And if you've fought the stock-footage look in your own pipelines, what did you try?

---

## Posting checklist

- [ ] Post Wednesday 7:00 AM ET (peak HN morning window)
- [ ] Use title option 1
- [ ] First 3 hours: reply to EVERY comment — HN rewards maker presence
- [ ] Don't argue with teardowns; ask follow-ups, note fixes publicly
- [ ] Evening: file top feedback as GitHub issues (shows the loop is real)
- [ ] Do NOT ask for upvotes anywhere (HN detects and buries brigading)
