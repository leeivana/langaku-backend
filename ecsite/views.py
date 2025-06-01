from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.exceptions import NotFound
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
    AddCartItemSerializer,
    PurchaseCartSerializer,
)
from .constants import (
    USER_ID,
    ITEM_ID,
    IDEMPOTENCY_KEY_HEADER,
    IDEMPOTENCY_KEY,
    QUANTITY,
    NAME,
    MIN_PRICE,
    MAX_PRICE,
    STATUS_SUCCESS,
    STATUS_FAILED,
    STATUS_PENDING,
    CART_ID,
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


def parse_serializer_error(serializer):
    errors = serializer.errors
    is_not_found = False
    for _, messages in errors.items():
        for msg in messages:
            if isinstance(msg, str) and "associated" in msg:
                is_not_found = True
                break

    return Response(
        {"error": errors},
        status=(
            status.HTTP_404_NOT_FOUND if is_not_found else status.HTTP_400_BAD_REQUEST
        ),
    )


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

    def list_items(self, req, cart_id=None):
        if not cart_id:
            return Response(
                {"error": "Cart Id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        cart_id = validate_integer(cart_id)
        if cart_id is None:
            return Response(
                {"error": "Invalid Cart Id"}, status=status.HTTP_400_BAD_REQUEST
            )

        cart_items = CartItem.objects.filter(cart_id=cart_id).select_related("item")

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

    def list(self, request):
        carts = Cart.objects.all()
        serializer = CartSerializer(carts, many=True)
        return Response({"carts": serializer.data}, status=status.HTTP_200_OK)

    @csrf_exempt
    @action(detail=True, methods=["delete"], url_path="items/(?P<cart_item_id>[^/.]+)")
    def delete_cart_item(self, request, pk: None, cart_item_id: None):
        cart_id = validate_integer(pk)
        if cart_id is None:
            return Response(
                {"error": "Valid Cart Id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item_id = validate_integer(cart_item_id)
        if item_id is None:
            return Response(
                {"error": "Valid Item Id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = validate_integer(request.data.get(USER_ID))
        if user_id is None:
            return Response(
                {"error": "Valid User Id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get cart belonging to user by id
            cart = Cart.objects.get(id=cart_id, user_id=user_id)
        except Cart.DoesNotExist:
            return Response(
                {"error": "No cart associated with provided Id"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            cart_item = CartItem.objects.get(id=item_id, cart_id=cart.id)
        except CartItem.DoesNotExist:
            return Response(
                {"error": "Cart item does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        cart_item.delete()
        cart = Cart.objects.get(user_id=user_id)
        serializer = CartSerializer(cart, many=False)
        return Response(
            {"cart": serializer.data},
            status=status.HTTP_200_OK,
        )

    @csrf_exempt
    def create(self, request):
        user_id = validate_integer(request.data.get(USER_ID))
        if user_id is None:
            return Response(
                {"error": "Valid User Id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=user_id)
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            cart = Cart.objects.create(user=user)

        serializer = CartSerializer(cart, many=False)
        return Response(
            {"cart": serializer.data},
            status=status.HTTP_200_OK,
        )

    @csrf_exempt
    @action(detail=True, methods=["post"], url_path="items")
    def add(self, request, pk: None):
        data = request.POST.copy()
        data[CART_ID] = pk

        serializer = AddCartItemSerializer(data=data)
        if not serializer.is_valid():
            return parse_serializer_error(serializer)

        validated = serializer.validated_data
        item = validated[ITEM_ID]
        user = validated[USER_ID]
        cart = validated[CART_ID]
        quantity = validated[QUANTITY]

        # Check if requested quantity is available
        if item.quantity >= quantity:
            # Validate cart belongs to user
            if user.id != cart.user.id:
                return Response(
                    {"error": "Cart does not exist for user"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item=item,
                defaults={QUANTITY: quantity},
            )

            # Check if total request quantity is available
            if not created:
                total_requested_quantity = cart_item.quantity + quantity
                if item.quantity < total_requested_quantity:
                    return Response(
                        {"error": "Requested quantity is not available"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                cart_item.quantity = total_requested_quantity
                cart_item.save()

            serializer = CartSerializer(cart, many=False)
            return Response({"cart": serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Requested quantity is not available"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @csrf_exempt
    @action(detail=True, methods=["post"])
    def purchase(self, request, pk=None):
        data = request.POST.copy()
        # Idempotency key is always required (either through request headers or in request data)
        data[IDEMPOTENCY_KEY] = request.headers.get(
            IDEMPOTENCY_KEY_HEADER
        ) or request.data.get(IDEMPOTENCY_KEY)
        data[CART_ID] = pk

        serializer = PurchaseCartSerializer(data=data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated = serializer.validated_data
        user = validated[USER_ID]
        cart_id = validated[CART_ID]
        idempotency_key = validated[IDEMPOTENCY_KEY]

        try:
            # If idempotency key exists, the same transaction has already happened
            idempotency_val = IdempotencyKey.objects.get(key=idempotency_key)
            serializer = IdempotencyKeySerializer(idempotency_val, many=False)
            return Response(
                {"response": serializer.data["response_data"]},
                status=status.HTTP_200_OK,
            )
        except IdempotencyKey.DoesNotExist:
            # Create new idempotency key if one doesn't exist
            idempotency_val = IdempotencyKey.objects.create(
                user=user, key=idempotency_key, status=STATUS_PENDING
            )

        try:
            # Fetching cart by id and user
            cart = Cart.objects.get(user=user, id=cart_id)
        except Cart.DoesNotExist:
            return Response(
                {"error": "No cart associated with provided Id"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not cart.items.exists():
            return Response(
                {"error": "Cart has no items"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Wrapping cart_item logic in atomic transaction for data consistency
        try:
            with transaction.atomic():
                # Using select_for_update to lock rows until transaction is completed
                cart_items = (
                    CartItem.objects.filter(cart_id=cart.id)
                    .select_for_update()
                    .select_related("item")
                )
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
                        raise Exception("Item does not have enough stock")
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
                idempotency_val.response_data, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"response": idempotency_val.response_data},
            status=status.HTTP_200_OK,
        )
