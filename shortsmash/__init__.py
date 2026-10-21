"""ShortSmash — prompt in, viral short out.

An AI video studio: Gemini writes the script and edit plan, Edge-TTS voices it,
Pexels/Pixabay supply the footage, FFmpeg cuts it into a captioned 9:16 short,
and official platform APIs publish it. Engagement is human-approved drafts only —
no bots, no fake likes, no detection-evasion, ever.
"""

import os as _os
from pathlib import Path as _Path

# Publishing moved to the shared creator-publish package (2026-10-19).
# Point its home here so existing OAuth tokens/clients keep working.
_os.environ.setdefault(
    "CREATOR_PUBLISH_HOME", str(_Path.home() / ".shortsmash"))

__version__ = "0.3.0"
__all__ = ["__version__"]
