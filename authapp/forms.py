from django import forms

class StaffAssignmentForm(forms.Form):
    # Add your fields here
    staff = forms.CharField(max_length=100)
    assignment = forms.CharField(max_length=100)
    # Add other fields as needed
