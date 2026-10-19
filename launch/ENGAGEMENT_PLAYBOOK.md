# Launch engagement playbook — ShortSmash

Goal: turn launch-day attention into stars and contributors without getting flagged as spam. One human voice, technical, honest.

## Ground rules

- **One account per platform.** Never sock-puppet. Never ask friends to upvote (HN detects and kills this; Reddit mods ban for it).
- **Reply to every technical comment within 2 hours** on launch day. Speed of maker response is the #1 momentum driver on Show HN.
- **Never argue.** "You're right, that's a gap — filed as an issue" beats any defense.
- **No emojis in HN replies.** Plain technical tone.
- **Cadence:** max 1 top-level comment per hour on Reddit threads; reply freely to direct questions.

## Response templates

### "What does this cost? / API costs?"
> The free path is genuinely free: Pixabay stock footage, Agnes AI free tier, Piper offline TTS, and any OpenAI-compatible LLM (points at local Ollama fine). Veo 3.1 and Kling are paid and strictly optional — bring your own key, they're for when you want premium AI-generated visuals instead of stock. Publishing via the official platform APIs costs nothing beyond the platforms' own free quotas.

### "How is this different from MoneyPrinterTurbo / other tools?"
> Two things: (1) the vision gate — every clip is verified by CLIP + Gemini before it ships, so you don't get the stock-footage look; (2) the dubbing engine — 50 languages with native voices and correct caption rendering (Urdu Nastaliq RTL, Hanzi karaoke). Plus 10 official publishing APIs instead of 3. Their community is 1000x bigger though — that's the honest gap.

### "Can I self-host it?"
> Yes, that's the default. Everything runs on your machine: `git clone`, `./install.sh`, keys in your own `.env`. Docker compose included. No accounts, no phone-home, SQLite queue. The Studio UI runs on localhost:8000.

### Feature request
> Good idea — can you open it as a GitHub issue so it doesn't get lost in this thread? I'll tag it for the roadmap. If you want to PR it, the adapter interfaces are small; happy to point you at the right file.

### "The demo video looks AI / quality critique"
> Fair — tell me specifically what looks off (voice? footage match? captions?) and I'll treat it as a bug report. The vision gate and script prompts are the two levers I can actually tune, so concrete critique is gold.

### Low-effort / hostile comment
> Don't engage beyond one polite reply. Never feed trolls on launch day.

## Timing

- **Show HN:** post Tue–Thu 8–10am ET. Be online for the next 6 hours minimum.
- **Reddit:** one subreddit per day (r/Python → r/SelfHosted → r/OpenSource). Morning US time.
- **X:** thread goes live same morning as HN; pin it.
- **Product Hunt:** separate day (Tue–Thu), not the same day as HN — don't split the audience.

## What NOT to do

- Don't cross-post the identical text anywhere (spam filters + community norms).
- Don't buy stars/upvotes — gets repos banned and HN submissions killed.
- Don't edit the HN title after posting unless it's factually wrong.
- Don't disappear after posting. An abandoned launch thread is worse than no launch.
