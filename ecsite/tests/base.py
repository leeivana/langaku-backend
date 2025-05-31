from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from ecsite.models import User, Item, Cart
from .helpers import generate_str, random_int

ITEM_COUNT = 5
ITEM_MAX_PRICE = 100
ITEM_MIN_PRICE = 50


class AuthenticatedTestCase(APITestCase):
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

        self.cheaper_items = self.create_item(2, ITEM_MIN_PRICE - 1)
        self.expensive_items = self.create_item(ITEM_MIN_PRICE + 1, ITEM_MAX_PRICE)
        self.cart = Cart.objects.create(user=self.user)
