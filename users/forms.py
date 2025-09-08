from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from .models import *
from loan.models import StaffAssignmentModel


class AdminForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-user",
                "placeholder": "Confirm Password",
            }
        ),
        required=True,
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
                }
            ),
            "admin_last_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Last Name",
                }
            ),
            "admin_email": forms.EmailInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Email Address",
                }
            ),
            "admin_phone": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Phone Number",
                }
            ),
            "admin_password": forms.PasswordInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Password",
                }
            ),
            "is_superadmin": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_admin_email(self):
        email = self.cleaned_data.get("admin_email")
        if AdminModel.objects.filter(admin_email=email).exists():
            raise ValidationError("An admin with this email already exists.")
        return email

    def clean_admin_password(self):
        password = self.cleaned_data.get("admin_password")
        if len(password) < 8:
            raise ValidationError(
                "Password must be at least 8 characters long.")
        return password  # Don't hash it here, it's handled in the model's save method

    def clean_admin_phone(self):
        phone = self.cleaned_data.get("admin_phone")
        if phone and (len(phone) != 10 or not phone.isdigit()):
            raise ValidationError(
                "Phone Number must be exactly 10 digits and contain only numbers."
            )
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("admin_password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")

        return cleaned_data


class StaffModelForm(forms.ModelForm):
    """Form for creating and managing staff members"""

    employee_id = forms.CharField(
        required=False,
        label="Employee ID",
        widget=forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"})
    )

    class Meta:
        model = StaffModel
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_no",
            "profile_picture"
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "First Name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Last Name"}),
            "email": forms.EmailInput(attrs={"class": "form-control form-control-user", "placeholder": "Email Address"}),
            "phone_no": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Phone Number"}),
            "profile_picture": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.employee_id:
            self.fields['employee_id'].initial = self.instance.employee_id

        if user and isinstance(user, AdminModel):
            self.instance.managed_by = user

    def clean_email(self):
        email = self.cleaned_data.get("email")
        instance = self.instance
        if StaffModel.objects.filter(email=email).exclude(pk=instance.pk).exists():
            raise ValidationError("A staff member with this email already exists.")
        return email

    def clean_phone_no(self):
        phone = self.cleaned_data.get("phone_no")
        if phone and (len(phone) != 10 or not phone.isdigit()):
            raise ValidationError("Phone Number must be exactly 10 digits and contain only numbers.")
        return phone

    def save(self, commit=True):
        staff = super().save(commit=False)
        if commit:
            staff.save()
        return staff


