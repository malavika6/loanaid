from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from .models import *


# Import optimized forms
from .admin_forms import AdminForm
from .staff_forms import StaffModelForm
from .franchise_forms import FranchiseForm


# StaffModelForm is now imported from staff_forms.py



# FranchiseForm is now imported from franchise_forms.py
