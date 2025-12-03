from django.db import models
import uuid
from django.conf import settings
from django.utils import timezone
from clients.models import UserProfile


class SoftDeleteManager(models.Manager):
    """Custom manager that excludes soft deleted objects by default"""
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def all_with_deleted(self):
        """Return all objects including soft deleted ones"""
        return super(SoftDeleteManager, self).get_queryset().all()

    def only_deleted(self):
        """Return only soft deleted objects"""
        return super().get_queryset().filter(deleted_at__isnull=False)

# Create your models here.


# One to One Product i.e dew-berry can only have one order item
# One To Many Product i.e dew-berry can have many order item but orderitem can only have 1 product at a time
# Many To Many


class Products(models.Model):
    class StatusofProduct(models.TextChoices):
        AVAILABLE = "Available"
        OUT_OF_STOCK = "Out of Stocks"
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=StatusofProduct.choices,
        default=StatusofProduct.AVAILABLE
    )
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    # Add relationship to user (seller)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products', null=True, blank=True)

    # Soft delete field
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Use custom manager with soft delete
    objects = SoftDeleteManager()  # Only active products (excludes soft deleted)
    all_objects = models.Manager()  # All products (includes soft deleted)

    def __str__(self):
        return f"Product Name: {self.name} Price: {self.price} Status: {self.status}"

    def delete(self, soft=True, *args, **kwargs):
        """Soft delete: set deleted_at timestamp instead of removing from db"""
        if soft:
            self.deleted_at = timezone.now()
            return self.save()
        else:
            return super().delete(*args, **kwargs)

    @classmethod
    def get_deleted_products_for_user(cls, user):
        """Class method to get soft deleted products for a specific user"""
        return cls.all_objects.filter(
            user=user,
            deleted_at__isnull=False
        )

    def restore(self):
        """Restore a soft deleted product"""
        self.deleted_at = None
        self.save()

    @classmethod
    def objects_active(cls):
        """Return only active (non-deleted) products"""
        return cls.objects.filter(deleted_at__isnull=True)


# attrbutes=> snake_case
# class-names=> Title case




class OrderItem(models.Model):
    class StatusofProduct(models.TextChoices):
        CANCELLED = "Cancelled"
        PENDING = "Pending"
        ON_DELIVERY = "On Delivery"
    quantity = models.PositiveIntegerField()
    number = models.UUIDField(default=uuid.uuid4, primary_key=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=30,
        choices=StatusofProduct.choices,
        default=StatusofProduct.PENDING
    )
    # sub_total
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name="order_items")
    # Add field to track if this order item was during a discount day
    is_discount_day = models.BooleanField(default=False)

    @property # Class Decorator Use for additional Functions
    def sub_total(self): # Class method refers
        return  self.product.price * self.quantity

    @property
    def original_sub_total(self):
        """
        Calculate the original price without discount
        """
        return self.product.price * self.quantity

    @property
    def discount_amount(self):
        """
        Calculate the discount amount if applicable
        """
        if self.is_discount_day:
            # Get the discount percentage for the date of this order item
            try:
                from discounts.models import DiscountDay
                discount_day = DiscountDay.objects.get(
                    seller=self.product.user,
                    date=self.created_at.date(),
                    is_active=True
                )
                return self.original_sub_total * (discount_day.discount_percentage / 100)
            except DiscountDay.DoesNotExist:
                return 0
        return 0

    @property
    def final_sub_total(self):
        """
        Calculate the final price after applying discount if applicable
        """
        if self.is_discount_day:
            return self.original_sub_total - self.discount_amount
        return self.sub_total

    def __str__(self):
        return f"Product: {self.product} Subtotal: {self.sub_total}"



class Order(models.Model):
    class StatusofProduct(models.TextChoices):
        CANCELLED = "Cancelled"
        PENDING = "Pending"
        ON_DELIVERY = "On Delivery"
    class PaymentChoice(models.TextChoices):
        COD = "Cash on Delivery"
        MAYA = "Pay Maya"
        G_CASH = "G-Cash"
        BPI = "B.P.I"
        GO_TYME = "Go Tyme"
        OTHERS = "Others"
    number = models.UUIDField(default=uuid.uuid4, primary_key=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=30,
        choices=StatusofProduct.choices,
        default=StatusofProduct.PENDING
    )
    payment = models.CharField(
        max_length=50,
        choices=PaymentChoice.choices,
        default=PaymentChoice.COD
    )
    # Add user relationship to track who placed the order
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    order_item = models.ManyToManyField(OrderItem)
    # Add payment status field
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Order {self.number} - Status: {self.status}"

    @property
    def total_amount(self):
        """
        Calculate the total amount of all order items in this order.
        This uses the final_sub_total of each OrderItem to account for discounts
        """
        total = sum(item.final_sub_total for item in self.order_item.all())
        return total

    @property
    def total_original_amount(self):
        """
        Calculate the total original amount (without discounts) of all order items in this order.
        """
        total = sum(item.original_sub_total for item in self.order_item.all())
        return total

    @property
    def total_discount_amount(self):
        """
        Calculate the total discount amount applied in this order.
        """
        total = sum(item.discount_amount for item in self.order_item.all())
        return total










