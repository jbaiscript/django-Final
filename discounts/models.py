from django.db import models
from django.conf import settings
from clients.models import UserProfile

class DiscountDay(models.Model):
    """
    Model to track special discount days for sellers
    """
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='discount_days')
    date = models.DateField()
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Discount percentage (e.g., 10.00 for 10%)")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Discount Day for {self.seller.username} on {self.date} ({self.discount_percentage}% off)"

    class Meta:
        unique_together = ('seller', 'date')
        ordering = ['-date']
