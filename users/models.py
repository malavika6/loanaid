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
    password = models.CharField(max_length=128, null=True)
    profile_picture = models.ImageField(upload_to="staff_profiles/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    can_create_loans = models.BooleanField(default=True)
    can_assign_franchises = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=True)
    managed_by = models.ForeignKey('AdminModel', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)


    def save(self, *args, **kwargs):
        if self.profile_completed and not self.adhaar_no:
            raise ValueError("Aadhaar number must be added before marking profile as completed.")

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
    
    def check_password(self, raw_password):
        """Check if the provided password matches the stored hash"""
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)
    
    def set_password(self, raw_password):
        """Set the password with proper hashing"""
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)


def generate_referral_code():
    return uuid.uuid4().hex[:8].upper()


class Franchise(models.Model):
    franchise_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey("StaffModel", on_delete=models.CASCADE, null=True, blank=True)
    franchise_name = models.CharField(max_length=255)
    franchise_owner = models.CharField(max_length=255)
    franchise_place = models.CharField(max_length=255, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="franchise_profiles/", null=True, blank=True)
    is_franchise = models.BooleanField(default=False)
    screenshot = models.FileField(upload_to="payment_screenshots/", blank=True, null=True)
    payment_status = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    mobile_no = models.CharField(
        max_length=10,
        validators=[RegexValidator(r"^\d{10}$", message="Enter a valid 10-digit mobile number.")]
    )
    password = models.CharField(max_length=128, null=True)
    referral_code = models.CharField(max_length=8, unique=True, default=generate_referral_code)
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
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith("pbkdf2_"):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.franchise_name
    
    def check_password(self, raw_password):
        """Check if the provided password matches the stored hash"""
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)
    
    def set_password(self, raw_password):
        """Set the password with proper hashing"""
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)
