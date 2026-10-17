# Product Hunt Launch Pack — ReelForge

## Tagline (60 chars)
The AI video pipeline with eyes — it rejects its own bad footage

## Description (260 chars)
Prompt in, viral short out. ReelForge writes the script, voices it, and
picks stock footage — then a local CLIP model *looks at every clip* and
rejects the wrong ones. Karaoke captions, music, 8 official publishing
APIs, trend harvesting, 7-language dubbing. Free, MIT, self-hosted.

## First comment (maker's)
Hey PH! I built ReelForge because every AI video tool ships the
"stock-footage look" — my biryani video came back with a burger, a robin,
and a houseplant in it. So I gave the pipeline eyes: a vision gate that
checks every clip before it ships. The demo video on the README was made
end-to-end by the tool itself. Happy to answer anything — especially
skeptical questions about the vision gate. ⚒️

## Topics
AI, Open Source, Video, Developer Tools, Social Media

## Assets checklist
- [ ] Logo: reuse the ⚒️ hammer emoji as the thumbnail (or export the README header)
- [ ] Gallery: 3 frames — (1) the burger fail, (2) the CLIP gate rejecting it, (3) the fixed video
- [ ] Demo video: demo/coffee-v1.mp4 (49s, captioned, silent-autoplay friendly)
- [ ] Link: https://github.com/abicevoice1-sudo/reelforge

## Timing
- [ ] Launch 12:01 AM PT Monday (full 24h runway)
- [ ] Pre-write answers to the 5 most likely questions (below)
- [ ] Rally X audience morning-of: "we're live on Product Hunt"

## Likely questions (pre-answer)
1. "How is this different from MoneyPrinterTurbo?" → the vision gate; official APIs not Selenium; 7-language dubbing.
2. "What does it cost to run?" → $0: free LLM tiers, free Pixabay, local CLIP/Piper, MIT.
3. "Windows support?" → Python + FFmpeg; CI runs Ubuntu, community-tested on Win/Mac welcome.
4. "Can it use my own footage?" → yes, drop files in clips/ or use visual_provider: custom.
5. "Why not AI-generated video?" → real footage beats AI slop for food; custom hook supports ComfyUI/Replicate if you pay.
