"""Visual sourcing: which footage fills each scene.

Providers (`visual_provider` in config, default "stock"):
  stock  — free Pixabay footage, verified by the two-stage vision gate
           (local CLIP + Gemini). The default; costs nothing.
  agnes  — free AI-generated video via Agnes AI (text-to-video, no GPU).
           Needs a free API key from https://platform.agnes-ai.com saved
           in the Secure Vault (provider "agnes"). Each scene's cinematic
           shot list becomes a real AI clip.
  custom — your own generator: set `visual_command` to a shell template
           that turns a prompt into an mp4, e.g. a ComfyUI workflow,
           a Replicate call, or MiniMax/Seedance via their APIs.
           Template vars: {prompt}, {out}, {duration}.

The custom path exists because AI-generated visuals are a paid,
bring-your-own-key world with a different API per vendor — so instead
of shipping one half-working integration, ReelForge shells out to
whatever you already use. The vision gate still checks the result.
"""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from .config import Config


def fetch(query: str, out: Path, cfg: Config, seed: int = 0,
          context: str = "", duration: float = 4.0) -> Path:
    """Fetch one scene's visuals via the configured provider."""
    provider = cfg.get("visual_provider", "stock")
    if provider == "custom":
        return _custom_generate(query, out, cfg, duration)
    if provider == "agnes":
        from . import agnes
        return agnes.generate(query, out, cfg, duration=duration)
    from . import stock
    return stock.fetch_stock(query, out, cfg, seed=seed, context=context)


def _custom_generate(query: str, out: Path, cfg: Config, duration: float) -> Path:
    template = cfg.get("visual_command", "")
    if not template:
        raise RuntimeError(
            "visual_provider=custom but no visual_command set. "
            "Example: visual_command: 'python my_gen.py --prompt {prompt} --out {out}'"
        )
    cmd = template.format(prompt=shlex.quote(query),
                          out=shlex.quote(str(out)),
                          duration=duration)
    subprocess.run(cmd, shell=True, check=True, timeout=600)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"visual_command produced no video at {out}")
    return out
