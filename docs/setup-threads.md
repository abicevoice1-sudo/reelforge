# Threads publishing setup (official API via graph.threads.net)

1. [developers.facebook.com](https://developers.facebook.com/) → create a **Meta app**,
   add the **Threads** use case.
2. Add your Threads account as a **Tester** (App Roles → Testers), accept the invite.
3. Generate a **short-lived token**, then exchange it for a **long-lived token**
   (valid ~60 days — refresh with `shortsmash` before it expires).
4. Find your **Threads user ID** (the numeric ID from the token debug / your profile).
5. Set:
   ```
   THREADS_USER_ID=123456789
   THREADS_ACCESS_TOKEN=<long-lived token>
   ```

Notes
- ⚠️ **Threads ingests video from a public URL** — it cannot receive a direct
  upload. Host the MP4 somewhere public first (S3, Cloudflare R2, your CDN) and
  set `public_video_url` in `~/.shortsmash/config.yaml`. ShortSmash will refuse
  with a clear error if it's missing.
- Video limits: ≤ 250 MB, ≤ 5 min. ShortSmash's 9:16 MP4s qualify.
- Text is capped at 500 chars (title + hashtags, truncated automatically).
