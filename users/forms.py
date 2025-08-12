from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from .models import *


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

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-user",
                "placeholder": "Confirm Password",
            }
        ),
        required=True,
    )

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
            "password",
            "confirm_password",
            "profile_picture"
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "First Name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Last Name"}),
            "email": forms.EmailInput(attrs={"class": "form-control form-control-user", "placeholder": "Email Address"}),
            "phone_no": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Phone Number"}),
            "password": forms.PasswordInput(attrs={"class": "form-control form-control-user", "placeholder": "Password"}),
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

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password and len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        staff = super().save(commit=False)
        if staff.password and not staff.password.startswith("pbkdf2_"):
            staff.password = make_password(staff.password)
        if commit:
            staff.save()
        return staff



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
        ]
        widgets = {
            "referral_code": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
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
            "wallet_balance": forms.TextInput(attrs={"class": "form-control", "placeholder": "Wallet Balance"}),
            "payment_status": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_franchise": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "screenshot": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill referral code if an instance exists
        if self.instance and self.instance.referral_code:
            self.fields["referral_code"].initial = self.instance.referral_code

        # Pre-fill confirm_password with the password if an instance exists
        if self.instance and self.instance.password:
            self.fields['confirm_password'].initial = self.instance.password

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


