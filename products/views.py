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
        # Only return non-deleted products
        products = Products.objects.filter(deleted_at__isnull=True)
        view = ProductSerializer(products, many=True)
        return Response(view.data)


class ProductRetriveUpdateDelete(APIView):
    def get(self, request, pk):
        try:
            # Only return non-deleted products
            product = Products.objects.filter(id=pk, deleted_at__isnull=True).first()
            if product is None:
                return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = ProductSerializer(product)
            return Response(serializer.data)
        except Products.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

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

    def post(self, request):
        # Validate that card number is provided
        card_number = request.data.get('card_number')
        if card_number is None:
            return Response({'message': 'Please input Credit Card No'})

        # Prepare order data (excluding items and card_number)
        order_data = {
            'user': request.user,
            'payment': request.data.get('payment', 'Cash on Delivery'),  # Default payment method
        }

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
        # Validate that card number is provided
        card_number = request.data.get('card_number')
        if card_number is None:
            return Response({'message': 'Please input Credit Card No'})

        # Prepare order data (excluding items and card_number)
        order_data = {
            'user': request.user,
            'payment': request.data.get('payment', 'Cash on Delivery'),  # Default payment method
        }

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

    def delete(self, request, order_number):
        try:
            order = Order.objects.get(number=order_number, user=request.user)
            order.delete()
            return Response({'message': 'Order deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


class PaymentView(APIView):
    def post(self, request):
        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            card_number = serializer.validated_data.get('card_number')
            if card_number is None:
                return Response({'message': 'Please input creadit card No.'})
            return Response({'message': 'Payment processed successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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