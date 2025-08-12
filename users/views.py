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
    sidebar_menu, username = get_user_context(request)
    if not sidebar_menu or not username:
        return redirect('/login')

    user_id = request.session.get('user_id')

    # Get franchises assigned to this staff
    staff = StaffModel.objects.get(pk=user_id)
    assigned_franchises = Franchise.objects.filter(staffassignmentmodel__staff_name=staff).distinct()

    # Loans assigned to staff or franchises they are assigned to
    staff_loans = LoanApplicationModel.objects.filter(assigned_to=staff)
    franchise_loans = LoanApplicationModel.objects.filter(franchise__in=assigned_franchises)
    all_loans = (staff_loans | franchise_loans).distinct()

    assigned_franchise_count = assigned_franchises.count()
    franchise_loan_count = franchise_loans.count()

    context = {
        'sidebar_menu': sidebar_menu,
        'username': username,
        'all_loans': franchise_loans,  # send loans as all_loans for template
        'franchise_loans': franchise_loan_count,
        'assigned_franchise_count': assigned_franchise_count,
        'assigned_franchises': assigned_franchises,
    }
    return render(request, 'dashboard.html', context)



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

    return render(request, 'profile_update.html')


def create_staff(request):
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")

    if not user_id or user_type != "admin":
        messages.error(request, "Unauthorized access. Please log in.")
        return redirect("/login/")

    if request.method == "POST":
        form = StaffModelForm(request.POST, request.FILES)
        if form.is_valid():
            plain_password = form.cleaned_data.get("password")
            try:
                staff = form.save(commit=False)
                staff.password = make_password(plain_password)  # Hash password
                staff.save()  # Auto-generates employee_id

                # Send email with credentials
                send_mail(
                    subject="Staff Account Created",
                    message=(
                        f"Hello {staff.get_full_name()},\n\n"
                        f"Your staff account has been created successfully.\n\n"
                        f"Employee ID: {staff.employee_id}\n"
                        f"Email: {staff.email}\n"
                        f"Password: {plain_password}\n\n"
                        f"Please log in and change your password after first login.\n\n"
                        f"Regards,\nAdmin Team"
                    ),
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[staff.email],
                    fail_silently=False,
                )

                messages.success(request, "Staff member added and email sent successfully!")
                return redirect("/list_staff")

            except IntegrityError as e:
                if "email" in str(e):
                    form.add_error("email", "A staff member with this email already exists.")
                else:
                    messages.error(request, "Failed to create staff member.")

        else:
            messages.error(request, "Please correct the errors in the form.")
            print("Form errors:", form.errors)

    else:
        form = StaffModelForm()

    return render(request, "create-staff.html", {"form": form})  # Handle case where admin doesn't exist


def view_staffs(request, staff_id):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or user_type != 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('/login')

    try:
        admin = AdminModel.objects.get(admin_id=user_id)
        staff_member = get_object_or_404(StaffModel, pk=staff_id)

        return render(request, 'staff_detail.html', {
            'staff_member': staff_member,
            'admin_name': f"{admin.admin_first_name} {admin.admin_last_name or ''}".strip()
        })

    except AdminModel.DoesNotExist:
        messages.error(request, "Admin not found.")
        return redirect('/login')


def list_staff(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or user_type != 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('/login')

    all_staff = StaffModel.objects.all().order_by('-created_at')
    return render(request, 'all_staffs.html', {'all_staff': all_staff})


def delete_staff(request, staff_id):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or user_type != 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('/login')

    staff_member = get_object_or_404(StaffModel, pk=staff_id)

    if request.method == 'POST':
        # Unassign all related loan applications
        LoanApplicationModel.objects.filter(assigned_to=staff_member).update(assigned_to=None)

        staff_member.delete()
        messages.success(request, "Staff member deleted successfully.")
        return redirect('/list_staff')

    messages.warning(request, "Invalid request method.")
    return redirect('/list_staff')



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