class StaffActivationForm(forms.Form):
    """Form for staff to activate their account and set password"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control form-control-user", "placeholder": "Password"}),
        min_length=8,
        help_text="Password must be at least 8 characters long."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control form-control-user", "placeholder": "Confirm Password"})
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        
        return cleaned_data



class FranchiseForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirm Password"}
        ),
        required=True,
    )

    class Meta:
        model = Franchise
        fields = [
            "franchise_name",
            "franchise_owner",
            "franchise_place",
            "email",
            "mobile_no",
            "password",
            "confirm_password",
            "aadhar",
            "GST",
            "pan",
            "ac_no",
            "ifsc_code",
            "payment_status",
            "is_franchise",
            "screenshot",
            "franchise_type",
            "referred_by",
        ]
        widgets = {
            "franchise_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Franchise Name"}),
            "franchise_owner": forms.TextInput(attrs={"class": "form-control", "placeholder": "Franchise Owner"}),
            "franchise_place": forms.TextInput(attrs={"class": "form-control", "placeholder": "Franchise Place"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address"}),
            "mobile_no": forms.TextInput(attrs={"class": "form-control", "placeholder": "Mobile Number"}),
            "password": forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
            "confirm_password": forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password"}),
            "aadhar": forms.TextInput(attrs={"class": "form-control", "placeholder": "Aadhar Number"}),
            "GST": forms.TextInput(attrs={"class": "form-control", "placeholder": "GST Number"}),
            "pan": forms.TextInput(attrs={"class": "form-control", "placeholder": "PAN Number"}),
            "ac_no": forms.TextInput(attrs={"class": "form-control", "placeholder": "Account Number"}),
            "ifsc_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "IFSC Code"}),
            "payment_status": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_franchise": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "screenshot": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "franchise_type": forms.Select(attrs={"class": "form-control"}),
            "referred_by": forms.Select(attrs={"class": "form-control", "placeholder": "Select Referrer (Optional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pre-fill confirm_password with the password if an instance exists
        if self.instance and self.instance.password:
            self.fields['confirm_password'].initial = self.instance.password
        
        # Set up referred_by field to show franchise names
        self.fields['referred_by'].queryset = Franchise.objects.filter(is_active=True).order_by('franchise_name')
        self.fields['referred_by'].empty_label = "Select a referrer (optional)"

    def clean_ac_no(self):
        """ Validate Account Number (should be 9 to 18 digits). """
        ac_no = self.cleaned_data.get("ac_no")
        if not ac_no.isdigit() or not (9 <= len(ac_no) <= 18):
            raise ValidationError(
                "Account Number must be between 9 to 18 digits and contain only numbers.")
        return ac_no

    def clean_ifsc_code(self):
        """ Validate IFSC Code (standard format: 4 letters, 0, 6 alphanumeric). """
        ifsc_code = self.cleaned_data.get("ifsc_code")

        if not ifsc_code:
            raise ValidationError("IFSC code is required.")

        ifsc_code = ifsc_code.strip().upper()
        import re
        ifsc_pattern = r"^[A-Z]{4}0[A-Z0-9]{6}$"

        if not re.match(ifsc_pattern, ifsc_code):
            raise ValidationError(
                "Enter a valid IFSC code (e.g., HDFC0001234).")

        return ifsc_code

    def clean(self):
        """ Ensure passwords match. """
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")


class FranchiseCreationForm(forms.ModelForm):
    """Form for initial franchise creation (admin use only)"""
    
    class Meta:
        model = Franchise
        fields = [
            "staff",
            "franchise_name", 
            "franchise_owner",
            "franchise_place",
            "franchise_type",
            "payment_status",
            "referred_by",
            "email",
            "mobile_no",
        ]
        widgets = {
            "staff": forms.Select(attrs={"class": "form-control"}),
            "franchise_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Franchise Name"}),
            "franchise_owner": forms.TextInput(attrs={"class": "form-control", "placeholder": "Franchise Owner"}),
            "franchise_place": forms.TextInput(attrs={"class": "form-control", "placeholder": "Franchise Place"}),
            "franchise_type": forms.Select(attrs={"class": "form-control"}),
            "payment_status": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "referred_by": forms.Select(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address"}),
            "mobile_no": forms.TextInput(attrs={"class": "form-control", "placeholder": "Mobile Number"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up referred_by field to show franchise names
        self.fields['referred_by'].queryset = Franchise.objects.filter(is_active=True).order_by('franchise_name')
        self.fields['referred_by'].empty_label = "Select a referrer (optional)"
        self.fields['staff'].empty_label = "Select staff (optional)"


class FranchiseProfileForm(forms.ModelForm):
    """Form for franchise profile completion after activation"""
    
    class Meta:
        model = Franchise
        fields = [
            "franchise_name",
            "franchise_owner", 
            "franchise_place",
            "email",
            "mobile_no",
            "aadhar",
            "GST", 
            "pan",
            "ac_no",
            "ifsc_code",
            "profile_picture",
        ]
        widgets = {
            "franchise_name": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Franchise Name"}),
            "franchise_owner": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Franchise Owner"}),
            "franchise_place": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Franchise Place"}),
            "email": forms.EmailInput(attrs={"class": "form-control form-control-user", "placeholder": "Email Address"}),
            "mobile_no": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Mobile Number"}),
            "aadhar": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Aadhar Number"}),
            "GST": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "GST Number"}),
            "pan": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "PAN Number"}),
            "ac_no": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Account Number"}),
            "ifsc_code": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "IFSC Code"}),
            "profile_picture": forms.ClearableFileInput(attrs={"class": "form-control form-control-user"}),
        }

    def clean_ac_no(self):
        """ Validate Account Number (should be 9 to 18 digits). """
        ac_no = self.cleaned_data.get("ac_no")
        if not ac_no.isdigit() or not (9 <= len(ac_no) <= 18):
            raise ValidationError(
                "Account Number must be between 9 to 18 digits and contain only numbers.")
        return ac_no

    def clean_ifsc_code(self):
        """ Validate IFSC Code (standard format: 4 letters, 0, 6 alphanumeric). """
        ifsc_code = self.cleaned_data.get("ifsc_code")

        if not ifsc_code:
            raise ValidationError("IFSC code is required.")

        ifsc_code = ifsc_code.strip().upper()
        import re
        ifsc_pattern = r"^[A-Z]{4}0[A-Z0-9]{6}$"

        if not re.match(ifsc_pattern, ifsc_code):
            raise ValidationError(
                "Enter a valid IFSC code (e.g., HDFC0001234).")

        return ifsc_code


class FranchiseActivationForm(forms.Form):
    """Form for franchise to set password during activation"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
        min_length=8,
        help_text="Password must be at least 8 characters long."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password"})
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")

        return cleaned_data


