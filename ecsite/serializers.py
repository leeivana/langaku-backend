from rest_framework import serializers
from .models import CartItem, Item, Cart, IdempotencyKey, User


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ["id", "name", "price", "quantity"]


class IdempotencyKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = IdempotencyKey
        fields = ["key", "user", "created_at", "response_data", "status"]


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["item", "quantity"]


class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = ["items"]


class AddCartItemSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        error_messages={
            "required": "Valid User Id is required",
            "does_not_exist": "No user associated with provided Id",
        },
    )
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(),
        error_messages={
            "required": "Valid Item Id is required",
            "does_not_exist": "No item associated with provided Id",
        },
    )
    cart_id = serializers.PrimaryKeyRelatedField(
        queryset=Cart.objects.all(),
        error_messages={
            "required": "Valid Cart Id is required",
            "does_not_exist": "No cart associated with provided Id",
        },
    )
    quantity = serializers.IntegerField(
        min_value=1,
        error_messages={"required": "Valid quantity is required"},
    )


class PurchaseCartSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(
        max_length=100,
        error_messages={
            "required": "Valid idempotency key is required",
            "null": "Valid idempotency key is required",
        },
    )
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        error_messages={
            "required": "Valid User Id is required",
            "does_not_exist": "No user associated with provided Id",
        },
    )
    cart_id = serializers.IntegerField(
        error_messages={
            "required": "Valid Cart Id is required",
            "does_not_exist": "No cart associated with provided Id",
        },
    )
