from rest_framework import serializers
from .models import CartItem, Item, Cart, IdempotencyKey, User
from .constants import ERROR_MESSAGES


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
            "required": ERROR_MESSAGES["invalid_user_id"],
            "does_not_exist": ERROR_MESSAGES["user_does_not_exist"],
        },
    )
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(),
        error_messages={
            "required": ERROR_MESSAGES["invalid_item_id"],
            "does_not_exist": ERROR_MESSAGES["item_does_not_exist"],
        },
    )
    cart_id = serializers.PrimaryKeyRelatedField(
        queryset=Cart.objects.all(),
        error_messages={
            "required": ERROR_MESSAGES["invalid_cart_id"],
            "does_not_exist": ERROR_MESSAGES["cart_does_not_exist"],
        },
    )
    quantity = serializers.IntegerField(
        min_value=1,
        error_messages={"required": ERROR_MESSAGES["invalid_quantity"]},
    )


class PurchaseCartSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(
        max_length=100,
        error_messages={
            "required": ERROR_MESSAGES["invalid_idempotency_key"],
            "null": ERROR_MESSAGES["invalid_idempotency_key"],
        },
    )
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        error_messages={
            "required": ERROR_MESSAGES["invalid_user_id"],
            "does_not_exist": ERROR_MESSAGES["user_does_not_exist"],
        },
    )
    cart_id = serializers.IntegerField(
        error_messages={
            "required": ERROR_MESSAGES["invalid_cart_id"],
            "does_not_exist": ERROR_MESSAGES["cart_does_not_exist"],
        },
    )
