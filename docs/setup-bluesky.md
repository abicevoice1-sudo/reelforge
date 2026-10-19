# Bluesky publishing setup (official AT Protocol)

The easiest of all ten — no app, no OAuth dance.

1. Log in at [bsky.app](https://bsky.app/) → **Settings → Privacy and security →
   App passwords** → **Add app password**. Name it `shortsmash`.
2. Copy the generated password (format `xxxx-xxxx-xxxx-xxxx`).
3. Set:
   ```
   BSKY_HANDLE=you.bsky.social
   BSKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
   ```

Notes
- ShortSmash talks raw ATProto HTTP: `createSession` → `uploadBlob(video)` →
  post with video embed. No SDK, no third-party service.
- Video limits: ≤ 50 MB, ≤ 60 s. If your video is longer, ShortSmash warns you
  in the pre-flight check — trim it or pick another platform.
- Never use your main account password — app passwords are revocable per app.
