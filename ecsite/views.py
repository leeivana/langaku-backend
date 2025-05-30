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
from .models import Item, Cart, CartItem, User, UserPurchaseRecord, IdempotencyKey
from .serializers import (
    ItemSerializer,
    CartSerializer,
    IdempotencyKeySerializer,
    CartItemSerializer,
)


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
        items = Item.objects.all()
        serializer = ItemSerializer(items, many=True)
        return Response({"items": serializer.data}, status=status.HTTP_200_OK)


class CartViewSet(viewsets.ViewSet):
    authentication_classes = [CsrfExemptSessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        items = Cart.objects.all()
        serializer = CartSerializer(items, many=True)
        return Response({"response": serializer.data}, status=status.HTTP_200_OK)

    @csrf_exempt
    @action(detail=False, methods=["post"])
    def delete_item(self, request, cart_id=None, item_id=None):
        if not cart_id:
            return Response(
                {"error": "Cart Id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not item_id:
            return Response(
                {"error": "Cart Id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

    @csrf_exempt
    @action(detail=False, methods=["post"])
    def add(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"error": "User Id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        quantity = int(request.data.get("quantity"))
        if not quantity:
            return Response(
                {"error": "Quantity is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        product_id = request.data.get("product_id")
        if not product_id:
            return Response(
                {"error": "Product Id is required"}, status=status.HTTP_400_BAD_REQUEST
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

        return Response(
            {"error": "Requested quantity is not available"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @csrf_exempt
    @action(detail=False, methods=["post"])
    def purchase(self, request):
        idempotency_key = request.headers.get("Idempotency-Key") or request.data.get(
            "idempotency_key"
        )
        if not idempotency_key:
            return Response(
                {"error": "Idempotency key is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"error": "User Id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        cart_id = int(request.data.get("cart_id"))
        if not cart_id:
            return Response(
                {"error": "Cart Id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User does not exist"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            idempotency_val = IdempotencyKey.objects.get(key=idempotency_key)
            serializer = IdempotencyKeySerializer(idempotency_val, many=False)
            return Response(
                {"response": serializer.data.response_data},
                status=status.HTTP_200_OK,
            )
        except IdempotencyKey.DoesNotExist:
            pass

        try:
            cart = Cart.objects.get(id=cart_id)
        except Cart.DoesNotExist:
            return Response(
                {"error": "Cart does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        cart_items = CartItem.objects.filter(cart_id=cart_id)
        if not cart_items.exists():
            return Response(
                {"error": "No cart items for cart"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Looping through all cart items and updating quantity
        for cart_item in cart_items:
            UserPurchaseRecord.objects.create(
                user=user, item=cart_item.item, quantity=cart_item.quantity
            )
            product = cart_item.item
            product.quantity = product.quantity - cart_item.quantity
            product.save()

        cart.delete()

        serializer = CartItemSerializer(cart_items, many=True)

        IdempotencyKey.objects.create(
            user=user, key=idempotency_key, response_data=serializer.data
        )

        return Response({"response": serializer.data}, status=status.HTTP_200_OK)
