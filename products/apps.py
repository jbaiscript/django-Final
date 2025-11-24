from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'


# Can be an error if name != app name

#app migrations pycache and cache if you can the name ( clear or update )