from django.contrib import admin

# Register your models here.


from .models import * 
admin.site.register(User)
# admin.site.register(Admin)
# admin.site.register(Customer)
# Register your models here.


# only use migration when chnages are made to models