from users.utils import get_sidebar_menu, get_user_context
from users.forms import StaffModelForm, StaffActivationForm, FranchiseActivationForm, FranchiseProfileForm
from users.forms import WalletUpdateForm
from users.forms import AdminProfileUpdateForm, StaffProfileUpdateForm, StaffPasswordChangeForm
from users.models import AdminModel, StaffModel, Franchise, Wallet
from users.jwt_utils import generate_activation_token, verify_activation_token
from loan.models import LoanApplicationModel, UploadedFile
from payment.models import Payment
import uuid
from django.core.mail import send_mail
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout as django_logout
from django.contrib.auth.hashers import check_password
from django.contrib.auth.decorators import login_required
from datetime import datetime
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from decimal import Decimal
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .utils import get_sidebar_menu, get_user_context


import logging



logger = logging.getLogger(__name__)




@csrf_exempt
def login(request):
    """
    Handle user login for all user types (admin, franchise, staff, executive).
    Make sure that the identifier you use (usually an email) is consistently used
    to fetch the correct record and that the session is set using the correct PK.
    """
    error = None
    
    # Debug CSRF and session info
    print(f"Request method: {request.method}")
    print(f"CSRF token in request: {request.POST.get('csrfmiddlewaretoken', 'NOT FOUND')}")
    print(f"Session ID: {request.session.session_key}")
    print(f"CSRF cookie: {request.COOKIES.get('csrftoken', 'NOT FOUND')}")

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
                if not franchise.is_active:
                    error = "Your account is not activated. Please check your email for activation link or contact administrator."
                elif franchise.password and check_password(password, franchise.password):
                    # Check if profile is complete
                    if not franchise.is_profile_complete():
                        # Profile not complete, redirect to profile completion
                        request.session.flush()
                        request.session['user_id'] = str(franchise.pk)
                        request.session['user_type'] = 'franchise'
                        request.session['franchise_id'] = str(franchise.pk)
                        request.session['username'] = franchise.franchise_name
                        request.session.set_expiry(3600)
                        logger.info(f"Franchise login successful but profile incomplete (ID: {franchise.pk})")
                        return redirect('franchise_profile_completion')
                    
                    # Profile complete, check payment status
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
                    else:
                        # If payment is not active, set flags for payment redirect
                        request.session['franchise_id'] = str(franchise.pk)
                        request.session['requires_payment'] = True
                        return redirect('payment_redirect')
                else:
                    error = "Invalid credentials. Please try again."
            except Franchise.DoesNotExist:
                pass

        # Check Staff
        if not user:
            try:
                staff = StaffModel.objects.get(email=identifier)
                # Check if staff is active
                if not staff.is_active:
                    error = "Your account is not activated. Please check your email for activation link or contact administrator."
                elif staff.password and check_password(password, staff.password):
                    user, user_type = staff, 'staff'
                    username = f"{staff.first_name} {staff.last_name or ''}".strip()
                else:
                    error = "Invalid credentials. Please try again."
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
            if not error:
                error = "Invalid credentials. Please try again."
            logger.warning(f"Login failed for identifier: {identifier}")
            messages.error(request, error)

    return render(request, 'login.html', {'error': error})


def staff_dashboard(request):
    """
    Staff dashboard view - simplified version
    """
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    
    if not user_id or user_type != 'staff':
        return redirect('/login')
    
    try:
        staff = StaffModel.objects.get(staff_id=user_id)
        
        # Get the franchises assigned to this staff
        assigned_franchises = Franchise.objects.filter(
            staffassignmentmodel__staff_name=staff
        ).distinct()
        
        # Get loans assigned to this staff
        staff_loans = LoanApplicationModel.objects.filter(assigned_to=user_id)
        
        # Get loans from assigned franchises
        franchise_loans = LoanApplicationModel.objects.filter(franchise__in=assigned_franchises)
        
        context = {
            'username': f"{staff.first_name} {staff.last_name or ''}".strip(),
            'sidebar_menu': get_sidebar_menu('staff'),
            'all_loans': franchise_loans,
            'staff_loans': staff_loans,
            'franchise_loans': franchise_loans.count(),
            'assigned_franchise_count': assigned_franchises.count(),
            'assigned_franchises': assigned_franchises,
        }
        return render(request, 'dashboard.html', context)
        
    except StaffModel.DoesNotExist:
        messages.error(request, "Staff member not found.")
        return redirect('/login')



