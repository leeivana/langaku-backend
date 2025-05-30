from rest_framework.test import APITestCase
from ecsite.models import Item, User
from .helpers import generate_str, random_int
from rest_framework import status


ITEM_COUNT = 5
MAX_PRICE = 100
MIN_PRICE = 50
ITEMS_URL = "/api/v1/items/"


class TestItemAPI(APITestCase):
    def validate_items(self, items, arrType):
        for item in items:
            item_name = item["name"]
            original = getattr(self, arrType)[item_name]
            self.assertTrue(original)
            self.assertEqual(original.price, item["price"])
            self.assertEqual(original.quantity, item["quantity"])

    def create_item(self, min, max) -> dict:
        item_dict = {}
        for _ in range(ITEM_COUNT):
            name = generate_str()
            item = Item.objects.create(
                name=name,
                price=random_int(min, max),
                quantity=random_int(min, max),
            )
            item_dict[name] = item
        return item_dict

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client.login(username="testuser", password="password")

        self.cheaper_items = self.create_item(1, MIN_PRICE)
        self.expensive_items = self.create_item(MIN_PRICE + 1, MAX_PRICE)

    def test_search_items(self):
        response = self.client.get(ITEMS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 10)

    def test_search_items_filter_name(self):
        # Getting the first item to filter on
        first_item = list(self.cheaper_items.values())[0]
        response = self.client.get(ITEMS_URL, data={"name": first_item.name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["items"]
        self.assertEqual(len(items), 1)

        # Checking if price and quantity match
        result = items[0]
        self.assertEqual(result["price"], first_item.price)
        self.assertEqual(result["quantity"], first_item.quantity)

    def test_search_items_filter_max(self):
        response = self.client.get(ITEMS_URL, data={"max_price": 50})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["items"]
        self.assertEqual(len(items), ITEM_COUNT)

        self.validate_items(items, "cheaper_items")

    def test_search_item_filter_max_invalid(self):
        response = self.client.get(ITEMS_URL, data={"max_price": "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_items_filter_min(self):
        response = self.client.get(ITEMS_URL, data={"min_price": 50})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["items"]
        self.assertEqual(len(items), ITEM_COUNT)

        self.validate_items(items, "expensive_items")

    def test_search_item_filter_max_invalid(self):
        response = self.client.get(ITEMS_URL, data={"min_price": "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
