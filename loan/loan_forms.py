from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
import re

from users.models import StaffModel, Franchise
from .models import (
    LoanApplicationModel, LoanModel, StatusModel, BankModel, 
    UploadedFile, StaffAssignmentModel
)


class LoanApplicationForm(forms.ModelForm):
    """Enhanced loan application form with improved validation"""
    
    # Custom fields with enhanced validation
    franchise_mobile_no = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control", 
            "placeholder": "Franchise Mobile No.", 
            "disabled": "disabled"
        }),
        required=False
    )
    
    franchise_place = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control", 
            "placeholder": "Franchise Place", 
            "disabled": "disabled"
        }),
        required=False
    )
    
    # Enhanced choice fields with better validation
    cibil_issue = forms.ChoiceField(
        choices=[
            ('Yes', 'Yes'), 
            ('No', 'No'), 
            ("Don't Know", "Don't Know")
        ],
        widget=forms.Select(attrs={"class": "form-select form-control"}),
        help_text="Indicates if there are any CIBIL issues"
    )
    
    it_payable = forms.ChoiceField(
        choices=[('Yes', 'Yes'), ('No', 'No')],
        widget=forms.Select(attrs={"class": "form-select form-control"}),
        help_text="Indicates if IT returns are payable"
    )
    
    guaranter_cibil_issue = forms.ChoiceField(
        choices=[
            ('Yes', 'Yes'), 
            ('No', 'No'), 
            ("Don't Know", "Don't Know")
        ],
        widget=forms.Select(attrs={"class": "form-select form-control"}),
        required=False,
        help_text="Guarantor's CIBIL issue status"
    )
    
    guaranter_it_payable = forms.ChoiceField(
        choices=[('Yes', 'Yes'), ('No', 'No')],
        widget=forms.Select(attrs={"class": "form-select form-control"}),
        required=False,
        help_text="Guarantor's IT payable status"
    )
    
    # Enhanced phone number validation
    phone_no = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Phone Number",
            "pattern": r"[0-9]{10,15}"
        }),
        validators=[
            RegexValidator(
                regex=r'^[0-9]{10,15}$',
                message='Phone number must be 10-15 digits'
            )
        ]
    )
    
    guaranter_phoneno = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Guarantor Phone Number",
            "pattern": r"[0-9]{10,15}"
        }),
        validators=[
            RegexValidator(
                regex=r'^[0-9]{10,15}$',
                message='Guarantor phone number must be 10-15 digits'
            )
        ]
    )
    
    # Enhanced CIBIL score validation
    cibil_score = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.NumberInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "CIBIL Score",
            "min": "300",
            "max": "900"
        }),
        help_text="CIBIL score should be between 300-900"
    )
    
    guaranter_cibil_score = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.NumberInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Guarantor CIBIL Score",
            "min": "300",
            "max": "900"
        }),
        help_text="Guarantor CIBIL score should be between 300-900"
    )
    
    # Enhanced loan amount validation
    loan_amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Loan Amount",
            "min": "1000",
            "step": "0.01"
        }),
        help_text="Minimum loan amount is ₹1,000"
    )
    
    # Enhanced date validation
    followup_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Follow-up Date", 
            "type": "date",
            "min": "today"
        }),
        help_text="Follow-up date should be today or in the future"
    )
    
    # Enhanced text fields
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "First Name"
        }),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z\s]+$',
                message='First name should contain only letters and spaces'
            )
        ]
    )
    
    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Last Name"
        }),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z\s]*$',
                message='Last name should contain only letters and spaces'
            )
        ]
    )
    
    district = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "District"
        })
    )
    
    place = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Place"
        })
    )
    
    guaranter_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Guarantor Name"
        }),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z\s]*$',
                message='Guarantor name should contain only letters and spaces'
            )
        ]
    )
    
    guaranter_job = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Guarantor Job"
        })
    )
    
    job = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Job"
        })
    )
    
    executive_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Executive Name"
        }),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z\s]*$',
                message='Executive name should contain only letters and spaces'
            )
        ]
    )
    
    mobileno_1 = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Mobile Number 1",
            "pattern": r"[0-9]{10,15}"
        }),
        validators=[
            RegexValidator(
                regex=r'^[0-9]{10,15}$',
                message='Mobile number must be 10-15 digits'
            )
        ]
    )
    
    mobileno_2 = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Mobile Number 2",
            "pattern": r"[0-9]{10,15}"
        }),
        validators=[
            RegexValidator(
                regex=r'^[0-9]{10,15}$',
                message='Mobile number must be 10-15 digits'
            )
        ]
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Description", 
            "rows": 3
        })
    )
    
    document_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Document Description", 
            "rows": 3
        })
    )
    
    # Foreign key fields with enhanced widgets
    franchise = forms.ModelChoiceField(
        queryset=Franchise.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-control"}),
        empty_label="Select Franchise"
    )
    
    loan_name = forms.ModelChoiceField(
        queryset=LoanModel.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-control'
        }),
        empty_label="Select Loan Type"
    )
    
    status_name = forms.ModelChoiceField(
        queryset=StatusModel.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-control"}),
        empty_label="Select Status"
    )
    
    bank_name = forms.ModelChoiceField(
        queryset=BankModel.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-control"}),
        empty_label="Select Bank"
    )
    
    assigned_to = forms.ModelChoiceField(
        queryset=StaffModel.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-control"}),
        empty_label="Select Staff Member"
    )
    
    class Meta:
        model = LoanApplicationModel
        fields = [
            "franchise",
            "franchise_mobile_no",
            "franchise_place",
            "first_name",
            "last_name",
            "district",
            "place",
            "phone_no",
            "guaranter_name",
            "guaranter_phoneno",
            "guaranter_job",
            "guaranter_cibil_score",
            "guaranter_cibil_issue",
            "guaranter_it_payable",
            "job",
            "cibil_score",
            "cibil_issue",
            "it_payable",
            'loan_name',
            "loan_amount",
            "followup_date",
            "description",
            "status_name",
            "bank_name",
            "executive_name",
            "mobileno_1",
            "mobileno_2",
            "document_description",
            "assigned_to",
        ]
    
    def __init__(self, *args, **kwargs):
        user_type = kwargs.pop('user_type', None)
        super().__init__(*args, **kwargs)
        
        # Set user type for conditional field handling
        self.user_type = user_type
        
        # Add help text and improve field attributes
        self.fields['first_name'].help_text = "Enter the applicant's first name"
        self.fields['phone_no'].help_text = "Enter a valid 10-15 digit phone number"
        self.fields['loan_amount'].help_text = "Enter the loan amount in rupees"
        
        # Make certain fields required based on user type
        if user_type == 'franchise':
            # Franchise users have limited access
            self.fields['franchise'].widget.attrs['readonly'] = True
            self.fields['franchise'].widget.attrs['disabled'] = True
    
    def clean(self):
        """Enhanced form validation"""
        cleaned_data = super().clean()
        
        # Validate phone numbers
        phone_no = cleaned_data.get('phone_no')
        guaranter_phoneno = cleaned_data.get('guaranter_phoneno')
        
        if phone_no and guaranter_phoneno and phone_no == guaranter_phoneno:
            raise ValidationError("Applicant and guarantor phone numbers cannot be the same")
        
        # Validate CIBIL scores
        cibil_score = cleaned_data.get('cibil_score')
        if cibil_score:
            try:
                score = int(cibil_score)
                if score < 300 or score > 900:
                    raise ValidationError("CIBIL score must be between 300 and 900")
            except (ValueError, TypeError):
                raise ValidationError("Invalid CIBIL score format")
        
        guaranter_cibil_score = cleaned_data.get('guaranter_cibil_score')
        if guaranter_cibil_score:
            try:
                score = int(guaranter_cibil_score)
                if score < 300 or score > 900:
                    raise ValidationError("Guarantor CIBIL score must be between 300 and 900")
            except (ValueError, TypeError):
                raise ValidationError("Invalid guarantor CIBIL score format")
        
        # Validate loan amount
        loan_amount = cleaned_data.get('loan_amount')
        if loan_amount and loan_amount < 1000:
            raise ValidationError("Loan amount must be at least ₹1,000")
        
        # Validate follow-up date
        followup_date = cleaned_data.get('followup_date')
        if followup_date:
            from django.utils import timezone
            if followup_date < timezone.now().date():
                raise ValidationError("Follow-up date cannot be in the past")
        
        return cleaned_data
    
    def clean_first_name(self):
        """Validate first name"""
        first_name = self.cleaned_data.get('first_name')
        if first_name:
            # Remove extra spaces and capitalize
            first_name = ' '.join(first_name.split()).title()
            
            # Check for minimum length
            if len(first_name) < 2:
                raise ValidationError("First name must be at least 2 characters long")
            
            # Check for valid characters
            if not re.match(r'^[a-zA-Z\s]+$', first_name):
                raise ValidationError("First name should contain only letters and spaces")
        
        return first_name
    
    def clean_phone_no(self):
        """Validate phone number"""
        phone_no = self.cleaned_data.get('phone_no')
        if phone_no:
            # Remove any non-digit characters
            phone_no = re.sub(r'\D', '', phone_no)
            
            # Check length
            if len(phone_no) < 10 or len(phone_no) > 15:
                raise ValidationError("Phone number must be between 10 and 15 digits")
            
            # Check if it's a valid Indian mobile number (optional)
            if len(phone_no) == 10 and not phone_no.startswith(('6', '7', '8', '9')):
                raise ValidationError("Please enter a valid Indian mobile number")
        
        return phone_no


