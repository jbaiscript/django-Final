from django.contrib import admin
from .models import *

admin.site.register(Products)
admin.site.register(OrderItem)
admin.site.register(Order)
# Register your models here.

