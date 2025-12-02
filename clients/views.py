from rest_framework import generics, views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, DjangoModelPermissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from django.http import HttpResponse

from .models import UserProfile, ShoppingList, ShoppingListItem
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    ShoppingListSerializer, ShoppingListDetailSerializer,
    ShoppingListItemSerializer, ProductSerializer, OrderSerializer,
    SellerApprovalSerializer, AdminUserManagementSerializer
)
from products.models import Products, Order, OrderItem

User = get_user_model()


# Helper: Generate JWT tokens
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


# Custom permission mixin (replaces all your is_customer/is_seller/is_admin checks)
class RoleBasedPermission(IsAuthenticated):
    allowed_roles = ()

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        try:
            return request.user.userprofile.role in self.allowed_roles
        except UserProfile.DoesNotExist:
            return False


class IsCustomer(RoleBasedPermission):
    allowed_roles = ('customer', 'admin')


class IsSeller(RoleBasedPermission):
    allowed_roles = ('seller',)

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        try:
            profile = request.user.userprofile
            return profile.role == 'seller' and profile.is_seller_approved
        except UserProfile.DoesNotExist:
            return False


class IsAdmin(RoleBasedPermission):
    allowed_roles = ('admin',)


# ==================== AUTH ====================
class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "tokens": get_tokens_for_user(user),
            "user": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(**serializer.validated_data)
        if not user:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({
            "tokens": get_tokens_for_user(user),
            "user": UserSerializer(user).data
        })


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# ==================== ADMIN ====================
class AdminUserManagementView(generics.ListCreateAPIView):
    serializer_class = AdminUserManagementSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        role = self.request.query_params.get('role')
        qs = User.objects.all()
        if role:
            qs = qs.filter(userprofile__role=role)
        return qs


class SellerApprovalView(generics.UpdateAPIView):
    serializer_class = SellerApprovalSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.filter(userprofile__role='seller')
    lookup_field = 'id'


# ==================== CUSTOMER - SHOPPING LIST ====================
class ShoppingListView(generics.ListCreateAPIView):
    serializer_class = ShoppingListSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ShoppingListDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ShoppingListDetailSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user)


class ShoppingListItemView(generics.ListCreateAPIView):
    serializer_class = ShoppingListItemSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        return ShoppingListItem.objects.filter(
            shopping_list_id=self.kwargs['shopping_list_id'],
            shopping_list__user=self.request.user
        )

    def perform_create(self, serializer):
        shopping_list = ShoppingList.objects.get(
            id=self.kwargs['shopping_list_id'],
            user=self.request.user
        )
        serializer.save(shopping_list=shopping_list)


class ShoppingListItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ShoppingListItemSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        return ShoppingListItem.objects.filter(
            id=self.kwargs['pk'],
            shopping_list_id=self.kwargs['shopping_list_id'],
            shopping_list__user=self.request.user
        )


# ==================== SELLER - PRODUCTS & ORDERS ====================
class SellerProductView(generics.ListCreateAPIView, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsSeller]

    def get_queryset(self):
        return Products.objects.filter(user=self.request.user, deleted_at__isnull=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        instance.delete(soft=True)  # soft delete


class SellerOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsSeller]

    def get_queryset(self):
        seller_products = Products.objects.filter(user=self.request.user, deleted_at__isnull=True)
        return Order.objects.filter(order_item__product__in=seller_products).distinct()


class SellerOrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsSeller]

    def get_queryset(self):
        seller_products = Products.objects.filter(user=self.request.user, deleted_at__isnull=True)
        return Order.objects.filter(order_item__product__in=seller_products).distinct()


class SellerRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        # Update profile to seller but not approved yet
        profile = user.userprofile
        profile.role = 'seller'
        profile.is_seller_approved = False
        profile.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Update profile to seller but not approved yet
        profile = user.userprofile
        profile.role = 'seller'
        profile.is_seller_approved = False
        profile.save()

        return Response({
            "tokens": get_tokens_for_user(user),
            "user": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


# ==================== UNIFIED AUTH ENDPOINT ====================
class AuthView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Determine action based on request data
        action = request.data.get('action', '').lower()

        # Also check if this looks like a login attempt (username and password fields exist, but not email)
        is_login_attempt = (
            'username' in request.data and
            'password' in request.data and
            'email' not in request.data
        )

        if action == 'login' or is_login_attempt:
            # Use the same login logic
            # Create a data dict that matches LoginSerializer expectations
            login_data = {
                'username': request.data.get('username'),
                'password': request.data.get('password')
            }

            serializer = UserLoginSerializer(data=login_data)
            serializer.is_valid(raise_exception=True)

            username = serializer.validated_data['username']
            password = serializer.validated_data['password']

            user = authenticate(username=username, password=password)

            if user is None:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

            tokens = get_tokens_for_user(user)
            user_serializer = UserSerializer(user)

            return Response({
                'tokens': tokens,
                'user': user_serializer.data
            }, status=status.HTTP_200_OK)
        else:
            # Default to register for all other cases
            serializer = UserRegistrationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            tokens = get_tokens_for_user(user)
            user_serializer = UserSerializer(user)

            return Response({
                'tokens': tokens,
                'user': user_serializer.data
            }, status=status.HTTP_201_CREATED)

    def get(self, request):
        # Handle profile retrieval
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
        user_serializer = UserSerializer(request.user)
        return Response(user_serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        # Handle profile update
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
        user = request.user
        user_serializer = UserSerializer(user, data=request.data, partial=False)
        if user_serializer.is_valid():
            user_serializer.save()
            return Response(user_serializer.data, status=status.HTTP_200_OK)
        return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        # Handle partial profile update
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
        user = request.user
        user_serializer = UserSerializer(user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return Response(user_serializer.data, status=status.HTTP_200_OK)
        return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Combined admin user management and seller approval
class AdminUserView(generics.ListCreateAPIView, generics.UpdateAPIView):
    serializer_class = AdminUserManagementSerializer
    permission_classes = [DjangoModelPermissions]
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        if not is_admin(user):
            return User.objects.none()  # Return empty queryset if not admin
        if self.request.query_params.get('role'):
            role = self.request.query_params.get('role')
            return User.objects.filter(userprofile__role=role)
        return User.objects.all()

    def update(self, request, *args, **kwargs):
        # Check if this is a seller approval request
        user_id = self.kwargs.get('id')
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if the request is for seller approval
        if 'is_seller_approved' in request.data:
            # Handle seller approval logic using SellerApprovalSerializer
            serializer = SellerApprovalSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Otherwise, handle normal user update
        return super().update(request, *args, **kwargs)