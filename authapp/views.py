from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from datetime import datetime
from django.utils import timezone
from users.models import Franchise, StaffModel
from users.models import *
from users.forms import *
from loan.models import LoanApplicationModel
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Prefetch, Q
from collections import defaultdict
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from django.urls import reverse
from django.conf import settings
from django.template.loader import render_to_string
from users.jwt_utils import generate_activation_token, verify_activation_token


def add_franchise(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    franchise_id = request.session.get('franchise_id')

    # Check for unauthorized access - allow admin, staff, and franchise users
    if not user_id or user_type not in ['admin', 'staff', 'franchise']:
        messages.error(request, "Unauthorized access. Please log in.")
        return redirect('/login/')

    # Get referring franchise if user is a franchise
    referring_franchise = None
    if user_type == 'franchise':
        try:
            referring_franchise = Franchise.objects.get(franchise_id=franchise_id)
        except Franchise.DoesNotExist:
            messages.error(request, "Franchise not found.")
            return redirect('/login/')

    # Handle POST request
    if request.method == 'POST':
        # Use different forms based on user type
        if user_type == 'franchise':
            form = FranchiseAddByFranchiseForm(request.POST, request.FILES, referring_franchise=referring_franchise)
        else:
            form = FranchiseCreationForm(request.POST, request.FILES)
            
        if form.is_valid():
            # Form is valid, process and save
            print("Form is valid, saving data...")
            franchise = form.save(commit=False)
            
            # Set default values for activation flow
            franchise.is_franchise = True
            franchise.is_active = False
            franchise.password = None  # No password during creation
            
            # Set default values for fields not in the simplified form
            franchise.aadhar = ""
            franchise.GST = ""
            franchise.pan = ""
            franchise.ac_no = ""
            franchise.ifsc_code = ""
            franchise.screenshot = None

            # Handle staff assignment and referral based on user type
            if user_type == 'staff':
                try:
                    staff = StaffModel.objects.get(pk=user_id)
                    franchise.staff = staff
                except StaffModel.DoesNotExist:
                    messages.error(request, "Staff user not found.")
                    return redirect('/login/')
            elif user_type == 'franchise':
                # For franchise users, set the referring franchise
                franchise.referred_by = referring_franchise

            try:
                franchise.save()

                # Create wallet for the new franchise
                from users.models import Wallet
                Wallet.objects.create(franchise=franchise)

                # Generate activation token
                activation_token = generate_activation_token(franchise.email, 'franchise')
                
                # Send activation email
                activation_url = request.build_absolute_uri(
                    reverse('franchise_activation', kwargs={'token': activation_token})
                )
                
                # Send email with activation link
                try:
                    # Render HTML email template
                    html_message = render_to_string('emails/franchise_activation_email.html', {
                        'franchise': franchise,
                        'activation_url': activation_url,
                        'referring_franchise': referring_franchise,
                    })
                    
                    # Create plain text version
                    referring_info = ""
                    if referring_franchise:
                        referring_info = f"\nReferred By: {referring_franchise.franchise_name} ({referring_franchise.referral_code})"
                    
                    plain_message = f"""Hello {franchise.franchise_owner},

Your franchise account has been created successfully!

Email: {franchise.email}
Referral Code: {franchise.referral_code}
Franchise Type: {franchise.get_franchise_type_display()}{referring_info}

Please click the following link to activate your account and set your password:
{activation_url}

This link will expire in 24 hours.

Best regards,
Loan Aid Team"""
                    
                    send_mail(
                        "🎉 Welcome to Loan Aid - Activate Your Franchise Account",
                        plain_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [franchise.email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    messages.success(
                        request, "Franchise added successfully. Activation email sent.")
                except Exception as e:
                    print(f"Failed to send activation email: {e}")
                    messages.warning(
                        request, "Franchise added but failed to send activation email. Please contact the franchise directly.")
                
                # Redirect based on user type
                if user_type == 'franchise':
                    return redirect("franchise_list")
                else:
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
            return render(request, 'add_franchise.html', {'form': form, 'user_type': user_type, 'referring_franchise': referring_franchise})

    # Handle GET request (initial form rendering)
    else:
        if user_type == 'franchise':
            form = FranchiseAddByFranchiseForm(referring_franchise=referring_franchise)
        else:
            form = FranchiseCreationForm()
        return render(request, 'add_franchise.html', {'form': form, 'user_type': user_type, 'referring_franchise': referring_franchise})


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

    # Apply filters
    search_query = request.GET.get('search', '')
    franchise_type_filter = request.GET.get('franchise_type', '')
    status_filter = request.GET.get('status', '')
    payment_status_filter = request.GET.get('payment_status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if search_query:
        franchises = franchises.filter(
            Q(franchise_name__icontains=search_query) |
            Q(franchise_owner__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(mobile_no__icontains=search_query) |
            Q(referral_code__icontains=search_query)
        )
    
    if franchise_type_filter:
        franchises = franchises.filter(franchise_type=franchise_type_filter)
    
    if status_filter:
        if status_filter == 'active':
            franchises = franchises.filter(is_active=True)
        elif status_filter == 'inactive':
            franchises = franchises.filter(is_active=False)
    
    if payment_status_filter:
        if payment_status_filter == 'paid':
            franchises = franchises.filter(payment_status=True)
        elif payment_status_filter == 'unpaid':
            franchises = franchises.filter(payment_status=False)
    
    if date_from:
        franchises = franchises.filter(created_at__date__gte=date_from)
    
    if date_to:
        franchises = franchises.filter(created_at__date__lte=date_to)

    return render(request, "list_franchise.html", {
        "franchises": franchises,
        "search_query": search_query,
        "franchise_type_filter": franchise_type_filter,
        "status_filter": status_filter,
        "payment_status_filter": payment_status_filter,
        "date_from": date_from,
        "date_to": date_to,
    })

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


def franchise_activation(request, token):
    """Handle franchise account activation"""
    try:
        # Verify the activation token
        email = verify_activation_token(token, 'franchise')
        if not email:
            messages.error(request, "Invalid or expired activation link.")
            return redirect('login')
        
        # Get the franchise
        franchise = get_object_or_404(Franchise, email=email)
        
        if franchise.is_active:
            messages.info(request, "Your account is already activated. Please log in.")
            return redirect('login')
        
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
        
    except Exception as e:
        messages.error(request, "An error occurred during activation. Please contact support.")
        return redirect('login')


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


def franchise_list(request):
    """
    Franchise list view for franchise users - shows only franchises referred by current franchise
    """
    # Check if franchise is logged in
    franchise_id = request.session.get("franchise_id")
    if not franchise_id:
        return redirect("/login")
    
    # Get the current franchise
    current_franchise = get_object_or_404(Franchise, franchise_id=franchise_id)
    
    # Get only franchises referred by the current franchise
    referred_franchises = Franchise.objects.filter(
        referred_by=current_franchise
    ).select_related('wallet')
    
    # Apply filters
    search_query = request.GET.get('search', '')
    franchise_type_filter = request.GET.get('franchise_type', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if search_query:
        referred_franchises = referred_franchises.filter(
            Q(franchise_name__icontains=search_query) |
            Q(franchise_owner__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(mobile_no__icontains=search_query) |
            Q(referral_code__icontains=search_query)
        )
    
    if franchise_type_filter:
        referred_franchises = referred_franchises.filter(franchise_type=franchise_type_filter)
    
    if status_filter:
        if status_filter == 'active':
            referred_franchises = referred_franchises.filter(is_active=True)
        elif status_filter == 'inactive':
            referred_franchises = referred_franchises.filter(is_active=False)
    
    if date_from:
        referred_franchises = referred_franchises.filter(created_at__date__gte=date_from)
    
    if date_to:
        referred_franchises = referred_franchises.filter(created_at__date__lte=date_to)
    
    # Prepare franchise data with additional information
    franchise_data = []
    for franchise in referred_franchises:
        # Get loan count for this franchise
        loan_count = LoanApplicationModel.objects.filter(franchise=franchise).count()
        
        # Get wallet balance
        wallet_balance = 0
        if hasattr(franchise, 'wallet'):
            wallet_balance = franchise.wallet.get_total_balance()
        
        franchise_data.append({
            'franchise': franchise,
            'loan_count': loan_count,
            'wallet_balance': wallet_balance,
        })
    
    context = {
        'franchises': franchise_data,
        'current_franchise': current_franchise,
        'search_query': search_query,
        'franchise_type_filter': franchise_type_filter,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'franchise_list.html', context)


def franchise_wallet(request):
    """
    Wallet view for franchise users - shows monthly wallet data with filtering
    """
    # Check if franchise is logged in
    franchise_id = request.session.get("franchise_id")
    if not franchise_id:
        return redirect("/login")
    
    # Get the current franchise
    current_franchise = get_object_or_404(Franchise, franchise_id=franchise_id)
    
    # Get wallet data
    try:
        wallet = current_franchise.wallet
    except:
        # Create wallet if it doesn't exist
        from users.models import Wallet
        wallet = Wallet.objects.create(franchise=current_franchise)
    
    # Get date filters from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Set default date range (current month)
    from datetime import datetime, date
    from django.utils import timezone
    import calendar
    
    if not start_date:
        today = timezone.now().date()
        start_date = today.replace(day=1)  # First day of current month
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        today = timezone.now().date()
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day)  # Last day of current month
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Calculate monthly totals
    monthly_data = {
        'allowance': wallet.allowance,
        'commission': wallet.commission,
        'incentive': wallet.incentive,
        'total': wallet.get_total_balance(),
        'period': f"{start_date.strftime('%B %Y')}",
        'start_date': start_date,
        'end_date': end_date,
    }
    
    # Get historical data for the selected period (if we had transaction history)
    # For now, we'll show the current wallet data
    historical_data = []
    
    # Add some sample historical data for demonstration
    # In a real implementation, you'd have a transaction model
    sample_months = []
    current_date = start_date
    while current_date <= end_date:
        sample_months.append({
            'month': current_date.strftime('%B %Y'),
            'allowance': wallet.allowance,
            'commission': wallet.commission,
            'incentive': wallet.incentive,
            'total': wallet.get_total_balance(),
            'date': current_date
        })
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    context = {
        'franchise': current_franchise,
        'wallet': wallet,
        'monthly_data': monthly_data,
        'historical_data': sample_months,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    }
    
    return render(request, 'franchise_wallet.html', context)



