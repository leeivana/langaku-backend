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
    ITEM_ID: "Valid Item Id is required",
    USER_ID: "Valid User Id is required",
}
