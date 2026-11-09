"""The MCP server around the executor: `tools/list` serves tools.json as is, `tools/call` runs
the executor. Every success is the API's JSON body, unchanged, as structured content and as
compact text for clients that read only text."""

import json
from collections.abc import Callable
from typing import Any

import mcp_types as types
from mcp.server.caching import CacheHint
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp.shared.exceptions import MCPError

from . import __version__
from .executor import Executor, UnknownToolError

# The tool list changes only with a new release, so clients may cache it for an hour.
LIST_CACHE = CacheHint(ttl_ms=3_600_000, scope="public")

# The API key to send: one fixed key (stdio, one user), or a function asked on each call (the
# hosted endpoint, where every request carries its caller's own key or none).
ApiKey = str | Callable[[], str | None] | None


def create_server(executor: Executor, api_key: ApiKey) -> Server[Any]:
    definitions = executor.definitions
    tools = [types.Tool.model_validate(t) for t in definitions["tools"]]

    async def list_tools(
        ctx: ServerRequestContext[Any], params: types.PaginatedRequestParams | None
    ) -> types.ListToolsResult:
        return types.ListToolsResult(tools=tools)

    async def call_tool(
        ctx: ServerRequestContext[Any], params: types.CallToolRequestParams
    ) -> types.CallToolResult:
        try:
            key = api_key() if callable(api_key) else api_key
            outcome = await executor.call(params.name, params.arguments, api_key=key)
        except UnknownToolError as exc:
            raise MCPError(types.INVALID_PARAMS, f"unknown tool: {exc}") from exc
        return result(outcome.body, outcome.is_error)

    server = definitions["server"]
    return Server(
        server["name"],
        version=__version__,
        title=server["title"],
        website_url=server["website_url"],
        cache_hints={"tools/list": LIST_CACHE},
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


def result(body: Any, is_error: bool) -> types.CallToolResult:
    """Compact JSON: every token reaches the agent's context."""
    text = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
        structured_content=body if isinstance(body, dict) else None,
        is_error=is_error,
    )
