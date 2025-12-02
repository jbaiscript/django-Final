from django.contrib import admin

from .models import *
# Register your models here.

# Register your models here.

admin.site.register(UserProfile)
admin.site.register(ShoppingList)
admin.site.register(ShoppingListItem)


# only use migration when chnages are made to models