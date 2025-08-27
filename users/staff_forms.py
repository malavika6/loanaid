from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator
from .models import StaffModel
import logging

logger = logging.getLogger(__name__)


class StaffModelForm(forms.ModelForm):
    """Enhanced form for creating and managing staff members"""
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-user",
                "placeholder": "Confirm Password",
                "autocomplete": "new-password"
            }
        ),
        required=True,
        help_text="Please confirm your password"
    )
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-user",
                "placeholder": "Current Password (for updates)",
                "autocomplete": "current-password"
            }
        ),
        required=False,
        help_text="Required when updating existing staff"
    )
    
    employee_id = forms.CharField(
        required=False,
        label="Employee ID",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": "readonly",
                "placeholder": "Auto-generated"
            }
        ),
        help_text="Automatically generated employee ID"
    )
    
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "staff_is_active"
            }
        ),
        help_text="Check if staff account is active"
    )
    
    can_create_loans = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "staff_can_create_loans"
            }
        ),
        help_text="Allow staff to create loan applications"
    )
    
    can_assign_franchises = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "staff_can_assign_franchises"
            }
        ),
        help_text="Allow staff to assign franchises"
    )
    
    can_view_reports = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "staff_can_view_reports"
            }
        ),
        help_text="Allow staff to view reports and analytics"
    )

    class Meta:
        model = StaffModel
        fields = [
            "first_name",
            "last_name", 
            "email",
            "phone_no",
            "password",
            "confirm_password",
            "profile_picture",
            "is_active",
            "can_create_loans",
            "can_assign_franchises", 
            "can_view_reports"
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "First Name",
                    "autocomplete": "given-name"
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Last Name",
                    "autocomplete": "family-name"
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Email Address",
                    "autocomplete": "email"
                }
            ),
            "phone_no": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Phone Number",
                    "autocomplete": "tel"
                }
            ),
            "password": forms.PasswordInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Password",
                    "autocomplete": "new-password"
                }
            ),
            "profile_picture": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*"
                }
            ),
        }
        help_texts = {
            'first_name': 'Enter the staff member\'s first name',
            'last_name': 'Enter the staff member\'s last name (optional)',
            'email': 'Enter a unique email address for the staff member',
            'phone_no': 'Enter a 10-digit mobile number',
            'password': 'Create a strong password (minimum 8 characters)',
            'profile_picture': 'Upload a profile picture (optional)'
        }

    def __init__(self, *args, **kwargs):
        self.is_update = kwargs.get('instance') is not None
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        # Set employee_id initial value if instance exists
        if self.instance and self.instance.employee_id:
            self.fields['employee_id'].initial = self.instance.employee_id
        
        # Make password optional for updates
        if self.is_update:
            self.fields['password'].required = False
            self.fields['password'].help_text = "Leave blank to keep current password"
            self.fields['current_password'].required = True
        else:
            self.fields['password'].required = True
            self.fields['current_password'].required = False
            self.fields['current_password'].widget = forms.HiddenInput()
        
        # Set managed_by if user is provided
        if self.user and hasattr(self.user, 'admin_id'):
            self.instance.managed_by = self.user

    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get("email")
        instance = self.instance
        
        if StaffModel.objects.filter(email=email).exclude(pk=instance.pk if instance else None).exists():
            raise ValidationError("A staff member with this email already exists.")
        
        return email

    def clean_phone_no(self):
        """Validate phone number format"""
        phone = self.cleaned_data.get("phone_no")
        
        if phone:
            # Remove any non-digit characters
            phone = ''.join(filter(str.isdigit, phone))
            
            if len(phone) != 10:
                raise ValidationError("Phone number must be exactly 10 digits.")
            
            if not phone.isdigit():
                raise ValidationError("Phone number must contain only numbers.")
        
        return phone

    def clean_password(self):
        """Validate password strength"""
        password = self.cleaned_data.get("password")
        
        if not password and not self.is_update:
            raise ValidationError("Password is required for new staff accounts.")
        
        if password:
            if len(password) < 8:
                raise ValidationError("Password must be at least 8 characters long.")
            
            if not any(c.isupper() for c in password):
                raise ValidationError("Password must contain at least one uppercase letter.")
            
            if not any(c.islower() for c in password):
                raise ValidationError("Password must contain at least one lowercase letter.")
            
            if not any(c.isdigit() for c in password):
                raise ValidationError("Password must contain at least one number.")
            
            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                raise ValidationError("Password must contain at least one special character.")
        
        return password

    def clean_current_password(self):
        """Validate current password for updates"""
        if self.is_update and not self.cleaned_data.get('current_password'):
            raise ValidationError("Current password is required for updates.")
        return self.cleaned_data.get('current_password')

    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        
        # Validate current password for updates
        if self.is_update:
            current_password = cleaned_data.get('current_password')
            if current_password and self.instance:
                if not self.instance.check_password(current_password):
                    raise ValidationError("Current password is incorrect.")
        
        return cleaned_data

    def save(self, commit=True):
        """Save staff member with password hashing"""
        staff = super().save(commit=False)
        
        # Hash password if provided and not already hashed
        if staff.password and not staff.password.startswith("pbkdf2_"):
            staff.password = make_password(staff.password)
        
        # Generate employee ID if not exists
        if not staff.employee_id:
            staff.employee_id = self._generate_employee_id()
        
        if commit:
            try:
                staff.save()
                logger.info(f"Staff member saved successfully: {staff.email}")
            except Exception as e:
                logger.error(f"Error saving staff member: {e}")
                raise
        
        return staff

    def _generate_employee_id(self):
        """Generate unique employee ID"""
        try:
            last_staff = StaffModel.objects.exclude(
                employee_id__isnull=True
            ).order_by('-staff_id').first()
            
            if last_staff and last_staff.employee_id:
                try:
                    last_number = int(last_staff.employee_id.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    last_number = 1001
            else:
                last_number = 1001
            
            return f"EMP-{last_number:04d}"
            
        except Exception as e:
            logger.error(f"Error generating employee ID: {e}")
            return f"EMP-{1001:04d}"


class StaffProfileUpdateForm(forms.ModelForm):
    """Form for updating staff profile without password change"""
    
    class Meta:
        model = StaffModel
        fields = [
            "first_name",
            "last_name",
            "email", 
            "phone_no",
            "profile_picture",
            "is_active",
            "can_create_loans",
            "can_assign_franchises",
            "can_view_reports"
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "First Name"
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Last Name"
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Email Address"
                }
            ),
            "phone_no": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Phone Number"
                }
            ),
            "profile_picture": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*"
                }
            ),
        }

    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get("email")
        instance = self.instance
        
        if StaffModel.objects.filter(email=email).exclude(pk=instance.pk).exists():
            raise ValidationError("A staff member with this email already exists.")
        
        return email

    def clean_phone_no(self):
        """Validate phone number format"""
        phone = self.cleaned_data.get("phone_no")
        
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            
            if len(phone) != 10:
                raise ValidationError("Phone number must be exactly 10 digits.")
            
            if not phone.isdigit():
                raise ValidationError("Phone number must contain only numbers.")
        
        return phone


