"""YouTube Data API v3 — official uploads (Shorts included).

Setup (docs/setup-youtube.md):
  1. Google Cloud project → enable YouTube Data API v3 → OAuth consent screen.
  2. Download OAuth client JSON → ~/.reelforge/youtube_client.json
  3. First run opens a browser to grant the youtube.upload scope; the token is
     cached at ~/.reelforge/youtube_token.json (refresh handled automatically).

A video <= 60s with #Shorts in the title/description is served as a Short.
"""

from __future__ import annotations

from pathlib import Path

from ..config import HOME, Config

CLIENT_JSON = HOME / "youtube_client.json"
TOKEN_JSON = HOME / "youtube_token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _service(cfg: Config):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        raise RuntimeError("pip install 'reelforge[youtube]' first.") from exc

    if not CLIENT_JSON.exists():
        raise RuntimeError(
            f"YouTube OAuth client not found at {CLIENT_JSON}. "
            "Follow docs/setup-youtube.md to create it (2 minutes).")

    creds = None
    if TOKEN_JSON.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_JSON), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_JSON), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_JSON.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def publish(video: Path, title: str, description: str, hashtags: list[str],
            cfg: Config | None = None, dry_run: bool = False,
            privacy: str = "public", category_id: str = "22") -> dict:
    tags = " ".join(hashtags)
    full_desc = f"{description}\n\n{tags}".strip()
    if dry_run:
        return {"platform": "youtube", "dry_run": True, "title": title,
                "privacy": privacy, "bytes": video.stat().st_size}

    from googleapiclient.http import MediaFileUpload
    yt = _service(cfg or Config())
    body = {
        "snippet": {"title": title[:100], "description": full_desc[:5000],
                    "tags": [h.lstrip("#") for h in hashtags][:30],
                    "categoryId": category_id},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = req.execute()
    vid = resp["id"]
    return {"platform": "youtube", "video_id": vid,
            "url": f"https://www.youtube.com/shorts/{vid}"}
