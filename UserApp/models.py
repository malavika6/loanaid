from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password
from django.db import models
import uuid


class UserModel(models.Model):
    user_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    phone_number = models.CharField(
        max_length=10,
        unique=True,
        validators=[RegexValidator(r"^\d{10}$", message="Enter a valid 10-digit mobile number.")]
    )
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith("pbkdf2_"):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


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


class StaffModel(models.Model):
    staff_id = models.AutoField(primary_key=True)
    employee_id = models.CharField(max_length=10, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone_no = models.CharField(
        max_length=10,
        validators=[RegexValidator(r"^\d{10}$", message="Enter a valid 10-digit mobile number.")]
    )
    password = models.CharField(max_length=128, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    profile_completed = models.BooleanField(default=False)
    adhaar_no = models.CharField(max_length=100, null=True, blank=True)
    adhaar_img = models.FileField(upload_to="adhaar/", null=True, blank=True)
    pan_no = models.CharField(max_length=100, null=True, blank=True)
    pan_img = models.FileField(upload_to="pancard/", null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    ifsc_code = models.CharField(max_length=100, null=True, blank=True)
    account_no = models.CharField(max_length=100, null=True, blank=True)
    branch = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''}".strip()

    def save(self, *args, **kwargs):
        if self.profile_completed and not self.adhaar_no:
            raise ValueError("Aadhaar number must be added before marking profile as completed.")
        if not self.employee_id:
            last_staff = StaffModel.objects.exclude(employee_id__isnull=True).order_by('-staff_id').first()
            last_number = int(last_staff.employee_id.split('-')[-1]) + 1 if last_staff and last_staff.employee_id else 1001
            self.employee_id = f"EMP-{last_number}"
        super().save(*args, **kwargs)


def generate_referral_code():
    return uuid.uuid4().hex[:8].upper()


class Franchise(models.Model):
    franchise_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey("StaffModel", on_delete=models.CASCADE, null=True, blank=True)
    franchise_name = models.CharField(max_length=255)
    franchise_owner = models.CharField(max_length=255)
    franchise_place = models.CharField(max_length=255, blank=True, null=True, default="Not Provided")
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

class LoanModel(models.Model):
    loan_id = models.AutoField(primary_key=True)
    loan_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.loan_name


class BankModel(models.Model):
    bank_id = models.AutoField(primary_key=True)
    bank_name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.bank_name
    
class StatusModel(models.Model):
    status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.status_name


class LoanApplicationModel(models.Model):
    STATUS_CHOICES = [
        ('Accept', 'Accept'),
        ('Reject', 'Reject'),
        ('Not selected', 'Not selected'),
    ]

    form_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    place = models.CharField(max_length=100, null=True, blank=True)
    phone_no = models.CharField(max_length=15, null=True, blank=True)
    guaranter_name = models.CharField(max_length=100, null=True, blank=True)
    guaranter_phoneno = models.CharField(max_length=50, null=True, blank=True)
    guaranter_job = models.CharField(max_length=100, null=True, blank=True)
    guaranter_cibil_score = models.CharField(max_length=50, null=True, blank=True)
    guaranter_cibil_issue = models.TextField(null=True, blank=True)
    guaranter_it_payable = models.BooleanField(default=False)
    guaranter_years = models.IntegerField(null=True, blank=True)
    job = models.CharField(max_length=100, null=True, blank=True)
    cibil_score = models.CharField(max_length=100, null=True, blank=True)
    cibil_issue = models.TextField(null=True, blank=True)
    it_payable = models.BooleanField(default=False)
    years = models.IntegerField(null=True, blank=True)
    loan_name = models.ForeignKey(LoanModel, on_delete=models.SET_NULL, null=True, blank=True)
    loan_amount = models.DecimalField(max_digits=10, default=0, decimal_places=2, null=True, blank=True)
    followup_date = models.DateField(null=True)
    description = models.TextField(null=True, blank=True)
    status_name = models.ForeignKey(StatusModel, on_delete=models.SET_NULL, null=True, blank=True)
    application_description = models.TextField(null=True, blank=True)
    bank_name = models.ForeignKey("BankModel", on_delete=models.SET_NULL, null=True, blank=True)
    executive_name = models.CharField(max_length=100, null=True, blank=True)
    mobileno_1 = models.CharField(max_length=15, null=True, blank=True)
    mobileno_2 = models.CharField(max_length=15, blank=True, null=True)
    assigned_to = models.ForeignKey(StaffModel, on_delete=models.SET_NULL, null=True, blank=True)
    franchise = models.ForeignKey(Franchise, on_delete=models.CASCADE, related_name='loan_applications', null=True, blank=True)
    document_description = models.TextField(null=True, blank=True)

    def __str__(self):
        loan = self.loan_name.loan_name if self.loan_name else "No Loan"
        return f"{self.first_name} {self.last_name or ''} - {loan}".strip()

class StaffSelectionModel(models.Model):
    selection_id = models.AutoField(primary_key=True)
    selection = models.CharField(max_length=100)

    def __str__(self):
        return self.selection
class StaffAssignmentModel(models.Model):
    assignment_id = models.AutoField(primary_key=True)

    # Staff Information
    staff_name = models.ForeignKey(
        StaffModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_to",
    )
    staff_full_name = models.CharField(max_length=255, blank=True, null=True)

    # Franchise Information
    franchise_name = models.ManyToManyField(Franchise)


    assigned_by = models.ForeignKey(
        AdminModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_by",
    )

    def __str__(self):
        staff = (
            f"{self.staff_name.first_name} {self.staff_name.last_name or ''}".strip()
            if self.staff_name else "No Staff"
        )
        franchises = ", ".join(
            [f.franchise_name for f in self.franchise_name.all()]
        ) if self.franchise_name.exists() else "No Franchise"

        return f"Assignment {self.assignment_id} - {staff} to {franchises}"


    def save(self, *args, **kwargs):
        # Store full name of the staff in a separate field
        if self.staff_name:
            self.staff_full_name = f"{self.staff_name.first_name} {self.staff_name.last_name or ''}".strip(
            )

        super().save(*args, **kwargs)

class UploadedFile(models.Model):
    file_id = models.AutoField(primary_key=True)
    loan_application = models.ForeignKey(LoanApplicationModel, related_name="uploaded_files", on_delete=models.CASCADE)
    file = models.FileField(upload_to="files/")
    file_type = models.CharField(max_length=50, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File for {self.loan_application.first_name} - {self.file_type or 'Unknown'}"

