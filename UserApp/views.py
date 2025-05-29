from UserApp.utils import get_sidebar_menu, get_user_context
from UserApp.forms import UserForm
from UserApp.models import AdminModel, Franchise, StaffModel, UserModel, LoanApplicationModel, Payment
import uuid
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout as django_logout
from django.contrib.auth.hashers import check_password
from django.db.models import Count
from django.db.models.functions import TruncMonth, TruncYear
from django.http import JsonResponse
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from UserApp.models import *
from UserApp.forms import *
from dashboard.views import *
from datetime import datetime
from django.shortcuts import render, redirect
from .models import StaffModel, LoanApplicationModel
from django.contrib import messages
from django.urls import reverse
from .utils import get_sidebar_menu, get_user_context


import logging

logger = logging.getLogger(__name__)


# Import your models and forms

logger = logging.getLogger(__name__)


def register(request):
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserForm()
    return render(request, 'register.html', {'form': form})


def login(request):
    """
    Handle user login for all user types (admin, franchise, staff, executive).
    Make sure that the identifier you use (usually an email) is consistently used
    to fetch the correct record and that the session is set using the correct PK.
    """
    error = None

    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')

        user = None
        user_type = None

        # Check Admin
        try:
            admin = AdminModel.objects.get(admin_email=identifier)
            if check_password(password, admin.admin_password):
                user, user_type = admin, 'admin'
        except AdminModel.DoesNotExist:
            pass

        # Check Franchise
        if not user:
            try:
                franchise = Franchise.objects.get(email=identifier)
                if check_password(password, franchise.password):
                    if franchise.payment_status:  # Payment verified
                        request.session.flush()
                        # Store using PK so that get_user_context can look it up with pk.
                        request.session['user_id'] = str(franchise.pk)
                        request.session['user_type'] = 'franchise'
                        request.session['franchise_id'] = str(franchise.pk)  # <-- THIS IS MISSING

                        # Clear old payment flags
                        request.session.pop('requires_payment', None)
                        request.session.set_expiry(
                            3600)  # 1-hour session expiry
                        logger.info(
                            f"Franchise login successful (ID: {franchise.pk})")
                        return redirect('/franchise_dashboard')
                    # If payment is not active, set flags for payment redirect
                    request.session['franchise_id'] = str(franchise.pk)
                    request.session['requires_payment'] = True
                    return redirect('payment_redirect')
            except Franchise.DoesNotExist:
                pass

        # Check Staff
        if not user:
            try:
                staff = StaffModel.objects.get(email=identifier)
                # NOTE: For security, you should use hashed passwords.
                if password == staff.password:
                    user, user_type = staff, 'staff'
            except StaffModel.DoesNotExist:
                pass

        # Check Executive
        if not user:
            try:
                executive = UserModel.objects.get(email=identifier)
                if check_password(password, executive.password):
                    user, user_type = executive, 'executive'
            except UserModel.DoesNotExist:
                pass

        # Login handling
        if user:
            request.session.flush()  # Clear any existing session data
            # Use the object's primary key so that our get_user_context (which should look up via PK) succeeds.
            request.session['user_id'] = str(user.pk)
            request.session['user_type'] = user_type
            request.session.set_expiry(3600)  # 1-hour session expiry

            logger.info(f"Login successful: {user_type} (ID: {user.pk})")

            # Redirect based on user type
            if user_type == 'admin':
                return redirect('/')
            elif user_type == 'franchise':
                return redirect('/franchise_dashboard')
            elif user_type == 'staff':
                return redirect('/dashboard')
            elif user_type == 'executive':
                return redirect(f'/index/{user.pk}')
        else:
            error = "Invalid credentials. Please try again."
            logger.warning(f"Login failed for identifier: {identifier}")
            messages.error(request, "Invalid credentials. Please try again.")

    return render(request, 'login.html', {'error': error})


# def staff_dashboard(request):
#     sidebar_menu, username = get_user_context(request)
#     if not sidebar_menu or not username:
#         return redirect('/login')

#     user_id = request.session.get('user_id')

#     # Get franchises assigned to this staff
#     staff = StaffModel.objects.get(pk=user_id)
#     assigned_franchises = Franchise.objects.filter(staffassignmentmodel__staff_name=staff).distinct()

#     # Loans assigned to staff or franchises they are assigned to
#     staff_loans = LoanApplicationModel.objects.filter(assigned_to=staff)
#     franchise_loans = LoanApplicationModel.objects.filter(franchise__in=assigned_franchises)
#     all_loans = (staff_loans | franchise_loans).distinct()

#     assigned_franchise_count = assigned_franchises.count()
#     franchise_loan_count = franchise_loans.count()

#     context = {
#         'sidebar_menu': sidebar_menu,
#         'username': username,
#         'all_loans': franchise_loans,  # send loans as all_loans for template
#         'franchise_loans': franchise_loan_count,
#         'assigned_franchise_count': assigned_franchise_count,
#         'assigned_franchises': assigned_franchises,
#     }
#     return render(request, 'dashboard.html', context)



