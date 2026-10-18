# YouTube publishing setup (~5 minutes, one time)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create a project.
2. **APIs & Services → Library** → enable **YouTube Data API v3**.
3. **OAuth consent screen** → External → fill app name/email → add scope
   `https://www.googleapis.com/auth/youtube.upload` → add yourself as test user.
4. **Credentials → Create Credentials → OAuth client ID** → Desktop app →
   download JSON → save as `~/.shortsmash/youtube_client.json`.
5. Run `shortsmash publish <slug> --platforms youtube` — a browser opens once;
   grant access. The token is cached at `~/.shortsmash/youtube_token.json`
   and refreshes itself.

Notes
- Videos ≤ 60s with `#Shorts` in the description are served as Shorts
  (ShortSmash adds it automatically for short videos).
- Quota: uploads cost ~1600 units; the default daily quota (10,000) ≈ 6 uploads/day.
  Request a quota increase in Cloud Console if you publish more.