class LoanForm(forms.ModelForm):
    """Enhanced form for loan types"""
    
    loan_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Loan Name"
        }),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s\-_]+$',
                message='Loan name should contain only letters, numbers, spaces, hyphens, and underscores'
            )
        ]
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Description", 
            "rows": 3
        })
    )
    
    class Meta:
        model = LoanModel
        fields = ['loan_name', 'description']
    
    def clean_loan_name(self):
        """Validate loan name"""
        loan_name = self.cleaned_data.get('loan_name')
        if loan_name:
            # Check for duplicate names (case-insensitive)
            if LoanModel.objects.filter(loan_name__iexact=loan_name).exists():
                raise ValidationError("A loan type with this name already exists")
            
            # Remove extra spaces and capitalize
            loan_name = ' '.join(loan_name.split()).title()
            
            # Check minimum length
            if len(loan_name) < 2:
                raise ValidationError("Loan name must be at least 2 characters long")
        
        return loan_name


class StatusForm(forms.ModelForm):
    """Enhanced form for status types"""
    
    status_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Status Name"
        }),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s\-_]+$',
                message='Status name should contain only letters, numbers, spaces, hyphens, and underscores'
            )
        ]
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Description", 
            "rows": 3
        })
    )
    
    class Meta:
        model = StatusModel
        fields = ['status_name', 'description']
    
    def clean_status_name(self):
        """Validate status name"""
        status_name = self.cleaned_data.get('status_name')
        if status_name:
            # Check for duplicate names (case-insensitive)
            if StatusModel.objects.filter(status_name__iexact=status_name).exists():
                raise ValidationError("A status with this name already exists")
            
            # Remove extra spaces and capitalize
            status_name = ' '.join(status_name.split()).title()
            
            # Check minimum length
            if len(status_name) < 2:
                raise ValidationError("Status name must be at least 2 characters long")
        
        return status_name


