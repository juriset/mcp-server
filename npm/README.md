# juriset-mcp (npm)

A thin wrapper: `npx -y juriset-mcp` runs the [Juriset MCP server](https://pypi.org/project/juriset-mcp/)
of the same version with `uvx` (or `uv tool run`, or `pipx run`). It needs one of those on the
PATH. Configuration, tools and limits are in the PyPI package's README; the environment
(`JURISET_API_KEY`, `JURISET_API_URL`) passes through.

```json
{ "mcpServers": { "juriset": { "command": "npx", "args": ["-y", "juriset-mcp"] } } }
```

Informational only, not legal advice.
