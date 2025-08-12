from django.db import models
from users.models import Franchise

class Payment(models.Model):
    franchise = models.ForeignKey(Franchise, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    payment_screenshot = models.ImageField(upload_to="payment_screenshots/", blank=True, null=True)
    status = models.CharField(max_length=10, choices=[
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id or 'No ID'} - {self.status}"
