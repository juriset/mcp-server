"""The generic executor: a tool call becomes one GET on /v1, and the API's body comes back
unchanged (Report, never interpret, PRD 6.4). Nothing here names a tool, rule type, domain or
jurisdiction: tools.json says which path each tool calls and how its arguments map onto it.
Relative imports only, so the PyPI package can ship this module as `juriset_mcp.executor`.
"""

import json
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

# GET `url` with `headers`; returns the status, the response headers (lower-case names) and the
# body text. Raises on a network failure.
Fetch = Callable[[str, Mapping[str, str]], Awaitable[tuple[int, Mapping[str, str], str]]]

DOCS_URL = "https://juriset.dev/docs"
RULE_TYPES_PATH = "/v1/rule-types"
RULE_TYPES_TTL = 3600.0  # seconds; rule types change only with a registry migration


class UnknownToolError(LookupError):
    """A call to a tool that is not defined: a protocol error, not a tool result."""


@dataclass(frozen=True)
class Outcome:
    """A tool's result: the API's JSON body, or an error body in the API's own shape."""

    body: Any
    is_error: bool


def error(code: str, message: str, details: Mapping[str, Any] | None = None) -> Outcome:
    """An error in the API's shape (`{"error": {code, message, docs_url, details}}`), for
    problems found before the API answers."""
    body = {
        "error": {
            "code": code,
            "message": message,
            "docs_url": f"{DOCS_URL}/errors#{code}",
            "details": dict(details) if details else None,
        }
    }
    return Outcome(body, is_error=True)


def request_path(call: Mapping[str, Any], args: Mapping[str, Any]) -> str:
    """The path and query string for `args`, query parameters in definition order. Everything
    but unreserved characters (and `,` in queries, the list separator) is percent-encoded."""
    path: str = call["path"]
    query = []
    for name, spec in call["arguments"].items():
        if name not in args:
            continue
        value = args[name]
        text = ",".join(value) if spec["list"] else str(value)
        if spec["in"] == "path":
            path = path.replace("{" + spec["param"] + "}", quote(text, safe=""))
        else:
            query.append(f"{spec['param']}={quote(text, safe=',')}")
    return path + ("?" + "&".join(query) if query else "")


class Executor:
    """Runs tools against the /v1 API at `api_url`. The rule-type list (to fill an omitted
    `domain`) is cached for an hour."""

    def __init__(
        self,
        definitions: Mapping[str, Any],
        *,
        api_url: str,
        fetch: Fetch,
        user_agent: str,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.definitions = definitions
        self.api_url = api_url.rstrip("/")
        self._fetch = fetch
        self._user_agent = user_agent
        self._clock = clock
        self._tools = {t["name"]: t for t in definitions["tools"]}
        self._domains: tuple[float, dict[str, str]] | None = None

    def message(self, name: str, **values: str) -> str:
        text: str = self.definitions["messages"][name]
        for key, value in values.items():
            text = text.replace("{" + key + "}", value)
        return text

    async def call(
        self, tool: str, arguments: Mapping[str, Any] | None, *, api_key: str | None
    ) -> Outcome:
        """Run `tool`. `api_key` is sent as a bearer token when given; without one the API's
        keyless tier answers (PRD 14), and its refusals (`rate_limited`, `plan_required`) come
        back as the tool's error."""
        call = self.definitions["calls"].get(tool)
        if call is None:
            raise UnknownToolError(tool)
        args = dict(arguments or {})
        problem = self._problem(tool, call, args)
        if problem is not None:
            return error(
                "invalid_arguments",
                self.message("invalid_arguments", tool=tool, problem=problem),
                {"tool": tool, "problem": problem},
            )
        source = call["domain_from"]
        if source is not None and "domain" not in args:
            domains = await self._rule_type_domains(api_key)
            if isinstance(domains, Outcome):
                return domains
            slug = args[source]
            if slug not in domains:
                known = sorted(domains)
                return error(
                    "rule_type_not_found",
                    self.message("rule_type_not_found", rule_type=slug, known=", ".join(known)),
                    {"rule_type": slug, "rule_types": known},
                )
            args["domain"] = domains[slug]
        return await self._get(request_path(call, args), api_key)

    def _problem(self, tool: str, call: Mapping[str, Any], args: Mapping[str, Any]) -> str | None:
        """What is wrong with `args`, in words, or None. Values are checked by the API."""
        unknown = sorted(set(args) - set(call["arguments"]))
        if unknown:
            takes = ", ".join(call["arguments"])
            return f"unknown argument {', '.join(unknown)}; it takes {takes}"
        missing = [a for a in self._tools[tool]["inputSchema"].get("required", []) if a not in args]
        # `domain` is optional only because the executor can fill it from the rule type.
        if missing:
            return f"missing {', '.join(missing)}"
        for name, value in args.items():
            if call["arguments"][name]["list"]:
                if not (
                    isinstance(value, list) and value and all(isinstance(v, str) for v in value)
                ):
                    return f"{name} is a non-empty list of strings"
            elif isinstance(value, bool) or not isinstance(value, str | int):
                return f"{name} is a single value, not {type(value).__name__}"
        return None

    async def _rule_type_domains(self, api_key: str | None) -> dict[str, str] | Outcome:
        """Rule type slug -> domain, or the outcome of a failed read."""
        now = self._clock()
        if self._domains is not None and now - self._domains[0] < RULE_TYPES_TTL:
            return self._domains[1]
        outcome = await self._get(RULE_TYPES_PATH, api_key)
        if outcome.is_error:
            return outcome
        try:
            domains = {t["slug"]: t["domain"] for t in outcome.body["rule_types"]}
        except (KeyError, TypeError):
            return self._unavailable("unexpected /v1/rule-types response")
        self._domains = (now, domains)
        return domains

    async def _get(self, path: str, api_key: str | None) -> Outcome:
        """GET `path`: the API's JSON body, its error body, or `api_unavailable`."""
        headers = {"Accept": "application/json", "User-Agent": self._user_agent}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            status, response_headers, text = await self._fetch(self.api_url + path, headers)
        except Exception as exc:  # every network failure is the same answer to an agent
            return self._unavailable(f"network error, {type(exc).__name__}")
        try:
            body = json.loads(text)
        except ValueError:
            return self._unavailable(f"HTTP {status}, not JSON")
        if 200 <= status < 300:
            return Outcome(body, is_error=False)
        if isinstance(body, dict) and isinstance(body.get("error"), dict):
            retry = response_headers.get("retry-after", "")
            if status == 429 and retry.isdigit():
                # The agent sees the body, not the headers: say when to try again.
                details = body["error"].get("details") or {}
                body["error"]["details"] = {"retry_after_seconds": int(retry), **details}
            return Outcome(body, is_error=True)  # the API's own error, as it sent it
        return self._unavailable(f"HTTP {status}")

    def _unavailable(self, reason: str) -> Outcome:
        return error(
            "api_unavailable", self.message("api_unavailable", reason=reason), {"reason": reason}
        )
