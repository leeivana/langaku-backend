from rest_framework import status
from .base import AuthenticatedTestCase
from ecsite.models import Cart, Item, IdempotencyKey
from ecsite.constants import STATUS_SUCCESS
from uuid import uuid4

CART_BASE_URL = "/api/v1/cart/"
UNASSOCIATED_ID = 123123123
INVALID_ID = "INVALID"


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
            data={"user_id": self.user.id, "quantity": INVALID_ID},
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
            data={"user_id": self.user.id, "quantity": 1, "item_id": UNASSOCIATED_ID},
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

        cart = Cart.objects.get(user_id=self.user.id)
        self.assertTrue(cart.items.exists())

    def test_add_cart_invalid_quantity(self):
        pass

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
            data={"user_id": INVALID_ID},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Valid User Id is required")

    def test_delete_cart_item_invalid_item(self):
        response = self.client.delete(
            f"{CART_BASE_URL}delete_item/",
            data={"user_id": self.user.id, "item_id": INVALID_ID},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Valid Item Id is required")

    def test_delete_cart_item_no_cart(self):
        response = self.client.delete(
            f"{CART_BASE_URL}delete_item/",
            data={"user_id": UNASSOCIATED_ID, "item_id": UNASSOCIATED_ID},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Cart does not exist for user")

    def test_delete_cart_item_incorrect_item(self):
        response = self.client.delete(
            f"{CART_BASE_URL}delete_item/",
            data={"user_id": self.user.id, "item_id": UNASSOCIATED_ID},
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

    # Purchase cart tests
    def test_purchase_cart_no_idempotency_key(self):
        response = self.client.post(
            f"{CART_BASE_URL}purchase/",
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Idempotency key is required")

    def test_purchase_cart_no_user_id(self):
        response = self.client.post(
            f"{CART_BASE_URL}purchase/",
            data={"idempotency_key": uuid4()},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "User Id is required")

    def test_purchase_cart_invalid_user_id(self):
        response = self.client.post(
            f"{CART_BASE_URL}purchase/",
            data={"idempotency_key": uuid4(), "user_id": UNASSOCIATED_ID},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "User does not exist")

    # Testing purchasing multiple (in-stock) items with idempotency_key in request body
    def test_purchase_cart_item(self):
        item = list(self.cheaper_items.values())[0]
        response = self.client.post(
            f"{CART_BASE_URL}add/",
            data={"user_id": self.user.id, "quantity": 1, "item_id": item.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            f"{CART_BASE_URL}purchase/",
            data={"idempotency_key": uuid4(), "user_id": self.user.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the cart is deleted
        with self.assertRaises(Cart.DoesNotExist):
            Cart.objects.get(user_id=self.user.id)

        updated_item = Item.objects.get(id=item.id)
        self.assertEqual(updated_item.quantity, item.quantity - 1)

    # Testing purchasing multiple (in-stock) items with Idempotency-Key header
    def test_purchase_cart_items(self):
        items = list(self.cheaper_items.values())
        for item in items:
            response = self.client.post(
                f"{CART_BASE_URL}add/",
                data={"user_id": self.user.id, "quantity": 1, "item_id": item.id},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            f"{CART_BASE_URL}purchase/",
            data={"user_id": self.user.id},
            headers={"Idempotency-Key": uuid4()},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the cart is deleted
        with self.assertRaises(Cart.DoesNotExist):
            Cart.objects.get(user_id=self.user.id)

        for item in items:
            updated_item = Item.objects.get(id=item.id)
            self.assertEqual(updated_item.quantity, item.quantity - 1)

    def test_purchase_cart_reuse_idempotency_key(self):
        item = list(self.cheaper_items.values())[0]
        self.client.post(
            f"{CART_BASE_URL}add/",
            data={"user_id": self.user.id, "quantity": 1, "item_id": item.id},
        )

        key_val = uuid4()
        response = self.client.post(
            f"{CART_BASE_URL}purchase/",
            data={"idempotency_key": key_val, "user_id": self.user.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        idempotency_key = IdempotencyKey.objects.get(key=key_val)
        self.assertEqual(idempotency_key.status, STATUS_SUCCESS)
        self.assertEqual(idempotency_key.user, self.user)
        self.assertEqual(idempotency_key.response_data, response.data["response"])

        second_response = self.client.post(
            f"{CART_BASE_URL}purchase/",
            data={"idempotency_key": key_val, "user_id": self.user.id},
        )

        self.assertEqual(response.data, second_response.data)
        # Checking that the item quantity only decremented by 1
        updated_item = Item.objects.get(id=item.id)
        self.assertEqual(updated_item.quantity, item.quantity - 1)

    def test_purchase_cart_item_no_stock(self):
        item = list(self.cheaper_items.values())[0]
        self.client.post(
            f"{CART_BASE_URL}add/",
            data={"user_id": self.user.id, "quantity": 1, "item_id": item.id},
        )

        # Updating item quantity
        item.quantity = 0
        item.save()

        response = self.client.post(
            f"{CART_BASE_URL}purchase/",
            data={"idempotency_key": uuid4(), "user_id": self.user.id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Item does not have enough stock")

    # Checking if transaction is cancelled / no changes are made if one of the items is out of stock
    def test_purchase_cart_items_no_stock(self):
        items = list(self.cheaper_items.values())
        for item in items:
            response = self.client.post(
                f"{CART_BASE_URL}add/",
                data={"user_id": self.user.id, "quantity": 1, "item_id": item.id},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Updating item quantity
        first_item = items[0]
        first_item.quantity = 0
        first_item.save()

        response = self.client.post(
            f"{CART_BASE_URL}purchase/",
            data={"idempotency_key": uuid4(), "user_id": self.user.id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Item does not have enough stock")
