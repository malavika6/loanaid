from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password
from django.db import models
import uuid


class AdminModel(models.Model):
    admin_id = models.AutoField(primary_key=True)
    admin_first_name = models.CharField(max_length=100)
    admin_last_name = models.CharField(max_length=100, blank=True, null=True)
    admin_email = models.EmailField(unique=True)
    admin_phone = models.CharField(
        max_length=10,
        validators=[RegexValidator(r"^\d{10}$", message="Enter a valid 10-digit mobile number.")],
        null=True,
        blank=True,
    )
    admin_password = models.CharField(max_length=128)
    is_superadmin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.admin_password and not self.admin_password.startswith("pbkdf2_"):
            self.admin_password = make_password(self.admin_password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.admin_first_name} {self.admin_last_name or ''}".strip()

    def get_full_name(self):
        return f"{self.admin_first_name} {self.admin_last_name or ''}".strip()


class StaffModel(models.Model):
    staff_id = models.AutoField(primary_key=True)
    employee_id = models.CharField(max_length=10, unique=True, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone_no = models.CharField(
        max_length=10,
        validators=[RegexValidator(r"^\d{10}$", message="Enter a valid 10-digit mobile number.")]
    )
    password = models.CharField(max_length=128, null=True, blank=True)
    profile_picture = models.ImageField(upload_to="staff_profiles/", null=True, blank=True)
    is_active = models.BooleanField(default=False)  # Changed to False by default
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)


    def save(self, *args, **kwargs):

        if self.password and not self.password.startswith("pbkdf2_"):
            self.password = make_password(self.password)

        if not self.employee_id:
            last_staff = StaffModel.objects.exclude(employee_id__isnull=True).order_by('-staff_id').first()
            if last_staff and last_staff.employee_id and last_staff.employee_id.split('-')[-1].isdigit():
                last_number = int(last_staff.employee_id.split('-')[-1]) + 1
            else:
                last_number = 1001
            self.employee_id = f"EMP-{last_number}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''}".strip()

    def get_full_name(self):
        return f"{self.first_name} {self.last_name or ''}".strip()


def generate_franchise_referral_code():
    """Generate referral code based on franchise ID (FR001, FR002, etc.)"""
    last_franchise = Franchise.objects.order_by('-franchise_id').first()
    if last_franchise:
        # Extract number from the last franchise_id and increment
        try:
            last_number = int(str(last_franchise.franchise_id)[-3:]) + 1
        except (ValueError, IndexError):
            last_number = 1
    else:
        last_number = 1
    return f"FR{last_number:03d}"


class Franchise(models.Model):
    FRANCHISE_TYPE_CHOICES = [
        ('business_associate', 'Business Associate'),
        ('premium_franchise', 'Premium Franchise'),
        ('virtual_franchise', 'Virtual Franchise'),
    ]
    
    franchise_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey("StaffModel", on_delete=models.CASCADE, null=True, blank=True)
    franchise_name = models.CharField(max_length=255)
    franchise_owner = models.CharField(max_length=255)
    franchise_place = models.CharField(max_length=255, blank=True, null=True)
    franchise_type = models.CharField(
        max_length=20,
        choices=FRANCHISE_TYPE_CHOICES,
        default='business_associate',
        verbose_name="Franchise Type"
    )
    profile_picture = models.ImageField(upload_to="franchise_profiles/", null=True, blank=True)
    is_franchise = models.BooleanField(default=True)
    screenshot = models.FileField(upload_to="payment_screenshots/", blank=True, null=True)
    payment_status = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    mobile_no = models.CharField(
        max_length=10,
        validators=[RegexValidator(r"^\d{10}$", message="Enter a valid 10-digit mobile number.")]
    )
    password = models.CharField(max_length=128, null=True)
    referral_code = models.CharField(max_length=8, unique=True, default=generate_franchise_referral_code, verbose_name="Franchise Referral Code")
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_franchises', verbose_name="Referred By")
    aadhar = models.CharField(max_length=50, blank=True, null=True)
    GST = models.CharField(max_length=50, blank=True, null=True)
    pan = models.CharField(max_length=50, blank=True, null=True)
    ac_no = models.CharField(
        max_length=20,
        validators=[RegexValidator(r"^\d{9,18}$", message="Enter a valid account number.")],
        blank=True,
        null=True,
    )
    ifsc_code = models.CharField(
        max_length=11,
        validators=[RegexValidator(r"^[A-Z]{4}0[A-Z0-9]{6}$", message="Enter a valid IFSC code.")],
        blank=True,
        null=True,
    )
    
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith("pbkdf2_"):
            self.password = make_password(self.password)
        
        # Generate referral code based on franchise ID if not already set
        if not self.referral_code:
            # First save to get the franchise_id
            super().save(*args, **kwargs)
            # Now generate referral code based on the franchise_id
            franchise_number = str(self.franchise_id)[-3:]  # Get last 3 characters
            try:
                number = int(franchise_number)
                self.referral_code = f"FR{number:03d}"
            except ValueError:
                # Fallback if conversion fails
                self.referral_code = f"FR{self.franchise_id.hex[:3].upper()}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.franchise_name
    
    def is_profile_complete(self):
        """Check if franchise profile is complete"""
        required_fields = [
            self.aadhar, self.pan, 
            self.ac_no, self.ifsc_code
        ]
        return all(field for field in required_fields)
    
    def get_profile_completion_percentage(self):
        """Get profile completion percentage"""
        required_fields = [
            self.aadhar, self.pan, 
            self.ac_no, self.ifsc_code
        ]
        optional_fields = [self.GST]  # GST is optional
        total_fields = len(required_fields) + len(optional_fields)
        completed = sum(1 for field in required_fields if field) + sum(1 for field in optional_fields if field)
        return (completed / total_fields) * 100


class Wallet(models.Model):
    wallet_id = models.AutoField(primary_key=True)
    franchise = models.OneToOneField(Franchise, on_delete=models.CASCADE, related_name='wallet')
    allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Allowance")
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Commission")
    incentive = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Incentive")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.franchise.franchise_name}"

    def get_total_balance(self):
        """Calculate total wallet balance"""
        return self.allowance + self.commission + self.incentive

    class Meta:
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"
