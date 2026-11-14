"""`juriset-mcp` (or `uvx juriset-mcp`): the Juriset MCP server over stdio.

JURISET_API_KEY   optional: your API key (https://juriset.dev/account). Without one the API's
                  keyless tier answers current rules, limited per IP address; as-of queries,
                  history and the change feed need a key whose plan includes them.
JURISET_API_URL   default https://api.juriset.dev
"""

import argparse
import os
from collections.abc import Mapping, Sequence

import anyio
import httpx
from mcp.server.stdio import stdio_server

from . import __version__, definitions
from .executor import Executor
from .server import create_server

API_URL = "https://api.juriset.dev"
TIMEOUT = 15.0  # seconds per API call


async def serve() -> None:
    api_key = os.environ.get("JURISET_API_KEY", "").strip() or None
    async with httpx.AsyncClient(timeout=TIMEOUT) as http:

        async def fetch(url: str, headers: Mapping[str, str]) -> tuple[int, Mapping[str, str], str]:
            response = await http.get(url, headers=dict(headers))
            return response.status_code, response.headers, response.text

        executor = Executor(
            definitions.load(),
            api_url=os.environ.get("JURISET_API_URL", "").strip() or API_URL,
            fetch=fetch,
            user_agent=f"juriset-mcp/{__version__} (stdio)",
        )
        server = create_server(executor, api_key)
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """`--help` and `--version` answer and exit. Without this the server started on any argument
    and sat waiting for an MCP client on stdin, so `juriset-mcp --help` looked like a hang."""
    parser = argparse.ArgumentParser(
        prog="juriset-mcp",
        description="The Juriset MCP server over stdio. An MCP client starts it; run by hand,"
        " it waits for a client on stdin.",
        epilog="environment:\n" + (__doc__ or "").split("\n\n", 1)[-1].rstrip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"juriset-mcp {__version__}")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    parse_args(argv)
    anyio.run(serve)


if __name__ == "__main__":
    main()