class BankForm(forms.ModelForm):
    """Enhanced form for bank information"""
    
    bank_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-user", 
            "placeholder": "Bank Name"
        }),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s\-_&.]+$',
                message='Bank name should contain only letters, numbers, spaces, hyphens, underscores, ampersands, and periods'
            )
        ]
    )
    
    class Meta:
        model = BankModel
        fields = ['bank_name']
    
    def clean_bank_name(self):
        """Validate bank name"""
        bank_name = self.cleaned_data.get('bank_name')
        if bank_name:
            # Check for duplicate names (case-insensitive)
            if BankModel.objects.filter(bank_name__iexact=bank_name).exists():
                raise ValidationError("A bank with this name already exists")
            
            # Remove extra spaces and capitalize
            bank_name = ' '.join(bank_name.split()).title()
            
            # Check minimum length
            if len(bank_name) < 2:
                raise ValidationError("Bank name must be at least 2 characters long")
        
        return bank_name


class LoanSearchForm(forms.Form):
    """Form for searching and filtering loan applications"""
    
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Search by name, phone, or loan type..."
        })
    )
    
    status_filter = forms.ModelChoiceField(
        queryset=StatusModel.objects.all(),
        required=False,
        empty_label="All Statuses",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    bank_filter = forms.ModelChoiceField(
        queryset=BankModel.objects.all(),
        required=False,
        empty_label="All Banks",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    loan_type_filter = forms.ModelChoiceField(
        queryset=LoanModel.objects.all(),
        required=False,
        empty_label="All Loan Types",
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
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Min Amount",
            "step": "0.01"
        })
    )
    
    max_amount = forms.DecimalField(
        required=False,
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Max Amount",
            "step": "0.01"
        })
    )
    
    def clean(self):
        """Validate search form"""
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


class FileUploadForm(forms.ModelForm):
    """Form for file uploads"""
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            "class": "form-control"
        }),
        help_text="Upload supporting documents (PDF, DOC, DOCX, JPG, PNG)"
    )
    
    file_type = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "File Type (e.g., ID Proof, Address Proof)"
        })
    )
    
    class Meta:
        model = UploadedFile
        fields = ['file', 'file_type']
    
    def clean_file(self):
        """Validate uploaded file"""
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("File size cannot exceed 10MB")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            file_extension = file.name.lower()
            
            if not any(file_extension.endswith(ext) for ext in allowed_extensions):
                raise ValidationError(
                    "Only PDF, DOC, DOCX, JPG, and PNG files are allowed"
                )
        
        return file
