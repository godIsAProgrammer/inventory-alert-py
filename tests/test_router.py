import io
import json
import unittest

from inventory_alert.router import InventoryRouter
from inventory_alert.store import InventoryStore


class FakeHandler:
    def __init__(self, method, path, body=None):
        self.command = method
        self.path = path
        raw = json.dumps(body).encode("utf-8") if body is not None else b""
        self.headers = {"content-length": str(len(raw))}
        self.rfile = io.BytesIO(raw)
        self.wfile = io.BytesIO()
        self.status = None
        self.response_headers = []

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        pass

    @property
    def json_body(self):
        return json.loads(self.wfile.getvalue().decode("utf-8"))


class RouterTest(unittest.TestCase):
    def route(self, method, path, body=None, store=None):
        handler = FakeHandler(method, path, body)
        InventoryRouter(store or InventoryStore()).handle(handler)
        return handler

    def test_health_endpoint(self):
        response = self.route("GET", "/health")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.json_body, {"ok": True})

    def test_create_item_and_list_alerts(self):
        store = InventoryStore()
        created = self.route(
            "POST",
            "/items",
            {"sku": "MILK-1L", "name": "Milk", "stock": 8, "reorder_level": 10},
            store,
        )
        alerts = self.route("GET", "/alerts", store=store)
        self.assertEqual(created.status, 201)
        self.assertEqual(alerts.json_body["count"], 1)
        self.assertEqual(alerts.json_body["alerts"][0]["status"], "low")

    def test_list_filters_status(self):
        store = InventoryStore([
            {"sku": "LOW-1", "name": "Low", "stock": 1, "reorder_level": 2},
            {"sku": "OK-1", "name": "Ok", "stock": 3, "reorder_level": 2},
        ])
        response = self.route("GET", "/items?status=ok", store=store)
        self.assertEqual([item["sku"] for item in response.json_body["items"]], ["OK-1"])

    def test_invalid_status_returns_400(self):
        response = self.route("GET", "/items?status=missing")
        self.assertEqual(response.status, 400)
        self.assertIn("status", response.json_body["error"])

    def test_patch_stock(self):
        store = InventoryStore([{"sku": "RICE-1", "name": "Rice", "stock": 3, "reorder_level": 2}])
        response = self.route("PATCH", "/items/RICE-1/stock", {"delta": -2, "reason": "sale"}, store)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.json_body["item"]["stock"], 1)
        self.assertEqual(response.json_body["item"]["status"], "low")

    def test_patch_missing_item_returns_404(self):
        response = self.route("PATCH", "/items/NOPE-1/stock", {"delta": 1})
        self.assertEqual(response.status, 404)

    def test_invalid_json_shape_returns_400(self):
        handler = FakeHandler("POST", "/items", body=[])
        InventoryRouter().handle(handler)
        self.assertEqual(handler.status, 400)
        self.assertIn("object", handler.json_body["error"])


if __name__ == "__main__":
    unittest.main()
