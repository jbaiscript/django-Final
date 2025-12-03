from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.db.models.signals import post_save


# User profile to extend the default User model with role-based functionality
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('seller', 'Seller'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')
    is_seller_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class ShoppingList(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_lists')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    class Meta:
        unique_together = ('name', 'user')


class ShoppingListItem(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name='items')
    product_id = models.IntegerField()  # Store the product ID from the products app
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Item {self.product_id} in {self.shopping_list.name}"

    class Meta:
        unique_together = ('shopping_list', 'product_id')


class Comment(models.Model):
    """
    Generic comment model that can be associated with any model using GenericForeignKey.
    This allows comments to be attached to products, orders, or other models.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')

    # Generic foreign key fields to link to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional: parent comment for nested replies
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.user.username} on {self.content_type.model} {self.object_id}'

    def is_reply(self):
        """Check if this comment is a reply to another comment"""
        return self.parent is not None

    def can_comment_on_product(self, user, product_id):
        """
        Check if the user has purchased the product before allowing a comment.
        This method checks if the user has any order that contains the specified product.
        """
        from products.models import Order, OrderItem

        # Check if the content_type is for a product
        try:
            product_content_type = ContentType.objects.get(app_label='products', model='products')
            if self.content_type == product_content_type:
                # Verify the user has purchased the product
                has_purchased = OrderItem.objects.filter(
                    order__user=user,
                    product_id=product_id
                ).exists()

                return has_purchased
        except ContentType.DoesNotExist:
            # The content_type is not for products, so no purchase verification needed
            return True

        # For non-product content types, allow commenting without purchase verification
        return True


# Auto-create user profile when a user is created
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

        # Add to appropriate group based on role
        profile = UserProfile.objects.get(user=instance)
        if profile.role == 'customer':
            group, created = Group.objects.get_or_create(name='Customer')
            instance.groups.add(group)
        elif profile.role == 'seller':
            group, created = Group.objects.get_or_create(name='Seller')
            instance.groups.add(group)
        elif profile.role == 'admin':
            group, created = Group.objects.get_or_create(name='Admin')
            instance.groups.add(group)

post_save.connect(create_user_profile, sender=User)

    


    
