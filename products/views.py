from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime
from .serializers import ProductSerializer, OrderSerializer, PaymentSerializer
from .models import Products, Order, OrderItem


# Create your views here.
class ProductView(APIView):
    def sanitizer(self, value):
        """Sanitize string values by removing extra whitespace"""
        if not isinstance(value, str):
            raise TypeError("Input must be a string")

        # Replace multiple spaces with a single space
        value = " ".join(value.split())

        # Strip any leading/trailing whitespace
        return value.strip()

    def post(self, request):
        # Check if user is an approved seller (replicating IsSeller logic)
        try:
            profile = request.user.userprofile
            is_approved_seller = profile.role == 'seller' and profile.is_seller_approved
        except:
            is_approved_seller = False

        if not is_approved_seller:
            return Response({'error': 'Only approved sellers can create products'}, status=status.HTTP_403_FORBIDDEN)

        def sanitizer(value):
            if not isinstance(value, str):
                raise TypeError("Input must be a string")

            # Replace multiple spaces with a single space
            value = " ".join(value.split())

            return value.title().strip()

        data = request.data.copy()

        if 'name' in data and isinstance(data['name'], str):
            data['name'] = sanitizer(data['name'])
        if 'description' in data and isinstance(data['description'], str):
            data['description'] = sanitizer(data['description'])

        serializer = ProductSerializer(data=data)

        if serializer.is_valid():
            # Save the product and associate it with the seller
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        # Only return non-deleted products - use default manager to avoid conflicts
        products = Products.objects.filter(deleted_at__isnull=True)  # This uses SoftDeleteManager by default
        view = ProductSerializer(products, many=True)
        return Response(view.data)


