"""Usage logging for Sage MCP Public.

Two Supabase tables (see migrations/0001_usage_logging.sql):
  * mcp_tool_calls — one row per MCP tool call (tool, arguments, client, latency)
  * mcp_http_log   — one row per HTTP request except /health

Railway only keeps ~7 days of logs, so this is the durable record for traffic
reporting. Writes are fire-and-forget: a logging failure never affects a request.
"""

import asyncio
import json
import logging
import time
from typing import Any

from server import database as db

logger = logging.getLogger("sage-mcp-public.usage")

_pending: set[asyncio.Task] = set()

SKIP_PATHS = {"/health"}
SCANNER_HINTS = (
    ".env", ".git", ".aws", "wp-", "php", ".yml", ".yaml", "config", "admin",
    "backup", ".bak", ".sql", "credentials", "actuator", "cgi-bin", ".ds_store",
)


def _fire(table: str, row: dict[str, Any]) -> None:
    async def _insert() -> None:
        try:
            client = await db.get_client()
            resp = await client.post(
                f"/{table}", content=json.dumps(row, default=str),
                headers={"Prefer": "return=minimal"},
            )
            if resp.status_code >= 300:
                logger.warning("usage insert into %s failed: %s %s",
                               table, resp.status_code, resp.text[:200])
        except Exception as e:  # never let logging break a request
            logger.warning("usage insert into %s errored: %s", table, e)

    try:
        task = asyncio.get_running_loop().create_task(_insert())
    except RuntimeError:
        return
    _pending.add(task)
    task.add_done_callback(_pending.discard)


def classify(path: str) -> str:
    p = path.lower()
    if p.startswith("/mcp"):
        return "mcp"
    if p.startswith("/.well-known") or p in ("/llms.txt", "/robots.txt", "/sitemap.xml"):
        return "discovery"
    if p in ("/", "/favicon.ico"):
        return "web"
    if any(h in p for h in SCANNER_HINTS):
        return "scanner"
    return "other"


def _header(headers: list[tuple[bytes, bytes]], name: bytes) -> str | None:
    for k, v in headers:
        if k.lower() == name:
            return v.decode("latin-1")
    return None


def _client_ip(scope: dict) -> str | None:
    headers = scope.get("headers") or []
    fwd = _header(headers, b"x-forwarded-for") or _header(headers, b"x-real-ip")
    if fwd:
        return fwd.split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else None


class UsageMiddleware:
    """Pure-ASGI middleware.

    * Rewrites ``/mcp/http`` → ``/mcp/http/`` so clients that omit the trailing
      slash (Claude does, every request) are served directly instead of via a
      307 round-trip that also broke expired-session recovery.
    * Logs every non-/health request to ``mcp_http_log`` at response start
      (so long-lived SSE streams are logged too).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        if scope.get("path") == "/mcp/http":
            scope = dict(scope)
            scope["path"] = "/mcp/http/"
            scope["raw_path"] = b"/mcp/http/"

        path = scope.get("path", "")
        if path in SKIP_PATHS:
            return await self.app(scope, receive, send)

        start = time.monotonic()
        headers = scope.get("headers") or []
        logged = False

        async def send_wrapper(message):
            nonlocal logged
            if message["type"] == "http.response.start" and not logged:
                logged = True
                _fire("mcp_http_log", {
                    "method": scope.get("method"),
                    "path": path[:500],
                    "query": (scope.get("query_string") or b"").decode("latin-1")[:500] or None,
                    "status": message.get("status"),
                    "duration_ms": int((time.monotonic() - start) * 1000),
                    "user_agent": (_header(headers, b"user-agent") or "")[:500] or None,
                    "ip": _client_ip(scope),
                    "host": _header(headers, b"host"),
                    "session_id": _header(headers, b"mcp-session-id"),
                    "traffic_class": classify(path),
                })
            await send(message)

        await self.app(scope, receive, send_wrapper)


def instrument_tool_calls(mcp) -> None:
    """Wrap FastMCP's tool manager so every tool call lands in mcp_tool_calls."""
    manager = mcp._tool_manager
    original = manager.call_tool

    async def call_tool(name, arguments, context=None, convert_result=False):
        start = time.monotonic()
        ok, err, result = True, None, None
        try:
            result = await original(name, arguments, context=context,
                                    convert_result=convert_result)
            return result
        except Exception as e:
            ok, err = False, f"{type(e).__name__}: {e}"[:1000]
            raise
        finally:
            row: dict[str, Any] = {
                "tool": name,
                "arguments": arguments or {},
                "ok": ok,
                "error": err,
                "duration_ms": int((time.monotonic() - start) * 1000),
            }
            try:
                row["result_bytes"] = len(json.dumps(result, default=str)) if result is not None else None
            except Exception:
                pass
            try:
                rc = context.request_context if context else None
                req = getattr(rc, "request", None)
                if req is not None and hasattr(req, "headers"):
                    row["user_agent"] = (req.headers.get("user-agent") or "")[:500] or None
                    row["session_id"] = req.headers.get("mcp-session-id")
                    fwd = req.headers.get("x-forwarded-for") or req.headers.get("x-real-ip")
                    row["ip"] = fwd.split(",")[0].strip() if fwd else (req.client.host if req.client else None)
                    row["transport"] = "streamable-http" if req.url.path.startswith("/mcp/http") else "sse"
                params = getattr(getattr(rc, "session", None), "client_params", None)
                info = getattr(params, "clientInfo", None)
                if info:
                    row["client_name"] = info.name
                    row["client_version"] = info.version
            except Exception as e:
                logger.debug("could not read request context: %s", e)
            _fire("mcp_tool_calls", row)

    manager.call_tool = call_tool
