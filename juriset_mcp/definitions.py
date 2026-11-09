"""The compiled tool definitions (tools.json), the only definition file the package carries."""

import json
from importlib import resources
from typing import Any


def load() -> dict[str, Any]:
    text = resources.files(__package__ or "app.mcp").joinpath("tools.json").read_text("utf-8")
    loaded: dict[str, Any] = json.loads(text)
    return loaded
