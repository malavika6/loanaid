from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from .models import *


class UserForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-user',
            'placeholder': 'Confirm Password'
        }), required=False
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-user',
            'placeholder': 'Password'
        })
    )

    class Meta:
        model = UserModel
        fields = ['name', 'phone_number', 'email', 'password']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-user',
                'placeholder': 'Full Name'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control form-control-user',
                'placeholder': 'Phone Number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-user',
                'placeholder': 'Email Address'
            }),
            'password': forms.PasswordInput(attrs={
                'class': 'form-control form-control-user',
                'placeholder': 'Password'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        # If confirm_password is filled in (registration), check if passwords match
        if confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            # Hash the password before saving if it's a registration
            user.password = make_password(user.password)
            user.save()
        return user

    def authenticate_user(self):
        """ Custom method to handle login authentication """
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']
        return authenticate(email=email, password=password)


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

    class Meta:
        model = StaffModel
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_no",
            "password",
            "is_active",
            "is_staff",
            "employee_id"
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "First Name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Last Name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Email Address",
                }
            ),
            "phone_no": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Phone Number",
                }
            ),
            "employee_id": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "password": forms.PasswordInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Password",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # If an admin user is provided, set them as the manager of the staff
        if user and isinstance(user, AdminModel):
            self.instance.managed_by = user

    def clean_email(self):
        email = self.cleaned_data.get("email")
        instance = self.instance  # Get current instance

        # Check if email already exists, excluding the current instance
        if StaffModel.objects.filter(email=email).exclude(pk=instance.pk).exists():
            raise ValidationError(
                "A staff member with this email already exists.")
        return email

    def clean_phone_no(self):
        phone = self.cleaned_data.get("phone_no")
        if phone and (len(phone) != 10 or not phone.isdigit()):
            raise ValidationError(
                "Phone Number must be exactly 10 digits and contain only numbers.")
        return phone

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password and len(password) < 8:
            raise ValidationError(
                "Password must be at least 8 characters long.")
        return password  # No hashing here

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")

        return cleaned_data

    # Ensure password is hashed before saving the model
    def save(self, commit=True):
        staff = super().save(commit=False)
        if commit:
            staff.save()
        return staff


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = StaffModel
        fields = [
            "adhaar_no",
            "adhaar_img",
            "pan_no",
            "pan_img",
            "bank_name",
            "ifsc_code",
            "account_no",
            "branch",
        ]
        widgets = {
            "adhaar_no": forms.TextInput(attrs={"class": "form-control", "placeholder": "Aadhaar No"}),
            "adhaar_img": forms.FileInput(attrs={"class": "form-control"}),
            "pan_no": forms.TextInput(attrs={"class": "form-control", "placeholder": "PAN No"}),
            "pan_img": forms.FileInput(attrs={"class": "form-control"}),
            "bank_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Bank Name"}),
            "ifsc_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "IFSC Code"}),
            "account_no": forms.TextInput(attrs={"class": "form-control", "placeholder": "Account No"}),
            "branch": forms.TextInput(attrs={"class": "form-control", "placeholder": "Branch"}),
        }

    def __init__(self, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)


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


