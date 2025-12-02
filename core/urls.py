"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from products.views import ProductView, ProductRetriveUpdateDelete, CustomerOrderView, PaymentView
from discounts.views import DiscountDayView, DiscountDayDetailView, SellerStatsView
from clients import views as client_views


urlpatterns = [
    path('admin/', admin.site.urls),

    # Product and Order endpoints
    path('api/product/', ProductView.as_view()),
    path('api/product/<int:pk>/', ProductRetriveUpdateDelete.as_view()),
    path('api/orders/', CustomerOrderView.as_view()),  # Handle order creation (POST) and list orders (GET)
    path('api/orders/<uuid:order_number>/', CustomerOrderView.as_view()),  # Handle single order (GET) and delete (DELETE)
    path('api/payment/', PaymentView.as_view()),

    # Auth Path
    path('api/auth/', client_views.AuthView.as_view()),

    # Shopping list endpoints
    path('api/auth/shopping-lists/', client_views.ShoppingListView.as_view()),
    path('api/auth/shopping-lists/<int:pk>/', client_views.ShoppingListDetailView.as_view()),
    path('api/auth/shopping-lists/<int:shopping_list_id>/items/', client_views.ShoppingListItemView.as_view()),
    path('api/auth/shopping-lists/<int:shopping_list_id>/items/<int:pk>/', client_views.ShoppingListItemDetailView.as_view()),

    # Seller endpoints
    path('api/auth/seller/register/', client_views.SellerRegistrationView.as_view()),
    path('api/auth/seller/products/', client_views.SellerProductView.as_view()),
    path('api/auth/seller/products/<int:pk>/', client_views.SellerProductView.as_view()),
    path('api/auth/seller/orders/', client_views.SellerOrderListView.as_view()),
    path('api/auth/seller/orders/<uuid:pk>/', client_views.SellerOrderDetailView.as_view()),

    # Admin 
    path('api/auth/admin/users/', client_views.AdminUserView.as_view()),

    # Discount Path
    path('api/discount-day/', DiscountDayView.as_view()),
    path('api/discount-day/<int:pk>/', DiscountDayDetailView.as_view()),
    path('api/seller/stats/', SellerStatsView.as_view()),  # Use the original view for stats
]

"""generic foreing key in django for comments"""
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT) # When in development or debug use local host as url

