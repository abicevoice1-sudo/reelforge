# Facebook profile publishing setup (official Graph API)

⚠️ **Honest caveat first:** Meta restricts profile video publishing for many app
types. If your app gets rejected for the needed permission, publish to a
**Facebook Page** instead — [setup-facebook_page.md](setup-facebook_page.md)
works for every app type.

1. [developers.facebook.com](https://developers.facebook.com/) → create a **Meta app**.
2. Add the permissions your use case needs (video upload to your own profile).
3. Generate a **user access token** with video-upload scope. Extend it to a
   long-lived token in the Graph API Explorer so you're not re-authing weekly.
4. Set:
   ```
   FB_ACCESS_TOKEN=<long-lived user token>
   ```

Notes
- ShortSmash uses the official resumable upload to `/{user-id}/videos`.
- Video limits: ≤ 10 GB, 240p minimum — effectively no constraint for shorts.
- If the API returns a permission error on your app type, that's Meta's policy,
  not a ShortSmash bug — the Page route is the reliable path.
