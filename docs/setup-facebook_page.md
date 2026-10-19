# Facebook Page publishing setup (official Graph API)

The reliable Facebook route — works for every app type, unlike profile
publishing ([setup-facebook.md](setup-facebook.md)).

1. Create (or use) a **Facebook Page** you admin.
2. [developers.facebook.com](https://developers.facebook.com/) → create a **Meta app**,
   request the **`pages_manage_posts`** permission.
3. In the **Graph API Explorer**: select your app, get a user token with
   `pages_manage_posts`, then query `/me/accounts` — copy the **Page access
   token** for your Page. Hit **Extend Access Token** for a long-lived one
   (~60 days).
4. Your **Page ID** is in the Page's About section (or the `/me/accounts`
   response as `id`).
5. Set:
   ```
   FB_PAGE_ID=123456789012345
   FB_PAGE_ACCESS_TOKEN=<long-lived page token>
   ```

Notes
- ShortSmash uses the official resumable upload to `/{page-id}/videos`, then
  publishes to the Page feed.
- Video limits: ≤ 10 GB — effectively no constraint for shorts.
- When the token expires (~60 days), ShortSmash reports an auth error —
  repeat step 3. Calendar reminder recommended.