def home(request):
    """
    Dashboard view for admin users.
    """
    # Debug removed
    
    sidebar_menu, username = get_user_context(request)
    # Debug removed
    
    # Fallback: Get username from session if get_user_context fails
    if not username:
        username = request.session.get('username', 'User')
        # Debug removed
    
    if not sidebar_menu:
        # Debug removed
        return redirect('/login')

    user_type = request.session.get('user_type')
    # Debug removed
    if user_type == 'admin':
        # Get admin user
        admin = AdminModel.objects.get(admin_id=request.session.get('user_id'))
        
        # Get today's follow-up loans
        today = datetime.now().date()
        today_followups = LoanApplicationModel.objects.filter(followup_date=today)
        
        # Get all statistics
        all_franchises = Franchise.objects.all()
        franchise_count = all_franchises.count()
        active_franchises = all_franchises.filter(is_active=True).count()
        
        all_staff = StaffModel.objects.all()
        staff_count = all_staff.count()
        active_staff = all_staff.filter(is_active=True).count()
        
        # Loan statistics
        all_loans = LoanApplicationModel.objects.all()
        loan_app_count = all_loans.count()
        pending_loans = all_loans.filter(status_name__status_name='Pending').count()
        approved_loans = all_loans.filter(status_name__status_name='Approved').count()
        rejected_loans = all_loans.filter(status_name__status_name='Rejected').count()
        
        # Recent activities
        recent_loans = all_loans.order_by('-form_id')[:10]
        recent_franchises = all_franchises.order_by('-created_at')[:5]
        
        # Wallet statistics
        from users.models import Wallet
        total_wallet_amount = sum(wallet.get_total_balance() for wallet in Wallet.objects.all())
        
        context = {
            'username': username,
            'admin': admin,
            'user_type': 'admin',
            'forms': recent_loans,
            'loans': today_followups,
            'recent_franchises': recent_franchises,
            'total_franchise_count': franchise_count,
            'active_franchise_count': active_franchises,
            'total_staff_count': staff_count,
            'active_staff_count': active_staff,
            'loan_app_count': loan_app_count,
            'pending_loans': pending_loans,
            'approved_loans': approved_loans,
            'rejected_loans': rejected_loans,
            'total_wallet_amount': total_wallet_amount,
            'sidebar_menu': sidebar_menu,
        }
        return render(request, 'index.html', context)

    elif user_type == 'staff':
        staff_id = request.session.get('user_id')
        staff = StaffModel.objects.get(staff_id=staff_id)

        # Get the franchises assigned to this staff from StaffAssignmentModel
        assigned_franchise_qs = Franchise.objects.filter(
            staffassignmentmodel__staff_name=staff
        ).distinct()

        # Build detailed list with wallet and loan counts
        from users.models import Wallet
        assigned_franchise_data = []
        total_wallet_amount = 0
        
        for franchise in assigned_franchise_qs:
            # Ensure wallet exists
            wallet, _ = Wallet.objects.get_or_create(franchise=franchise)
            # Loan count for this franchise
            loan_count = LoanApplicationModel.objects.filter(franchise=franchise).count()
            wallet_total = wallet.get_total_balance()
            total_wallet_amount += wallet_total
            
            assigned_franchise_data.append({
                'franchise': franchise,
                'wallet': wallet,
                'loan_count': loan_count,
                'wallet_total': wallet_total,
            })

        # Get loans from assigned franchises
        loans_from_franchises = LoanApplicationModel.objects.filter(
            franchise__in=assigned_franchise_qs
        ).select_related('franchise', 'status_name', 'loan_name')
        
        # Loan statistics
        total_loans = loans_from_franchises.count()
        pending_loans = loans_from_franchises.filter(status_name__status_name='Pending').count()
        approved_loans = loans_from_franchises.filter(status_name__status_name='Approved').count()
        rejected_loans = loans_from_franchises.filter(status_name__status_name='Rejected').count()
        
        # Recent loans
        recent_loans = loans_from_franchises.order_by('-form_id')[:10]
        
        # Today's follow-ups
        today = datetime.now().date()
        today_followups = loans_from_franchises.filter(followup_date=today)

        context = {
            'username': username,
            'staff': staff,
            'user_type': 'staff',
            'sidebar_menu': sidebar_menu,
            'all_loans': recent_loans,
            'today_followups': today_followups,
            'total_loans': total_loans,
            'pending_loans': pending_loans,
            'approved_loans': approved_loans,
            'rejected_loans': rejected_loans,
            'assigned_franchise_count': len(assigned_franchise_data),
            'assigned_franchises': assigned_franchise_data,
            'total_wallet_amount': total_wallet_amount,
        }
        return render(request, 'dashboard.html', context)


    elif user_type == 'franchise':
        """
        Franchise dashboard view - shows only franchise's own data
        """
        franchise_id = request.session.get('user_id')
        try:
            franchise = Franchise.objects.get(franchise_id=franchise_id)
            
            # Get franchise's own loan statistics
            franchise_loans = LoanApplicationModel.objects.filter(franchise=franchise)
            total_loans = franchise_loans.count()
            pending_loans = franchise_loans.filter(status_name__status_name='Pending').count()
            approved_loans = franchise_loans.filter(status_name__status_name='Approved').count()
            rejected_loans = franchise_loans.filter(status_name__status_name='Rejected').count()
            under_review_loans = franchise_loans.filter(status_name__status_name='Under Review').count()
            
            # Get recent loan applications (only their own)
            recent_loans = franchise_loans.order_by('-form_id')[:5]
            
            # Get today's follow-ups
            today = datetime.now().date()
            today_followups = franchise_loans.filter(followup_date=today)
            
            # Get wallet information
            from users.models import Wallet
            wallet, _ = Wallet.objects.get_or_create(franchise=franchise)
            wallet_total = wallet.get_total_balance()
            
            # Get referred franchises (if any)
            referred_franchises = Franchise.objects.filter(referred_by=franchise)
            referred_count = referred_franchises.count()
            
            context = {
                'franchise': franchise,
                'username': franchise.franchise_name,
                'user_type': 'franchise',
                'sidebar_menu': get_sidebar_menu('franchise'),
                'total_loans': total_loans,
                'pending_loans': pending_loans,
                'approved_loans': approved_loans,
                'rejected_loans': rejected_loans,
                'under_review_loans': under_review_loans,
                'recent_loans': recent_loans,
                'today_followups': today_followups,
                'wallet': wallet,
                'wallet_total': wallet_total,
                'referred_franchises': referred_franchises,
                'referred_count': referred_count,
            }
            return render(request, 'franchise_dashboard.html', context)
            
        except Franchise.DoesNotExist:
            messages.error(request, "Franchise not found.")
            return redirect('/login')
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
        # Updated to work with StaffModel instead of UserModel
        staff_member = StaffModel.objects.get(staff_id=user_id)
        other_user_name = f"{staff_member.first_name} {staff_member.last_name or ''}".strip()
    except StaffModel.DoesNotExist:
        return redirect('/login')

    # Fetch loans related to this staff member
    related_loans = LoanApplicationModel.objects.filter(
        assigned_to=staff_member)  # Use 'assigned_to' to filter by staff
    loan_count = related_loans.count()

    # Count the number of franchises
    all_franchises = Franchise.objects.all()
    franchise_count = all_franchises.count()

    context = {
        'username': other_user_name,
        'other_user': staff_member,
        'related_loans': related_loans,
        'loan_count': loan_count,
        'franchise_count': franchise_count,
        'can_add_loan': True  # Staff can add loans
    }

    return render(request, 'home.html', context)


