from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
)
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.management import call_command
from django.db import transaction
from .models import Item, Cart, CartItem, User, UserPurchaseRecord, IdempotencyKey
from .serializers import (
    ItemSerializer,
    CartSerializer,
    IdempotencyKeySerializer,
    CartItemSerializer,
)
from .constants import (
    USER_ID,
    CART_ID,
    ITEM_ID,
    IDEMPOTENCY_KEY_HEADER,
    IDEMPOTENCY_KEY,
    QUANTITY,
    PRODUCT_ID,
    NAME,
    MIN_PRICE,
    MAX_PRICE,
    STATUS_SUCCESS,
    STATUS_FAILED,
    STATUS_PENDING,
)


def validate_integer(val) -> int:
    try:
        val = int(val)
    except (ValueError, TypeError):
        # Catching for value error and type error
        # Type error if value is incompatible
        # Value error if value cannot be converted
        return None

    return val


# Disable CSRF check for this assigment
class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


@api_view(["POST"])
def initialize_data(request):
    try:
        file_name = request.data.get("file", "MOCK_DATA.json")
        print(f"Initializing data from {file_name}")
        call_command("init_data", file=file_name)

        return Response(
            {"message": f"Data initialized successfully from {file_name}"},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ItemViewSet(viewsets.ViewSet):
    def list(self, request):
        # Getting name, min price and max price from query params
        name = request.query_params.get(NAME)
        min_price_raw = request.query_params.get(MIN_PRICE)
        min_price = validate_integer(min_price_raw)
        if min_price is None and min_price_raw:
            return Response(
                {"error": "Min price must be a valid integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        max_price_raw = request.query_params.get(MAX_PRICE)
        max_price = validate_integer(max_price_raw)
        if max_price is None and max_price_raw:
            return Response(
                {"error": "Max price must be a valid integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items = Item.objects.all()

        if name:
            items = items.filter(name__icontains=name)

        if min_price:
            items = items.filter(price__gte=min_price)

        if max_price:
            items = items.filter(price__lte=max_price)

        serializer = ItemSerializer(items, many=True)
        return Response({"items": serializer.data}, status=status.HTTP_200_OK)


class CartViewSet(viewsets.ViewSet):
    authentication_classes = [CsrfExemptSessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request, cart_id=None):
        if not cart_id:
            return Response(
                {"error": "Cart Id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        cart_id = validate_integer(cart_id)
        if cart_id is None:
            return Response(
                {"error": "Invalid Cart Id"}, status=status.HTTP_400_BAD_REQUEST
            )

        cart_items = CartItem.objects.filter(cart_id=cart_id)
        if not cart_items.exists():
            return Response(
                {"error": "No associated cart items"}, status=status.HTTP_404_NOT_FOUND
            )

        response = []
        for cart_item in cart_items:
            product = cart_item.item
            item_data = {
                "cart_item_id": cart_item.id,
                "name": product.name,
                "quantity": product.quantity,
                "requested_quantity": cart_item.quantity,
                "price": product.price,
                # is_out_of_stock is defined by whether or not the requested quantity is available
                "is_out_of_stock": product.quantity < cart_item.quantity,
            }
            response.append(item_data)

        return Response({"response": response}, status=status.HTTP_200_OK)

    @csrf_exempt
    @action(detail=False, methods=["delete"])
    def delete_item(self, request):
        cart_id = validate_integer(request.data.get(CART_ID))
        if cart_id is None:
            return Response(
                {"error": "Valid Cart Id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = validate_integer(request.data.get(USER_ID))
        if user_id is None:
            return Response(
                {"error": "Valid User Id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item_id = validate_integer(request.data.get(ITEM_ID))
        if item_id is None:
            return Response(
                {"error": "Valid Item Id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cart_item = CartItem.objects.get(id=item_id, cart_id=cart_id)
            user = User.objects.get(id=user_id)
            if cart_item.cart.user != user:
                return Response(
                    {"response": "Cannot modify cart"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except CartItem.DoesNotExist:
            return Response(
                {"error": "Cart item does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        cart_item.delete()

        return Response(
            {"response": "Item successfully removed from cart"},
            status=status.HTTP_200_OK,
        )

    @csrf_exempt
    @action(detail=False, methods=["post"])
    def add(self, request):
        user_id = validate_integer(request.data.get(USER_ID))
        if user_id is None:
            return Response(
                {"error": "Valid User Id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quantity = validate_integer(request.data.get(QUANTITY))
        if quantity is None:
            return Response(
                {"error": "Quantity is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if quantity <= 0:
            return Response(
                {"error": "Quantity must be a positive integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product_id = validate_integer(request.data.get(PRODUCT_ID))
        if product_id is None:
            return Response(
                {"error": "Valid Product Id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = Item.objects.get(id=product_id)
        except Item.DoesNotExist:
            return Response(
                {"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if requested quantity is available
        if product.quantity >= quantity:
            # Get cart for user, if doesn't exist, create
            try:
                cart = Cart.objects.get(user_id=user_id)
            except Cart.DoesNotExist:
                user = User.objects.get(id=user_id)
                cart = Cart.objects.create(user=user)

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item=product,
                defaults={"quantity": quantity},
            )

            # Check if total request quantity is available
            if not created:
                total_requested_quantity = cart_item.quantity + quantity
                if product.quantity < total_requested_quantity:
                    return Response(
                        {"error": "Requested quantity is not available"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                cart_item.quantity = total_requested_quantity
                cart_item.save()

            serializer = CartSerializer(cart, many=False)
            return Response({"response": serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Requested quantity is not available"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @csrf_exempt
    @action(detail=False, methods=["post"])
    def purchase(self, request):
        # Idempotency key is always required (either through request headers or in request data)
        idempotency_key = request.headers.get(
            IDEMPOTENCY_KEY_HEADER
        ) or request.data.get(IDEMPOTENCY_KEY)
        if not idempotency_key:
            return Response(
                {"error": "Idempotency key is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = validate_integer(request.data.get(USER_ID))
        if user_id is None:
            return Response(
                {"error": "User Id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        cart_id = validate_integer((request.data.get(CART_ID)))
        if cart_id is None:
            return Response(
                {"error": "Valid Cart id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # If idempotency key exists, the same transaction has already happened
            idempotency_val = IdempotencyKey.objects.get(key=idempotency_key)
            serializer = IdempotencyKeySerializer(idempotency_val, many=False)
            return Response(
                {"response": serializer.data.response_data},
                status=status.HTTP_200_OK,
            )
        except IdempotencyKey.DoesNotExist:
            # Create new idempotency key if one doesn't exist
            idempotency_val = IdempotencyKey.objects.create(
                user=user, key=idempotency_key, status=STATUS_PENDING
            )

        try:
            # Fetching cart by id and user
            cart = Cart.objects.get(id=cart_id, user=user)
        except Cart.DoesNotExist:
            return Response(
                {"error": "Cart does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Wrapping cart_item logic in atomic transaction for data consistency
        try:
            with transaction.atomic():
                # Using select_for_update to lock rows until transaction is completed
                cart_items = CartItem.objects.filter(
                    cart_id=cart_id
                ).select_for_update()
                if not cart_items.exists():
                    return Response(
                        {"error": "No cart items for cart"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                # Looping through all cart items and updating quantity
                for cart_item in cart_items:
                    product = cart_item.item
                    if product.quantity < cart_item.quantity:
                        # Raising exception to rollback transaction
                        raise Exception("Product does not have enough stock")
                    UserPurchaseRecord.objects.create(
                        user=user, item=cart_item.item, quantity=cart_item.quantity
                    )
                    product.quantity -= cart_item.quantity
                    product.save()

                cart.delete()
                serializer = CartItemSerializer(cart_items, many=True)
                idempotency_val.response_data = serializer.data
                idempotency_val.status = STATUS_SUCCESS
                idempotency_val.save()
        except Exception as e:
            idempotency_val.status = STATUS_FAILED
            idempotency_val.response_data = {"error": str(e)}
            idempotency_val.save()

        return Response(
            {"response": idempotency_val.response_data},
            status=(
                status.HTTP_200_OK
                if idempotency_val.status == STATUS_SUCCESS
                else status.HTTP_400_BAD_REQUEST
            ),
        )
