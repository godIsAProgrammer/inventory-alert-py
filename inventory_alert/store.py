from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from threading import RLock
from typing import Iterable

SKU_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,31}$")


@dataclass(frozen=True)
class Item:
    sku: str
    name: str
    stock: int
    reorder_level: int
    location: str = "main"

    @property
    def status(self) -> str:
        # 库存小于等于补货阈值时即进入 low 状态，便于运营直接拉取预警。
        return "low" if self.stock <= self.reorder_level else "ok"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status
        return data


class InventoryStore:
    def __init__(self, initial_items: Iterable[dict] | None = None):
        self._items: dict[str, Item] = {}
        self._lock = RLock()
        for item in initial_items or []:
            self.upsert(item)

    def upsert(self, payload: dict) -> Item:
        item = normalize_item(payload)
        with self._lock:
            self._items[item.sku] = item
        return item

    def list_items(self, status: str | None = None) -> list[Item]:
        with self._lock:
            items = sorted(self._items.values(), key=lambda item: item.sku)
        if status is None:
            return items
        if status not in {"low", "ok"}:
            raise ValueError("status must be low or ok")
        return [item for item in items if item.status == status]

    def get(self, sku: str) -> Item | None:
        with self._lock:
            return self._items.get(str(sku).upper())

    def adjust_stock(self, sku: str, delta: int, reason: str = "") -> Item:
        if not isinstance(delta, int):
            raise ValueError("delta must be an integer")
        with self._lock:
            current = self._items.get(str(sku).upper())
            if current is None:
                raise KeyError("item not found")
            next_stock = current.stock + delta
            if next_stock < 0:
                raise ValueError("stock cannot be negative")
            # reason 目前只做请求意图校验，不写入模型，后续可扩展为库存流水。
            _ = str(reason).strip()
            updated = Item(
                sku=current.sku,
                name=current.name,
                stock=next_stock,
                reorder_level=current.reorder_level,
                location=current.location,
            )
            self._items[current.sku] = updated
            return updated

    def alerts(self) -> list[Item]:
        return self.list_items(status="low")


def normalize_item(payload: dict) -> Item:
    if not isinstance(payload, dict):
        raise ValueError("item body must be an object")
    sku = str(payload.get("sku", "")).strip().upper()
    if not SKU_RE.match(sku):
        raise ValueError("sku must be 3-32 chars: uppercase letters, numbers, hyphen")
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("name is required")
    if len(name) > 80:
        raise ValueError("name must be at most 80 chars")
    stock = parse_non_negative_int(payload.get("stock"), "stock")
    reorder_level = parse_non_negative_int(payload.get("reorder_level"), "reorder_level")
    location = str(payload.get("location", "main")).strip() or "main"
    if len(location) > 40:
        raise ValueError("location must be at most 40 chars")
    return Item(sku=sku, name=name, stock=stock, reorder_level=reorder_level, location=location)


def parse_non_negative_int(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be a non-negative integer")
    if value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def create_default_store() -> InventoryStore:
    return InventoryStore(
        [
            {
                "sku": "MILK-1L",
                "name": "常温牛奶 1L",
                "stock": 8,
                "reorder_level": 10,
                "location": "A-01",
            },
            {
                "sku": "RICE-5KG",
                "name": "东北大米 5KG",
                "stock": 42,
                "reorder_level": 12,
                "location": "B-03",
            },
        ]
    )