def update_profile(request):
    """Handle profile updates for all user types"""
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    
    if not user_id or not user_type:
        messages.error(request, "Please log in to access your profile.")
        return redirect('/login/')
    
    try:
        if user_type == 'franchise':
            franchise = Franchise.objects.get(franchise_id=user_id)
            if request.method == 'POST':
                form = FranchiseProfileForm(request.POST, request.FILES, instance=franchise)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Profile updated successfully!")
                    return redirect('profile')
                else:
                    messages.error(request, "Please correct the errors in the form.")
            else:
                form = FranchiseProfileForm(instance=franchise)
            
            context = {
                'form': form,
                'user_profile': franchise,
                'sidebar_menu': get_sidebar_menu(user_type),
                'username': franchise.franchise_name
            }
            return render(request, 'profile.html', context)
            
        elif user_type == 'staff':
            staff = StaffModel.objects.get(staff_id=user_id)
            if request.method == 'POST':
                form = StaffProfileUpdateForm(request.POST, request.FILES, instance=staff)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Profile updated successfully!")
                    return redirect('home')
                else:
                    messages.error(request, "Please correct the errors in the form.")
            else:
                form = StaffProfileUpdateForm(instance=staff)
            
            context = {
                'form': form,
                'user_profile': staff,
                'sidebar_menu': get_sidebar_menu(user_type),
                'username': f"{staff.first_name} {staff.last_name or ''}".strip(),
                'user_type': user_type
            }
            return render(request, 'staff_profile_update.html', context)
            
        elif user_type == 'admin':
            admin = AdminModel.objects.get(admin_id=user_id)
            if request.method == 'POST':
                form = AdminProfileUpdateForm(request.POST, request.FILES, instance=admin)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Profile updated successfully!")
                    return redirect('profile')
                else:
                    messages.error(request, "Please correct the errors in the form.")
            else:
                form = AdminProfileUpdateForm(instance=admin)

            return render(request, 'admin_profile.html', {
                'form': form,
                'user_profile': admin,
                'sidebar_menu': get_sidebar_menu(user_type),
                'username': f"{admin.admin_first_name} {admin.admin_last_name or ''}".strip()
            })
            
        else:
            messages.error(request, "Invalid user type.")
            return redirect('/login/')
            
    except (Franchise.DoesNotExist, StaffModel.DoesNotExist, AdminModel.DoesNotExist):
        messages.error(request, "User profile not found.")
        return redirect('/login/')
    except Exception as e:
        logger.error(f"Error in update_profile: {e}")
        messages.error(request, "An error occurred while updating your profile.")
        return redirect('/login/')


