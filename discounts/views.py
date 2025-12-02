from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime
from .serializers import DiscountDaySerializer, DiscountDayCreateSerializer
from .models import DiscountDay
from products.models import OrderItem
from clients.models import UserProfile


class DiscountDayView(APIView):
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.request.method == 'GET':
            # Allow unauthenticated users to view discount days
            return []
        else:
            # Require authentication for other methods (POST, PUT, etc.)
            return [IsAuthenticated()]

    def get(self, request):
        # Check if stats are requested by URL path or via query param
        if ('/api/seller/stats' in request.path or
            ('/api/promotions' in request.path and request.query_params.get('view') == 'stats')):
            # If accessed via stats path, delegate to SellerStatsView
            stats_view = SellerStatsView()
            return stats_view.get(request)

        # Return discount days (original functionality)
        # For public view, show all discount days, not just seller's
        discount_days = DiscountDay.objects.all().order_by('-date')
        serializer = DiscountDaySerializer(discount_days, many=True)
        return Response(serializer.data)

    def post(self, request):
        user = request.user
        try:
            user_profile = UserProfile.objects.get(user=user)
            if user_profile.role != 'seller':
                return Response({'error': 'Only sellers can create discount days'}, status=status.HTTP_403_FORBIDDEN)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['seller'] = user.id
        serializer = DiscountDayCreateSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            discount_day = serializer.save(seller=user)
            response_serializer = DiscountDaySerializer(discount_day)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DiscountDayDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_discount_day(self, pk, user):
        try:
            return DiscountDay.objects.get(id=pk, seller=user)
        except DiscountDay.DoesNotExist:
            return None

    def get(self, request, pk):
        discount_day = self._get_discount_day(pk, request.user)
        if discount_day is None:
            return Response({'error': 'Discount day not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = DiscountDaySerializer(discount_day)
        return Response(serializer.data)

    def patch(self, request, pk):
        discount_day = self._get_discount_day(pk, request.user)
        if discount_day is None:
            return Response({'error': 'Discount day not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'date' in request.data:
            new_date = request.data['date']
            if datetime.strptime(new_date, '%Y-%m-%d').date() < timezone.now().date():
                return Response({'error': 'Discount date cannot be in the past.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DiscountDayCreateSerializer(
            discount_day, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            discount_day = serializer.save()
            response_serializer = DiscountDaySerializer(discount_day)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        discount_day = self._get_discount_day(pk, request.user)
        if discount_day is None:
            return Response({'error': 'Discount day not found'}, status=status.HTTP_404_NOT_FOUND)

        discount_day.delete()
        return Response({'message': 'Discount day deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


class SellerStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        stats_type = request.GET.get('type', 'discount')

        if stats_type == 'discount':
            date_str = request.GET.get('date')
            if date_str:
                return self._get_discount_day_stats_for_date(user, date_str)
            else:
                return self._get_all_discount_day_stats(user)
        elif stats_type == 'non-discount':
            start_date_str = request.GET.get('start_date')
            end_date_str = request.GET.get('end_date')
            return self._get_non_discount_day_stats(user, start_date_str, end_date_str)
        else:
            return Response({'error': 'Invalid type. Use "discount" or "non-discount".'}, status=status.HTTP_400_BAD_REQUEST)

    def _get_discount_day_stats_for_date(self, user, date_str):
        try:
            discount_day_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            discount_day = DiscountDay.objects.get(seller=user, date=discount_day_date)
            order_items = OrderItem.objects.filter(
                product__user=user, created_at__date=discount_day_date, is_discount_day=True
            )
            stats = self._calculate_stats(order_items)

            return Response({
                'discount_day_id': discount_day.id,
                'date': discount_day.date,
                'discount_percentage': discount_day.discount_percentage,
                **stats
            })
        except DiscountDay.DoesNotExist:
            return Response({'error': 'Discount day not found'}, status=status.HTTP_404_NOT_FOUND)

    def _get_all_discount_day_stats(self, user):
        discount_days = DiscountDay.objects.filter(seller=user)
        stats_list = []
        for discount_day in discount_days:
            order_items = OrderItem.objects.filter(
                product__user=user, created_at__date=discount_day.date, is_discount_day=True
            )
            stats = self._calculate_stats(order_items)
            stats['discount_day_id'] = discount_day.id
            stats['date'] = discount_day.date
            stats['discount_percentage'] = discount_day.discount_percentage
            stats_list.append(stats)

        summary = {
            'total_discount_days': len(stats_list),
            'total_items_sold_during_discount_days': sum(stat['total_items_sold'] for stat in stats_list),
            'total_profit_from_discount_days': sum(stat['total_profit'] for stat in stats_list),
            'total_discount_given': sum(stat['total_discount_amount'] for stat in stats_list),
        }

        return Response({
            'stats_type': 'discount_days',
            'discount_day_stats': stats_list,
            'summary': summary
        })

    def _get_non_discount_day_stats(self, user, start_date_str, end_date_str):
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            discount_days = DiscountDay.objects.filter(
                seller=user, date__range=[start_date, end_date], is_active=True
            ).values_list('date', flat=True)
            order_items = OrderItem.objects.filter(
                product__user=user, created_at__date__range=[start_date, end_date]
            ).exclude(created_at__date__in=list(discount_days), is_discount_day=True)
        else:
            # Default to current month if no dates provided
            current_month_start = timezone.now().replace(day=1).date()
            next_month = current_month_start.replace(day=28) + timezone.timedelta(days=4)
            current_month_end = next_month - timezone.timedelta(days=next_month.day)
            discount_days = DiscountDay.objects.filter(
                seller=user, date__month=timezone.now().month, date__year=timezone.now().year, is_active=True
            ).values_list('date', flat=True)
            order_items = OrderItem.objects.filter(
                product__user=user, created_at__month=timezone.now().month, created_at__year=timezone.now().year
            ).exclude(created_at__date__in=list(discount_days), is_discount_day=True)

        total_items = order_items.aggregate(total=Count('*'))['total'] or 0
        total_profit = sum(item.sub_total for item in order_items)

        return Response({
            'stats_type': 'non_discount_days',
            'stats': {
                'total_items_sold': total_items,
                'total_profit': total_profit
            }
        })

    def _calculate_stats(self, order_items):
        """Helper method to calculate stats from order items"""
        total_items = order_items.aggregate(total=Count('*'))['total'] or 0
        total_profit = sum(item.final_sub_total for item in order_items)
        total_original = sum(item.original_sub_total for item in order_items)
        total_discount = sum(item.discount_amount for item in order_items)

        return {
            'total_items_sold': total_items,
            'total_profit': total_profit,
            'total_original_revenue': total_original,
            'total_discount_amount': total_discount
        }

    def _get_products_sold_on_discount_days(self, user, date_str=None):
        """Get detailed information about products sold during discount days"""
        from products.models import OrderItem
        if date_str:
            # Get products sold on a specific discount day
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                discount_day = DiscountDay.objects.get(seller=user, date=target_date)
                order_items = OrderItem.objects.filter(
                    product__user=user,
                    created_at__date=target_date,
                    is_discount_day=True
                ).select_related('product')
            except DiscountDay.DoesNotExist:
                return Response({'error': 'Discount day not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Get products sold on all discount days for this seller
            discount_days = DiscountDay.objects.filter(seller=user)
            order_items = OrderItem.objects.filter(
                product__user=user,
                is_discount_day=True
            ).select_related('product')

        # Group items by product and discount day
        products_sold = {}
        for item in order_items:
            product_id = item.product.id
            product_name = item.product.name
            product_date = item.created_at.date()

            if product_id not in products_sold:
                products_sold[product_id] = {
                    'product_name': product_name,
                    'product_price': float(item.product.price),
                    'discount_days': {},
                    'total_quantity_sold': 0,
                    'total_revenue': 0
                }

            if product_date not in products_sold[product_id]['discount_days']:
                products_sold[product_id]['discount_days'][str(product_date)] = {
                    'quantity': 0,
                    'revenue': 0,
                    'discount_percentage': 0
                }

            # Get discount percentage for this day
            try:
                discount_day = DiscountDay.objects.get(seller=user, date=product_date)
                discount_percentage = discount_day.discount_percentage
            except DiscountDay.DoesNotExist:
                discount_percentage = 0

            products_sold[product_id]['discount_days'][str(product_date)]['quantity'] += item.quantity
            products_sold[product_id]['discount_days'][str(product_date)]['revenue'] += float(item.final_sub_total)
            products_sold[product_id]['discount_days'][str(product_date)]['discount_percentage'] = float(discount_percentage)

            products_sold[product_id]['total_quantity_sold'] += item.quantity
            products_sold[product_id]['total_revenue'] += float(item.final_sub_total)

        return Response({
            'products_sold_during_discount_days': list(products_sold.values()),
            'total_products_sold_during_discount_days': len(products_sold)
        })

    def get(self, request):
        user = request.user
        stats_type = request.GET.get('type', 'discount')

        if stats_type == 'discount':
            date_str = request.GET.get('date')
            if date_str:
                # Check if products parameter is provided to get detailed product info
                if request.GET.get('view') == 'products':
                    return self._get_products_sold_on_discount_days(user, date_str)
                else:
                    return self._get_discount_day_stats_for_date(user, date_str)
            else:
                # Check if products parameter is provided to get detailed product info
                if request.GET.get('view') == 'products':
                    return self._get_products_sold_on_discount_days(user)
                else:
                    return self._get_all_discount_day_stats(user)
        elif stats_type == 'non-discount':
            start_date_str = request.GET.get('start_date')
            end_date_str = request.GET.get('end_date')
            return self._get_non_discount_day_stats(user, start_date_str, end_date_str)
        else:
            return Response({'error': 'Invalid type. Use "discount" or "non-discount".'}, status=status.HTTP_400_BAD_REQUEST)