# ============================================================================
# ADMIN FORMS
# ============================================================================

class AdminProfileUpdateForm(forms.ModelForm):
    """Form for updating admin profile (without password change)"""
    
    class Meta:
        model = AdminModel
        fields = [
            "admin_first_name",
            "admin_last_name",
            "profile_picture",
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
            "profile_picture": forms.ClearableFileInput(
                attrs={
                    "class": "form-control form-control-user"
                }
            ),
        }

    # Limit admin profile updates to only name and profile picture


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
        
        if not any(c.isupper() for c in new_password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        
        if not any(c.islower() for c in new_password):
            raise ValidationError("Password must contain at least one lowercase letter.")
        
        if not any(c.isdigit() for c in new_password):
            raise ValidationError("Password must contain at least one number.")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in new_password):
            raise ValidationError("Password must contain at least one special character.")
        
        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_new_password = cleaned_data.get("confirm_new_password")

        if new_password and confirm_new_password and new_password != confirm_new_password:
            raise ValidationError("New passwords do not match.")

        return cleaned_data


# =============================================================================
# WALLET FORM
# =============================================================================

class WalletUpdateForm(forms.Form):
    franchise = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={"class": "form-select form-control"}),
        required=True,
        help_text="Choose a franchise"
    )

    commission = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Commission", "min": "0", "step": "0.01"})
    )
    incentive = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Incentive", "min": "0", "step": "0.01"})
    )

    def __init__(self, *args, **kwargs):
        user_type = kwargs.pop('user_type', None)
        user_id = kwargs.pop('user_id', None)
        super().__init__(*args, **kwargs)
        # Dynamically set queryset and empty label
        qs = Franchise.objects.all().order_by('franchise_name')
        if user_type == 'staff' and user_id:
            try:
                staff = StaffModel.objects.get(staff_id=user_id)
                from loan.models import StaffAssignmentModel
                qs = Franchise.objects.filter(staffassignmentmodel__staff_name=staff).distinct().order_by('franchise_name')
            except Exception:
                pass
        self.fields['franchise'].choices = [('', 'Select Franchise')] + [
            (str(f.pk), f.franchise_name) for f in qs
        ]

    def save(self):
        franchise_id = self.cleaned_data['franchise']
        from .models import Wallet
        franchise = Franchise.objects.get(pk=franchise_id)
        wallet, _ = Wallet.objects.get_or_create(franchise=franchise)
        # Allowance is fixed at 10,000 (non-editable)
        if self.cleaned_data.get('commission') is not None:
            wallet.commission = self.cleaned_data['commission']
        if self.cleaned_data.get('incentive') is not None:
            wallet.incentive = self.cleaned_data['incentive']
        wallet.save()
        return wallet

# =============================================================================
# STAFF ASSIGNMENT FORM
# =============================================================================

class StaffAssignmentForm(forms.ModelForm):
    """Form to assign one staff to multiple franchises, or edit an assignment"""

    # Override staff_name as ChoiceField to ensure consistent rendering
    staff_name = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={"class": "form-select form-control"}),
        required=True,
        label="Staff"
    )

    class Meta:
        model = StaffAssignmentModel
        fields = [
            "staff_name",
            "franchise_name",
        ]
        widgets = {
            "franchise_name": forms.CheckboxSelectMultiple(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        # Optional user context (admin) passed from views
        self.user_context = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Populate staff choices explicitly to ensure rendering
        staff_qs = StaffModel.objects.all().order_by("first_name", "last_name")
        self.fields["staff_name"].choices = [('', 'Select Staff')] + [
            (str(s.pk), f"{s.first_name} {s.last_name or ''}".strip()) for s in staff_qs
        ]
        self.fields["franchise_name"].queryset = Franchise.objects.all().order_by("franchise_name")

    def save(self, commit=True):
        # Convert selected staff id back to instance before saving
        staff_id = self.cleaned_data.get('staff_name')
        if staff_id:
            self.instance.staff_name = StaffModel.objects.get(pk=staff_id)
        instance = super().save(commit=commit)
        # Ensure ManyToMany is saved when commit=True; if commit=False, caller must handle save_m2m
        if commit and hasattr(self, "save_m2m"):
            self.save_m2m()
        return instance

