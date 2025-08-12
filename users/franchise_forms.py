from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator
from .models import Franchise
import re
import logging

logger = logging.getLogger(__name__)


class FranchiseForm(forms.ModelForm):
    """Enhanced form for creating and managing franchises"""
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
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
                "class": "form-control",
                "placeholder": "Current Password (for updates)",
                "autocomplete": "current-password"
            }
        ),
        required=False,
        help_text="Required when updating existing franchise"
    )
    
    referral_code = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": "readonly",
                "placeholder": "Auto-generated"
            }
        ),
        help_text="Automatically generated referral code"
    )
    
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "franchise_is_active"
            }
        ),
        help_text="Check if franchise account is active"
    )
    
    payment_status = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "franchise_payment_status"
            }
        ),
        help_text="Check if payment is verified"
    )

    class Meta:
        model = Franchise
        fields = [
            "referral_code",
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
            "wallet_balance",
            "payment_status",
            "is_franchise",
            "screenshot",
            "is_active"
        ]
        widgets = {
            "franchise_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Franchise Name",
                    "autocomplete": "organization"
                }
            ),
            "franchise_owner": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Franchise Owner",
                    "autocomplete": "name"
                }
            ),
            "franchise_place": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Franchise Place",
                    "autocomplete": "address-level2"
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email Address",
                    "autocomplete": "email"
                }
            ),
            "mobile_no": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Mobile Number",
                    "autocomplete": "tel"
                }
            ),
            "password": forms.PasswordInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Password",
                    "autocomplete": "new-password"
                }
            ),
            "confirm_password": forms.PasswordInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Confirm Password",
                    "autocomplete": "new-password"
                }
            ),
            "aadhar": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Aadhar Number",
                    "maxlength": "12"
                }
            ),
            "GST": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "GST Number",
                    "maxlength": "15"
                }
            ),
            "pan": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "PAN Number",
                    "maxlength": "10"
                }
            ),
            "ac_no": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Account Number",
                    "maxlength": "18"
                }
            ),
            "ifsc_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "IFSC Code",
                    "maxlength": "11"
                }
            ),
            "wallet_balance": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Wallet Balance",
                    "step": "0.01",
                    "min": "0"
                }
            ),
            "is_franchise": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                    "id": "franchise_is_franchise"
                }
            ),
            "screenshot": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*,.pdf"
                }
            ),
        }
        help_texts = {
            'franchise_name': 'Enter the franchise business name',
            'franchise_owner': 'Enter the franchise owner\'s full name',
            'franchise_place': 'Enter the city/location of the franchise',
            'email': 'Enter a unique email address for the franchise',
            'mobile_no': 'Enter a 10-digit mobile number',
            'password': 'Create a strong password (minimum 8 characters)',
            'aadhar': 'Enter 12-digit Aadhar number',
            'GST': 'Enter 15-character GST number',
            'pan': 'Enter 10-character PAN number',
            'ac_no': 'Enter 9-18 digit account number',
            'ifsc_code': 'Enter 11-character IFSC code',
            'wallet_balance': 'Enter initial wallet balance',
            'screenshot': 'Upload payment screenshot or document'
        }

    def __init__(self, *args, **kwargs):
        self.is_update = kwargs.get('instance') is not None
        super().__init__(*args, **kwargs)
        
        # Set referral_code initial value if instance exists
        if self.instance and self.instance.referral_code:
            self.fields['referral_code'].initial = self.instance.referral_code
        
        # Make password optional for updates
        if self.is_update:
            self.fields['password'].required = False
            self.fields['password'].help_text = "Leave blank to keep current password"
            self.fields['current_password'].required = True
        else:
            self.fields['password'].required = True
            self.fields['current_password'].required = False
            self.fields['current_password'].widget = forms.HiddenInput()

    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get("email")
        instance = self.instance
        
        if Franchise.objects.filter(email=email).exclude(pk=instance.pk if instance else None).exists():
            raise ValidationError("A franchise with this email already exists.")
        
        return email

    def clean_mobile_no(self):
        """Validate mobile number format"""
        mobile = self.cleaned_data.get("mobile_no")
        
        if mobile:
            # Remove any non-digit characters
            mobile = ''.join(filter(str.isdigit, mobile))
            
            if len(mobile) != 10:
                raise ValidationError("Mobile number must be exactly 10 digits.")
            
            if not mobile.isdigit():
                raise ValidationError("Mobile number must contain only numbers.")
        
        return mobile

    def clean_aadhar(self):
        """Validate Aadhar number format"""
        aadhar = self.cleaned_data.get("aadhar")
        
        if aadhar:
            # Remove any non-digit characters
            aadhar = ''.join(filter(str.isdigit, aadhar))
            
            if len(aadhar) != 12:
                raise ValidationError("Aadhar number must be exactly 12 digits.")
            
            if not aadhar.isdigit():
                raise ValidationError("Aadhar number must contain only numbers.")
        
        return aadhar

    def clean_GST(self):
        """Validate GST number format"""
        gst = self.cleaned_data.get("GST")
        
        if gst:
            gst = gst.strip().upper()
            
            # GST format: 2 digits + 10 characters + 1 digit + 1 character
            gst_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
            
            if not re.match(gst_pattern, gst):
                raise ValidationError("Enter a valid GST number (e.g., 22AAAAA0000A1Z5).")
        
        return gst

    def clean_pan(self):
        """Validate PAN number format"""
        pan = self.cleaned_data.get("pan")
        
        if pan:
            pan = pan.strip().upper()
            
            # PAN format: 5 letters + 4 digits + 1 letter
            pan_pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
            
            if not re.match(pan_pattern, pan):
                raise ValidationError("Enter a valid PAN number (e.g., ABCDE1234F).")
        
        return pan

    def clean_ac_no(self):
        """Validate account number format"""
        ac_no = self.cleaned_data.get("ac_no")
        
        if ac_no:
            # Remove any non-digit characters
            ac_no = ''.join(filter(str.isdigit, ac_no))
            
            if not (9 <= len(ac_no) <= 18):
                raise ValidationError("Account number must be between 9 to 18 digits.")
            
            if not ac_no.isdigit():
                raise ValidationError("Account number must contain only numbers.")
        
        return ac_no

    def clean_ifsc_code(self):
        """Validate IFSC code format"""
        ifsc_code = self.cleaned_data.get("ifsc_code")
        
        if ifsc_code:
            ifsc_code = ifsc_code.strip().upper()
            
            # IFSC format: 4 letters + 0 + 6 alphanumeric
            ifsc_pattern = r"^[A-Z]{4}0[A-Z0-9]{6}$"
            
            if not re.match(ifsc_pattern, ifsc_code):
                raise ValidationError("Enter a valid IFSC code (e.g., HDFC0001234).")
        
        return ifsc_code

    def clean_password(self):
        """Validate password strength"""
        password = self.cleaned_data.get("password")
        
        if not password and not self.is_update:
            raise ValidationError("Password is required for new franchise accounts.")
        
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
        """Save franchise with password hashing"""
        franchise = super().save(commit=False)
        
        # Hash password if provided and not already hashed
        if franchise.password and not franchise.password.startswith("pbkdf2_"):
            franchise.password = make_password(franchise.password)
        
        # Generate referral code if not exists
        if not franchise.referral_code:
            franchise.referral_code = self._generate_referral_code()
        
        if commit:
            try:
                franchise.save()
                logger.info(f"Franchise saved successfully: {franchise.email}")
            except Exception as e:
                logger.error(f"Error saving franchise: {e}")
                raise
        
        return franchise

    def _generate_referral_code(self):
        """Generate unique referral code"""
        try:
            import uuid
            return uuid.uuid4().hex[:8].upper()
        except Exception as e:
            logger.error(f"Error generating referral code: {e}")
            return "REF00001"


