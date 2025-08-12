from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import re

from users.models import Franchise, StaffModel
from .payment_models import (
    Payment, PaymentMethod, PaymentPlan, PaymentGateway,
    PaymentTransaction, PaymentReminder
)


class PaymentMethodForm(forms.ModelForm):
    """Form for payment method management"""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Payment Method Name"
        }),
        validators=[
            forms.RegexValidator(
                regex=r'^[a-zA-Z0-9\s\-_&.]+$',
                message='Name should contain only letters, numbers, spaces, hyphens, underscores, ampersands, and periods'
            )
        ]
    )
    
    payment_type = forms.ChoiceField(
        choices=PaymentMethod.PAYMENT_TYPES,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "placeholder": "Description",
            "rows": 3
        })
    )
    
    processing_fee = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Processing Fee",
            "step": "0.01"
        })
    )
    
    processing_fee_type = forms.ChoiceField(
        choices=[
            ('fixed', 'Fixed Amount'),
            ('percentage', 'Percentage')
        ],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    min_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Minimum Amount",
            "step": "0.01"
        })
    )
    
    max_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Maximum Amount",
            "step": "0.01"
        })
    )
    
    class Meta:
        model = PaymentMethod
        fields = [
            'name', 'payment_type', 'description', 'processing_fee',
            'processing_fee_type', 'min_amount', 'max_amount', 'is_active'
        ]
    
    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        min_amount = cleaned_data.get('min_amount')
        max_amount = cleaned_data.get('max_amount')
        
        if min_amount and max_amount and min_amount >= max_amount:
            raise ValidationError("Minimum amount must be less than maximum amount")
        
        return cleaned_data


class PaymentPlanForm(forms.ModelForm):
    """Form for payment plan management"""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Plan Name"
        }),
        validators=[
            forms.RegexValidator(
                regex=r'^[a-zA-Z0-9\s\-_&.]+$',
                message='Name should contain only letters, numbers, spaces, hyphens, underscores, ampersands, and periods'
            )
        ]
    )
    
    plan_type = forms.ChoiceField(
        choices=PaymentPlan.PLAN_TYPES,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Plan Amount",
            "step": "0.01"
        })
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "placeholder": "Plan Description",
            "rows": 3
        })
    )
    
    grace_period_days = forms.IntegerField(
        min_value=0,
        max_value=365,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Grace Period (days)"
        })
    )
    
    late_fee = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Late Fee",
            "step": "0.01"
        })
    )
    
    late_fee_type = forms.ChoiceField(
        choices=[
            ('fixed', 'Fixed Amount'),
            ('percentage', 'Percentage')
        ],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    class Meta:
        model = PaymentPlan
        fields = [
            'name', 'plan_type', 'amount', 'description',
            'grace_period_days', 'late_fee', 'late_fee_type', 'is_active'
        ]


class PaymentForm(forms.ModelForm):
    """Form for payment creation and management"""
    
    franchise = forms.ModelChoiceField(
        queryset=Franchise.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Select Franchise"
    )
    
    payment_plan = forms.ModelChoiceField(
        queryset=PaymentPlan.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Select Payment Plan (Optional)"
    )
    
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Select Payment Method (Optional)"
    )
    
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Payment Amount",
            "step": "0.01"
        })
    )
    
    due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date"
        })
    )
    
    reference_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Reference Number (Optional)"
        })
    )
    
    payment_screenshot = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            "class": "form-control",
            "accept": "image/*"
        }),
        help_text="Upload payment screenshot (JPG, PNG, GIF)"
    )
    
    payment_proof = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            "class": "form-control"
        }),
        help_text="Upload additional payment proof (PDF, DOC, DOCX)"
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "placeholder": "Additional Notes",
            "rows": 3
        })
    )
    
    assigned_to = forms.ModelChoiceField(
        queryset=StaffModel.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Assign to Staff (Optional)"
    )
    
    class Meta:
        model = Payment
        fields = [
            'franchise', 'payment_plan', 'payment_method', 'amount',
            'due_date', 'reference_number', 'payment_screenshot',
            'payment_proof', 'notes', 'assigned_to'
        ]
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set user for conditional field handling
        self.user = user
        
        # Add help text
        self.fields['amount'].help_text = "Enter the payment amount in rupees"
        self.fields['due_date'].help_text = "Set due date for payment (optional)"
    
    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        payment_method = cleaned_data.get('payment_method')
        due_date = cleaned_data.get('due_date')
        
        # Validate amount against payment method limits
        if payment_method and amount:
            if amount < payment_method.min_amount:
                raise ValidationError(
                    f"Amount must be at least ₹{payment_method.min_amount}"
                )
            if amount > payment_method.max_amount:
                raise ValidationError(
                    f"Amount cannot exceed ₹{payment_method.max_amount}"
                )
        
        # Validate due date
        if due_date:
            from django.utils import timezone
            if due_date < timezone.now().date():
                raise ValidationError("Due date cannot be in the past")
        
        return cleaned_data
    
    def clean_payment_screenshot(self):
        """Validate payment screenshot"""
        screenshot = self.cleaned_data.get('payment_screenshot')
        if screenshot:
            # Check file size (max 5MB)
            if screenshot.size > 5 * 1024 * 1024:
                raise ValidationError("Screenshot size cannot exceed 5MB")
            
            # Check file extension
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            file_extension = screenshot.name.lower()
            
            if not any(file_extension.endswith(ext) for ext in allowed_extensions):
                raise ValidationError(
                    "Only JPG, PNG, and GIF files are allowed for screenshots"
                )
        
        return screenshot
    
    def clean_payment_proof(self):
        """Validate payment proof document"""
        proof = self.cleaned_data.get('payment_proof')
        if proof:
            # Check file size (max 10MB)
            if proof.size > 10 * 1024 * 1024:
                raise ValidationError("Proof document size cannot exceed 10MB")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx']
            file_extension = proof.name.lower()
            
            if not any(file_extension.endswith(ext) for ext in allowed_extensions):
                raise ValidationError(
                    "Only PDF, DOC, and DOCX files are allowed for proof documents"
                )
        
        return proof


