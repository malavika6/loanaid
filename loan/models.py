from django.db import models
from users.models import StaffModel, Franchise, AdminModel
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta   


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
    address = models.TextField(null=True, blank=True, help_text="Complete address of the applicant")
    guaranter_name = models.CharField(max_length=100, null=True, blank=True)
    guaranter_phoneno = models.CharField(max_length=50, null=True, blank=True)
    guaranter_job = models.CharField(max_length=100, null=True, blank=True)
    guaranter_cibil_score = models.CharField(max_length=50, null=True, blank=True)
    guaranter_cibil_issue = models.CharField(max_length=20, choices=[('Yes', 'Yes'), ('No', 'No'), ("Don't Know", "Don't Know")], default='No', null=True, blank=True)
    guaranter_it_payable = models.CharField(max_length=10, choices=[('Yes', 'Yes'), ('No', 'No')], default='No', null=True, blank=True)
    job = models.CharField(max_length=100, null=True, blank=True)
    cibil_score = models.CharField(max_length=100, null=True, blank=True)
    cibil_issue = models.CharField(max_length=20, choices=[('Yes', 'Yes'), ('No', 'No'), ("Don't Know", "Don't Know")], default='No')
    it_payable = models.CharField(max_length=10, choices=[('Yes', 'Yes'), ('No', 'No')], default='No')
    years = models.IntegerField(null=True, blank=True)
    loan_name = models.ForeignKey(LoanModel, on_delete=models.SET_NULL, null=True, blank=True)
    loan_amount = models.DecimalField(max_digits=10, default=0, decimal_places=2, null=True, blank=True)
    followup_date = models.DateField(null=True, blank=True)
    status_name = models.ForeignKey(StatusModel, on_delete=models.SET_NULL, null=True, blank=True)
    bank_name = models.ForeignKey("BankModel", on_delete=models.SET_NULL, null=True, blank=True)
    executive_name = models.CharField(max_length=100, null=True, blank=True)
    reference_no_1 = models.CharField(max_length=50, null=True, blank=True, help_text="Reference Number 1")
    reference_no_2 = models.CharField(max_length=50, blank=True, null=True, help_text="Reference Number 2")
    assigned_to = models.ForeignKey(StaffModel, on_delete=models.SET_NULL, null=True, blank=True)
    franchise = models.ForeignKey(Franchise, on_delete=models.CASCADE, related_name='loan_applications', null=True, blank=True)
    document_description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-form_id']
        verbose_name = 'Loan Application'
        verbose_name_plural = 'Loan Applications'

    def __str__(self):
        loan = self.loan_name.loan_name if self.loan_name else "No Loan"
        return f"{self.first_name} {self.last_name or ''} - {loan}".strip()
    
    def calculate_followup_date(self):
        """Calculate follow-up date based on status"""
        if not self.status_name:
            return None
            
        status_name = self.status_name.status_name.lower()
        current_date = timezone.now().date()
        
        # Define follow-up periods based on status
        followup_periods = {
            'pending': 3,           # 3 days for pending
            'under review': 5,      # 5 days for under review
            'approved': 7,          # 7 days for approved
            'rejected': 1,          # 1 day for rejected
            'not selected': 1,      # 1 day for not selected
        }
        
        # Get the period for this status
        days_to_add = followup_periods.get(status_name, 3)  # Default 3 days
        
        return current_date + timedelta(days=days_to_add)
    
    def save(self, *args, **kwargs):
        """Override save to auto-update follow-up date when status changes"""
        # Check if this is a status update
        if self.pk:
            try:
                old_instance = LoanApplicationModel.objects.get(pk=self.pk)
                # If status changed, update follow-up date
                if old_instance.status_name != self.status_name:
                    self.followup_date = self.calculate_followup_date()
            except LoanApplicationModel.DoesNotExist:
                # New instance, set initial follow-up date
                if self.status_name:
                    self.followup_date = self.calculate_followup_date()
        else:
            # New instance, set initial follow-up date
            if self.status_name:
                self.followup_date = self.calculate_followup_date()
        
        super().save(*args, **kwargs)
    
class UploadedFile(models.Model):
    file_id = models.AutoField(primary_key=True)
    loan_application = models.ForeignKey(LoanApplicationModel, related_name="uploaded_files", on_delete=models.CASCADE)
    file = models.FileField(upload_to="files/")
    file_type = models.CharField(max_length=50, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File for {self.loan_application.first_name} - {self.file_type or 'Unknown'}"
    
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




