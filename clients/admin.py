from django.contrib import admin
from django.contrib.auth.models import User
from .models import Admin, Customer, Seller

# Register your models here.
admin.site.register(Admin)
admin.site.register(Customer)
admin.site.register(Seller)
# Register your models here.


# only use migration when chnages are made to models