def create_staff(request):
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")

    if not user_id or user_type != "admin":
        messages.error(request, "Unauthorized access. Please log in.")
        return redirect("/login/")

    if request.method == "POST":
        form = StaffModelForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                staff = form.save(commit=False)
                staff.is_active = False  # Set inactive by default
                staff.save()  # Auto-generates employee_id

                # Generate JWT activation token
                activation_token = generate_activation_token(staff.email, 'staff', staff.staff_id)

                # Create activation URL
                activation_url = request.build_absolute_uri(
                    reverse('staff_activation', kwargs={'token': activation_token})
                )

                # Send activation email
                try:
                    # Render email template
                    html_message = render_to_string('emails/staff_activation_email.html', {
                        'staff': staff,
                        'activation_url': activation_url,
                    })
                    plain_message = strip_tags(html_message)

                    send_mail(
                        subject="Activate Your Staff Account - Loan Aid",
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[staff.email],
                        fail_silently=False,
                    )

                    messages.success(request, f"Staff member {staff.get_full_name()} created successfully! An activation email has been sent to {staff.email}.")
                except Exception as e:
                    messages.warning(request, f"Staff created but email could not be sent. Error: {str(e)}")
                    logger.error(f"Failed to send activation email to {staff.email}: {str(e)}")

                return redirect("/list_staff")

            except IntegrityError as e:
                if "email" in str(e):
                    form.add_error("email", "A staff member with this email already exists.")
                else:
                    messages.error(request, "Failed to create staff member.")
                    logger.error(f"IntegrityError creating staff: {str(e)}")

        else:
            messages.error(request, "Please correct the errors in the form.")
            print("Form errors:", form.errors)

    else:
        form = StaffModelForm()

    return render(request, "create-staff.html", {"form": form})

