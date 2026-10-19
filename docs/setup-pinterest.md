# Pinterest publishing setup (official API v5)

1. [developers.pinterest.com](https://developers.pinterest.com/) → create an **app**.
2. In the OAuth flow request the scopes **`boards:read`, `boards:write`,
   `pins:read`, `pins:write`**, and copy the **access token**.
3. Pick (or create) the **board** your shorts go on. Its numeric ID is in the
   board's URL: `pinterest.com/<you>/<board-name>/` → open the board, the ID
   shows in API responses; easiest: create the board, then run any
   "list my boards" call in their API explorer and copy the `id`.
4. Set:
   ```
   PINTEREST_ACCESS_TOKEN=<your token>
   PINTEREST_BOARD_ID=1234567890123456
   ```

Notes
- ShortSmash posts via `POST /v5/pins` with the video file (multipart upload) —
  official API, no scraping.
- Video limits: ≤ 2 GB, ≤ 5 min. ShortSmash's 9:16 MP4s qualify.
- Pinterest is a search engine as much as a social app: the AI-generated
  title/description double as your Pin SEO.
