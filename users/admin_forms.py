from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator
from .models import AdminModel, StaffModel, Franchise
from loan.models import LoanApplicationModel, StaffAssignmentModel
import logging

logger = logging.getLogger(__name__)


class AdminForm(forms.ModelForm):
    """Optimized admin form with enhanced validation"""
    
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
                "placeholder": "Current Password (if updating)",
                "autocomplete": "current-password"
            }
        ),
        required=False,
        help_text="Required when updating existing admin"
    )

    class Meta:
        model = AdminModel
        fields = [
            "admin_first_name",
            "admin_last_name", 
            "admin_email",
            "admin_phone",
            "admin_password",
            "is_superadmin",
        ]
        widgets = {
            "admin_first_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "First Name",
                    "autocomplete": "given-name"
                }
            ),
            "admin_last_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Last Name",
                    "autocomplete": "family-name"
                }
            ),
            "admin_email": forms.EmailInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Email Address",
                    "autocomplete": "email"
                }
            ),
            "admin_phone": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Phone Number (10 digits)",
                    "autocomplete": "tel"
                }
            ),
            "admin_password": forms.PasswordInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Password",
                    "autocomplete": "new-password"
                }
            ),
            "is_superadmin": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                    "id": "is_superadmin"
                }
            ),
        }
        help_texts = {
            "admin_first_name": "Enter your first name",
            "admin_last_name": "Enter your last name (optional)",
            "admin_email": "Enter a valid email address",
            "admin_phone": "Enter a 10-digit phone number",
            "admin_password": "Password must be at least 8 characters long",
            "is_superadmin": "Check if this admin should have superadmin privileges"
        }

    def __init__(self, *args, **kwargs):
        self.is_update = kwargs.get('instance') is not None
        super().__init__(*args, **kwargs)
        
        # Make current password required for updates
        if self.is_update:
            self.fields['current_password'].required = True
            self.fields['admin_password'].required = False
            self.fields['admin_password'].help_text = "Leave blank to keep current password"
        
        # Add custom validation attributes
        self.fields['admin_first_name'].widget.attrs.update({
            'minlength': '2',
            'maxlength': '100'
        })
        self.fields['admin_last_name'].widget.attrs.update({
            'maxlength': '100'
        })
        self.fields['admin_password'].widget.attrs.update({
            'minlength': '8',
            'pattern': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
        })

    def clean_admin_email(self):
        """Validate admin email uniqueness"""
        email = self.cleaned_data.get("admin_email")
        if not email:
            raise ValidationError("Email is required.")
        
        # Check if email already exists (excluding current instance for updates)
        existing_admin = AdminModel.objects.filter(admin_email=email)
        if self.instance and self.instance.pk:
            existing_admin = existing_admin.exclude(pk=self.instance.pk)
        
        if existing_admin.exists():
            raise ValidationError("An admin with this email already exists.")
        
        return email.lower().strip()

    def clean_admin_password(self):
        """Validate admin password strength"""
        password = self.cleaned_data.get("admin_password")
        
        if not password and not self.is_update:
            raise ValidationError("Password is required for new admin accounts.")
        
        if password:
            if len(password) < 8:
                raise ValidationError("Password must be at least 8 characters long.")
            
            # Check password complexity
            if not any(c.isupper() for c in password):
                raise ValidationError("Password must contain at least one uppercase letter.")
            
            if not any(c.islower() for c in password):
                raise ValidationError("Password must contain at least one lowercase letter.")
            
            if not any(c.isdigit() for c in password):
                raise ValidationError("Password must contain at least one number.")
            
            if not any(c in '@$!%*?&' for c in password):
                raise ValidationError("Password must contain at least one special character (@$!%*?&).")
        
        return password

    def clean_admin_phone(self):
        """Validate admin phone number"""
        phone = self.cleaned_data.get("admin_phone")
        if phone:
            # Remove any non-digit characters
            phone = ''.join(filter(str.isdigit, phone))
            
            if len(phone) != 10:
                raise ValidationError("Phone number must be exactly 10 digits.")
            
            # Check if phone already exists
            existing_admin = AdminModel.objects.filter(admin_phone=phone)
            if self.instance and self.instance.pk:
                existing_admin = existing_admin.exclude(pk=self.instance.pk)
            
            if existing_admin.exists():
                raise ValidationError("An admin with this phone number already exists.")
        
        return phone

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        password = cleaned_data.get("admin_password")
        confirm_password = cleaned_data.get("confirm_password")
        current_password = cleaned_data.get("current_password")

        # For updates, validate current password
        if self.is_update and not password:
            if not current_password:
                raise ValidationError("Current password is required when updating admin.")
            
            # Verify current password
            if not self.instance.check_password(current_password):
                raise ValidationError("Current password is incorrect.")

        # Validate password confirmation
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        """Save admin with proper password handling"""
        admin = super().save(commit=False)
        
        # Hash password if provided
        if self.cleaned_data.get("admin_password"):
            admin.admin_password = make_password(self.cleaned_data["admin_password"])
        
        if commit:
            admin.save()
        
        return admin


