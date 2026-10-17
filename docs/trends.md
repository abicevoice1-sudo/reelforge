# Trend harvesting

`reelforge trends <niche>` finds what the world is talking about right now —
free, no API keys, no accounts.

## Sources

| Source | What | Key needed |
|---|---|---|
| Google News RSS | Fresh articles per niche query | No |
| Hacker News API | Front-page tech/AI stories | No |

Deliberately **not** used: Reddit's public JSON API (requires OAuth since 2023 —
returns 403 without it) and Google Trends' trending endpoint (deprecated, 404s).

## Niches

`food` `fitness` `tech` `ai` `finance` `travel` `motivation` `health` `general`

Each niche maps to curated Google News queries (`reelforge/trends.py`,
`NICHE_QUERIES`). Tech/AI niches also pull Hacker News.

## Scoring

- Google News: recency-decayed (`100 / age_hours^0.8`) — news goes stale fast.
- Hacker News: `(points + 2×comments) / age_hours^0.9` — discussion matters.
- Near-duplicate titles are collapsed, keeping the highest score.

## Usage

```bash
reelforge trends food --limit 10
reelforge batch food --count 5        # top 5 trends → 5 videos
reelforge batch ai --count 3 --duration 45
reelforge batch --topics "ramen,pho,tacos" --count 3   # skip harvest
```

## Adding a niche

Add an entry to `NICHE_QUERIES` in `reelforge/trends.py`:

```python
"gaming": ["video games", "game release", "esports"],
```
