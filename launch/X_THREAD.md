# X launch thread — ShortSmash (ready to post)

Post as a thread. Attach demo/tickle-v1.mp4 (or the GIF) to Tweet 1 — the visual hook.

---

**Tweet 1 (visual hook):**
Every "AI shorts" tool assembles clips BLINDLY. Stock API returns something, it goes in the video. Burger in the cooking tutorial.

So I built ShortSmash: one prompt → finished short, with every clip verified by AI vision before it ships. Free, open source, MIT.

[attach demo video]

**Tweet 2 (features):**
Under the hood:
→ LLM writes script + shot-by-shot edit plan
→ Neural TTS, 50 languages, native voices
→ CLIP + Gemini vision gate on every clip
→ Karaoke captions, cinematic grade, ducked music
→ Veo 3.1 / Kling / Agnes / Pixabay as visual providers

**Tweet 3 (distribution):**
The part that took the longest: one-click publishing to 10 platforms through their OFFICIAL APIs.

YouTube Shorts, TikTok, Instagram, X, Threads, Bluesky, LinkedIn, Pinterest, Facebook. Schedule it with "Friday 6pm" in plain English.

**Tweet 4 (why open source):**
The SaaS clones charge per video for what is, under the hood, blind stock assembly with a markup.

ShortSmash is MIT. The vision gate, the 50-language dubbing engine, the publishing adapters — inspectable, forkable. I'd rather have 500 contributors than 500 subscribers.

**Tweet 5 (CTA):**
Try it:

git clone https://github.com/hydope/shortsmash && cd shortsmash
./install.sh
shortsmash "why you can't tickle yourself"

⭐ if you build something with it: github.com/hydope/shortsmash
