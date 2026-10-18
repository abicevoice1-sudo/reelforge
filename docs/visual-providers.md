# Visual providers

`visual_provider` in `~/.shortsmash/config.yaml` (default: `stock`).

## stock (default, free)

Pixabay footage, every clip verified by the two-stage vision gate
(local CLIP + Gemini). Costs nothing.

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
