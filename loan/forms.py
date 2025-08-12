from django import forms
from django.core.exceptions import ValidationError      
from users.models import StaffModel, Franchise
from loan.models import (
    LoanApplicationModel,   
    LoanModel,
    StatusModel,
    BankModel,
    UploadedFile,
    StaffAssignmentModel
)
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
