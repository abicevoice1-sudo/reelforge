# Dockerfile for Glama build-and-release of the ShortSmash MCP server.
#
# Glama builds this image, runs the stdio MCP server from it, probes the tool
# list (generate_video, get_trends, list_projects, project_status), runs
# security scans, and assigns the quality score. punkpeye/awesome-mcp-servers
# requires that score (via the Glama score badge) before merging.
#
# Startup deps are light: shortsmash[mcp] = mcp<2 + core deps
# (typer, rich, pydantic, httpx, python-dotenv, pyyaml, creator-publish).
# Heavy extras (torch/transformers for the vision gate, faster-whisper,
# edge-tts, ffmpeg) are NOT installed: the MCP server starts without them;
# only actual video generation needs them (Glama's probe only lists tools).
FROM python:3.12-slim

WORKDIR /app

# Install the MCP-enabled distribution from PyPI (release 0.3.0)
RUN pip install --no-cache-dir "shortsmash[mcp]"

# shortsmash-mcp is the console entry point -> shortsmash.mcp_server:main (stdio)
ENTRYPOINT ["shortsmash-mcp"]
