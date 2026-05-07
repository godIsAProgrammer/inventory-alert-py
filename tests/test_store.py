import unittest

from inventory_alert.store import InventoryStore, normalize_item


class StoreTest(unittest.TestCase):
    def test_normalize_item_trims_and_uppercases_sku(self):
        item = normalize_item({"sku": " milk-1l ", "name": " 牛奶 ", "stock": 8, "reorder_level": 10})
        self.assertEqual(item.sku, "MILK-1L")
        self.assertEqual(item.name, "牛奶")
        self.assertEqual(item.status, "low")

    def test_rejects_invalid_sku(self):
        with self.assertRaisesRegex(ValueError, "sku must"):
            normalize_item({"sku": "xx", "name": "bad", "stock": 1, "reorder_level": 1})

    def test_rejects_negative_stock(self):
        with self.assertRaisesRegex(ValueError, "stock"):
            normalize_item({"sku": "GOOD-1", "name": "bad", "stock": -1, "reorder_level": 1})

    def test_lists_items_in_sku_order(self):
        store = InventoryStore([
            {"sku": "B-001", "name": "B", "stock": 9, "reorder_level": 1},
            {"sku": "A-001", "name": "A", "stock": 1, "reorder_level": 2},
        ])
        self.assertEqual([item.sku for item in store.list_items()], ["A-001", "B-001"])

    def test_filters_low_items(self):
        store = InventoryStore([
            {"sku": "LOW-1", "name": "Low", "stock": 1, "reorder_level": 2},
            {"sku": "OK-1", "name": "Ok", "stock": 3, "reorder_level": 2},
        ])
        self.assertEqual([item.sku for item in store.list_items(status="low")], ["LOW-1"])

    def test_adjust_stock_changes_status(self):
        store = InventoryStore([{"sku": "RICE-1", "name": "Rice", "stock": 3, "reorder_level": 2}])
        updated = store.adjust_stock("rice-1", -2, reason="sale")
        self.assertEqual(updated.stock, 1)
        self.assertEqual(updated.status, "low")

    def test_adjust_stock_rejects_negative_result(self):
        store = InventoryStore([{"sku": "RICE-1", "name": "Rice", "stock": 3, "reorder_level": 2}])
        with self.assertRaisesRegex(ValueError, "negative"):
            store.adjust_stock("RICE-1", -4)

    def test_missing_item_raises_key_error(self):
        store = InventoryStore()
        with self.assertRaises(KeyError):
            store.adjust_stock("NOPE-1", 1)


if __name__ == "__main__":
    unittest.main()
