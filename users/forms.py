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
        
        if not ac_no:
            raise ValidationError("Account Number is required.")
        
        ac_no = str(ac_no).strip()
        
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
        
        # Mark required fields
        self.fields['franchise_name'].required = True
        self.fields['franchise_owner'].required = True
        self.fields['email'].required = True
        self.fields['mobile_no'].required = True
        self.fields['franchise_type'].required = True

    def clean_mobile_no(self):
        mobile_no = self.cleaned_data.get('mobile_no')
        if mobile_no:
            if not mobile_no.isdigit() or len(mobile_no) != 10:
                raise forms.ValidationError("Mobile number must be exactly 10 digits.")
        return mobile_no

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and Franchise.objects.filter(email=email).exists():
            raise forms.ValidationError("A franchise with this email already exists.")
        return email


class FranchiseProfileForm(forms.ModelForm):
    """Form for franchise profile completion after activation"""
    
    class Meta:
        model = Franchise
        fields = [
            "aadhar",
            "GST", 
            "pan",
            "ac_no",
            "ifsc_code",
            "profile_picture",
        ]
        widgets = {
            "aadhar": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Aadhar Number"}),
            "GST": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "GST Number (Optional)"}),
            "pan": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "PAN Number"}),
            "ac_no": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Account Number"}),
            "ifsc_code": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "IFSC Code"}),
            "profile_picture": forms.ClearableFileInput(attrs={"class": "form-control form-control-user"}),
        }

    def clean_ac_no(self):
        """ Validate Account Number (should be 9 to 18 digits). """
        ac_no = self.cleaned_data.get("ac_no")
        
        if not ac_no:
            raise ValidationError("Account Number is required.")
        
        ac_no = str(ac_no).strip()
        
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


class FranchiseEditByAdminForm(forms.ModelForm):
    """Form for admin/staff to edit only the fields they originally created"""
    
    class Meta:
        model = Franchise
        fields = [
            # Fields originally created by admin/staff
            "staff",                    # Assigned staff member
            "franchise_name",           # Basic franchise info
            "franchise_owner",          # Basic franchise info  
            "franchise_place",          # Basic franchise info
            "email",                    # Contact info
            "mobile_no",                # Contact info
            "franchise_type",           # Business settings
            "payment_status",           # Business settings
            "referred_by",              # Referral chain
            "is_active",                # Account status
            "is_franchise",             # Account type
            # Note: Excluded franchise-added fields like aadhar, GST, pan, ac_no, ifsc_code, profile_picture, screenshot
        ]
        widgets = {
            "staff": forms.Select(attrs={"class": "form-control"}),
            "franchise_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Franchise Name"}),
            "franchise_owner": forms.TextInput(attrs={"class": "form-control", "placeholder": "Franchise Owner"}),
            "franchise_place": forms.TextInput(attrs={"class": "form-control", "placeholder": "Franchise Place"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address"}),
            "mobile_no": forms.TextInput(attrs={"class": "form-control", "placeholder": "Mobile Number"}),
            "franchise_type": forms.Select(attrs={"class": "form-control"}),
            "payment_status": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_franchise": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "referred_by": forms.Select(attrs={"class": "form-control", "placeholder": "Select Referrer (Optional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up referred_by field to show franchise names
        self.fields['referred_by'].queryset = Franchise.objects.filter(is_active=True).order_by('franchise_name')
        self.fields['referred_by'].empty_label = "Select a referrer (optional)"
        
        # Set up staff field to show staff members
        from users.models import StaffModel
        self.fields['staff'].queryset = StaffModel.objects.filter(is_active=True).order_by('first_name')
        self.fields['staff'].empty_label = "Select staff (optional)"



class FranchisePasswordForm(forms.Form):
    """Form for franchise to change their own password"""
    current_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Current Password"}
        ),
        required=True,
        label="Current Password"
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "New Password"}
        ),
        required=True,
        min_length=8,
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirm New Password"}
        ),
        required=True,
        label="Confirm New Password"
    )

    def __init__(self, franchise=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.franchise = franchise

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get('current_password')
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        # Check if current password is correct
        if self.franchise and current_password:
            if not self.franchise.check_password(current_password):
                raise ValidationError("Current password is incorrect.")

        # Check if new passwords match
        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError("New passwords do not match.")

        return cleaned_data


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


class FranchiseAddByFranchiseForm(forms.ModelForm):
    """Form for franchise users to add new franchises (with read-only staff and payment status)"""

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
            "staff": forms.Select(attrs={"class": "form-control", "disabled": "disabled"}),
            "franchise_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Franchise Name"}),
            "franchise_owner": forms.TextInput(attrs={"class": "form-control", "placeholder": "Franchise Owner"}),
            "franchise_place": forms.TextInput(attrs={"class": "form-control", "placeholder": "Franchise Place"}),
            "franchise_type": forms.Select(attrs={"class": "form-control"}),
            "payment_status": forms.CheckboxInput(attrs={"class": "form-check-input", "disabled": "disabled"}),
            "referred_by": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly", "placeholder": "Referral Code"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address"}),
            "mobile_no": forms.TextInput(attrs={"class": "form-control", "placeholder": "Mobile Number"}),
        }

    def __init__(self, *args, **kwargs):
        self.referring_franchise = kwargs.pop('referring_franchise', None)
        super().__init__(*args, **kwargs)
        
        # Set up staff field as read-only
        self.fields['staff'].queryset = StaffModel.objects.all()
        self.fields['staff'].empty_label = "Will be assigned by admin"
        self.fields['staff'].help_text = "Staff assignment will be managed by admin"
        
        # Set up referred_by field with referring franchise info
        if self.referring_franchise:
            self.fields['referred_by'].initial = f"{self.referring_franchise.franchise_name} ({self.referring_franchise.referral_code})"
            self.fields['referred_by'].help_text = "This franchise will be referred by you"
        
        # Set default values for read-only fields
        self.fields['payment_status'].initial = False
        self.fields['payment_status'].help_text = "Payment status will be managed by admin"

    def save(self, commit=True):
        """Save the franchise with the referring franchise set"""
        franchise = super().save(commit=False)
        if self.referring_franchise:
            franchise.referred_by = self.referring_franchise
        if commit:
            franchise.save()
        return franchise


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

    allowance = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Allowance", "min": "0", "step": "0.01"}),
        help_text="Monthly allowance amount"
    )

    commission = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Commission", "min": "0", "step": "0.01"}),
        help_text="Commission amount"
    )
    incentive = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Incentive", "min": "0", "step": "0.01"}),
        help_text="Incentive amount"
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
        
        # Update allowance if provided
        if self.cleaned_data.get('allowance') is not None:
            wallet.allowance = self.cleaned_data['allowance']
        
        # Update commission if provided
        if self.cleaned_data.get('commission') is not None:
            wallet.commission = self.cleaned_data['commission']
        
        # Update incentive if provided
        if self.cleaned_data.get('incentive') is not None:
            wallet.incentive = self.cleaned_data['incentive']
        
        wallet.save()
        return wallet