class FranchiseProfileUpdateForm(forms.ModelForm):
    """Form for updating franchise profile without password change"""
    
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
            "is_active"
        ]
        widgets = {
            "franchise_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Franchise Name"
                }
            ),
            "franchise_owner": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Franchise Owner"
                }
            ),
            "franchise_place": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Franchise Place"
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email Address"
                }
            ),
            "mobile_no": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Mobile Number"
                }
            ),
            "aadhar": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Aadhar Number"
                }
            ),
            "GST": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "GST Number"
                }
            ),
            "pan": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "PAN Number"
                }
            ),
            "ac_no": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Account Number"
                }
            ),
            "ifsc_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "IFSC Code"
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
        
        if Franchise.objects.filter(email=email).exclude(pk=instance.pk).exists():
            raise ValidationError("A franchise with this email already exists.")
        
        return email

    def clean_mobile_no(self):
        """Validate mobile number format"""
        mobile = self.cleaned_data.get("mobile_no")
        
        if mobile:
            mobile = ''.join(filter(str.isdigit, mobile))
            
            if len(mobile) != 10:
                raise ValidationError("Mobile number must be exactly 10 digits.")
            
            if not mobile.isdigit():
                raise ValidationError("Mobile number must contain only numbers.")
        
        return mobile

    def clean_aadhar(self):
        """Validate Aadhar number format"""
        aadhar = self.cleaned_data.get("aadhar")
        
        if aadhar:
            aadhar = ''.join(filter(str.isdigit, aadhar))
            
            if len(aadhar) != 12:
                raise ValidationError("Aadhar number must be exactly 12 digits.")
            
            if not aadhar.isdigit():
                raise ValidationError("Aadhar number must contain only numbers.")
        
        return aadhar

    def clean_GST(self):
        """Validate GST number format"""
        gst = self.cleaned_data.get("GST")
        
        if gst:
            gst = gst.strip().upper()
            gst_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
            
            if not re.match(gst_pattern, gst):
                raise ValidationError("Enter a valid GST number (e.g., 22AAAAA0000A1Z5).")
        
        return gst

    def clean_pan(self):
        """Validate PAN number format"""
        pan = self.cleaned_data.get("pan")
        
        if pan:
            pan = pan.strip().upper()
            pan_pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
            
            if not re.match(pan_pattern, pan):
                raise ValidationError("Enter a valid PAN number (e.g., ABCDE1234F).")
        
        return pan

    def clean_ac_no(self):
        """Validate account number format"""
        ac_no = self.cleaned_data.get("ac_no")
        
        if ac_no:
            ac_no = ''.join(filter(str.isdigit, ac_no))
            
            if not (9 <= len(ac_no) <= 18):
                raise ValidationError("Account number must be between 9 to 18 digits.")
            
            if not ac_no.isdigit():
                raise ValidationError("Account number must contain only numbers.")
        
        return ac_no

    def clean_ifsc_code(self):
        """Validate IFSC code format"""
        ifsc_code = self.cleaned_data.get("ifsc_code")
        
        if ifsc_code:
            ifsc_code = ifsc_code.strip().upper()
            ifsc_pattern = r"^[A-Z]{4}0[A-Z0-9]{6}$"
            
            if not re.match(ifsc_pattern, ifsc_code):
                raise ValidationError("Enter a valid IFSC code (e.g., HDFC0001234).")
        
        return ifsc_code


