from django.db import models
from django.contrib.auth.models import User


class Item(models.Model):
    name = models.CharField(max_length=100)
    # Price is assumed to be in Yen without decimals.
    price = models.IntegerField()
    quantity = models.PositiveIntegerField(default=0)


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    items = models.ManyToManyField(Item, through="CartItem")


class IdempotencyKey(models.Model):
    key = models.CharField(max_length=100, null=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    response_data = models.JSONField(null=True)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("cart", "item")


class UserPurchaseRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "{} of {} purchased on {}".format(
            self.quantity, self.item.name, self.timestamp
        )
