from django.db import models

from django.contrib.auth.models import User


# Use default user model from django as roles common data 

# Create your models here.


class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="is_admin")
    


class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="is_seller")
    store_name = models.CharField(max_length=50)
    profile = models.ImageField(upload_to="profile/")



class Customer(models.Model):
    customer = models.OneToOneField(User, on_delete=models.CASCADE, related_name="is_customer")
    address = models.CharField(max_length=250) 
    profile = models.ImageField(upload_to="profile/", default="profile/default.jpg")




# from django.contrib.auth.models import AbstractUser



# class User(AbstractUser):
#     email = models.EmailField(max_length=254, unique=True)
    
    
    
    





    


    
