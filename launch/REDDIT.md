# Reddit drafts — ShortSmash

## r/SideProject

**Title:** I built an open-source pipeline that turns one sentence into a published short video (50-language dubbing included)

**Body:**

After months of nights, I'm launching ShortSmash v0.3.0: https://github.com/abicevoice1-sudo/shortsmash

Type a topic → it writes the script, narrates it (50 languages, native neural voices), finds footage, adds karaoke captions, renders 1080×1920, and publishes to 10 platforms in one click.

The thing I'm most proud of: a two-stage vision gate (local CLIP + Gemini) that verifies every clip before it ships. No more burger-in-the-biryani-video.

Also: proper Urdu Nastaliq RTL karaoke, Mandarin re-voicing, lyrics video mode, and an Auto tab that goes from trend to scheduled publish with API quota budgeting.

Visual providers: Pixabay (free), Agnes AI (free tier), Veo 3.1 + Kling (paid, BYO key). MIT licensed, one-command install.

The README has a demo made end-to-end by the tool, including the Chinese version. Roast it — I want the brutal feedback.

## r/opensource

**Title:** ShortSmash — MIT-licensed prompt-to-published short video pipeline (Veo 3.1 / Kling / 50-language dubbing)

**Body:**

https://github.com/abicevoice1-sudo/shortsmash

Full pipeline, all local-first where it matters: LLM script + edit plan → neural TTS (Edge/Piper/gTTS) → CLIP-verified stock or AI-generated footage → karaoke ASS captions → FFmpeg → 10 publishers → SQLite scheduler.

v0.3.0 adds Veo 3.1 and Kling AI providers, Grok as an LLM option, and a Mandarin demo. Everything's tested (52 tests, CI green). Contributions welcome — especially new publishers and TTS providers.
