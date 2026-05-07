from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

from .store import InventoryStore, create_default_store


class InventoryRouter:
    def __init__(self, store: InventoryStore | None = None):
        self.store = store or create_default_store()

    def handle(self, handler) -> None:
        parsed = urlparse(handler.path)
        method = handler.command

        if method == "GET" and parsed.path == "/health":
            return send_json(handler, 200, {"ok": True})

        if method == "GET" and parsed.path == "/items":
            params = parse_qs(parsed.query)
            status = first(params, "status")
            try:
                items = [item.to_dict() for item in self.store.list_items(status=status)]
            except ValueError as error:
                return send_json(handler, 400, {"error": str(error)})
            return send_json(handler, 200, {"items": items})

        if method == "GET" and parsed.path == "/alerts":
            alerts = [item.to_dict() for item in self.store.alerts()]
            return send_json(handler, 200, {"alerts": alerts, "count": len(alerts)})

        if method == "POST" and parsed.path == "/items":
            try:
                item = self.store.upsert(read_json(handler))
            except ValueError as error:
                return send_json(handler, 400, {"error": str(error)})
            return send_json(handler, 201, {"item": item.to_dict()})

        stock_match = match_stock_path(parsed.path)
        if method == "PATCH" and stock_match:
            try:
                payload = read_json(handler)
                item = self.store.adjust_stock(
                    stock_match,
                    payload.get("delta"),
                    reason=payload.get("reason", ""),
                )
            except KeyError:
                return send_json(handler, 404, {"error": "item not found"})
            except ValueError as error:
                return send_json(handler, 400, {"error": str(error)})
            return send_json(handler, 200, {"item": item.to_dict()})

        return send_json(handler, 404, {"error": "not found"})


def first(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    return values[0] if values else None


def match_stock_path(path: str) -> str | None:
    prefix = "/items/"
    suffix = "/stock"
    if path.startswith(prefix) and path.endswith(suffix):
        sku = path[len(prefix) : -len(suffix)]
        return sku or None
    return None


def read_json(handler) -> dict:
    length = int(handler.headers.get("content-length", "0") or "0")
    if length > 100_000:
        raise ValueError("request body is too large")
    raw = handler.rfile.read(length).decode("utf-8") if length else "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid json") from exc
    if not isinstance(payload, dict):
        raise ValueError("json body must be an object")
    return payload


def send_json(handler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    handler.send_response(status)
    handler.send_header("content-type", "application/json; charset=utf-8")
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
