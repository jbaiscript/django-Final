from rest_framework import serializers
from .models import *
import re
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User


class ProductSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField(source='user.id')
    store_owner = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Products
        fields = (
            'id',
            'name',
            'description',
            'price',
            'stock',
            'status',
            'user_id',
            'store_owner',
            'deleted_at'
        )
        read_only_fields = ('deleted_at',)

    def sanitize_string_field(self, value):
        """Sanitize string field by removing extra whitespace and normalizing"""
        if isinstance(value, str):
            sanitized = " ".join(value.split())
            return sanitized
        return value

    def validate_name(self, value):
        """Validate and sanitize the product name"""
        sanitized_value = self.sanitize_string_field(value)
        if len(sanitized_value) < 1:
            raise serializers.ValidationError("Name cannot be empty")
        return sanitized_value

    def validate_description(self, value):
        """Validate and sanitize the product description"""
        return self.sanitize_string_field(value)

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value


class ProductMutationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Products
        fields = ["id", "name", "description", "price", "stock", "status"]

    def create(self, validated_data):
        return Products.objects.create(**validated_data)


class StrippedCharField(serializers.CharField):
    """Custom field that removes all whitespace from string values"""

    def to_internal_value(self, data):
        original_value = super().to_internal_value(data)
        
        if isinstance(original_value, str):
            # Removes ALL whitespace (including between words) → "  Hello   World  " becomes "HelloWorld"
            cleaned_value = ''.join(original_value.split())
            return cleaned_value
        
        return original_value


class PaymentSerializer(serializers.ModelSerializer):
    card_number = StrippedCharField(max_length=16, min_length=16, required=False, write_only=True)

    class Meta:
        model = Order
        fields = ('payment', 'card_number')

    def validate_card_number(self, value):
        """Validate that the card number contains only digits and is exactly 16 characters"""
        if not re.match(r'^\d{16}$', value):
            raise serializers.ValidationError('Card number must be exactly 16 digits.')

        if value.startswith("0000"):
            raise serializers.ValidationError("Card number cannot start with 0000")

        return value


class OrderItemSerializer(serializers.ModelSerializer):
    sub_total = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ('number', 'quantity', 'created_at', 'updated_at', 'status', 'product', 'is_discount_day', 'sub_total')


class OrderItemCreateSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = OrderItem
        fields = ('product', 'quantity', 'product_id')

    def to_internal_value(self, data):
        # Map product_id to product field
        if 'product_id' in data:
            from .models import Products
            try:
                product = Products.objects.get(id=data['product_id'])
                data['product'] = product.pk
            except Products.DoesNotExist:
                raise serializers.ValidationError({'product_id': 'Product with this ID does not exist'})
        return super().to_internal_value(data)

    def validate(self, attrs):
        # Additional validation to ensure product exists and has sufficient stock
        from .models import Products
        # Get the product_id from attrs since it's been processed by to_internal_value
        product = attrs.get('product')

        if product:
            try:
                product_obj = Products.objects.get(id=product.id if hasattr(product, 'id') else product)
                quantity = attrs.get('quantity', 0)
                if hasattr(product_obj, 'stock') and product_obj.stock < quantity:
                    raise serializers.ValidationError({'quantity': 'Insufficient stock available'})
            except Products.DoesNotExist:
                raise serializers.ValidationError({'product': 'Product with this ID does not exist'})

        return attrs

class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True, source='order_item')
    items = OrderItemCreateSerializer(many=True, write_only=True)  # Accept items in request
    card_number = serializers.CharField(max_length=16, min_length=16, required=False, write_only=True)

    class Meta:
        model = Order
        fields = ('number', 'created_at', 'updated_at', 'status', 'payment', 'user', 'order_items', 'items', 'card_number')
        read_only_fields = ('user',)  # Make user read-only since it's set by the view

    def validate_card_number(self, value):
        """Check if the credit card number is exactly 16 digits"""
        if not re.match(r'^\d{16}$', value):
            raise serializers.ValidationError('Card number must be exactly 16 digits.')
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        card_number = validated_data.pop('card_number', None)
        # The 'user' is passed separately in the view

        # Create the order
        order = Order.objects.create(**validated_data)

        # Create and associate order items
        order_items = []
        for item_data in items_data:
            # Remove product_id from the data since it's not a field on OrderItem
            item_data.pop('product_id', None)
            order_item = OrderItem.objects.create(**item_data)
            order_items.append(order_item)

        # Add order items to the order
        order.order_item.set(order_items)

        return order


