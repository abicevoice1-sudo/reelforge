# Dev.to Article — "I compared 20 open-source video pipelines. Here's what I learned."

> Publish Day 5 of launch week. This is the link-magnet piece: bookmarked,
> shared, and Google-ranked long after launch day.

---

**Title:** I compared 20 open-source AI video pipelines. Only one checks its own work.

**Cover:** the burger-in-biryani frame vs the fixed frame, side by side.

---

Every open-source text-to-video pipeline does the same thing: LLM writes a
script, TTS reads it, a stock API returns clips, FFmpeg stitches it. I
tested 20 of them — MoneyPrinterTurbo (129K stars), ShortGPT, OpenPost,
Postiz, and sixteen more — and found the same flaw in all of them:

**Nobody looks at the footage.**

I generated a biryani video with a leading pipeline. It contained a burger,
a robin, and a houseplant. The stock API returned garbage and the pipeline
shipped it, because no step in any of these tools actually *sees* the video.

## The categories

**The factories** (MoneyPrinterTurbo, ShortGPT, ai-video-generator) turn
prompts into shorts. Turbo is the most mature by far — WebUI, batch mode,
20+ LLM providers. But its reviews all mention the "stock-footage look,"
and none of them verify a single frame.

**The workspaces** (OpenPost, Postiz) are superb manual studios — 16+
platforms, teams, scheduling. But they generate nothing from a prompt.
Different sport.

**The infrastructure** (Remotion, n8n, browser-use, Skyvern) is what you'd
use to *build* a pipeline. Powerful, but nobody ships the product for you.

## The fix: give the pipeline eyes

I built ReelForge with a two-stage vision gate:

1. **Local CLIP** (ViT-B/32, offline, no quota, no cost) scores every
   candidate clip's middle frame against 15 confuser categories —
   burgers, birds, houseplants, empty pans, citrus fruit.
2. **Gemini vision** double-checks when quota allows.

Wrong clip → rejected → next candidate. Automatically. Calibrated 11/11
on real render frames.

Plus the unglamorous gates nobody builds: an **audio safety gate**
(silent renders fail instead of shipping) and a **resume** command (failed
renders pick up mid-pipeline instead of starting over).

## What I'd steal from each

- MoneyPrinterTurbo's batch mode and trend harvesting → built both
- Postiz's analytics → built a YouTube stats pull
- ShortGPT's dubbing → built 7-language re-voicing
- OpenPost's MCP server → built one (4 tools)

## The honest scorecard

[comparison table from README]

ReelForge is MIT, 37 tests, and the demo video in the README was made
end-to-end by the tool itself — burger-free.

https://github.com/abicevoice1-sudo/reelforge

---

*If you've fought the stock-footage look in your own pipelines, I'd love
to hear what you tried — the vision gate is the part I most want torn
apart.*
