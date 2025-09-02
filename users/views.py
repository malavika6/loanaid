from users.utils import get_sidebar_menu, get_user_context
from users.forms import StaffModelForm, StaffActivationForm, FranchiseActivationForm, FranchiseProfileForm
from users.forms import AdminProfileUpdateForm
from users.models import AdminModel, StaffModel, Franchise
from users.jwt_utils import generate_activation_token, verify_activation_token
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
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
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
    print("=== DEBUG: Home view called ===")
    print(f"Session data: {dict(request.session)}")
    
    sidebar_menu, username = get_user_context(request)
    print(f"get_user_context returned: sidebar_menu={sidebar_menu is not None}, username='{username}'")
    
    # Fallback: Get username from session if get_user_context fails
    if not username:
        username = request.session.get('username', 'User')
        print(f"Using fallback username: {username}")
    
    if not sidebar_menu:
        print("No sidebar menu, redirecting to login")
        return redirect('/login')

    user_type = request.session.get('user_type')
    print(f"Final values - user_type: {user_type}, username: {username}")
    print("=== END DEBUG ===")
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
        """
        Franchise dashboard view - simplified version
        """
        franchise_id = request.session.get('user_id')
        try:
            franchise = Franchise.objects.get(franchise_id=franchise_id)
            
            # Get franchise statistics
            total_loans = LoanApplicationModel.objects.filter(franchise=franchise).count()
            pending_loans = LoanApplicationModel.objects.filter(
                franchise=franchise, 
                status_name__status_name__in=['Pending', 'Under Review']
            ).count()
            approved_loans = LoanApplicationModel.objects.filter(
                franchise=franchise, 
                status_name__status_name='Approved'
            ).count()
            
            # Get recent loan applications
            recent_loans = LoanApplicationModel.objects.filter(
                franchise=franchise
            ).order_by('-form_id')[:5]
            
            context = {
                'franchise': franchise,
                'username': franchise.franchise_name,
                'sidebar_menu': get_sidebar_menu('franchise'),
                'total_loans': total_loans,
                'pending_loans': pending_loans,
                'approved_loans': approved_loans,
                'recent_loans': recent_loans,
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
                form = StaffModelForm(request.POST, request.FILES, instance=staff)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Profile updated successfully!")
                    return redirect('profile')
                else:
                    messages.error(request, "Please correct the errors in the form.")
            else:
                form = StaffModelForm(instance=staff)
            
            context = {
                'form': form,
                'user_profile': staff,
                'sidebar_menu': get_sidebar_menu(user_type),
                'username': f"{staff.first_name} {staff.last_name or ''}".strip()
            }
            return render(request, 'profile.html', context)
            
        elif user_type == 'admin':
            admin = AdminModel.objects.get(admin_id=user_id)
            if request.method == 'POST':
                form = AdminProfileUpdateForm(request.POST, instance=admin)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Profile updated successfully!")
                    return redirect('profile')
                else:
                    messages.error(request, "Please correct the errors in the form.")
            else:
                form = AdminProfileUpdateForm(instance=admin)
            
            context = {
                'form': form,
                'user_profile': admin,
                'sidebar_menu': get_sidebar_menu(user_type),
                'username': f"{admin.admin_first_name} {admin.admin_last_name or ''}".strip()
            }
            return render(request, 'profile.html', context)
            
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

    all_staff = StaffModel.objects.all().order_by('-created_at')
    
    # Get sidebar menu context
    sidebar_menu = get_sidebar_menu(user_type)
    
    return render(request, 'all_staffs.html', {
        'all_staff': all_staff,
        'sidebar_menu': sidebar_menu
    })


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