class AdminProfileUpdateForm(forms.ModelForm):
    """Form for updating admin profile (without password change)"""
    
    class Meta:
        model = AdminModel
        fields = [
            "admin_first_name",
            "admin_last_name",
            "admin_email",
            "admin_phone",
        ]
        widgets = {
            "admin_first_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "First Name"
                }
            ),
            "admin_last_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Last Name"
                }
            ),
            "admin_email": forms.EmailInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Email Address"
                }
            ),
            "admin_phone": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Phone Number"
                }
            ),
        }

    def clean_admin_email(self):
        """Validate email uniqueness for profile updates"""
        email = self.cleaned_data.get("admin_email")
        if email:
            existing_admin = AdminModel.objects.filter(admin_email=email).exclude(pk=self.instance.pk)
            if existing_admin.exists():
                raise ValidationError("An admin with this email already exists.")
        return email.lower().strip()


class AdminPasswordChangeForm(forms.Form):
    """Form for changing admin password"""
    
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

    def __init__(self, admin_instance, *args, **kwargs):
        self.admin_instance = admin_instance
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        """Validate current password"""
        current_password = self.cleaned_data.get("current_password")
        if not self.admin_instance.check_password(current_password):
            raise ValidationError("Current password is incorrect.")
        return current_password

    def clean_new_password(self):
        """Validate new password strength"""
        new_password = self.cleaned_data.get("new_password")
        
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        # Check password complexity
        if not any(c.isupper() for c in new_password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        
        if not any(c.islower() for c in new_password):
            raise ValidationError("Password must contain at least one lowercase letter.")
        
        if not any(c.isdigit() for c in new_password):
            raise ValidationError("Password must contain at least one number.")
        
        if not any(c in '@$!%*?&' for c in new_password):
            raise ValidationError("Password must contain at least one special character (@$!%*?&).")
        
        return new_password

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_new_password = cleaned_data.get("confirm_new_password")

        if new_password and confirm_new_password and new_password != confirm_new_password:
            raise ValidationError("New passwords do not match.")

        return cleaned_data

    def save(self):
        """Update admin password"""
        new_password = self.cleaned_data["new_password"]
        self.admin_instance.admin_password = make_password(new_password)
        self.admin_instance.save()
        return self.admin_instance


class AdminSearchForm(forms.Form):
    """Form for searching admin records"""
    
    SEARCH_CHOICES = [
        ('all', 'All Fields'),
        ('name', 'Name'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('role', 'Role'),
    ]
    
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search admins...",
                "aria-label": "Search admins"
            }
        )
    )
    
    search_field = forms.ChoiceField(
        choices=SEARCH_CHOICES,
        initial='all',
        widget=forms.Select(
            attrs={
                "class": "form-select"
            }
        )
    )
    
    role_filter = forms.ChoiceField(
        choices=[
            ('', 'All Roles'),
            ('superadmin', 'Super Admin'),
            ('admin', 'Regular Admin'),
        ],
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select"
            }
        )
    )
    
    status_filter = forms.ChoiceField(
        choices=[
            ('', 'All Status'),
            ('active', 'Active'),
            ('inactive', 'Inactive'),
        ],
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select"
            }
        )
    )

    def clean_search_query(self):
        """Clean and validate search query"""
        query = self.cleaned_data.get("search_query", "").strip()
        if query and len(query) < 2:
            raise ValidationError("Search query must be at least 2 characters long.")
        return query

    def get_search_filter(self):
        """Get Django filter based on form data"""
        search_query = self.cleaned_data.get("search_query")
        search_field = self.cleaned_data.get("search_field")
        role_filter = self.cleaned_data.get("role_filter")
        status_filter = self.cleaned_data.get("status_filter")
        
        filters = {}
        
        # Apply role filter
        if role_filter:
            if role_filter == 'superadmin':
                filters['is_superadmin'] = True
            elif role_filter == 'admin':
                filters['is_superadmin'] = False
        
        # Apply status filter
        if status_filter:
            filters['is_active'] = (status_filter == 'active')
        
        return filters, search_query, search_field
