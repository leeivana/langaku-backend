CART_URL = "/api/v1/cart/"
ITEMS_URL = "/api/v1/items/"

URL_MAP = {
    "purchase": lambda cart_id: f"{CART_URL}{cart_id}/purchase/",
    "get": lambda cart_id: f"{CART_URL}{cart_id}/",
    "add_item": lambda cart_id: f"{CART_URL}{cart_id}/items/",
    "delete_item": lambda cart_id, item_id: f"{CART_URL}{cart_id}/items/{item_id}/",
}
