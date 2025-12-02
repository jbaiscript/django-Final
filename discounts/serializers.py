from rest_framework import serializers
from .models import DiscountDay
from django.contrib.auth.models import User


class DiscountDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountDay
        fields = '__all__'


class DiscountDayCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountDay
        fields = ['date', 'discount_percentage', 'is_active']
    
    def create(self, validated_data):
        # The seller is passed through the context during creation
        request = self.context.get('request')
        if request:
            validated_data['seller'] = request.user
        return super().create(validated_data)