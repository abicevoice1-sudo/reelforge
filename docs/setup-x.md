# X publishing setup (official API v2)

1. [developer.x.com](https://developer.x.com/) → create a **Project + App**.
2. In app settings → **User authentication settings** → enable **OAuth 1.0a**,
   permissions **Read and Write**.
3. Copy the **API Key/Secret** and generate **Access Token/Secret** (for your own account).
4. Set:
   ```
   X_API_KEY=
   X_API_SECRET=
   X_ACCESS_TOKEN=
   X_ACCESS_SECRET=
   ```

Notes
- Free tier: 1,500 posts/month — plenty for a shorts pipeline.
- Video limits on free/basic: ≤ 512 MB, ≤ 140 s. ReelForge's 9:16 MP4s qualify.
- ReelForge uploads with the chunked v1.1 media endpoint, then posts via v2.
