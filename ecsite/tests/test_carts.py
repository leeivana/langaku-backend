from rest_framework import status
from .base import AuthenticatedTestCase

CART_BASE_URL = "/api/v1/cart/"


class TestCartsAPI(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()

    # Get carts test
    def test_get_carts(self):
        response = self.client.get(CART_BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        carts = response.data["carts"]
        self.assertEqual(len(carts), 1)

    # Add card item tests
    def test_add_cart_item_empty_payload(self):
        response = self.client.post(f"{CART_BASE_URL}add/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Valid User Id is required")

    def test_add_cart_item_only_user_id(self):
        response = self.client.post(
            f"{CART_BASE_URL}add/", data={"user_id": self.user.id}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Quantity is required")

    def test_add_cart_item_invalid_quantity(self):
        response = self.client.post(
            f"{CART_BASE_URL}add/",
            data={"user_id": self.user.id, "quantity": "INVALID"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Quantity is required")

    def test_add_cart_item_negative_quantity(self):
        response = self.client.post(
            f"{CART_BASE_URL}add/",
            data={"user_id": self.user.id, "quantity": -10},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Quantity must be a positive integer")

    def test_add_cart_item_empty_item_id(self):
        response = self.client.post(
            f"{CART_BASE_URL}add/",
            data={"user_id": self.user.id, "quantity": 1},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Valid Item Id is required")

    def test_add_cart_item_invalid_item_id(self):
        response = self.client.post(
            f"{CART_BASE_URL}add/",
            data={"user_id": self.user.id, "quantity": 1, "item_id": 123123123},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Item not found")

    def test_add_cart_item(self):
        item = list(self.cheaper_items.values())[0]
        response = self.client.post(
            f"{CART_BASE_URL}add/",
            data={"user_id": self.user.id, "quantity": 1, "item_id": item.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_items = response.data["cart"]["items"]
        self.assertEqual(len(cart_items), 1)
        self.assertEqual(cart_items[0], item.id)

    def test_add_cart_items(self):
        items = list(self.cheaper_items.values())
        for item in items:
            response = self.client.post(
                f"{CART_BASE_URL}add/",
                data={"user_id": self.user.id, "quantity": 1, "item_id": item.id},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(CART_BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_items = response.data["carts"][0]["items"]

        for item in items:
            self.assertTrue(item.id in cart_items)

    def test_add_cart_item_invalid_quantity(self):
        item = list(self.cheaper_items.values())[0]
        response = self.client.post(
            f"{CART_BASE_URL}add/",
            data={
                "user_id": self.user.id,
                "quantity": item.quantity + 1,
                "item_id": item.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Requested quantity is not available")

    # Delete cart item test
    def test_delete_cart_item_invalid_user(self):
        response = self.client.delete(
            f"{CART_BASE_URL}delete_item/",
            data={"user_id": "INVALID"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Valid User Id is required")

    def test_delete_cart_item_invalid_item(self):
        response = self.client.delete(
            f"{CART_BASE_URL}delete_item/",
            data={"user_id": self.user.id, "item_id": "INVALID"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Valid Item Id is required")

    def test_delete_cart_item_no_cart(self):
        response = self.client.delete(
            f"{CART_BASE_URL}delete_item/",
            data={"user_id": 123, "item_id": 123},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Cart does not exist for user")

    def test_delete_cart_item_incorrect_item(self):
        response = self.client.delete(
            f"{CART_BASE_URL}delete_item/",
            data={"user_id": self.user.id, "item_id": 123},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Cart item does not exist")

    def test_delete_cart_item(self):
        item = list(self.cheaper_items.values())[0]
        response = self.client.post(
            f"{CART_BASE_URL}add/",
            data={"user_id": self.user.id, "quantity": 1, "item_id": item.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_items = response.data["cart"]["items"]
        self.assertEqual(len(cart_items), 1)

        response = self.client.delete(
            f"{CART_BASE_URL}delete_item/",
            data={"user_id": self.user.id, "item_id": item.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_items = response.data["cart"]["items"]
        self.assertEqual(len(cart_items), 0)
