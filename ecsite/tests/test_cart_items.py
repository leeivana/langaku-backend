from rest_framework import status
from .base import AuthenticatedTestCase
from ecsite.models import Cart, Item, IdempotencyKey
from ecsite.constants import (
    USER_ID,
    QUANTITY,
    ITEM_ID,
    ERROR_MESSAGES,
)

CART_BASE_URL = "/api/v1/cart/"
UNASSOCIATED_ID = 123123123
INVALID_ID = "INVALID"


class TestCartItemsAPI(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()

    def test_add_cart_item_empty_payload(self):
        cart = self.create_and_return_cart()

        response = self.client.post(f"{CART_BASE_URL}{cart.id}/items/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(USER_ID, response.data["error"])
        self.assertEqual(
            response.data["error"][USER_ID][0],
            ERROR_MESSAGES["invalid_user_id"],
        )

    def test_add_cart_item_only_user_id(self):
        cart = self.create_and_return_cart()

        response = self.client.post(
            f"{CART_BASE_URL}{cart.id}/items/", data={USER_ID: self.user.id}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(ITEM_ID, response.data["error"])
        self.assertEqual(
            response.data["error"][ITEM_ID][0],
            ERROR_MESSAGES["invalid_item_id"],
        )

    def test_add_cart_item_invalid_quantity(self):
        cart = self.create_and_return_cart()

        response = self.client.post(
            f"{CART_BASE_URL}{cart.id}/items/",
            data={USER_ID: self.user.id, QUANTITY: INVALID_ID},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Quantity is required")

    def test_add_cart_item_negative_quantity(self):
        cart = self.create_and_return_cart()

        response = self.client.post(
            f"{CART_BASE_URL}{cart.id}/items/",
            data={USER_ID: self.user.id, QUANTITY: -10},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(QUANTITY, response.data["error"])
        self.assertEqual(
            response.data["error"][QUANTITY][0],
            "Ensure this value is greater than or equal to 1.",
        )

    def test_add_cart_item_empty_item_id(self):
        cart = self.create_and_return_cart()

        response = self.client.post(
            f"{CART_BASE_URL}{cart.id}/items/",
            data={USER_ID: self.user.id, QUANTITY: 1},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(ITEM_ID, response.data["error"])
        self.assertEqual(
            response.data["error"][ITEM_ID][0],
            ERROR_MESSAGES["invalid_item_id"],
        )

    def test_add_cart_item_invalid_item_id(self):
        cart = self.create_and_return_cart()

        response = self.client.post(
            f"{CART_BASE_URL}{cart.id}/items/",
            data={USER_ID: self.user.id, QUANTITY: 1, ITEM_ID: UNASSOCIATED_ID},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn(ITEM_ID, response.data["error"])
        self.assertEqual(
            response.data["error"][ITEM_ID][0],
            ERROR_MESSAGES["item_does_not_exist"],
        )

    def test_add_cart_item(self):
        cart = self.create_and_return_cart()

        item = list(self.cheaper_items.values())[0]
        response = self.client.post(
            f"{CART_BASE_URL}{cart.id}/items/",
            data={USER_ID: self.user.id, QUANTITY: 1, ITEM_ID: item.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_items = response.data["cart"]["items"]
        self.assertEqual(len(cart_items), 1)
        self.assertEqual(cart_items[0], item.id)

        cart = Cart.objects.get(user_id=self.user.id)
        self.assertTrue(cart.items.exists())

    def test_add_cart_items(self):
        cart = self.create_and_return_cart()

        items = list(self.cheaper_items.values())
        for item in items:
            response = self.client.post(
                f"{CART_BASE_URL}{cart.id}/items/",
                data={USER_ID: self.user.id, QUANTITY: 1, ITEM_ID: item.id},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(CART_BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_items = response.data["carts"][0]["items"]

        for item in items:
            self.assertTrue(item.id in cart_items)

    def test_add_cart_item_invalid_quantity(self):
        cart = self.create_and_return_cart()

        item = list(self.cheaper_items.values())[0]
        response = self.client.post(
            f"{CART_BASE_URL}{cart.id}/items/",
            data={
                USER_ID: self.user.id,
                QUANTITY: item.quantity + 1,
                ITEM_ID: item.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"],
            ERROR_MESSAGES["quantity_unavailable"],
        )

    # Delete cart item test
    def test_delete_cart_item_invalid_user(self):
        cart = self.create_and_return_cart()

        response = self.client.delete(
            f"{CART_BASE_URL}{cart.id}/items/{UNASSOCIATED_ID}/",
            data={USER_ID: INVALID_ID},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"],
            ERROR_MESSAGES["invalid_user_id"],
        )

    def test_delete_cart_item_invalid_item(self):
        cart = self.create_and_return_cart()

        response = self.client.delete(
            f"{CART_BASE_URL}{cart.id}/items/{INVALID_ID}/",
            data={USER_ID: self.user.id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"],
            ERROR_MESSAGES["invalid_item_id"],
        )

    def test_delete_cart_item_no_cart(self):
        response = self.client.delete(
            f"{CART_BASE_URL}{UNASSOCIATED_ID}/items/{UNASSOCIATED_ID}/",
            data={USER_ID: UNASSOCIATED_ID},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data["error"],
            ERROR_MESSAGES["cart_does_not_exist"],
        )

    def test_delete_cart_item_incorrect_item(self):
        cart = self.create_and_return_cart()

        cart = Cart.objects.get(user=self.user)
        response = self.client.delete(
            f"{CART_BASE_URL}{cart.id}/items/{UNASSOCIATED_ID}/",
            data={USER_ID: self.user.id},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], ERROR_MESSAGES["item_does_not_exist"])

    def test_delete_cart_item(self):
        cart = self.create_and_return_cart()
        item = list(self.cheaper_items.values())[0]
        response = self.client.post(
            f"{CART_BASE_URL}{cart.id}/items/",
            data={USER_ID: self.user.id, QUANTITY: 1, ITEM_ID: item.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_items = response.data["cart"]["items"]
        self.assertEqual(len(cart_items), 1)

        response = self.client.delete(
            f"{CART_BASE_URL}{cart.id}/items/{item.id}/",
            data={USER_ID: self.user.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_items = response.data["cart"]["items"]
        self.assertEqual(len(cart_items), 0)
