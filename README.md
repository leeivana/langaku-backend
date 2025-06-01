# E-Commerce API with Python and Django

## Table of Contents
- [Setup](#setup)
- [API Design](#api-design)
  - [Item Listing](#item-listing)
  - [Create Cart](#create-cart)
  - [Add Item to Cart](#add-item-to-cart)
  - [Purchase Items in Cart](#purchase-items-in-cart)
- [System Design](#system-design)
  - [Option 1: Latest Stock and Price at Checkout](#option-1-latest-stock-and-price-at-checkout)
  - [Option 2: Price and Stock is Locked When Added](#option-2-price-and-stock-is-locked-when-added)
- [Case Study](#case-study)
  - [How Stock Fluctuations Are Handled](#how-stock-fluctuations-are-handled)
  - [How Price Fluctuations Are Handled](#how-price-fluctuations-are-handled)


## Setup

Load initial data

```
python manage.py init_data
```

Admin User

-   username: testuser
-   password: testpassword

## API Design

### Item Listing

#### API Endpoint: `GET {base_url}/api/v1/items`

Retrieves an array of items (id, name, price, quantity).

#### Possible Filters:

-   min_value (int)
-   max_value (int)
-   name (string)

#### Example Request:

`GET {base_url}/api/v1/items?min_value=500&max_value=1000`

#### Response

```json
{
    "items": [
        {
            "id": 1,
            "name": "Wine - Port Late Bottled Vintage",
            "price": 869,
            "quantity": 7
        },
        {
            "id": 2,
            "name": "Appetizer - Crab And Brie",
            "price": 4358,
            "quantity": 19
        },
        {
            "id": 3,
            "name": "Mussels - Frozen",
            "price": 1470,
            "quantity": 4
        }
    ]
}
```

### Create Cart

#### API Endpoint: `POST {base_url}/api/v1/cart/`

This endpoint creates a cart for a given user id.
If a cart already exists for the provided user id, the existing cart information will returned.
If not, the new created cart information will be returned.

#### Request

```json
{
    "user_id": int
}
```

#### Response

```json
{
    "cart": {
        "items": []
    }
}
```

### View Cart

#### API Endpoint: `GET {base_url}/api/v1/cart/{cart_id}`

This endpoint returns the cart data given a cart_id

#### Request

`GET {base_url}/api/v1/cart/{cart_id}`

#### Response

```json
{
    "cart": {
        "items": [1, 2, 3]
    }
}
```

### Add Item to Cart

#### API Endpoint: `POST {base_url}/api/v1/cart/{cart_id}/items`

This endpoint adds the specified item (referenced by item_id) with the specified quantity into the user's cart.
The below cases are handed:

-   If a user is adding an item that already exists in the cart
    -   The new total quantity is checked (existing + requested) to see if there is enough stock
-   If a user is adding a new item to the cart
    -   A new cart item instance will be created for the specified quantity and item (given there is enough stock)

#### Request

```json
{
    "user_id": int,
    // Quantity value must equal or greater than 1
    "quantity": int,
    "item_id": int
}
```

#### Response

```json
{
    "cart": {
        "items": [item_id]
    }
}
```

### Delete Item in Cart

#### API Endpoint: `DELETE {base_url}/api/v1/cart/{cart_id}/items/{item_id}`

This endpoint deletes the specified item_id from the cart (queried by cart_id).
If the user_id in the request does not match the user_id in the Cart, an error is returned.
The deleted cart data is returned.

#### Request

```json
{
    "user_id": int
}
```

#### Response

```json
{
    "cart": {
        "items": [item_id]
    },
}
```

### Purchase Items in Cart

#### API Endpoint: `POST {base_url}/api/v1/cart/{cart_id}/purchase`

This endpoint purchases all the items within the specified cart (derived from the cart_id within the URL).
An valid and unused idempotency key is required in either the headers (`Idempotency-Key`) or within the request data (`idempotency_key`).
If the idempotency key has been used previous, the previous response data will be returned.

A valid user_id is also required within the request body. This user id has to reference the owner of the cart.
The response returns the purchased cart item information

#### Request

```json
{
    "idempotency_key": str,
    "user_id": str
}
```

#### Response

```json
{
    "response": [
        {
            "item": 1,
            "quantity": 1
        }
    ]
}
```

## System Design

### Checkout Behaviour (Stock & Price Fluctuations)

When building out an e-commerce system, users may add items to their cart and delay the checkout process. During this period, the stock level of items and their price may change. This introduces key product decisions that should be made centering around the question of: **Should price and stock be guaranteed at checkout or reflect the latest information at checkout?**

Below are multiple approaches to go about this problem.

### Option 1: Latest Stock and Price at Checkout

At checkout, the system would query for the items in the cart and compare the latest stock and price. If there are price fluctuations or the stock has run out, the user would be notified.

#### Pros:

-   Users cannot exploit stale prices or stock
    -   e.x. A user would not be able to add items to their cart and purchase multiple years later
-   Ensures up-to-date pricing following business rules etc...
-   Accurate stock validation to prevent overselling
    -   Since the request stock amount is always validated against the latest stock count, there is not risk of overselling

#### Cons:

-   Additional UI prompts and modals to address price / stock change notifications
-   Users may be frustrated if they are purchasing and suddenly the stock has depleted or the price has suddenly increased

### Option 2: Price and stock is locked when added

At checkout, the system would lock in the price and stock (quantity) for a certain period of time after the user adds it to their cart.

#### Pros:

-   Guarantees stock and price for users, improved user experience
-   Stock and price guarantee for a locked period of time can increase customer turnaround
    -   Users are incentivized to buy quicker as their stock and price are guaranteed for a period of time

#### Cons:

-   More implementation work on the backend to lock stock and price, release lock and price after a certain duration
-   Inactive carts can fluctuate item stock inventory
    -   If multiple people add items to their cart and do not check out, the remaining stock count is inaccurate

## Case Study

The current implementation utilizes Option 1 (Latest stock & price at checkout).

## Reasoning

Utilizing Option 1 and validating stock and price during the time of purchase ensures:

-   Data integrity: Stock is never oversold
-   Simplicity: This is one of the most simpliest approaches that allows data consistency in regards to inventory levels and pricing

## Approach

Within the `purchase()` method of `CartViewSet`, `transaction.atomic` (atomic transaction) is utilized to ensure atominicity. Therefore, if any database call fails or errors are returned, the entire transaction is rolledback. This prevents partial updates / purchases.

`select_for_update()` is also used to lock `CartItem` rows to allow concurrent safe stock checking.

## How stock fluctuations are handled

In the current implementation of the cart purchasing logic, the stock is validated at the time of checkout.

-   `select_for_update()` is used to lock relavent `CartItem` rows to check quantity
-   If a item's `quantity` is less than the request amount, an error is returned and the entire transaction is rolledback / aborted

## How price fluctuations are handled

The current implementation of cart purchasing does not support price fluctuations. This is mainly because there currently is no way to update prices in the system. However, price fluctuations during checkout can be easily checked by:

-   Storing the purchase price into the `CartItem`
-   Validating price when item was added to cart to current price of the item within the database

## Future Improvements

-   Price flucutation alert (deviating between cart item price and item price)
-   Pagination / limits for item search endpoint