class StaffPasswordChangeForm(forms.Form):
    """Form for changing staff password"""
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-user",
                "placeholder": "Current Password"
            }
        ),
        required=True,
        help_text="Enter your current password"
    )
    
    new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-user",
                "placeholder": "New Password"
            }
        ),
        required=True,
        help_text="Enter your new password"
    )
    
    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-user",
                "placeholder": "Confirm New Password"
            }
        ),
        required=True,
        help_text="Confirm your new password"
    )

    def __init__(self, staff_instance, *args, **kwargs):
        self.staff_instance = staff_instance
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        """Validate current password"""
        current_password = self.cleaned_data.get('current_password')
        
        if not self.staff_instance.check_password(current_password):
            raise ValidationError("Current password is incorrect.")
        
        return current_password

    def clean_new_password(self):
        """Validate new password strength"""
        password = self.cleaned_data.get("new_password")
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        if not any(c.isupper() for c in password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        
        if not any(c.islower() for c in password):
            raise ValidationError("Password must contain at least one lowercase letter.")
        
        if not any(c.isdigit() for c in password):
            raise ValidationError("Password must contain at least one number.")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            raise ValidationError("Password must contain at least one special character.")
        
        return password

    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_new_password = cleaned_data.get("confirm_new_password")
        
        if new_password and confirm_new_password and new_password != confirm_new_password:
            raise ValidationError("New passwords do not match.")
        
        return cleaned_data

    def save(self):
        """Update staff password"""
        new_password = self.cleaned_data.get('new_password')
        self.staff_instance.set_password(new_password)
        self.staff_instance.save()
        logger.info(f"Password changed for staff member: {self.staff_instance.email}")


class StaffSearchForm(forms.Form):
    """Form for searching and filtering staff members"""
    
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search by name, email, or employee ID..."
            }
        ),
        help_text="Search staff members by name, email, or employee ID"
    )
    
    status_filter = forms.ChoiceField(
        choices=[
            ('', 'All Statuses'),
            ('active', 'Active'),
            ('inactive', 'Inactive')
        ],
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-control"
            }
        )
    )
    
    permission_filter = forms.ChoiceField(
        choices=[
            ('', 'All Permissions'),
            ('can_create_loans', 'Can Create Loans'),
            ('can_assign_franchises', 'Can Assign Franchises'),
            ('can_view_reports', 'Can View Reports')
        ],
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-control"
            }
        )
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date"
            }
        ),
        help_text="Filter by creation date from"
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date"
            }
        ),
        help_text="Filter by creation date to"
    )

    def clean(self):
        """Validate date range"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError("Start date cannot be after end date.")
        
        return cleaned_data