class LoanApplicationForm(forms.ModelForm):
    franchise_mobile_no = forms.CharField(
        widget=forms.TextInput(attrs={
                               "class": "form-control", "placeholder": "Franchise Mobile No.", "disabled": "disabled"}),
        required=False
    )
    franchise_place = forms.CharField(
        widget=forms.TextInput(attrs={
                               "class": "form-control", "placeholder": "Franchise Place", "disabled": "disabled"}),
        required=False
    )
    cibil_issue = forms.ChoiceField(
        choices=[('Yes', 'Yes'), ('No', 'No'), ("Don't Know", "Don't Know")],
        widget=forms.Select(attrs={"class": "form-control"})
    )
    it_payable = forms.ChoiceField(
        choices=[('Yes', 'Yes'), ('No', 'No')],
        widget=forms.Select(attrs={"class": "form-control"})
    )
    guaranter_cibil_issue = forms.ChoiceField(
        choices=[('Yes', 'Yes'), ('No', 'No'), ("Don't Know", "Don't Know")],
        widget=forms.Select(attrs={"class": "form-control"}),
        required=False
    )
    guaranter_it_payable = forms.ChoiceField(
        choices=[('Yes', 'Yes'), ('No', 'No')],
        widget=forms.Select(attrs={"class": "form-control"}),
        required=False
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
        ]
        widgets = {
            "franchise": forms.Select(attrs={"class": "form-select form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "First Name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Last Name"}),
            "district": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "District"}),
            "place": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Place"}),
            "phone_no": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Phone Number"}),
            "guaranter_name": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Guarantor Name"}),
            "guaranter_phoneno": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Guarantor Phone Number"}),
            "guaranter_job": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Guarantor Job"}),
            "guaranter_cibil_score": forms.NumberInput(attrs={"class": "form-control form-control-user", "placeholder": "Guarantor CIBIL Score"}),
            "guaranter_cibil_issue": forms.Select(attrs={"class": "form-select form-control"}),
            "guaranter_it_payable": forms.Select(attrs={"class": "form-select form-control"}),
            "job": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Job"}),
            "cibil_score": forms.NumberInput(attrs={"class": "form-control form-control-user", "placeholder": "CIBIL Score"}),
            "cibil_issue": forms.Select(attrs={"class": "form-select form-control"}),
            "it_payable": forms.Select(attrs={"class": "form-select form-control"}),
            'loan_name': forms.Select(attrs={'class': 'form-select form-control', 'required': False}),
            "loan_amount": forms.NumberInput(attrs={"class": "form-control form-control-user", "placeholder": "Loan Amount"}),
            "followup_date": forms.DateInput(attrs={"class": "form-control form-control-user", "placeholder": "Follow-up Date", "type": "date"}),
            "description": forms.Textarea(attrs={"class": "form-control form-control-user", "placeholder": "Description", "rows": 3}),
            "status_name": forms.Select(attrs={"class": "form-select form-control"}),
            "bank_name": forms.Select(attrs={"class": "form-select form-control"}),
            "executive_name": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Executive Name"}),
            "mobileno_1": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Mobile Number 1"}),
            "mobileno_2": forms.TextInput(attrs={"class": "form-control form-control-user", "placeholder": "Mobile Number 2"}),
            "document_description": forms.Textarea(attrs={"class": "form-control form-control-user", "placeholder": "Document Description", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        user_type = kwargs.pop('user_type', None)
        super().__init__(*args, **kwargs)
        if user_type == 'franchise':
            self.fields['followup_date'].widget.attrs['disabled'] = True
            self.fields['status_name'].widget.attrs['disabled'] = True
            self.fields['executive_name'].widget.attrs['disabled'] = True
            self.fields['mobileno_1'].widget.attrs['disabled'] = True
            self.fields['mobileno_2'].widget.attrs['disabled'] = True

        # Ensure franchise dropdown is populated
        self.fields['franchise'].queryset = Franchise.objects.all()

        if self.instance.franchise:
            self.fields['franchise_mobile_no'].initial = self.instance.franchise.mobile_no
            self.fields['franchise_place'].initial = self.instance.franchise.franchise_place

        self.fields['franchise_mobile_no'].widget.attrs['disabled'] = 'disabled'
        self.fields['franchise_place'].widget.attrs['disabled'] = 'disabled'


class StaffAssignmentForm(forms.ModelForm):
    staff_name = forms.ModelChoiceField(
        queryset=StaffModel.objects.all(),
        widget=forms.Select(attrs={"class": "form-select form-control"}),
        label="Staff Name"
    )
    franchise_name = forms.ModelMultipleChoiceField(
        queryset=Franchise.objects.all(),
        widget=forms.CheckboxSelectMultiple(
            attrs={"class": "form-check-input"}),
        label="Select Franchise(s)"
    )

    class Meta:
        model = StaffAssignmentModel
        fields = ['staff_name', 'franchise_name']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            # Filter franchises based on user, if needed
            self.fields["franchise_name"].queryset = Franchise.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        staff = cleaned_data.get("staff_name")
        franchises = cleaned_data.get("franchise_name")

        if staff and franchises:
            existing = StaffAssignmentModel.objects.filter(
                staff_name=staff,
                franchise_name__in=franchises
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError(
                    "One or more of the selected franchises are already assigned to this staff.")


class LoanForm(forms.ModelForm):
    class Meta:
        model = LoanModel
        fields = ["loan_name", "description"]
        widgets = {
            "loan_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Loan Name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Loan Description",
                    "rows": 3,
                    "required": False,
                }
            ),
        }


class StatusForm(forms.ModelForm):
    class Meta:
        model = StatusModel
        fields = ["status_name", "description"]
        widgets = {
            "status_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Status Name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Status Description",
                    "rows": 3,
                    "required": False,
                }
            ),
        }


class BankForm(forms.ModelForm):
    class Meta:
        model = BankModel
        fields = ["bank_name"]
        widgets = {
            "bank_name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "Bank Name",
                }
            )
        }

    def clean_bank_name(self):
        bank_name = self.cleaned_data['bank_name'].strip()

        # Check if bank name already exists (case-insensitive)
        if BankModel.objects.filter(bank_name__iexact=bank_name).exists():
            raise ValidationError("A bank with this name already exists.")

        return bank_name


class UploadedFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ["loan_application", "file", "file_type"]
        widgets = {
            "loan_application": forms.Select(
                attrs={"class": "form-select form-control"}
            ),
            "file": forms.FileInput(attrs={"class": "form-control"}),
            "file_type": forms.TextInput(
                attrs={
                    "class": "form-control form-control-user",
                    "placeholder": "File Type/Description",
                }
            ),
        }