def staff_activation(request, token):
    """Handle staff account activation using JWT"""
    # Verify the JWT token
    email = verify_activation_token(token, 'staff')
    
    if not email:
        return render(request, 'staff_activation.html', {
            'error': 'Invalid or expired activation link. Please contact the administrator.'
        })

    try:
        staff = StaffModel.objects.get(
            email=email,
            is_active=False
        )
    except StaffModel.DoesNotExist:
        return render(request, 'staff_activation.html', {
            'error': 'Staff account not found or already activated.'
        })

    if request.method == 'POST':
        form = StaffActivationForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            
            # Set password and activate account
            staff.password = make_password(password)
            staff.is_active = True
            staff.save()
            
            # Redirect to login page with success message
            messages.success(request, 'Your account has been activated successfully! You can now log in with your email and password.')
            return redirect('/login')
    else:
        form = StaffActivationForm()

    return render(request, 'staff_activation.html', {
        'form': form,
        'staff': staff
    })


def view_staffs(request, staff_id):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or user_type != 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('/login')

    try:
        admin = AdminModel.objects.get(admin_id=user_id)
        staff_member = get_object_or_404(StaffModel, pk=staff_id)

        # Get sidebar menu context
        sidebar_menu = get_sidebar_menu(user_type)

        return render(request, 'staff_detail.html', {
            'staff_member': staff_member,
            'admin_name': f"{admin.admin_first_name} {admin.admin_last_name or ''}".strip(),
            'sidebar_menu': sidebar_menu
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

    # Get base queryset
    all_staff = StaffModel.objects.all().order_by('-created_at')
    
    # Apply filters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if search_query:
        all_staff = all_staff.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_no__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'active':
            all_staff = all_staff.filter(is_active=True)
        elif status_filter == 'inactive':
            all_staff = all_staff.filter(is_active=False)
    
    if date_from:
        all_staff = all_staff.filter(created_at__date__gte=date_from)
    
    if date_to:
        all_staff = all_staff.filter(created_at__date__lte=date_to)
    
    # Get sidebar menu context
    sidebar_menu = get_sidebar_menu(user_type)
    
    return render(request, 'all_staffs.html', {
        'all_staff': all_staff,
        'sidebar_menu': sidebar_menu,
        'search_query': search_query,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


def staff_loan_management(request):
    """
    Staff loan management view - shows loans from assigned franchises with accept/reject/pending functionality
    """
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or user_type != 'staff':
        messages.error(request, "Unauthorized access.")
        return redirect('/login')

    try:
        staff = StaffModel.objects.get(staff_id=user_id)
        
        # Get the franchises assigned to this staff
        assigned_franchises = Franchise.objects.filter(
            staffassignmentmodel__staff_name=staff
        ).distinct()
        
        # Get loans from assigned franchises
        loans = LoanApplicationModel.objects.filter(
            franchise__in=assigned_franchises
        ).select_related('franchise', 'loan_name', 'status_name', 'bank_name')
        
        # Apply filters
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        franchise_filter = request.GET.get('franchise', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        
        if search_query:
            loans = loans.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(phone_no__icontains=search_query) |
                Q(loan_name__loan_name__icontains=search_query)
            )
        
        if status_filter:
            if status_filter == 'pending':
                loans = loans.filter(status_name__status_name='Pending')
            elif status_filter == 'approved':
                loans = loans.filter(status_name__status_name='Approved')
            elif status_filter == 'rejected':
                loans = loans.filter(status_name__status_name='Rejected')
            elif status_filter == 'under_review':
                loans = loans.filter(status_name__status_name='Under Review')
        
        if franchise_filter:
            loans = loans.filter(franchise_id=franchise_filter)
        
        if date_from:
            loans = loans.filter(created_at__date__gte=date_from)
        
        if date_to:
            loans = loans.filter(created_at__date__lte=date_to)
        
        # Get sidebar menu context
        sidebar_menu = get_sidebar_menu(user_type)
        
        context = {
            'loans': loans,
            'assigned_franchises': assigned_franchises,
            'sidebar_menu': sidebar_menu,
            'search_query': search_query,
            'status_filter': status_filter,
            'franchise_filter': franchise_filter,
            'date_from': date_from,
            'date_to': date_to,
        }
        
        return render(request, 'staff_loan_management.html', context)
        
    except StaffModel.DoesNotExist:
        messages.error(request, "Staff member not found.")
        return redirect('/login')


def update_loan_status(request, loan_id):
    """
    Update loan status (Accept/Reject/Pending) - Staff only
    """
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or user_type != 'staff':
        messages.error(request, "Unauthorized access.")
        return redirect('/login')

    try:
        staff = StaffModel.objects.get(staff_id=user_id)
        
        # Get the loan
        loan = get_object_or_404(LoanApplicationModel, form_id=loan_id)
        
        # Check if staff has permission to manage this loan (from assigned franchises)
        assigned_franchises = Franchise.objects.filter(
            staffassignmentmodel__staff_name=staff
        ).distinct()
        
        if loan.franchise not in assigned_franchises:
            messages.error(request, "You don't have permission to manage this loan.")
            return redirect('staff_loan_management')
        
        if request.method == 'POST':
            new_status = request.POST.get('status')
            if new_status in ['Accept', 'Reject', 'Pending']:
                # Update the workstatus field
                loan.workstatus = new_status
                loan.save()
                messages.success(request, f"Loan status updated to {new_status}")
            else:
                messages.error(request, "Invalid status selected.")
        
        return redirect('staff_loan_management')
        
    except StaffModel.DoesNotExist:
        messages.error(request, "Staff member not found.")
        return redirect('/login')


def delete_staff(request, staff_id):
    """
    Staff deletion view - simplified version
    """
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    
    if not user_id or user_type != 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('/login')
    
    try:
        admin = AdminModel.objects.get(admin_id=user_id)
        staff_member = get_object_or_404(StaffModel, pk=staff_id)
        
        if request.method == 'POST':
            staff_member.delete()
            messages.success(request, f"Staff member {staff_member.get_full_name()} deleted successfully.")
            return redirect('list_staff')
        else:
            return render(request, 'confirm_delete_staff.html', {
                'staff_member': staff_member,
                'admin_name': f"{admin.admin_first_name} {admin.admin_last_name or ''}".strip(),
                'sidebar_menu': get_sidebar_menu('admin')
            })
            
    except AdminModel.DoesNotExist:
        messages.error(request, "Admin not found.")
        return redirect('/login')
    except Exception as e:
        logger.error(f"Error deleting staff: {e}")
        messages.error(request, "An error occurred while deleting the staff member.")
        return redirect('list_staff')



def delete_files(request, id):
    file = get_object_or_404(UploadedFile, pk=id)
    loan_id = file.loan_application.form_id
    if request.method == 'POST':
        file.delete()
        # Adjust the redirect based on your URL name for the user list page
        return redirect('loan-page', loan_id)
    return redirect('loan-page', loan_id)








def activate_staff(request, staff_id):
    """
    Activate a staff member's account (admin only)
    """
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or user_type != 'admin':
        messages.error(request, "Unauthorized access.")
        return redirect('/login')

    try:
        admin = AdminModel.objects.get(admin_id=user_id)
        staff_member = get_object_or_404(StaffModel, pk=staff_id)

        if request.method == 'POST':
            staff_member.is_active = True
            staff_member.save()
            messages.success(request, f"Account activated successfully for {staff_member.get_full_name()}.")
            return redirect('view_profile', staff_id=staff_id)
        else:
            messages.warning(request, "Invalid request method.")
            return redirect('view_profile', staff_id=staff_id)

    except AdminModel.DoesNotExist:
        messages.error(request, "Admin not found.")
        return redirect('/login')


def franchise_activation(request, token):
    """Handle franchise account activation"""
    
    try:
        # Verify the activation token
        email = verify_activation_token(token, 'franchise')
        
        if not email:
            return render(request, 'franchise_activation.html', {
                'error': 'Invalid or expired activation link. Please contact the administrator.'
            })
        
        # Get the franchise
        try:
            franchise = Franchise.objects.get(email=email, is_active=False)
        except Franchise.DoesNotExist:
            return render(request, 'franchise_activation.html', {
                'error': 'Franchise account not found or already activated.'
            })
        
        if request.method == 'POST':
            form = FranchiseActivationForm(request.POST)
            if form.is_valid():
                # Set password and activate account
                franchise.password = make_password(form.cleaned_data['password'])
                franchise.is_active = True
                franchise.save()
                
                messages.success(request, "Account activated successfully! Please log in with your email and password.")
                return redirect('login')
        else:
            form = FranchiseActivationForm()
        
        return render(request, 'franchise_activation.html', {
            'form': form,
            'franchise': franchise,
            'token': token
        })
        
    except Exception:
        return render(request, 'franchise_activation.html', {
            'error': 'An error occurred during activation. Please contact support.'
        })




def franchise_profile_completion(request):
    """Handle franchise profile completion after login"""
    franchise_id = request.session.get('franchise_id')
    if not franchise_id:
        messages.error(request, "Please log in first.")
        return redirect('login')
    
    franchise = get_object_or_404(Franchise, franchise_id=franchise_id)
    
    if not franchise.is_active:
        messages.error(request, "Your account is not activated.")
        return redirect('login')
    
    if request.method == 'POST':
        form = FranchiseProfileForm(request.POST, request.FILES, instance=franchise)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile completed successfully!")
            return redirect('franchise_dashboard')
    else:
        form = FranchiseProfileForm(instance=franchise)
    
    return render(request, 'franchise_profile_completion.html', {
        'form': form,
        'franchise': franchise
    })


def wallet_manage(request):
    """Add/update wallet values for a franchise and view totals.
    Accessible to admin and staff.
    """
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id or user_type not in ['admin', 'staff']:
        messages.error(request, 'Unauthorized access.')
        return redirect('/login')

    sidebar_menu = get_sidebar_menu(user_type)

    wallet = None
    selected_franchise = None
    total = None
    # Build franchise list for dropdown
    if user_type == 'admin':
        franchise_qs = Franchise.objects.all().order_by('franchise_name')
    else:
        try:
            staff = StaffModel.objects.get(staff_id=user_id)
            from loan.models import StaffAssignmentModel
            assigned = StaffAssignmentModel.objects.filter(staff_name=staff).prefetch_related('franchise_name')
            franchise_set = []
            for a in assigned:
                franchise_set.extend(list(a.franchise_name.all()))
            # Deduplicate and sort by name
            unique_ids = {f.pk for f in franchise_set}
            franchise_qs = Franchise.objects.filter(pk__in=unique_ids).order_by('franchise_name')
        except StaffModel.DoesNotExist:
            franchise_qs = Franchise.objects.none()

    # Apply filters
    search_query = request.GET.get('search', '')
    franchise_filter = request.GET.get('franchise', '')
    min_total = request.GET.get('min_total', '')
    max_total = request.GET.get('max_total', '')
    
    # Filter franchises based on search
    if search_query:
        franchise_qs = franchise_qs.filter(
            Q(franchise_name__icontains=search_query) |
            Q(franchise_owner__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(referral_code__icontains=search_query)
        )
    
    # Filter by specific franchise
    if franchise_filter:
        franchise_qs = franchise_qs.filter(pk=franchise_filter)

    # Build wallet rows for list view (for all accessible franchises)
    wallet_rows = []
    for f in franchise_qs:
        wallet_obj, _ = Wallet.objects.get_or_create(franchise=f)
        total_balance = wallet_obj.get_total_balance()
        
        # Apply total amount filters
        if min_total:
            try:
                min_val = float(min_total)
                if total_balance < min_val:
                    continue
            except ValueError:
                pass
        
        if max_total:
            try:
                max_val = float(max_total)
                if total_balance > max_val:
                    continue
            except ValueError:
                pass
        
        wallet_rows.append({
            'franchise': f,
            'wallet': wallet_obj,
            'total': total_balance,
        })

    if request.method == 'POST':
        form = WalletUpdateForm(request.POST, user_type=user_type, user_id=user_id)
        if form.is_valid():
            wallet = form.save()
            selected_franchise = wallet.franchise
            total = wallet.get_total_balance()
            messages.success(request, 'Wallet updated successfully.')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = WalletUpdateForm(user_type=user_type, user_id=user_id)

    # If franchise is selected from GET param, show its wallet
    fid = request.GET.get('franchise')
    if fid:
        try:
            selected_franchise = Franchise.objects.get(pk=fid)
            wallet, _ = Wallet.objects.get_or_create(franchise=selected_franchise)
            total = wallet.get_total_balance()
            if request.method != 'POST':
                form = WalletUpdateForm(
                    user_type=user_type,
                    user_id=user_id,
                    initial={
                        'franchise': str(selected_franchise.pk),
                        'commission': wallet.commission,
                        'incentive': wallet.incentive,
                    }
                )
        except Franchise.DoesNotExist:
            pass

    return render(request, 'wallet_manage.html', {
        'form': form,
        'sidebar_menu': sidebar_menu,
        'selected_franchise': selected_franchise,
        'wallet': wallet,
        'total': total,
        'franchises': franchise_qs,
        'wallet_rows': wallet_rows,
        'search_query': search_query,
        'franchise_filter': franchise_filter,
        'min_total': min_total,
        'max_total': max_total,
        'user_type': user_type,
    })


def wallet_update(request):
    """Wallet update form view for admin and staff"""
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    
    if not user_id or user_type not in ['admin', 'staff']:
        messages.error(request, 'Unauthorized access.')
        return redirect('/login')
    
    # Get accessible franchises
    if user_type == 'admin':
        franchises = Franchise.objects.all().order_by('franchise_name')
    else:  # staff
        try:
            staff = StaffModel.objects.get(staff_id=user_id)
            from loan.models import StaffAssignmentModel
            assigned = StaffAssignmentModel.objects.filter(staff_name=staff).prefetch_related('franchise_name')
            franchise_set = []
            for a in assigned:
                franchise_set.extend(list(a.franchise_name.all()))
            # Deduplicate and sort by name
            unique_ids = {f.pk for f in franchise_set}
            franchises = Franchise.objects.filter(pk__in=unique_ids).order_by('franchise_name')
        except StaffModel.DoesNotExist:
            franchises = Franchise.objects.none()
    
    selected_franchise = request.GET.get('franchise')
    current_commission = ''
    current_incentive = ''
    
    if selected_franchise:
        try:
            franchise = Franchise.objects.get(pk=selected_franchise)
            wallet, created = Wallet.objects.get_or_create(franchise=franchise)
            current_commission = wallet.commission
            current_incentive = wallet.incentive
        except Franchise.DoesNotExist:
            selected_franchise = None
    
    if request.method == 'POST':
        franchise_id = request.POST.get('franchise')
        commission = request.POST.get('commission', 0)
        incentive = request.POST.get('incentive', 0)
        
        if franchise_id:
            try:
                franchise = Franchise.objects.get(pk=franchise_id)
                wallet, created = Wallet.objects.get_or_create(franchise=franchise)
                
                # Set absolute amounts (not add to existing)
                wallet.commission = Decimal(commission or 0)
                wallet.incentive = Decimal(incentive or 0)
                wallet.save()
                
                messages.success(request, f'Wallet updated for {franchise.franchise_name}')
                return redirect('wallet_manage')
            except Franchise.DoesNotExist:
                messages.error(request, 'Franchise not found')
        else:
            messages.error(request, 'Please select a franchise')
    
    context = {
        'franchises': franchises,
        'selected_franchise': selected_franchise,
        'current_commission': current_commission,
        'current_incentive': current_incentive,
    }
    
    return render(request, 'wallet_update.html', context)
