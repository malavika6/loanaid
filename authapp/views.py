from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from datetime import datetime
from django.utils import timezone
from users.models import Franchise
from users.models import *
from authapp.forms import StaffAssignmentForm
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Prefetch
from collections import defaultdict
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError


def add_franchise(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    # Check for unauthorized access
    if not user_id or user_type not in ['admin', 'staff']:
        messages.error(request, "Unauthorized access. Please log in.")
        return redirect('/login/')

    # Handle POST request
    if request.method == 'POST':
        form = FranchiseForm(request.POST, request.FILES)
        if form.is_valid():
            # Form is valid, process and save
            print("Form is valid, saving data...")
            franchise = form.save(commit=False)
            plain_password = request.POST.get('password')

            # Use Django's make_password to hash the password
            franchise.password = make_password(plain_password)

            # If logged-in user is staff, set the staff relation
            if user_type == 'staff':
                try:
                    staff = StaffModel.objects.get(pk=user_id)
                    franchise.staff = staff
                except StaffModel.DoesNotExist:
                    messages.error(request, "Staff user not found.")
                    return redirect('/login/')

            try:
                franchise.save()

                # Send email with franchise details
                send_mail(
                    "Franchise Account Created",
                    f"Hello {franchise.franchise_owner},\n\nYour franchise account has been created successfully!\n\nUsername: {franchise.email}\nPassword: {plain_password}\nReferral Code: {franchise.referral_code}\n\nPlease log in and update your password immediately.",
                    "info@loanaidindia.com",
                    [franchise.email],
                    fail_silently=False,
                )

                messages.success(
                    request, "Franchise added successfully and credentials sent via email.")
                return redirect("list_franchise")
            except IntegrityError as e:
                if 'email' in str(e):
                    form.add_error('email', 'Franchise with this Email already exists.')
                if 'referral_code' in str(e):
                    form.add_error('referral_code', 'Franchise with this Referral code already exists.')
        else:
            # If the form is invalid, return the form again with errors
            messages.error(request, "Please correct the errors in the form.")
            print("Form errors:", form.errors)
            return render(request, 'add_franchise.html', {'form': form})

    # Handle GET request (initial form rendering)
    else:
        form = FranchiseForm()
        return render(request, 'add_franchise.html', {'form': form})


def list_franchise(request):
    # Check if user is logged in via session
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")

    if not user_id or user_type not in ["admin", "staff"]:
        messages.error(request, "Unauthorized access. Please log in.")
        return redirect("/login/")

    # Fetch franchises based on user type
    if user_type in ["admin", "staff"]:
        franchises = Franchise.objects.all()  # Both admin and staff can see all franchises

    return render(request, "list_franchise.html", {"franchises": franchises})

def view_franchise_profile(request):
    # Check if the franchise is logged in
    franchise_id = request.session.get("franchise_id")
    if not franchise_id:
        messages.error(request, "Unauthorized access. Please log in.")
        return redirect("login")

    # Fetch franchise details
    franchise = get_object_or_404(Franchise, franchise_id=franchise_id)

    return render(request, "profile.html", {"franchise": franchise})


def delete_franchise(request, franchise_id):
    # Check authorization
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or user_type not in ['admin', 'staff']:
        messages.error(request, "Unauthorized access.")
        return redirect('/login/')

    franchise = get_object_or_404(Franchise, franchise_id=franchise_id)
    franchise.delete()
    messages.success(request, "Franchise deleted successfully.")
    return redirect('list_franchise')


def franchise_dashboard(request):
    franchise_id = request.session.get("franchise_id")
    if not franchise_id:
        return redirect("/login")

    # Get the franchise object or 404 if not found
    franchise = get_object_or_404(Franchise, franchise_id=franchise_id)

    # Get loans related to this franchise
    loans_from_franchises = LoanApplicationModel.objects.filter(franchise_id=franchise_id).select_related('franchise', 'loan_name')

    # Count the loans
    loan_count = loans_from_franchises.count()

    # Pass franchise, loans, and loan_count to the template
    context = {
        "franchise": franchise,
        "loans": loans_from_franchises,
        "loan_count": loan_count,
    }
    return render(request, 'franchise_dashboard.html', context)



def edit_franchise(request, franchise_id):
    franchise = get_object_or_404(Franchise, franchise_id=franchise_id)
    print(franchise,"test tstets")

    if request.method == 'POST':
        form = FranchiseForm(request.POST, request.FILES, instance=franchise)
        if form.is_valid():
            franchise = form.save(commit=False)

            # Ensure password is not rehashed if unchanged
            plain_password = request.POST.get('password')
            if plain_password and plain_password != franchise.password:
                # Use the set_password method to encrypt the password
                franchise.set_password(plain_password)
                franchise.confirm_password = plain_password

            franchise.save()
            messages.success(request, "Franchise updated successfully.")
            return redirect("list_franchise")

        else:
            messages.error(request, "Please correct the errors in the form.")

    else:
        # Pre-fill password field and confirm_password in the form instead
        form = FranchiseForm(instance=franchise)
        # Remove get_password usage; do not pre-fill password fields for security
        # If you want to pre-fill with the hashed password (not recommended), use:
        # form.fields['password'].initial = franchise.password
        # form.fields['confirm_password'].initial = franchise.password
        # But best practice is to leave them blank
    return render(request, 'add_franchise.html', {'form': form, 'franchise': franchise, 'is_edit': True})



def franchise_logout(request):
    request.session.flush()  # Clear the session
    messages.success(request, "Logged out successfully.")
    return redirect("login")


def assign_staff(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("/login")

    admin = get_object_or_404(AdminModel, admin_id=user_id)

    if request.method == "POST":
        form = StaffAssignmentForm(request.POST, user=admin)
        if form.is_valid():
            staff = form.cleaned_data["staff_name"]
            franchises = form.cleaned_data["franchise_name"]

            created_count = 0
            duplicate_count = 0

            # Create one StaffAssignmentModel per staff, then set franchises (ManyToMany)
            assignment, created = StaffAssignmentModel.objects.get_or_create(
                staff_name=staff,
                assigned_by=admin
            )
            # Check for duplicates before setting
            existing_franchises = set(assignment.franchise_name.all())
            new_franchises = set(franchises) - existing_franchises
            duplicate_count = len(franchises) - len(new_franchises)
            if new_franchises:
                assignment.franchise_name.add(*new_franchises)
                created_count = len(new_franchises)

            if created_count:
                messages.success(request, f"Assigned {created_count} franchise(s) successfully.")
            if duplicate_count:
                messages.warning(request, f"{duplicate_count} franchise(s) were already assigned and skipped.")

            return redirect("staff_assignments")
    else:
        form = StaffAssignmentForm(user=admin)

    return render(request, "assign_assignment.html", {
        "form": form,
        "username": f"{admin.admin_first_name} {admin.admin_last_name or ''}",
    })


def all_staff_assignments(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("/login")

    admin = get_object_or_404(AdminModel, admin_id=user_id)

    staff_assignments = defaultdict(list)
    all_assignments = StaffAssignmentModel.objects.select_related('staff_name', 'assigned_by').prefetch_related('franchise_name')


    for assignment in all_assignments:
        staff_assignments[assignment.staff_name].append(assignment)

    return render(request, "staff_assignments.html", {
        "staff_assignments": dict(staff_assignments),
        "admin": admin,
        "username": f"{admin.admin_first_name} {admin.admin_last_name or ''}",
    })


# Update staff assignment


def update_assignment(request, assignment_id):
    assignment = get_object_or_404(StaffAssignmentModel, assignment_id=assignment_id)
    if request.method == "POST":
        form = StaffAssignmentForm(request.POST, instance=assignment, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff assignment updated successfully.")
            return redirect("staff_assignments")
    else:
        form = StaffAssignmentForm(instance=assignment, user=request.user)
    return render(request, "assign_assignment.html", {"form": form, "assignment": assignment})

