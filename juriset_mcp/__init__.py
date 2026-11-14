"""The Juriset MCP server (T7, PRD 7.1): a thin, read-only client of the public `/v1` API.

This package imports nothing outside itself except third-party libraries (relative imports
only), so `packaging/mcp` can ship it unchanged as the PyPI distribution `juriset-mcp`, where it
installs as `juriset_mcp`. Tools are data (`tools.yaml`, compiled to `tools.json`); the executor
and server are generic (PRD 6.5).
"""

__version__ = "0.1.3"