def home(request):
    """
    Dashboard view for admin users.
    """
    sidebar_menu, username = get_user_context(request)
    if not sidebar_menu or not username:
        return redirect('/login')

    user_type = request.session.get('user_type')
    print(
        "user_type", user_type)  # Debugging line to check user_type)
    if user_type == 'admin':
        today = datetime.now().date()
        all_loans = LoanApplicationModel.objects.filter(followup_date=today)
        loan_followup = all_loans.filter(
            assigned_to=request.session.get('user_id'))

        all_franchises = Franchise.objects.all()
        franchise_count = all_franchises.count()

        all_staff = StaffModel.objects.all()
        staff_count = all_staff.count()

        loan_app = LoanApplicationModel.objects.all()
        loan_app_count = loan_app.count()
        last_loan_app = loan_app.order_by('-form_id')[:10]

        context = {
            'username': username,
            'forms': last_loan_app,
            'loans': all_loans,
            'total_franchise_count': franchise_count,
            'total_staff_count': staff_count,
            'loan_app_count': loan_app_count,
            'all_franchises': all_franchises,
            'all_staff': all_staff,
            'sidebar_menu': sidebar_menu,
            'can_add_loan': True
        }
        return render(request, 'index.html', context)

    elif user_type == 'staff':
        staff_id = request.session.get('user_id')
        staff = StaffModel.objects.get(staff_id=staff_id)


        # Get the franchises assigned to this staff from StaffAssignmentModel
        assigned_franchise_qs = Franchise.objects.filter(
            staffassignmentmodel__staff_name=staff
        ).distinct()

        # Convert to set
        assigned_franchises = set()
        for franchise in assigned_franchise_qs:
            assigned_franchises.add(franchise)

        # Count of assigned franchises
        assigned_franchise_count = len(assigned_franchises)

        # Get loans assigned to this staff directly
        staff_loans = LoanApplicationModel.objects.filter(assigned_to=staff_id)

        # Get loans associated with the assigned franchises
        loans_from_franchises = LoanApplicationModel.objects.filter(franchise__in=assigned_franchises)
        franchise_loan_count = loans_from_franchises.count()

        context = {
            'username': username,
            'sidebar_menu': sidebar_menu,
            'all_loans': loans_from_franchises,
            'staff_loans': staff_loans,
            'franchise_loans': franchise_loan_count,
            'assigned_franchise_count': assigned_franchise_count,
            'assigned_franchises': assigned_franchises,
        }
        return render(request, 'dashboard.html', context)


    elif user_type == 'franchise':
        staff_loans = LoanApplicationModel.objects.filter(
            assigned_to=request.session.get('staff_id'))

        context = {
            'username': username,
            'sidebar_menu': sidebar_menu,
        }
        return render(request, 'franchise_dashboard.html', context)
    else:
        # If the user is neither admin nor staff, redirect them to login or another page.
        return redirect('/login')


def payment_redirect(request):
    """
    Render a page with UPI payment instructions and auto-redirect using JavaScript.
    """
    franchise_id = request.session.get('franchise_id')
    requires_payment = request.session.get('requires_payment', False)

    if not franchise_id or not requires_payment:
        return redirect('login')

    # UPI Payment Deep Link details
    upi_id = '8138911511@ybl'
    payment_amount = 500  # Example amount
    payment_note = 'Franchise Membership Payment'
    upi_link = f"upi://pay?pa={upi_id}&pn=Franchise&mc=&tid=&tr=&tn={payment_note}&am={payment_amount}&cu=INR"

    context = {
        'upi_link': upi_link
    }
    return render(request, 'payment_redirect.html', context)


def payment_confirmation(request):
    """
    Process payment confirmation uploads.
    """
    franchise_id = request.session.get('franchise_id')
    if not franchise_id:
        return redirect('login')

    if request.method == 'POST':
        screenshot = request.FILES.get('payment_screenshot')
        transaction_id = request.POST.get('transaction_id', str(uuid.uuid4()))
        try:
            franchise = Franchise.objects.get(pk=franchise_id)

            # Create a payment record (assumes you have a Payment model)
            payment = Payment.objects.create(
                franchise=franchise,
                transaction_id=transaction_id,
                payment_screenshot=screenshot,
                status='pending'  # Waiting for admin verification
            )

            # Mark franchise as pending verification
            franchise.payment_status = False
            franchise.save()

            messages.success(
                request, "Payment receipt uploaded! We will verify it soon.")
            return redirect('/franchise_dashboard')

        except Franchise.DoesNotExist:
            messages.error(request, "Franchise not found.")

    return redirect('/franchise_dashboard')


def logout_view(request):
    """
    Log out the user by clearing the session.
    """
    request.session.pop('user_id', None)
    request.session.pop('user_type', None)
    django_logout(request)
    request.session.flush()
    return redirect('/')