class ProductRetriveUpdateDelete(APIView):
    def get(self, request, pk):
        # Regular product endpoint - only shows non-deleted products to customers
        # Customers should not see deleted products
        product = Products.objects.filter(  # This is SoftDeleteManager which filters out deleted by default
            id=pk,
            deleted_at__isnull=True
        ).first()
        if product is None:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(product)
        return Response(serializer.data)

    def put(self, request, pk):
        try:
            product = Products.objects.filter(id=pk, deleted_at__isnull=True).first()
            if product is None:
                return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

            serializer = ProductSerializer(product, data=request.data)
            if serializer.is_valid():
                # Update product status based on stock after validation
                updated_product = serializer.save()
                # Update status based on stock
                if updated_product.stock > 0:
                    updated_product.status = updated_product.StatusofProduct.AVAILABLE
                else:
                    updated_product.status = updated_product.StatusofProduct.OUT_OF_STOCK
                updated_product.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Products.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        try:
            product = Products.objects.filter(id=pk, deleted_at__isnull=True).first()
            if product is None:
                return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

            serializer = ProductSerializer(product, data=request.data, partial=True)
            if serializer.is_valid():
                # Update product status based on stock after validation
                updated_product = serializer.save()
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
        try:
            product = Products.objects.get(id=pk)
            # Perform soft delete
            product.delete(soft=True)
            return Response({'message': 'Product soft deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Products.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)


class OrderView(APIView):
    permission_classes = [IsAuthenticated]  # Require authentication to place orders

    def get(self, request, order_number=None):
        """
        Get a specific order if order_number is provided, or all orders of the authenticated user
        """
        if order_number:
            try:
                order = Order.objects.get(number=order_number, user=request.user)
                serializer = OrderSerializer(order)
                return Response(serializer.data)
            except Order.DoesNotExist:
                return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Get all orders for the current user
            orders = Order.objects.filter(user=request.user).order_by('-created_at')
            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data)

    def post(self, request):
        # Prepare order data (excluding items)
        order_data = {
            'user': request.user,
            'payment': request.data.get('payment', Order.PaymentChoice.COD),  # Default payment method
        }

        # Validate payment method
        payment_method = request.data.get('payment', Order.PaymentChoice.COD)
        if payment_method not in [choice[0] for choice in Order.PaymentChoice.choices]:
            return Response({'error': 'Invalid payment method'}, status=status.HTTP_400_BAD_REQUEST)

        # Create the order
        order = Order.objects.create(**order_data)

        # Handle items separately after order is created
        items_data = request.data.get('items', [])
        order_items = []
        for item_data in items_data:
            from .models import Products
            # Get the product based on product_id from the request
            product_id = item_data.get('product_id')
            quantity_requested = item_data.get('quantity', 1)
            if product_id:
                try:
                    product = Products.objects.get(id=product_id)
                    # Check stock availability
                    if product.stock < quantity_requested:
                        # Rollback: delete the order since insufficient stock
                        order.delete()
                        return Response(
                            {'error': f'Insufficient stock for {product.name}. Available: {product.stock}, Requested: {quantity_requested}'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    # Create order item
                    order_item = OrderItem.objects.create(
                        product=product,
                        quantity=quantity_requested
                    )
                    order_items.append(order_item)

                    # Decrease product stock
                    product.stock -= quantity_requested
                    if product.stock <= 0:
                        product.status = product.StatusofProduct.OUT_OF_STOCK
                    product.save()
                except Products.DoesNotExist:
                    # Rollback: delete the order since we can't create the items
                    order.delete()
                    return Response(
                        {'error': f'Product with id {product_id} does not exist'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # Add order items to the order
        order.order_item.set(order_items)

        # Update order items for discount days
        try:
            for item in order.order_item.all():
                # Check if item has a valid product
                if item.product and item.product.user:
                    current_date = timezone.now().date()
                    try:
                        from discounts.models import DiscountDay
                        discount_day = DiscountDay.objects.get(
                            seller=item.product.user,
                            date=current_date,
                            is_active=True
                        )
                        item.is_discount_day = True
                        item.save()
                    except DiscountDay.DoesNotExist:
                        item.is_discount_day = False
                        item.save()
        except Exception as e:
            # Log the error but don't fail the order
            print(f"Error updating discount days: {e}")
            pass  # Continue with the order even if discount update fails

        # Serialize the created order for response
        response_serializer = OrderSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, order_number):
        """
        Update an existing order for authenticated user. Only allows updating status and payment method.
        Order items cannot be modified after creation to maintain order integrity.
        """
        try:
            order = Order.objects.get(number=order_number, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        # Only allow updating of specific fields (not order items)
        allowed_fields = ['status', 'payment']
        update_data = {}

        for field in allowed_fields:
            if field in request.data:
                update_data[field] = request.data[field]

        serializer = OrderSerializer(order, data=update_data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, order_number):
        """
        Partially update an existing order for authenticated user. Only allows updating status and payment method.
        Order items cannot be modified after creation to maintain order integrity.
        """
        try:
            order = Order.objects.get(number=order_number, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        # Only allow updating of specific fields (not order items)
        allowed_fields = ['status', 'payment']
        update_data = {}

        for field in allowed_fields:
            if field in request.data:
                update_data[field] = request.data[field]

        serializer = OrderSerializer(order, data=update_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_number=None):
        if order_number:
            # Get specific order
            try:
                order = Order.objects.get(number=order_number, user=request.user)
                serializer = OrderSerializer(order)
                return Response(serializer.data)
            except Order.DoesNotExist:
                return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Get all orders for the current user
            orders = Order.objects.filter(user=request.user).order_by('-created_at')
            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data)

    def post(self, request):
        # Prepare order data (excluding items)
        order_data = {
            'user': request.user,
            'payment': request.data.get('payment', Order.PaymentChoice.COD),  # Default payment method
        }

        # Validate payment method
        payment_method = request.data.get('payment', Order.PaymentChoice.COD)
        if payment_method not in [choice[0] for choice in Order.PaymentChoice.choices]:
            return Response({'error': 'Invalid payment method'}, status=status.HTTP_400_BAD_REQUEST)

        # Create the order
        order = Order.objects.create(**order_data)

        # Handle items separately after order is created
        items_data = request.data.get('items', [])
        order_items = []
        for item_data in items_data:
            from .models import Products
            # Get the product based on product_id from the request
            product_id = item_data.get('product_id')
            quantity_requested = item_data.get('quantity', 1)
            if product_id:
                try:
                    product = Products.objects.get(id=product_id)
                    # Check stock availability
                    if product.stock < quantity_requested:
                        # Rollback: delete the order since insufficient stock
                        order.delete()
                        return Response(
                            {'error': f'Insufficient stock for {product.name}. Available: {product.stock}, Requested: {quantity_requested}'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    # Create order item
                    order_item = OrderItem.objects.create(
                        product=product,
                        quantity=quantity_requested
                    )
                    order_items.append(order_item)

                    # Decrease product stock
                    product.stock -= quantity_requested
                    if product.stock <= 0:
                        product.status = product.StatusofProduct.OUT_OF_STOCK
                    product.save()
                except Products.DoesNotExist:
                    # Rollback: delete the order since we can't create the items
                    order.delete()
                    return Response(
                        {'error': f'Product with id {product_id} does not exist'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # Add order items to the order
        order.order_item.set(order_items)

        # Update order items for discount days
        try:
            for item in order.order_item.all():
                # Check if item has a valid product
                if item.product and item.product.user:
                    current_date = timezone.now().date()
                    try:
                        from discounts.models import DiscountDay
                        discount_day = DiscountDay.objects.get(
                            seller=item.product.user,
                            date=current_date,
                            is_active=True
                        )
                        item.is_discount_day = True
                        item.save()
                    except DiscountDay.DoesNotExist:
                        item.is_discount_day = False
                        item.save()
        except Exception as e:
            # Log the error but don't fail the order
            print(f"Error updating discount days: {e}")
            pass  # Continue with the order even if discount update fails

        # Serialize the created order for response
        response_serializer = OrderSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, order_number):
        """
        Update an existing order. Only allows updating status and payment method.
        Order items cannot be modified after creation to maintain order integrity.
        """
        try:
            order = Order.objects.get(number=order_number, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        # Only allow updating of specific fields (not order items)
        allowed_fields = ['status', 'payment']
        update_data = {}

        for field in allowed_fields:
            if field in request.data:
                update_data[field] = request.data[field]

        serializer = OrderSerializer(order, data=update_data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, order_number):
        """
        Partially update an existing order. Only allows updating status and payment method.
        Order items cannot be modified after creation to maintain order integrity.
        """
        try:
            order = Order.objects.get(number=order_number, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        # Only allow updating of specific fields (not order items)
        allowed_fields = ['status', 'payment']
        update_data = {}

        for field in allowed_fields:
            if field in request.data:
                update_data[field] = request.data[field]

        serializer = OrderSerializer(order, data=update_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, order_number):
        try:
            order = Order.objects.get(number=order_number, user=request.user)
            order.delete()
            return Response({'message': 'Order deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


class PaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_number = request.data.get('order_number')
        amount_paid = request.data.get('amount')
        card_number = request.data.get('card_number')

        if not order_number:
            return Response({'error': 'Order number is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not amount_paid:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Convert amount to decimal for comparison
            from decimal import Decimal
            amount_paid = Decimal(str(amount_paid))

            # Get the order
            order = Order.objects.get(number=order_number, user=request.user)

            # Get the total amount for this order
            total_amount = order.total_amount

            # Check if the amount paid is at least the total amount
            if amount_paid < total_amount:
                return Response({
                    'error': f'Payment amount is less than order total. Required: {total_amount}, Provided: {amount_paid}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate payment method specific requirements
            if order.payment == Order.PaymentChoice.COD:
                # For Cash on Delivery, no card number is required
                if card_number:
                    return Response({
                        'error': f'Card number is not required for {order.payment}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # For non-COD payments, card number is required
                if not card_number:
                    return Response({
                        'error': f'Card number is required for {order.payment}'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Validate card number format (16 digits)
                if not isinstance(card_number, str) or len(card_number.replace(' ', '')) != 16 or not card_number.replace(' ', '').isdigit():
                    return Response({
                        'error': 'Card number must be exactly 16 digits'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Process the payment
            order.is_paid = True
            # Optionally update status to reflect payment
            if order.status == 'Pending':
                order.status = 'On Delivery'
            order.save()

            return Response({
                'message': 'Payment processed successfully',
                'order_number': order_number,
                'total_amount': total_amount,
                'is_paid': True,
                'payment_method': order.payment
            }, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({'error': 'Invalid amount format'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Payment processing error: {str(e)}'}, status=status.HTTP_500_INTERNAL_ERROR)


class InventoryUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            product = Products.objects.get(id=pk, user=request.user)

            # Get the restock amount
            restock_amount = request.data.get('restock', 0)
            if restock_amount and int(restock_amount) > 0:
                product.stock += int(restock_amount)
                if product.stock > 0:
                    product.status = product.StatusofProduct.AVAILABLE
                product.save()

                return Response({
                    'message': f'Product restocked successfully. New stock: {product.stock}',
                    'current_stock': product.stock
                })

            # Or update stock directly
            new_stock = request.data.get('stock', None)
            if new_stock is not None:
                product.stock = int(new_stock)
                if product.stock > 0:
                    product.status = product.StatusofProduct.AVAILABLE
                else:
                    product.status = product.StatusofProduct.OUT_OF_STOCK
                product.save()

                return Response({
                    'message': 'Product stock updated successfully',
                    'current_stock': product.stock
                })

            return Response(
                {'error': 'Please provide either "restock" or "stock" value'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Products.DoesNotExist:
            return Response({'error': 'Product not found or unauthorized'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({'error': 'Stock value must be a valid number'}, status=status.HTTP_400_BAD_REQUEST)


class SoftDeletedProductsView(APIView):
    """View to handle soft deleted products"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve soft deleted products for the authenticated user"""
        # Only show soft deleted products that belong to the current user
        deleted_products = Products.get_deleted_products_for_user(request.user)
        serializer = ProductSerializer(deleted_products, many=True)
        return Response(serializer.data)


class RestoreProductView(APIView):
    """View to restore soft deleted products"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Restore a soft deleted product"""
        try:
            # Find the soft deleted product that belongs to the user
            product = Products.all_objects.get(id=pk, user=request.user)

            # Check if the product is actually deleted
            if product.deleted_at is None:
                return Response(
                    {'error': 'Product is not soft deleted'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Restore the product
            product.restore()

            serializer = ProductSerializer(product)
            return Response({
                'message': 'Product restored successfully',
                'product': serializer.data
            }, status=status.HTTP_200_OK)

        except Products.DoesNotExist:
            return Response(
                {'error': 'Product not found or unauthorized'},
                status=status.HTTP_404_NOT_FOUND
            )