from django.db import models
import uuid 

# Create your models here.


# One to One Product i.e dew-berry can only have one order item 
# One To Many Product i.e dew-berry can have many order item but orderitem can only have 1 product at a time
# Many To Many  



class Status(models.Model):
    class StatusofProduct(models.TextChoices):
        AVAILABLE = "Available"
        OUT_OF_STOCK = "Out of Stocks"
        
class StatusofDelivery(models.Model):
    class StatusofProduct(models.TextChoices):
        CANCELLED = "Cancelled"
        PENDING = "Pending"
        ON_DELIVERY = "On Delivery"


class Payment(models.Model):
    class PaymentChoice(models.TextChoices):
        COD = "Cash on Delivery"
        MAYA = "Pay Maya"
        G_CASH = "G-Cash"
        BPI = "B.P.I"
        GO_TYME = "Go Tyme"
        OTHERS = "Others"
   


class Products(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.StatusofProduct.choices,
        default=Status.StatusofProduct.AVAILABLE
    )
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    """
     add null true and black true if 

     Please select a fix:
     1) Provide a one-off default now (will be set on all existing rows with a null value for this column)
      2) Quit and manually define a default value in models.py.
     Select an option:
    """

    # """ can be use to doc string or multi comment


    def __str__(self):
        return f"Product Name: {self.name} Price: {self.price} Status: {self.status}"
    

# attrbutes=> snake_case
# class-names=> Title case


class OrderItem(models.Model):
    quantity = models.PositiveIntegerField()
    number = models.UUIDField(default=uuid.uuid4(), primary_key=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=30,
        choices=StatusofDelivery.StatusofProduct.choices,
        default=StatusofDelivery.StatusofProduct.PENDING
    )
    # sub_total
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name="order_items")
    
    @property # Class Decorator Use for additional Functions
    def sub_total(self): # Class method refers
        return  self.product.price * self.quantity
    
    def __str__(self):
        return f"Product: {self.product} Subtotal: {self.sub_total}"
    


class Order(models.Model):
    number = models.UUIDField(default=uuid.uuid4(), primary_key=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=30,
        choices=StatusofDelivery.StatusofProduct.choices,
        default=StatusofDelivery.StatusofProduct.PENDING
    )
    payment = models.CharField(
        max_length=50,
        choices=Payment.PaymentChoice.choices,
        default=Payment.PaymentChoice.COD
    )
    order_item = models.ManyToManyField(OrderItem)
    
    def __str__(self):
        return f"Order {self.number} - Status: {self.status}"










