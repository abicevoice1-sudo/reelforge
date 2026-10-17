# X Thread — ReelForge launch

Post as a thread, one tweet per numbered item. Attach the demo video to tweet 1.

---

**1/** I built an AI video pipeline with eyes. 👁️

Every text-to-video tool assembles clips blindly — that's the "stock-footage look."

ReelForge visually inspects every clip with a local CLIP model before it ships. Wrong footage gets rejected automatically.

Prompt in, viral short out. 🧵

**2/** The problem: I generated a biryani video and the "AI" put a BURGER, a ROBIN, and a HOUSEPLANT in it.

Stock APIs return garbage. Every pipeline ships it. Nobody checks.

**3/** The fix: a two-stage vision gate.

Stage 1: local CLIP (offline, free, no quota) scores each clip against 15 confuser categories.

Stage 2: Gemini vision double-checks.

Bad clip → rejected → next candidate. Automatically.

**4/** What you get:

`reelforge trends food` → what's hot right now (free, no keys)
`reelforge batch food --count 5` → 5 videos from 5 trends, unattended
`reelforge agent "make a 30s biryani reel, post Friday 6pm"`

**5/** The full stack, all free:

📝 NVIDIA/Gemini/Ollama scripts (pydantic-validated)
🎙️ Edge-TTS → offline neural voice
👁️ CLIP-verified footage
🔥 Karaoke captions
🎵 Auto-downloaded music, ducked under narration
📤 Official YT/TikTok/IG/X APIs (no Selenium hacks)

**6/** Plus: an MCP server so Claude Code can drive the whole factory, `resume` for failed renders, and comment-reply drafts you approve with one tap.

No fake engagement. No bots. The capability isn't in the codebase — by design.

**7/** MIT licensed. 32 tests passing. Demo video in the README was made by the tool itself.

https://github.com/abicevoice1-sudo/reelforge

If you've fought the stock-footage look, I'd love your teardown. 👇
