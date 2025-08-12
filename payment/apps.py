from django.apps import AppConfig

class PaymentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payment'  # ✅ This must match the actual app folder name: 'staff'

