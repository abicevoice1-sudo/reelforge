# X launch thread — ShortSmash v0.3.0

Post as a thread. Attach: assets/social-preview.png to post 1, demo/coffee-v1-zh.mp4 to post 4.

---

**1/** I built the thing I wished existed: type one sentence, get a viral-ready short video.

Script ✓ Neural voiceover in 50 languages ✓ Footage that's actually verified ✓ Karaoke captions ✓ Published to 10 platforms in one click ✓

Meet ShortSmash 🔨 — free & open source.

**2/** The problem with every AI shorts tool: they assemble clips BLINDLY. Whatever the stock API returns first goes in. Burger in the biryani video. Robin in the cooking tutorial.

ShortSmash runs every clip through a two-stage vision gate (local CLIP + Gemini) before it ships. Nothing unverified makes the cut.

**3/** The dubbing is the part I'm proudest of. 50 languages with native neural voices — not translationese.

Urdu gets proper Nastaliq calligraphy with RTL karaoke. Mandarin gets a native voice + Hanzi captions. Roman Urdu/Hindi for the diaspora that reads Latin script.

**4/** Watch the same video re-voiced in Mandarin — zero human editing, one command:

`shortsmash dub coffee-v1 --lang zh`

[attach coffee-v1-zh.mp4]

**5/** v0.3.0 adds the heavy artillery for visuals: Google Veo 3.1 and Kling AI join Agnes AI + Pixabay as providers. Free path stays default; paid models are bring-your-own-key.

**6/** One command installs everything:

`curl -fsSL https://raw.githubusercontent.com/abicevoice1-sudo/shortsmash/main/install.sh | bash`

Then `shortsmash serve` opens the Studio. MIT licensed. Star it if you make something cool with it 👇

github.com/abicevoice1-sudo/shortsmash