class FranchisePasswordChangeForm(forms.Form):
    """Form for changing franchise password"""
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Current Password"
            }
        ),
        required=True,
        help_text="Enter your current password"
    )
    
    new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "New Password"
            }
        ),
        required=True,
        help_text="Enter your new password"
    )
    
    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirm New Password"
            }
        ),
        required=True,
        help_text="Confirm your new password"
    )

    def __init__(self, franchise_instance, *args, **kwargs):
        self.franchise_instance = franchise_instance
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        """Validate current password"""
        current_password = self.cleaned_data.get('current_password')
        
        if not self.franchise_instance.check_password(current_password):
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
        """Update franchise password"""
        new_password = self.cleaned_data.get('new_password')
        self.franchise_instance.set_password(new_password)
        self.franchise_instance.save()
        logger.info(f"Password changed for franchise: {self.franchise_instance.email}")


class FranchiseSearchForm(forms.Form):
    """Form for searching and filtering franchises"""
    
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search by name, owner, email, or referral code..."
            }
        ),
        help_text="Search franchises by name, owner, email, or referral code"
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
    
    payment_filter = forms.ChoiceField(
        choices=[
            ('', 'All Payment Statuses'),
            ('verified', 'Payment Verified'),
            ('pending', 'Payment Pending')
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