# =============================================================================
# STAFF ASSIGNMENT FORM
# =============================================================================

class StaffAssignmentForm(forms.ModelForm):
    """Form to assign one staff to multiple franchises, or edit an assignment"""

    # Override staff_name as ModelChoiceField to ensure proper model handling
    staff_name = forms.ModelChoiceField(
        queryset=StaffModel.objects.none(),
        widget=forms.Select(attrs={"class": "form-select form-control"}),
        required=True,
        label="Staff",
        empty_label="Select Staff"
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

        # Set the queryset for staff_name field
        staff_qs = StaffModel.objects.all().order_by("first_name", "last_name")
        self.fields["staff_name"].queryset = staff_qs
        
        # Set the queryset for franchise_name field
        self.fields["franchise_name"].queryset = Franchise.objects.all().order_by("franchise_name")
        
        # Set initial values for editing
        if self.instance and self.instance.pk:
            if self.instance.staff_name:
                self.fields["staff_name"].initial = self.instance.staff_name
            else:
                self.fields["staff_name"].initial = None

    def save(self, commit=True):
        # With ModelChoiceField, the staff_name is already a StaffModel instance
        # So we can just call the parent save method
        instance = super().save(commit=commit)
        
        # Ensure ManyToMany is saved when commit=True; if commit=False, caller must handle save_m2m
        if commit and hasattr(self, "save_m2m"):
            self.save_m2m()
        return instance


class StaffProfileUpdateForm(forms.ModelForm):
    """Form for staff profile updates - name and profile picture only"""
    
    class Meta:
        model = StaffModel
        fields = ['first_name', 'last_name', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control form-control-user',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control form-control-user',
                'placeholder': 'Last Name'
            }),
            'profile_picture': forms.ClearableFileInput(attrs={
                'class': 'form-control form-control-user',
                'accept': 'image/*'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['profile_picture'].required = False
        self.fields['profile_picture'].help_text = "Upload a profile picture (JPG, PNG, GIF - Max 5MB)"

    def clean_profile_picture(self):
        profile_picture = self.cleaned_data.get('profile_picture')
        
        if profile_picture:
            # Check file size (5MB limit)
            if profile_picture.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Profile picture size should not exceed 5MB.")
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if profile_picture.content_type not in allowed_types:
                raise forms.ValidationError("Only JPG, PNG, and GIF images are allowed.")
        
        return profile_picture


class StaffPasswordChangeForm(forms.Form):
    """Form for staff password change"""
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-user",
            "placeholder": "Current Password"
        }),
        required=True
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-user",
            "placeholder": "New Password"
        }),
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-user",
            "placeholder": "Confirm New Password"
        }),
        required=True
    )

    def __init__(self, staff_instance, *args, **kwargs):
        self.staff_instance = staff_instance
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        """Validate current password"""
        current_password = self.cleaned_data.get("current_password")
        if not self.staff_instance.check_password(current_password):
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
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError("New passwords don't match.")

        return cleaned_data

