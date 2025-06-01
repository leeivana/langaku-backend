from rest_framework import status
from .base import AuthenticatedTestCase
from ecsite.models import Cart, Item, IdempotencyKey
from ecsite.constants import (
    STATUS_SUCCESS,
    USER_ID,
    QUANTITY,
    ITEM_ID,
    IDEMPOTENCY_KEY,
    IDEMPOTENCY_KEY_HEADER,
    ERROR_MESSAGES,
)
from uuid import uuid4
from .constants import URL_MAP, CART_URL

UNASSOCIATED_ID = 123123123
INVALID_ID = "INVALID"


class TestCartsAPI(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()

    # Get carts test
    def test_get_carts(self):
        response = self.client.get(CART_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        carts = response.data["carts"]
        self.assertEqual(len(carts), 1)

    def test_create_cart_invalid_user_id(self):
        response = self.client.post(CART_URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], ERROR_MESSAGES["invalid_user_id"])

    def test_create_cart(self):
        response = self.client.post(CART_URL, data={"user_id": self.user.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["cart"]["items"]), 0)

    # Purchase cart tests
    def test_purchase_cart_no_idempotency_key(self):
        cart = self.create_and_return_cart()
        response = self.client.post(
            URL_MAP["purchase"](cart.id),
            data={USER_ID: self.user.id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"][IDEMPOTENCY_KEY][0],
            ERROR_MESSAGES["invalid_idempotency_key"],
        )

    def test_purchase_cart_no_user_id(self):
        response = self.client.post(
            URL_MAP["purchase"](UNASSOCIATED_ID),
            data={IDEMPOTENCY_KEY: str(uuid4())},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"][USER_ID][0],
            ERROR_MESSAGES["invalid_user_id"],
        )

    def test_purchase_cart_invalid_cart_id(self):
        response = self.client.post(
            URL_MAP["purchase"](UNASSOCIATED_ID),
            data={IDEMPOTENCY_KEY: str(uuid4()), USER_ID: self.user.id},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "No cart associated with provided Id")

    # Testing purchasing multiple (in-stock) items with idempotency_key in request body
    def test_purchase_cart_item(self):
        cart = self.create_and_return_cart()
        item = list(self.cheaper_items.values())[0]
        response = self.client.post(
            URL_MAP["add_item"](cart.id),
            data={USER_ID: self.user.id, QUANTITY: 1, ITEM_ID: item.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            URL_MAP["purchase"](cart.id),
            data={IDEMPOTENCY_KEY: str(uuid4()), USER_ID: self.user.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the cart is deleted
        with self.assertRaises(Cart.DoesNotExist):
            Cart.objects.get(user_id=self.user.id)

        updated_item = Item.objects.get(id=item.id)
        self.assertEqual(updated_item.quantity, item.quantity - 1)

    # Testing purchasing multiple (in-stock) items with Idempotency-Key header
    def test_purchase_cart_items(self):
        cart = self.create_and_return_cart()
        items = list(self.cheaper_items.values())
        for item in items:
            response = self.client.post(
                URL_MAP["add_item"](cart.id),
                data={USER_ID: self.user.id, QUANTITY: 1, ITEM_ID: item.id},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            URL_MAP["purchase"](cart.id),
            data={USER_ID: self.user.id},
            headers={IDEMPOTENCY_KEY_HEADER: str(uuid4())},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the cart is deleted
        with self.assertRaises(Cart.DoesNotExist):
            Cart.objects.get(user_id=self.user.id)

        for item in items:
            updated_item = Item.objects.get(id=item.id)
            self.assertEqual(updated_item.quantity, item.quantity - 1)

    def test_purchase_cart_reuse_idempotency_key(self):
        cart = self.create_and_return_cart()
        item = list(self.cheaper_items.values())[0]
        self.client.post(
            URL_MAP["add_item"](cart.id),
            data={USER_ID: self.user.id, QUANTITY: 1, ITEM_ID: item.id},
        )

        key_val = str(uuid4())
        response = self.client.post(
            URL_MAP["purchase"](cart.id),
            data={IDEMPOTENCY_KEY: key_val, USER_ID: self.user.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        idempotency_key = IdempotencyKey.objects.get(key=key_val)
        self.assertEqual(idempotency_key.status, STATUS_SUCCESS)
        self.assertEqual(idempotency_key.user, self.user)
        self.assertEqual(idempotency_key.response_data, response.data["response"])

        second_response = self.client.post(
            URL_MAP["purchase"](cart.id),
            data={IDEMPOTENCY_KEY: key_val, USER_ID: self.user.id},
        )

        self.assertEqual(response.data, second_response.data)
        # Checking that the item quantity only decremented by 1
        updated_item = Item.objects.get(id=item.id)
        self.assertEqual(updated_item.quantity, item.quantity - 1)

    def test_purchase_cart_item_no_stock(self):
        cart = self.create_and_return_cart()
        item = list(self.cheaper_items.values())[0]
        self.client.post(
            URL_MAP["add_item"](cart.id),
            data={USER_ID: self.user.id, QUANTITY: 1, ITEM_ID: item.id},
        )

        # Updating item quantity
        item.quantity = 0
        item.save()

        response = self.client.post(
            URL_MAP["purchase"](cart.id),
            data={IDEMPOTENCY_KEY: str(uuid4()), USER_ID: self.user.id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Item does not have enough stock")

    # Checking if transaction is cancelled / no changes are made if one of the items is out of stock
    def test_purchase_cart_items_no_stock(self):
        cart = self.create_and_return_cart()
        items = list(self.cheaper_items.values())
        for item in items:
            response = self.client.post(
                URL_MAP["add_item"](cart.id),
                data={USER_ID: self.user.id, QUANTITY: 1, ITEM_ID: item.id},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Updating item quantity
        first_item = items[0]
        first_item.quantity = 0
        first_item.save()

        response = self.client.post(
            URL_MAP["purchase"](cart.id),
            data={IDEMPOTENCY_KEY: str(uuid4()), USER_ID: self.user.id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Item does not have enough stock")
