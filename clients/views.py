from rest_framework import generics, views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, DjangoModelPermissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone

from .models import UserProfile, ShoppingList, ShoppingListItem, Comment
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    ShoppingListSerializer, ShoppingListDetailSerializer,
    ShoppingListItemSerializer, ProductSerializer, OrderSerializer,
    SellerApprovalSerializer, AdminUserManagementSerializer,
    CommentSerializer, CommentCreateSerializer
)
from products.models import Products, Order, OrderItem

User = get_user_model()


# Helper: Generate JWT tokens
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def is_admin(user):
    """Helper function to check if user is admin"""
    try:
        return user.userprofile.role == 'admin'
    except UserProfile.DoesNotExist:
        return False


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
class SellerProductView(views.APIView):
    permission_classes = [IsSeller]

    def get(self, request, pk=None):
        if pk:
            # Handle single product retrieval
            show_deleted = request.query_params.get('deleted', '').lower() == 'true'

            if show_deleted:
                # Try to get the deleted product owned by this seller
                try:
                    product = Products._default_manager.get(
                        id=pk,
                        user=request.user,
                        deleted_at__isnull=False
                    )
                    serializer = ProductSerializer(product)
                    return Response(serializer.data)
                except Products.DoesNotExist:
                    return Response({'error': 'Deleted product not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                # Get active product
                try:
                    product = Products.objects.get(id=pk, user=request.user)
                    serializer = ProductSerializer(product)
                    return Response(serializer.data)
                except Products.DoesNotExist:
                    return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Handle list of products
            show_deleted = request.query_params.get('deleted', '').lower() == 'true'
            if show_deleted:
                # Show only deleted products with explicit query
                products = Products._default_manager.filter(
                    user=request.user,
                    deleted_at__isnull=False
                )
                print(f"DEBUG: Found {products.count()} deleted products for user {request.user.id}")
            else:
                # Show only active products
                products = Products.objects.filter(user=request.user)
                print(f"DEBUG: Found {products.count()} active products for user {request.user.id}")

            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data)

    def post(self, request):
        # Create product with explicit user assignment
        try:
            # Create product instance without saving to DB yet
            serializer = ProductSerializer(data=request.data)
            if serializer.is_valid():
                # Save the product first
                product = serializer.save()
                # Then explicitly assign the user and save again
                product.user = request.user
                product.save()

                # Verify the user assignment worked
                if product.user != request.user:
                    print(f"ERROR: User assignment failed. Expected {request.user.id}, got {product.user.id if product.user else None}")

                # Return the fully updated product data
                return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"ERROR creating product: {str(e)}")
            return Response({'error': 'Failed to create product', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        # Update product
        try:
            product = Products.objects.get(id=pk, user=request.user)
            serializer = ProductSerializer(product, data=request.data)
            if serializer.is_valid():
                updated_product = serializer.save()
                # Ensure user remains the same after update
                if updated_product.user != request.user:
                    updated_product.user = request.user
                    updated_product.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Products.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        # Handle product restoration from soft delete
        if 'restore' in request.data and request.data['restore'] is True:
            try:
                product = Products._default_manager.get(
                    id=pk,
                    user=request.user,
                    deleted_at__isnull=False
                )
                # Perform restore explicitly
                product.deleted_at = None
                product.save()
                serializer = ProductSerializer(product)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Products.DoesNotExist:
                return Response(
                    {'error': 'Deleted product not found or already active'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Regular partial update
            try:
                product = Products.objects.get(id=pk, user=request.user)
                serializer = ProductSerializer(product, data=request.data, partial=True)
                if serializer.is_valid():
                    updated_product = serializer.save()
                    # Ensure user remains the same after partial update
                    if updated_product.user != request.user:
                        updated_product.user = request.user
                        updated_product.save()
                    # Update status based on stock if stock was updated
                    if 'stock' in request.data:
                        if updated_product.stock > 0:
                            updated_product.status = updated_product.StatusofProduct.AVAILABLE
                        else:
                            updated_product.status = updated_product.StatusofProduct.OUT_OF_STOCK
                        updated_product.save()
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except Products.DoesNotExist:
                return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        # Soft delete product
        try:
            # First, check if the product exists for this user (regardless of delete status)
            product = Products._default_manager.get(id=pk, user=request.user)

            # If the product is already deleted, return appropriate message
            if product.deleted_at is not None:
                return Response({'message': 'Product is already soft deleted'}, status=status.HTTP_200_OK)

            # Perform soft delete explicitly
            product.deleted_at = timezone.now()
            product.save()
            return Response({'message': 'Product soft deleted successfully'}, status=status.HTTP_200_OK)
        except Products.DoesNotExist:
            return Response({'error': 'Product not found or does not belong to you'}, status=status.HTTP_404_NOT_FOUND)


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


# ==================== COMMENTS ====================
class CommentView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        return CommentSerializer

    def get_queryset(self):
        """
        Get comments for a specific object (e.g., product, order) using content_type and object_id
        Query parameters: content_type (model name) and object_id
        """
        content_type_param = self.request.query_params.get('content_type')
        object_id_param = self.request.query_params.get('object_id')

        if content_type_param and object_id_param:
            try:
                content_type = ContentType.objects.get(model=content_type_param)
                return Comment.objects.filter(
                    content_type=content_type,
                    object_id=object_id_param,
                    parent__isnull=True  # Only top-level comments, replies are nested
                ).select_related('user')
            except ContentType.DoesNotExist:
                return Comment.objects.none()
        else:
            # If no content_type and object_id provided, return all comments by the user
            return Comment.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        content_type = serializer.validated_data.get('content_type')
        object_id = serializer.validated_data.get('object_id')

        # Additional check to ensure user has purchased the product
        try:
            product_content_type = ContentType.objects.get(app_label='products', model='products')

            if content_type == product_content_type:
                from products.models import OrderItem
                has_purchased = OrderItem.objects.filter(
                    order__user=user,
                    product_id=object_id
                ).exists()

                if not has_purchased:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError("You can only comment on products you have purchased.")

        except ContentType.DoesNotExist:
            pass  # If content type doesn't exist, let it pass

        serializer.save(user=user)


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.filter(user=self.request.user)