# LinkedIn publishing setup (official API)

1. [developer.linkedin.com](https://developer.linkedin.com/) → **Create app**.
2. Under **Products**, request **Share on LinkedIn** (usually approved quickly
   for personal use).
3. Run the **OAuth 2.0 flow** with the `w_member_social` scope and copy the
   **access token**. (LinkedIn tokens expire in 60 days — re-authorize when
   ShortSmash reports an auth error.)
4. Set:
   ```
   LINKEDIN_ACCESS_TOKEN=<your token>
   ```

Notes
- ShortSmash uploads via the official flow: register upload → PUT binary →
  create `ugcPost` as a video post on your profile.
- Video limits: ≤ 200 MB, ≤ 10 min. ShortSmash's 9:16 MP4s qualify.
- Posts go to your **personal profile**. Company-page posting needs a
  different API product and isn't wired up — the adapter will tell you.
