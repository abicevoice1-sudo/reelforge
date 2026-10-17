# TikTok publishing setup (official Content Posting API)

1. Go to [developers.tiktok.com](https://developers.tiktok.com/) → **Manage apps** → create an app.
2. Add the **Content Posting API** product; request scopes `video.upload` and `video.publish`.
   - Sandbox mode works immediately for your own account; production needs app review.
3. Set the redirect URI (e.g. `https://example.com/callback`) and complete OAuth:
   authorize → exchange the `code` for tokens:
   `POST https://open.tiktokapis.com/v2/oauth/token/` with client_key, client_secret, code.
4. Save the tokens:
   ```
   TIKTOK_ACCESS_TOKEN=<access_token>
   TIKTOK_REFRESH_TOKEN=<refresh_token>
   ```
   Access tokens expire — refresh via the same endpoint with `grant_type=refresh_token`.

Notes
- Direct-post to public requires an approved (audited) app; sandbox posts are private to you — perfect for testing.
- ReelForge uses the FILE_UPLOAD flow (chunked PUT), which works for videos up to 10 min.
