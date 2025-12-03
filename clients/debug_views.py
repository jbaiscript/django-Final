from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from products.models import Products

class IsSeller:
    """Simple seller permission check"""
    def has_permission(self, request, view):
        try:
            return request.user.userprofile.role == 'seller'
        except:
            return False

class DebugSoftDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request):
        """Debug endpoint to check soft delete status"""
        # Get all products for this user, including deleted ones
        all_products = Products._default_manager.filter(user=request.user)

        # Debug: Check all products regardless of user to see what exists
        all_db_products = Products._default_manager.all()
        total_db_count = all_db_products.count()

        # Products specifically for this user
        user_products = all_products
        result = {
            'request_user_id': request.user.id,
            'request_user_email': request.user.email,
            'request_user_role': getattr(request.user.userprofile, 'role', 'unknown'),
            'total_products_for_user': user_products.count(),
            'active_products_for_user': user_products.filter(deleted_at__isnull=True).count(),
            'deleted_products_for_user': user_products.filter(deleted_at__isnull=False).count(),
            'total_products_in_db': total_db_count,  # Total products regardless of user
            'product_details': []
        }

        for product in all_products:
            result['product_details'].append({
                'id': product.id,
                'name': product.name,
                'user_id': product.user.id if product.user else None,
                'is_deleted': product.deleted_at is not None,
                'deleted_at': product.deleted_at.isoformat() if product.deleted_at else None
            })

        return Response(result)

class TestUserAssignmentView(APIView):
    permission_classes = [IsAuthenticated, IsSeller]

    def post(self, request):
        """Test endpoint to verify user assignment"""
        user_id = request.user.id
        email = request.user.email

        # Create a test product directly
        from products.models import Products
        from .serializers import ProductSerializer

        # Add user to the data for the serializer
        data = request.data.copy()
        data['user'] = user_id  # Explicitly set user

        serializer = ProductSerializer(data=data)
        if serializer.is_valid():
            product = serializer.save(user=request.user)
            return Response({
                'message': 'Product created successfully',
                'product_id': product.id,
                'user_id': product.user.id if product.user else None,
                'request_user_id': request.user.id
            })
        return Response({
            'error': 'Invalid data',
            'serializer_errors': serializer.errors
        })