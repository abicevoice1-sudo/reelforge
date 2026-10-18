# Visual providers

`visual_provider` in `~/.shortsmash/config.yaml` (default: `stock`).

## stock (default, free)

Pixabay footage, every clip verified by the two-stage vision gate
(local CLIP + Gemini). Costs nothing.

## agnes (free)

Agnes AI text-to-video — genuinely free tier, no GPU or card needed.
Free signup at platform.agnes-ai.com, save the key, set
`visual_provider: agnes`. Note: the free queue fills at peak hours;
ShortSmash retries with backoff.

## veo (paid — best quality)

Google Veo 3.1, the same engine behind Google Flow (Flow has no public
API; this is the API path to the same models). Native audio, 4/6/8s
clips, superb prompt adherence.

```yaml
visual_provider: veo
veo_model: veo-3.1-fast-generate-preview  # or veo-3.1-generate-preview (best), veo-3.1-lite-generate-preview (cheapest)
```

Needs `GEMINI_API_KEY` from aistudio.google.com in a project **with
billing enabled** — Veo is paid-only, no free tier. Pricing is per
second of generated video.

## kling (paid — top-tier motion)

Kling AI text-to-video, famous for motion quality. 5s/10s clips.

```yaml
visual_provider: kling
kling_model: kling-v2-1
kling_duration: 5  # or 10
```

Needs `KLING_ACCESS_KEY` + `KLING_SECRET_KEY` from kling.ai/dev/api-key
(the secret shows only once — save it).

## custom (bring your own generator)

Point ShortSmash at any text-to-video system — ComfyUI, Replicate,
MiniMax, Seedance, Runway, or your own script:

```yaml
visual_provider: custom
visual_command: 'python ~/my_gen.py --prompt {prompt} --out {out} --duration {duration}'
```

Template variables: `{prompt}` (scene description), `{out}` (target mp4 path),
`{duration}` (seconds). Your command must write a valid mp4 to `{out}`
within 10 minutes. The vision gate still checks the result before it ships.

Why a shell command instead of a built-in integration? Every AI video vendor
has a different API, auth scheme, and pricing tier — a single half-working
built-in would rot. The shell boundary lets you plug in whatever you
already pay for, and swap vendors without touching ShortSmash.
