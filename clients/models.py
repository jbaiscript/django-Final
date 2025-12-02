from django.db import models
from django.contrib.auth.models import User, Group
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

    


    
