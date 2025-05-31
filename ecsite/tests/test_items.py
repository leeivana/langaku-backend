from rest_framework import status
from .base import AuthenticatedTestCase, ITEM_COUNT
from .base import ITEM_MIN_PRICE
from ecsite.constants import NAME, MAX_PRICE, MIN_PRICE

ITEMS_URL = "/api/v1/items/"


class TestItemAPI(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()

    def validate_items(self, items, arrType):
        for item in items:
            item_name = item[NAME]
            original = getattr(self, arrType)[item_name]
            self.assertTrue(original)
            self.assertEqual(original.price, item["price"])
            self.assertEqual(original.quantity, item["quantity"])

    def test_search_items(self):
        response = self.client.get(ITEMS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 10)

    def test_search_items_filter_name(self):
        # Getting the first item to filter on
        first_item = list(self.cheaper_items.values())[0]
        response = self.client.get(ITEMS_URL, data={NAME: first_item.name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["items"]
        self.assertEqual(len(items), 1)

        # Checking if price and quantity match
        result = items[0]
        self.assertEqual(result["price"], first_item.price)
        self.assertEqual(result["quantity"], first_item.quantity)

    def test_search_items_filter_max(self):
        response = self.client.get(ITEMS_URL, data={MAX_PRICE: ITEM_MIN_PRICE})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["items"]
        self.assertEqual(len(items), ITEM_COUNT)

        self.validate_items(items, "cheaper_items")

    def test_search_item_filter_max_invalid(self):
        response = self.client.get(ITEMS_URL, data={MAX_PRICE: "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_items_filter_min(self):
        response = self.client.get(ITEMS_URL, data={MIN_PRICE: ITEM_MIN_PRICE})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["items"]
        self.assertEqual(len(items), ITEM_COUNT)

        self.validate_items(items, "expensive_items")

    def test_search_item_filter_max_invalid(self):
        response = self.client.get(ITEMS_URL, data={MIN_PRICE: "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
