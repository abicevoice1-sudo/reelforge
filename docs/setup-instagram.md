# Instagram Reels publishing setup (official Graph API)

Prerequisites: an Instagram **Business or Creator** account linked to a Facebook Page.

1. [developers.facebook.com](https://developers.facebook.com/) → create an app → add the
   **Instagram Graph API** product.
2. Grant your app `instagram_basic` and `instagram_content_publish`; generate a
   **long-lived Page access token** (valid 60 days; refresh before expiry).
3. Get your IG user id: `GET /me/accounts?fields=instagram_business_account` →
   save as `IG_USER_ID`.
4. Set:
   ```
   IG_ACCESS_TOKEN=<long-lived page token>
   IG_USER_ID=<instagram business account id>
   ```

The MP4 must be at a **public https URL** — Meta's servers download it.
Options: your own site/CDN, Cloudflare R2, or any static host. Then either:
- `reelforge publish <slug> --platforms instagram --video-url https://…/final.mp4`, or
- set `public_video_url` in `~/.reelforge/config.yaml`.

Notes
- Reels: 3s–15 min, 9:16 recommended, ≤ 1 GB. ReelForge renders exactly that.
- Container processing takes ~30s; ReelForge polls until it's ready, then publishes.
