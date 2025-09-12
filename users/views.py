from users.utils import get_sidebar_menu, get_user_context
from users.forms import StaffModelForm
from users.models import AdminModel, StaffModel, Franchise
from loan.models import LoanApplicationModel, UploadedFile
from payment.models import Payment
import uuid
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout as django_logout
from django.contrib.auth.hashers import check_password
from datetime import datetime
from django.contrib import messages
from .utils import get_sidebar_menu, get_user_context


import logging



logger = logging.getLogger(__name__)




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
        username = None

        # Check Admin
        try:
            admin = AdminModel.objects.get(admin_email=identifier)
            if check_password(password, admin.admin_password):
                user, user_type = admin, 'admin'
                username = f"{admin.admin_first_name} {admin.admin_last_name or ''}".strip()
        except AdminModel.DoesNotExist:
            pass

        # Check Franchise
        if not user:
            try:
                franchise = Franchise.objects.get(email=identifier)
                if check_password(password, franchise.password):
                    if franchise.payment_status:  # Payment verified
                        request.session.flush()
                        request.session['user_id'] = str(franchise.pk)
                        request.session['user_type'] = 'franchise'
                        request.session['franchise_id'] = str(franchise.pk)
                        request.session['username'] = franchise.franchise_name
                        request.session.pop('requires_payment', None)
                        request.session.set_expiry(3600)
                        logger.info(f"Franchise login successful (ID: {franchise.pk})")
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
                    username = f"{staff.first_name} {staff.last_name or ''}".strip()
            except StaffModel.DoesNotExist:
                pass

        # Login handling
        if user:
            request.session.flush()  # Clear any existing session data
            request.session['user_id'] = str(user.pk)
            request.session['user_type'] = user_type
            request.session['username'] = username
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


def staff_dashboard(request):
    """
    Staff dashboard view - now optimized and delegated to staff_views
    """
    from .staff_views import StaffDashboardView
    
    # Use the optimized staff dashboard view
    staff_view = StaffDashboardView()
    return staff_view.get(request)



def home(request):
    """
    Dashboard view for admin users - now optimized and delegated to AdminDashboardView
    """
    from .admin_views import AdminDashboardView
    # Use the optimized admin dashboard view
    admin_view = AdminDashboardView()
    return admin_view.get(request)
    # ...existing code...


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
        # Use StaffModel for user lookup
        other_user = StaffModel.objects.get(staff_id=user_id)
        other_user_name = f"{other_user.first_name} {other_user.last_name or ''}".strip()
    except StaffModel.DoesNotExist:
        return redirect('/login')

    # Fetch loans related to this staff member
    related_loans = LoanApplicationModel.objects.filter(
        assigned_to=other_user)
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

    return render(request, 'profile_update.html')


def create_staff(request):
    """
    Staff creation view - now optimized and delegated to admin_views
    """
    from .admin_views import create_staff_view
    return create_staff_view(request)


def view_staffs(request, staff_id):
    """
    Staff detail view - now optimized and delegated to admin_views
    """
    from .admin_views import view_staff_detail
    return view_staff_detail(request, staff_id)


def list_staff(request):
    """
    Staff listing view - now optimized and delegated to admin_views
    """
    from .admin_views import list_staff_view
    return list_staff_view(request)


def delete_staff(request, staff_id):
    """
    Staff deletion view - now optimized and delegated to admin_views
    """
    from .admin_views import delete_staff_view
    return delete_staff_view(request, staff_id)



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