class PaymentVerificationForm(forms.Form):
    """Form for payment verification by admin/staff"""
    
    VERIFICATION_CHOICES = [
        ('verified', 'Verify Payment'),
        ('rejected', 'Reject Payment'),
        ('under_review', 'Mark Under Review')
    ]
    
    verification_action = forms.ChoiceField(
        choices=VERIFICATION_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "placeholder": "Verification Notes",
            "rows": 3
        })
    )
    
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "placeholder": "Rejection Reason (required if rejecting)",
            "rows": 3
        })
    )
    
    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        verification_action = cleaned_data.get('verification_action')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if verification_action == 'rejected' and not rejection_reason:
            raise ValidationError("Rejection reason is required when rejecting a payment")
        
        return cleaned_data


class PaymentSearchForm(forms.Form):
    """Form for searching and filtering payments"""
    
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Search by franchise, transaction ID, or reference..."
        })
    )
    
    franchise_filter = forms.ModelChoiceField(
        queryset=Franchise.objects.all(),
        required=False,
        empty_label="All Franchises",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    status_filter = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Payment.PAYMENT_STATUS,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    verification_filter = forms.ChoiceField(
        choices=[('', 'All Verification Statuses')] + Payment.VERIFICATION_STATUS,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    payment_method_filter = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.filter(is_active=True),
        required=False,
        empty_label="All Payment Methods",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date"
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date"
        })
    )
    
    min_amount = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Min Amount",
            "step": "0.01"
        })
    )
    
    max_amount = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Max Amount",
            "step": "0.01"
        })
    )
    
    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        min_amount = cleaned_data.get('min_amount')
        max_amount = cleaned_data.get('max_amount')
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date cannot be after end date")
        
        # Validate amount range
        if min_amount and max_amount and min_amount > max_amount:
            raise ValidationError("Minimum amount cannot be greater than maximum amount")
        
        return cleaned_data


class PaymentGatewayForm(forms.ModelForm):
    """Form for payment gateway configuration"""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Gateway Name"
        })
    )
    
    gateway_type = forms.ChoiceField(
        choices=PaymentGateway.GATEWAY_TYPES,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    api_key = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "API Key"
        })
    )
    
    secret_key = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Secret Key"
        })
    )
    
    webhook_secret = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Webhook Secret"
        })
    )
    
    configuration = forms.JSONField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "placeholder": "Additional Configuration (JSON)",
            "rows": 5
        })
    )
    
    class Meta:
        model = PaymentGateway
        fields = [
            'name', 'gateway_type', 'api_key', 'secret_key',
            'webhook_secret', 'test_mode', 'configuration', 'is_active'
        ]
    
    def clean_configuration(self):
        """Validate JSON configuration"""
        configuration = self.cleaned_data.get('configuration')
        if configuration:
            try:
                import json
                if isinstance(configuration, str):
                    json.loads(configuration)
            except (json.JSONDecodeError, TypeError):
                raise ValidationError("Invalid JSON configuration")
        return configuration


class PaymentReminderForm(forms.ModelForm):
    """Form for payment reminder management"""
    
    reminder_type = forms.ChoiceField(
        choices=PaymentReminder.REMINDER_TYPES,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "placeholder": "Reminder Message",
            "rows": 4
        })
    )
    
    scheduled_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            "class": "form-control",
            "type": "datetime-local"
        })
    )
    
    class Meta:
        model = PaymentReminder
        fields = ['reminder_type', 'message', 'scheduled_date']
    
    def clean_scheduled_date(self):
        """Validate scheduled date"""
        scheduled_date = self.cleaned_data.get('scheduled_date')
        if scheduled_date:
            from django.utils import timezone
            if scheduled_date <= timezone.now():
                raise ValidationError("Scheduled date must be in the future")
        return scheduled_date


class BulkPaymentForm(forms.Form):
    """Form for bulk payment operations"""
    
    OPERATION_CHOICES = [
        ('verify', 'Verify Selected Payments'),
        ('reject', 'Reject Selected Payments'),
        ('assign', 'Assign to Staff'),
        ('export', 'Export Selected Payments'),
    ]
    
    operation = forms.ChoiceField(
        choices=OPERATION_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    payment_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "placeholder": "Operation Notes",
            "rows": 3
        })
    )
    
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "placeholder": "Rejection Reason (required if rejecting)",
            "rows": 3
        })
    )
    
    assigned_to = forms.ModelChoiceField(
        queryset=StaffModel.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Select Staff Member"
    )
    
    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        operation = cleaned_data.get('operation')
        rejection_reason = cleaned_data.get('rejection_reason')
        assigned_to = cleaned_data.get('assigned_to')
        
        if operation == 'reject' and not rejection_reason:
            raise ValidationError("Rejection reason is required when rejecting payments")
        
        if operation == 'assign' and not assigned_to:
            raise ValidationError("Staff member is required when assigning payments")
        
        return cleaned_data
