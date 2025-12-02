from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from .models import UserProfile, ShoppingList, ShoppingListItem
from products.models import Products, Order


User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES, default='customer', required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name', 'role')

    def create(self, validated_data):
        role = validated_data.pop('role', 'customer')
        user = User.objects.create_user(**validated_data)

        # Update user profile with role
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()

        # Add to appropriate group
        if role == 'customer':
            group, created = Group.objects.get_or_create(name='Customer')
            user.groups.add(group)
        elif role == 'seller':
            group, created = Group.objects.get_or_create(name='Seller')
            user.groups.add(group)
        elif role == 'admin':
            group, created = Group.objects.get_or_create(name='Admin')
            user.groups.add(group)
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='userprofile.role', read_only=True)
    is_seller_approved = serializers.BooleanField(source='userprofile.is_seller_approved', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_seller_approved', 'date_joined')
        read_only_fields = ('role', 'is_seller_approved', 'date_joined')


class ShoppingListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingList
        fields = ('id', 'name', 'user', 'created_at', 'updated_at')
        read_only_fields = ('user', 'created_at', 'updated_at')


class ShoppingListItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    product_price = serializers.SerializerMethodField()

    class Meta:
        model = ShoppingListItem
        fields = ('id', 'shopping_list', 'product_id', 'product_name', 'product_price', 'quantity', 'added_at')
        read_only_fields = ('added_at',)

    def get_product_name(self, obj):
        try:
            product = Products.objects.get(id=obj.product_id)
            return product.name
        except Products.DoesNotExist:
            return f"Product ID {obj.product_id} (not found)"

    def get_product_price(self, obj):
        try:
            product = Products.objects.get(id=obj.product_id)
            return float(product.price)
        except Products.DoesNotExist:
            return 0.0


class ShoppingListDetailSerializer(serializers.ModelSerializer):
    items = ShoppingListItemSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingList
        fields = ('id', 'name', 'user', 'created_at', 'updated_at', 'items')
        read_only_fields = ('user', 'created_at', 'updated_at')


class AdminUserManagementSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='userprofile.role')
    is_seller_approved = serializers.BooleanField(source='userprofile.is_seller_approved')
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_seller_approved', 'date_joined')
        read_only_fields = ('date_joined',)

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('userprofile', {})
        role = profile_data.get('role')
        is_seller_approved = profile_data.get('is_seller_approved')
        
        # Update the user instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update the user profile
        profile = instance.userprofile
        if role:
            profile.role = role
        if is_seller_approved is not None:
            profile.is_seller_approved = is_seller_approved
        profile.save()
        
        return instance


class SellerApprovalSerializer(serializers.ModelSerializer):
    is_seller_approved = serializers.BooleanField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'is_seller_approved')
        read_only_fields = ('id', 'username')

    def update(self, instance, validated_data):
        is_seller_approved = validated_data.get('is_seller_approved')
        profile = instance.userprofile
        profile.is_seller_approved = is_seller_approved
        profile.save()
        
        if is_seller_approved and profile.role == 'seller':
            # Add to Seller group when approved
            seller_group, created = Group.objects.get_or_create(name='Seller')
            instance.groups.add(seller_group)
        return instance


# Serializers for product and order views
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Products
        exclude = ('deleted_at',)  # Exclude the soft delete field from API responses
        read_only_fields = ('user',)


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'