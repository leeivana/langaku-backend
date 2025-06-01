# Request Constants
USER_ID = "user_id"
ITEM_ID = "item_id"
CART_ID = "cart_id"
QUANTITY = "quantity"
NAME = "name"
MIN_PRICE = "min_price"
MAX_PRICE = "max_price"

# Idempotency Related Constants
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
IDEMPOTENCY_KEY = "idempotency_key"

STATUS_SUCCESS = "success"
STATUS_PENDING = "pending"
STATUS_FAILED = "failed"

STATUS_CHOICES = [
    (STATUS_SUCCESS, "Success"),
    (STATUS_PENDING, "Pending"),
    (STATUS_FAILED, "Failed"),
]

ERROR_MESSAGES = {
    "invalid_item_id": "Valid Item Id is required",
    "item_does_not_exist": "No item associated with provided Id",
    "invalid_user_id": "Valid User Id is required",
    "user_does_not_exist": "No user associated with provided Id",
    "invalid_cart_id": "Valid Cart Id is required",
    "cart_does_not_exist": "No cart associated with provided Id",
    "invalid_quantity": "Valid quantity is required",
    "invalid_idempotency_key": "Valid idempotency key is required",
    "quantity_unavailable": "Requested quantity is not available",
    "invalid_min_price": "Min price must be a valid integer",
    "invalid_max_price": "Max price must be a valid integer",
    "no_cart_items": "Cart does not have any items",
}
