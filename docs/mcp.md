# MCP server

Let AI agents drive the video factory. The MCP server exposes ShortSmash as
tools over stdio for Claude Code, Cursor, Windsurf, or any MCP client.

## Setup

```bash
pip install 'shortsmash[mcp]'
```

Add to your MCP client config (e.g. `~/.claude.json` or Cursor settings):

```json
{"mcpServers": {"shortsmash": {
    "command": "/path/to/shortsmash/.venv/bin/python",
    "args": ["-m", "shortsmash.mcp_server"]
}}}
```

## Tools

| Tool | What it does |
|---|---|
| `generate_video(topic, duration=30)` | Full pipeline: script → voice → verified footage → captions → render. Returns the project slug. |
| `get_trends(niche="general", limit=10)` | What's trending right now, ranked. |
| `list_projects()` | All projects and their render state. |
| `project_status(slug)` | Stage checklist: script, clips, captions, video. |

## Example agent session

> "Check the top 3 AI trends, make a 30s video about the most interesting one."

The agent calls `get_trends`, picks a topic, calls `generate_video`, and
reports the slug — no CLI needed.
