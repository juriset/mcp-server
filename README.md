# Juriset MCP server

The [Juriset](https://juriset.dev) MCP server: verified, versioned, cited jurisdiction rules
for AI agents. It starts with US and Canadian employment and payroll rules (minimum wage,
overtime, paid leave, termination notice, payroll contribution rates).

Every value carries its citation: the official source URL, a verbatim excerpt and the stored
snapshot. Each was extracted by one model and checked blind against the primary source by a
model from another vendor; escalations are reviewed by a human. Every version has a stable id
(`rv_…`) to record with a decision, so you can show later exactly which rule applied.

Juriset reports what official sources say. It never computes an answer for a case and never
merges levels of government into one rule. Informational only, not legal advice.

mcp-name: dev.juriset/juriset

## Use it

Two ways in, the same eight read-only tools behind both.

### Hosted, nothing to install

Streamable HTTP at `https://mcp.juriset.dev/mcp`. Add it as a remote MCP server in any client
that takes a URL. No key is needed to try it; for your plan's limits and the key-only tools,
send `Authorization: Bearer jrs_live_…` with a key from <https://juriset.dev/account>.

Claude Code: `claude mcp add --transport http juriset https://mcp.juriset.dev/mcp`

### Local (stdio), from PyPI or npm

Needs [uv](https://docs.astral.sh/uv/) (`uvx`) or Node 18+ (`npx`, which runs the same Python
server through `uvx`).

```json
{ "mcpServers": { "juriset": { "command": "uvx", "args": ["juriset-mcp"] } } }
```

Claude Code: `claude mcp add juriset -- uvx juriset-mcp`. With npm instead of uv:
`"command": "npx", "args": ["-y", "juriset-mcp"]`.

No account is needed to try it: without a key the API's keyless tier answers current rules,
read-only, at 60 requests an hour and 500 a day per IP address. As-of queries, history and the
change feed need an API key whose plan includes them. Get one at
<https://juriset.dev/account>, then add `"env": {"JURISET_API_KEY": "jrs_…"}` to the config.

| Variable | Meaning |
|---|---|
| `JURISET_API_KEY` | Optional API key, sent as a bearer token. |
| `JURISET_API_URL` | Default `https://api.juriset.dev`; set for staging. |

## Tools

All read-only. Slugs: a jurisdiction is `us-wa` (Washington), `us` (US federal), `ca-ab`
(Alberta); a rule type is `minimum_wage`, `overtime`, …

| Tool | Use it to |
|---|---|
| `list_jurisdictions` | Find a jurisdiction's slug from its name or postal code. |
| `list_rule_types` | See the rule types, their domains and the JSON Schema of their values. |
| `get_rule` | Get the rule in force today, with citations. |
| `get_rule_as_of` | Get the rule in force on a past or future date. |
| `get_rule_history` | List every published version of a rule. |
| `compare_jurisdictions` | Get one rule type across jurisdictions. |
| `list_changes` | Page through what changed since a date. |
| `resolve_version` | Fetch exactly the version a stored id names, forever. |

Where levels of government stack (US federal and state overtime) the response lists each level
as its own entry. Nothing is merged.

## This repository

A read-only mirror of the published package, so you can read exactly what runs and file issues.
The server is developed in the private Juriset monorepo and released from there to
[PyPI](https://pypi.org/project/juriset-mcp/) and [npm](https://www.npmjs.com/package/juriset-mcp);
each release is copied here unchanged. Issues are welcome; pull requests are read but not merged
directly (a fix lands in the monorepo and arrives here with the next release).

| Path | What it is |
|---|---|
| `juriset_mcp/` | The server: `__main__.py` (stdio entry), `server.py`, `executor.py` (calls the public `/v1` API), `tools.json` (the tool definitions, generated) |
| `pyproject.toml` | Builds the same `juriset-mcp` wheel: `uv build --wheel` |
| `npm/` | The npm package, a small wrapper that runs the PyPI version with `uvx` |
| `server.json` | The record in the official MCP Registry (`dev.juriset/juriset`) |

Run from a checkout: `uv run juriset-mcp` (stdio). The server only reads from the public API
(`JURISET_API_URL`, default `https://api.juriset.dev`); it stores nothing and sends nothing else.

## Licence

MIT, see [LICENSE](LICENSE). The rule data the tools return is covered by the Juriset
[terms of service](https://juriset.dev/terms). Juriset reports what official sources say;
it is not legal advice.
