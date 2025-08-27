from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

from users.models import Franchise, AdminModel, StaffModel


class PaymentMethod(models.Model):
    """Payment method configuration"""
    PAYMENT_TYPES = [
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('card', 'Credit/Debit Card'),
        ('cheque', 'Cheque'),
        ('cash', 'Cash'),
        ('online', 'Online Payment Gateway'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    processing_fee = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    processing_fee_type = models.CharField(
        max_length=10,
        choices=[
            ('fixed', 'Fixed Amount'),
            ('percentage', 'Percentage')
        ],
        default='fixed'
    )
    min_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    max_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=999999.99,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_payment_type_display()})"
    
    def calculate_processing_fee(self, amount):
        """Calculate processing fee for given amount"""
        if self.processing_fee_type == 'fixed':
            return self.processing_fee
        else:
            return (amount * self.processing_fee) / 100


class PaymentPlan(models.Model):
    """Payment plan configuration for franchises"""
    PLAN_TYPES = [
        ('one_time', 'One Time'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    grace_period_days = models.PositiveIntegerField(
        default=0,
        help_text="Grace period in days after due date"
    )
    late_fee = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    late_fee_type = models.CharField(
        max_length=10,
        choices=[
            ('fixed', 'Fixed Amount'),
            ('percentage', 'Percentage')
        ],
        default='fixed'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - ₹{self.amount} ({self.get_plan_type_display()})"
    
    def calculate_late_fee(self, overdue_days, overdue_amount):
        """Calculate late fee for overdue payments"""
        if overdue_days <= self.grace_period_days:
            return Decimal('0.00')
        
        if self.late_fee_type == 'fixed':
            return self.late_fee
        else:
            return (overdue_amount * self.late_fee) / 100


class Payment(models.Model):
    """Enhanced payment model with comprehensive tracking"""
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('disputed', 'Disputed'),
    ]
    
    VERIFICATION_STATUS = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('under_review', 'Under Review'),
    ]
    
    # Basic payment information
    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    franchise = models.ForeignKey(
        Franchise, 
        on_delete=models.CASCADE,
        related_name='payments'
    )
    payment_plan = models.ForeignKey(
        PaymentPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    
    # Amount and fees
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    processing_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )
    late_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Payment details
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    payment_screenshot = models.ImageField(
        upload_to="payment_screenshots/", 
        blank=True, 
        null=True
    )
    payment_proof = models.FileField(
        upload_to="payment_proofs/",
        blank=True,
        null=True,
        help_text="Additional payment proof documents"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS, 
        default='pending'
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS,
        default='pending'
    )
    
    # Timestamps
    due_date = models.DateField(null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    verification_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Assignment and notes
    assigned_to = models.ForeignKey(
        StaffModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_payments'
    )
    verified_by = models.ForeignKey(
        AdminModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments'
    )
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'verification_status']),
            models.Index(fields=['franchise', 'created_at']),
            models.Index(fields=['due_date', 'status']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_id} - {self.franchise.franchise_name} - ₹{self.amount}"
    
    def save(self, *args, **kwargs):
        """Calculate total amount before saving"""
        if not self.total_amount:
            self.total_amount = self.amount + self.processing_fee + self.late_fee
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if payment is overdue"""
        if self.due_date and self.status in ['pending', 'processing']:
            return timezone.now().date() > self.due_date
        return False
    
    @property
    def overdue_days(self):
        """Calculate number of overdue days"""
        if self.is_overdue:
            return (timezone.now().date() - self.due_date).days
        return 0
    
    @property
    def can_be_verified(self):
        """Check if payment can be verified"""
        return (
            self.status == 'completed' and 
            self.verification_status == 'pending' and
            self.payment_screenshot
        )
    
    def mark_as_verified(self, verified_by, notes=""):
        """Mark payment as verified"""
        self.verification_status = 'verified'
        self.verified_by = verified_by
        self.verification_date = timezone.now()
        self.notes = notes
        self.save()
    
    def mark_as_rejected(self, verified_by, reason):
        """Mark payment as rejected"""
        self.verification_status = 'rejected'
        self.verified_by = verified_by
        self.verification_date = timezone.now()
        self.rejection_reason = reason
        self.save()


class PaymentTransaction(models.Model):
    """Detailed transaction tracking"""
    TRANSACTION_TYPES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
        ('fee', 'Fee'),
    ]
    
    transaction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    description = models.TextField()
    gateway_response = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.payment.payment_id}"


class PaymentReminder(models.Model):
    """Payment reminder system"""
    REMINDER_TYPES = [
        ('due_date', 'Due Date Reminder'),
        ('overdue', 'Overdue Reminder'),
        ('grace_period', 'Grace Period Reminder'),
        ('custom', 'Custom Reminder'),
    ]
    
    reminder_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='reminders'
    )
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    message = models.TextField()
    scheduled_date = models.DateTimeField()
    sent_date = models.DateTimeField(null=True, blank=True)
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['scheduled_date']
    
    def __str__(self):
        return f"{self.reminder_type} - {self.payment.payment_id} - {self.scheduled_date}"
    
    @property
    def is_due(self):
        """Check if reminder is due to be sent"""
        return (
            not self.is_sent and 
            timezone.now() >= self.scheduled_date
        )


class PaymentGateway(models.Model):
    """Payment gateway configuration"""
    GATEWAY_TYPES = [
        ('razorpay', 'Razorpay'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('custom', 'Custom Gateway'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    gateway_type = models.CharField(max_length=20, choices=GATEWAY_TYPES)
    is_active = models.BooleanField(default=True)
    api_key = models.CharField(max_length=255, blank=True)
    secret_key = models.CharField(max_length=255, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    test_mode = models.BooleanField(default=True)
    configuration = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = "Payment Gateways"
    
    def __str__(self):
        return f"{self.name} ({self.get_gateway_type_display()})"
    
    @property
    def is_test_mode(self):
        """Check if gateway is in test mode"""
        return self.test_mode
    
    def get_configuration(self):
        """Get gateway configuration"""
        return self.configuration or {}