def other_user_dashboard(request, user_id):
    try:
        # This should be correct since you use 'id' for the UserModel
        other_user = UserModel.objects.get(user_id=user_id)
        other_user_name = f"{other_user.name} "
    except UserModel.DoesNotExist:
        return redirect('/login')

    # Check if 'other_user' is a StaffModel, and get the related staff instance
    try:
        # Or use 'user_id' if that's how it's related
        staff_member = StaffModel.objects.get(email=other_user.email)
    except StaffModel.DoesNotExist:
        staff_member = None

    # Fetch loans related to this user (checking the staff member)
    related_loans = LoanApplicationModel.objects.filter(
        assigned_to=staff_member)  # Use 'assigned_to' to filter by staff
    loan_count = related_loans.count()

    # Count the number of franchises
    all_franchises = Franchise.objects.all()
    franchise_count = all_franchises.count()

    context = {
        'username': other_user_name,
        'other_user': other_user,
        'related_loans': related_loans,
        'loan_count': loan_count,
        'franchise_count': franchise_count,
        'can_add_loan': True  # 4th type user can add loans
    }

    return render(request, 'home.html', context)


def update_profile(request):
    user_id = request.session.get('user_id', None)
    if user_id is None:
        return redirect('/login')

    staff = StaffModel.objects.get(staff_id=user_id)

    if request.method == 'POST':
        form = ProfileUpdateForm(
            request.POST, request.FILES, instance=staff)  # Use staff directly
        if form.is_valid():
            form.save()
            staff.profile_completed = True  # Mark the profile as completed
            staff.save()
            return redirect('/')
    else:
        form = ProfileUpdateForm(instance=staff)  # Use staff directly

    return render(request, 'profile_update.html', {'form': form, 'username': f"{staff.first_name} {staff.last_name}"})


def create_staff(request):
    user_id = request.session.get('user_id')
    if user_id is None:
        return redirect('/login')

    try:
        admin = AdminModel.objects.get(admin_id=user_id)
        if not admin.is_superadmin:
            return redirect('/')  # Redirect non-admin users

        if request.method == 'POST':
            form = StaffModelForm(request.POST, request.FILES)
            if form.is_valid():
                staff = form.save(commit=False)
                staff.save()  # Save staff with all details
                messages.success(request, "Staff member added successfully!")
                return redirect('/')  # Redirect after successful creation
            else:
                messages.error(
                    request, "There was an error in the form. Please correct it.")

        else:
            form = StaffModelForm()

        return render(request, 'create-staff.html', {'form': form})

    except AdminModel.DoesNotExist:
        return redirect('/login')  # Handle case where admin doesn't exist


def view_staffs(request, staff_id):
    user_id = request.session.get('user_id')
    if user_id is None:
        return redirect('/login')

    try:
        admin = AdminModel.objects.get(admin_id=user_id)
        admin_name = f"{admin.admin_first_name} {admin.admin_last_name or ''}".strip()

        # Fetch staff details
        staff_member = get_object_or_404(StaffModel, pk=staff_id)

        return render(request, 'staff_detail.html', {
            'staff_member': staff_member,
            'admin_name': admin_name
        })

    except AdminModel.DoesNotExist:
        messages.error(request, "Admin not found. Please log in again.")
        return redirect('/login')


def list_staff(request):
    all_staff = StaffModel.objects.all()
    context = {'all_staff': all_staff}
    return render(request, 'all_staffs.html', context)


def delete_staff(request, staff_id):
    staff_member = get_object_or_404(StaffModel, pk=staff_id)

    if request.method == 'POST':
        LoanApplicationModel.objects.filter(
            assigned_to=staff_member).update(assigned_to=None)

        staff_member.delete()

        return redirect('/')
    return redirect('/')


def delete_files(request, id):
    file = get_object_or_404(UploadedFile, pk=id)
    loan_id = file.loan_application.form_id
    if request.method == 'POST':
        file.delete()
        # Adjust the redirect based on your URL name for the user list page
        return redirect('loan-page', loan_id)
    return redirect('loan-page', loan_id)


def get_sidebar_menu(user_type):
    """
    Generate sidebar menu items based on user type.
    """
    menu = []

    if user_type == 'admin':
        menu = [
            {'name': 'Dashboard', 'url': '/'},
            {'name': 'Manage Franchises', 'url': '/list_franchise'},
            {'name': 'Manage Staff', 'url': '/list_staff'},
            {'name': 'Add Loan', 'url': '/add-loan'},
        ]
    elif user_type == 'franchise':
        menu = [
            {'name': 'Dashboard', 'url': '/franchise_dashboard'},
            {'name': 'My Loans', 'url': '/loan-page'},
            {'name': 'Profile', 'url': '/profile'},
        ]
    elif user_type == 'staff':
        menu = [
            {'name': 'Dashboard', 'url': '/dashboard'},
            {'name': 'Assignments', 'url': '/staff_assignments'},
            {'name': 'Profile', 'url': '/profile'},
        ]
    elif user_type == 'executive':
        menu = [
            {'name': 'Dashboard', 'url': f'/index/{user_type}'},
            {'name': 'Profile', 'url': '/profile'},
        ]

    return menu


def some_view(request):
    user_type = request.session.get('user_type', None)
    sidebar_menu = get_sidebar_menu(user_type)

    context = {
        'sidebar_menu': sidebar_menu,
        # ...other context variables...
    }

    return render(request, 'some_template.html', context)
