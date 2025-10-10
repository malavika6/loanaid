from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.hashers import check_password
import logging

from users.models import AdminModel, StaffModel, Franchise
from users.decorators import admin_required, staff_required, franchise_required, login_required, franchise_profile_complete
from .models import (
    LoanApplicationModel, LoanModel, StatusModel, BankModel, 
    UploadedFile, StaffAssignmentModel
)
from .forms import LoanApplicationForm, LoanForm, StatusForm, BankForm
from .loan_utils import get_loan_context, get_loan_stats, get_loan_filters

logger = logging.getLogger('loan')


@method_decorator(franchise_profile_complete, name='dispatch')
class LoanApplicationView(View):
    """Optimized loan application form view with role-based access control"""
    
    def get_user_context(self, user_id, user_type):
        """Get user context based on user type"""
        try:
            if user_type == 'admin':
                user = AdminModel.objects.get(admin_id=user_id)
                username = f"{user.admin_first_name} {user.admin_last_name}".strip()
                can_access_all = user.is_superadmin or user.is_staff
                
            elif user_type == 'staff':
                user = StaffModel.objects.get(staff_id=user_id)
                username = f"{user.first_name} {user.last_name}".strip()
                can_access_all = False
                
            elif user_type == 'franchise':
                user = Franchise.objects.get(franchise_id=user_id)
                username = user.franchise_name
                can_access_all = False
                
            elif user_type == 'executive':
                # Executive functionality removed - UserModel was deleted
                # For now, return None to redirect to login
                return None, None, None
                
            else:
                return None, None, None
                
            return user, username, can_access_all
            
        except Exception as e:
            logger.error(f"Error fetching user details: {e}")
            return None, None, None
    
    def get_loan_queryset(self, user, user_type, can_access_all):
        """Get loan queryset based on user permissions"""
        if can_access_all:
            return LoanApplicationModel.objects.select_related(
                'franchise', 'loan_name', 'status_name', 'bank_name'
            ).prefetch_related('uploaded_files').order_by('-created_at', '-form_id')
        
        elif user_type == 'staff':
            # Get franchises assigned to staff
            assignment = StaffAssignmentModel.objects.filter(
                staff_name=user
            ).prefetch_related('franchise_name').first()
            
            if assignment:
                franchises = assignment.franchise_name.all()
                return LoanApplicationModel.objects.filter(
                    franchise__in=franchises
                ).select_related(
                    'franchise', 'loan_name', 'status_name', 'bank_name'
                ).prefetch_related('uploaded_files').order_by('-created_at', '-form_id')
            return LoanApplicationModel.objects.none()
            
        elif user_type == 'franchise':
            return LoanApplicationModel.objects.filter(
                franchise=user
            ).select_related(
                'franchise', 'loan_name', 'status_name', 'bank_name'
            ).prefetch_related('uploaded_files').order_by('-created_at', '-form_id')
            
        elif user_type == 'executive':
            # Executive functionality removed - UserModel was deleted
            # For now, return empty queryset
            return LoanApplicationModel.objects.none()
            
        return LoanApplicationModel.objects.none()
    
    def get(self, request):
        """Handle GET request for loan application form"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or not user_type:
            logger.warning("Unauthorized access attempt. Redirecting to /login")
            return redirect('/login')
        
        logger.info(f"User accessing loan form: ID={user_id}, Type={user_type}")
        
        user, username, can_access_all = self.get_user_context(user_id, user_type)
        if not user:
            return redirect('/login')
        
        # Get loan queryset
        loan = self.get_loan_queryset(user, user_type, can_access_all)
        
        # Get related data with optimization
        status = StatusModel.objects.all()
        bank = BankModel.objects.all()
        
        # Define hidden fields for franchise users
        hide_fields = []
        if user_type == 'franchise':
            hide_fields = ['status_name', 'executive_name', 'reference_no_1', 'reference_no_2']
        
        form = LoanApplicationForm(user_type=user_type)
        if user_type == 'franchise':
            for field in hide_fields:
                if field in form.fields:
                    form.fields.pop(field)
        
        context = get_loan_context(username, loan, status, bank, form, hide_fields)
        return render(request, 'loan-form.html', context)
    
    def post(self, request):
        """Handle POST request for loan application submission"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        logger.info(f"POST request received - User ID: {user_id}, User Type: {user_type}")
        
        if not user_id or not user_type:
            logger.warning("No user_id or user_type in session, redirecting to login")
            return redirect('/login')
        
        user, username, can_access_all = self.get_user_context(user_id, user_type)
        if not user:
            logger.warning("User not found, redirecting to login")
            return redirect('/login')
        
        files = request.FILES.getlist('files')
        logger.info(f"Files uploaded: {len(files)}")
        logger.info(f"POST data keys: {list(request.POST.keys())}")
        
        form = LoanApplicationForm(request.POST, request.FILES, user_type=user_type)
        
        # Hide fields for franchise users
        if user_type == 'franchise':
            hide_fields = ['status_name', 'executive_name', 'reference_no_1', 'reference_no_2']
            for field in hide_fields:
                if field in form.fields:
                    form.fields.pop(field)
        
        logger.info(f"Form is_valid: {form.is_valid()}")
        logger.info(f"Form data: {form.data}")
        logger.info(f"Form files: {form.files}")
        
        if form.is_valid():
            try:
                logger.info("Form is valid, attempting to save...")
                loan_form = form.save(commit=False)
                
                # Assign franchise based on user type
                if user_type == 'admin' and not can_access_all:
                    loan_form.franchise = user
                    logger.info(f"Assigned franchise (admin): {user}")
                elif user_type == 'staff':
                    assignment = StaffAssignmentModel.objects.filter(staff_name=user).first()
                    if assignment:
                        franchise = assignment.franchise_name.first()
                        loan_form.franchise = franchise
                        logger.info(f"Assigned franchise (staff): {franchise}")
                elif user_type == 'franchise':
                    loan_form.franchise = user
                    logger.info(f"Assigned franchise (franchise): {user}")
                elif user_type == 'executive':
                    loan_form.executive = user
                    logger.info(f"Assigned executive: {user}")
                
                loan_form.save()
                logger.info(f"Loan application saved successfully with ID: {loan_form.form_id}")
                
                # Handle file uploads
                for file in files:
                    UploadedFile.objects.create(
                        file=file, 
                        loan_application=loan_form
                    )
                logger.info(f"Uploaded {len(files)} files")
                
                messages.success(request, "Loan application submitted successfully!")
                return redirect('all-application')
            except Exception as e:
                logger.error(f"Error saving application: {str(e)}", exc_info=True)
                messages.error(request, f"Error saving application: {str(e)}")
        else:
            logger.error(f"Form validation errors: {form.errors.as_json()}")
            logger.error(f"Form non-field errors: {form.non_field_errors()}")
            for field, errors in form.errors.items():
                logger.error(f"Field '{field}' errors: {errors}")
            messages.error(request, "Please correct the errors below.")
        
        # If form is invalid, re-render with errors
        status = StatusModel.objects.all()
        bank = BankModel.objects.all()
        hide_fields = ['status_name', 'executive_name', 'reference_no_1', 'reference_no_2'] if user_type == 'franchise' else []
        
        context = get_loan_context(username, None, status, bank, form, hide_fields)
        return render(request, 'loan-form.html', context)


class LoanDetailView(View):
    """Optimized loan detail view with role-based access control"""
    
    def get_user_context(self, user_id, user_type):
        """Get user context based on user type"""
        try:
            if user_type == 'admin':
                user = AdminModel.objects.get(admin_id=user_id)
                username = f"{user.admin_first_name} {user.admin_last_name}" if user.admin_last_name else f"{user.admin_first_name}"
                return user, username
            elif user_type == 'staff':
                user = StaffModel.objects.get(staff_id=user_id)
                username = f"{user.first_name} {user.last_name}".strip()
                return user, username
            elif user_type == 'franchise':
                user = Franchise.objects.get(franchise_id=user_id)
                username = user.franchise_name
                return user, username
            else:
                return None, None
        except Exception as e:
            logger.error(f"Error fetching user details: {e}")
            return None, None
    
    def get(self, request, form_id):
        """Handle GET request for loan detail page"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or not user_type:
            return redirect('/login')
        
        user, username = self.get_user_context(user_id, user_type)
        if not user:
            return redirect('/login')
        
        # Get loan application with optimization
        form_instance = get_object_or_404(
            LoanApplicationModel.objects.select_related(
                'franchise', 'loan_name', 'status_name', 'bank_name'
            ), 
            form_id=form_id
        )
        
        # Check access permissions based on user type
        if user_type == 'admin':
            # Admin can access all loans or only their own depending on permissions
            if not user.is_superadmin and not user.is_staff:
                if form_instance.franchise != user:
                    return redirect('/')
        elif user_type == 'staff':
            # Staff can access loans from their assigned franchises
            assigned_franchises = Franchise.objects.filter(
                staffassignmentmodel__staff_name=user
            ).distinct()
            if form_instance.franchise not in assigned_franchises:
                return redirect('/')
        elif user_type == 'franchise':
            # Franchise can only access their own loans
            if form_instance.franchise != user:
                return redirect('/')
        
        # Get files with optimization
        files = UploadedFile.objects.filter(loan_application=form_instance)
        
        # Create form with user type restrictions
        form = LoanApplicationForm(instance=form_instance, user_type=user_type)
        
        # Apply field restrictions based on user type
        if user_type == 'franchise':
            # Franchise users can't edit status-related fields
            restricted_fields = ['status_name', 'executive_name', 'reference_no_1', 'reference_no_2']
            for field in restricted_fields:
                if field in form.fields:
                    form.fields[field].widget.attrs['readonly'] = True
                    form.fields[field].widget.attrs['disabled'] = True
        elif user_type == 'staff':
            # Staff can edit most fields but may have some restrictions
            # For now, staff can edit all fields
            pass
        
        context = {
            'username': username,
            'user_type': user_type,
            'form': form,
            'files': files
        }
        return render(request, 'loan-page.html', context)
    
    def post(self, request, form_id):
        """Handle POST request for loan updates"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or not user_type:
            return redirect('/login')
        
        user, username = self.get_user_context(user_id, user_type)
        if not user:
            return redirect('/login')
        
        form_instance = get_object_or_404(LoanApplicationModel, form_id=form_id)
        
        # Check access permissions based on user type
        if user_type == 'admin':
            # Admin can access all loans or only their own depending on permissions
            if not user.is_superadmin and not user.is_staff:
                if form_instance.franchise != user:
                    return redirect('/')
        elif user_type == 'staff':
            # Staff can access loans from their assigned franchises
            assigned_franchises = Franchise.objects.filter(
                staffassignmentmodel__staff_name=user
            ).distinct()
            if form_instance.franchise not in assigned_franchises:
                return redirect('/')
        elif user_type == 'franchise':
            # Franchise can only access their own loans
            if form_instance.franchise != user:
                return redirect('/')
        
        if request.POST.get('submit-form'):
            # Update loan application fields
            self.update_loan_fields(request, form_instance, user_type)
            form_instance.save()
            messages.success(request, "Loan application updated successfully!")
            return redirect('all-application')
        
        elif request.POST.get('new_files'):
            # Handle new file uploads
            files = request.FILES.getlist('uploaded_files')
            for file in files:
                UploadedFile.objects.create(
                    file=file,
                    loan_application=form_instance
                )
            messages.success(request, "Files uploaded successfully!")
            return redirect('loan-page', form_id)
        
        return redirect('loan-page', form_id)
    
    def update_loan_fields(self, request, form_instance, user_type):
        """Update loan application fields from POST data with user type restrictions"""
        # Base fields that all users can update
        fields_to_update = [
            'first_name', 'last_name', 'district', 'place', 'phone_no', 'address',
            'loan_amount', 'document_description', 'guaranter_name', 'guaranter_phoneno', 
            'guaranter_job', 'guaranter_cibil_score', 'guaranter_cibil_issue',
            'guaranter_it_payable', 'job', 'cibil_score', 'cibil_issue', 
            'it_payable', 'years'
        ]
        
        # Add staff/admin specific fields
        if user_type in ['staff', 'admin']:
            staff_fields = ['executive_name', 'reference_no_1', 'reference_no_2']
            fields_to_update.extend(staff_fields)
        
        for field in fields_to_update:
            if field in request.POST:
                setattr(form_instance, field, request.POST.get(field))
        
        # Handle foreign key fields
        loan_id = request.POST.get('loan_name')
        if loan_id:
            try:
                form_instance.loan_name = LoanModel.objects.get(loan_id=loan_id)
            except LoanModel.DoesNotExist:
                pass
        
        bank_id = request.POST.get('bank_name')
        if bank_id:
            try:
                form_instance.bank_name = BankModel.objects.get(bank_id=bank_id)
            except BankModel.DoesNotExist:
                pass
        
        # Handle status updates - only staff and admin can update status
        status_id = request.POST.get('status_name')
        if status_id and user_type in ['staff', 'admin']:
            try:
                status = StatusModel.objects.get(status_id=status_id)
                form_instance.status_name = status
                
                # Set workstatus to indicate staff has processed this loan
                if user_type == 'staff':
                    # Map status to workstatus
                    status_mapping = {
                        'Pending': 'Pending',
                        'Approved': 'Accept', 
                        'Rejected': 'Reject'
                    }
                    # Get status name and map to workstatus
                    status_name = status.status_name
                    if status_name in status_mapping:
                        form_instance.workstatus = status_mapping[status_name]
                    else:
                        form_instance.workstatus = 'Pending'  # Default to Pending
                    
                    # Set follow-up date based on status
                    from datetime import datetime, timedelta
                    current_date = datetime.now().date()
                    
                    followup_periods = {
                        'Pending': 3,
                        'Accept': 7,
                        'Reject': 1,
                    }
                    
                    workstatus = form_instance.workstatus
                    days_to_add = followup_periods.get(workstatus, 3)
                    form_instance.followup_date = current_date + timedelta(days=days_to_add)
                    
            except StatusModel.DoesNotExist:
                pass


@method_decorator(franchise_profile_complete, name='dispatch')
class LoanListView(View):
    """Optimized loan list view with filtering and pagination"""
    
    def get_user_context(self, user_id, user_type):
        """Get user context based on user type"""
        try:
            if user_type == 'admin':
                user = AdminModel.objects.get(admin_id=user_id)
                username = f"{user.admin_first_name} {user.admin_last_name}" if user.admin_last_name else f"{user.admin_first_name}"
                can_access_all = True
                
            elif user_type == 'staff':
                user = StaffModel.objects.get(staff_id=user_id)
                username = f"{user.first_name} {user.last_name if user.last_name else ''}"
                can_access_all = True
                
            elif user_type == 'franchise':
                user = Franchise.objects.get(franchise_id=user_id)
                username = user.franchise_name
                can_access_all = False
                
            else:
                return None, None, None
                
            return user, username, can_access_all
            
        except Exception as e:
            logger.error(f"Error fetching user details: {e}")
            return None, None, None
    
    def get_loan_queryset(self, user, user_type, can_access_all):
        """Get loan queryset based on user permissions"""
        if can_access_all:
            queryset = LoanApplicationModel.objects.select_related(
                'franchise', 'loan_name', 'status_name', 'bank_name'
            ).prefetch_related('uploaded_files').order_by('-created_at', '-form_id')
        else:
            queryset = LoanApplicationModel.objects.filter(
                franchise=user
            ).select_related(
                'franchise', 'loan_name', 'status_name', 'bank_name'
            ).prefetch_related('uploaded_files').order_by('-created_at', '-form_id')
        
        return queryset
    
    def get(self, request):
        """Handle GET request for loan list"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or not user_type:
            return redirect('/login')
        
        user, username, can_access_all = self.get_user_context(user_id, user_type)
        if not user:
            return redirect('/login')
        
        # Get base queryset
        loan_app = self.get_loan_queryset(user, user_type, can_access_all)
        
        # Apply filters
        loan_app = get_loan_filters(request, loan_app)
        
        # Pagination
        paginator = Paginator(loan_app, 10)  # 10 items per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get all franchises for dropdown
        all_franchises = Franchise.objects.all().order_by('franchise_name')
        
        # Get all statuses for dropdown
        all_statuses = StatusModel.objects.all().order_by('status_name')
        
        # Get all banks for dropdown
        all_banks = BankModel.objects.all().order_by('bank_name')
        
        # Get all loan types for dropdown
        all_loan_types = LoanModel.objects.all().order_by('loan_name')
        
        context = {
            'username': username,
            'user_type': user_type,
            'loan_applications': page_obj,
            'all_franchises': all_franchises,
            'all_statuses': all_statuses,
            'all_banks': all_banks,
            'all_loan_types': all_loan_types,
            # Filter values
            'first_name_filter': request.GET.get('first_name', ''),
            'last_name_filter': request.GET.get('last_name', ''),
            'district_filter': request.GET.get('district', ''),
            'place_filter': request.GET.get('place', ''),
            'address_filter': request.GET.get('address', ''),
            'loan_type_filter': request.GET.get('loan_type', ''),
            'status_filter': request.GET.get('status', ''),
            'bank_filter': request.GET.get('bank', ''),
            'executive_filter': request.GET.get('executive', ''),
            'reference_no_1_filter': request.GET.get('reference_no_1', ''),
            'followup_from': request.GET.get('followup_from', ''),
            'followup_to': request.GET.get('followup_to', ''),
            'loan_name_filter': request.GET.get('loan_name', ''),
            'franchise_filter': request.GET.get('franchise', ''),
            'min_amount': request.GET.get('min_amount', ''),
            'max_amount': request.GET.get('max_amount', ''),
            'page_obj': page_obj,
        }
        
        return render(request, 'all-files.html', context)


class LoanStatusView(View):
    """Optimized loan status view"""
    
    def get(self, request):
        """Handle GET request for loan status"""
        user_phone = request.GET.get('phone_no')
        if not user_phone:
            return JsonResponse({'error': 'Phone number required'}, status=400)
        
        try:
            loan_application = LoanApplicationModel.objects.select_related('status_name').get(
                phone_no=user_phone
            )
            status = loan_application.status_name.status_name if loan_application.status_name else "Not Available"
            
            progress_percentage = self.get_progress_percentage(status)
            
            context = {
                'progress_percentage': progress_percentage,
                'status': status,
            }
            return render(request, 'dashboard.html', context)
            
        except LoanApplicationModel.DoesNotExist:
            return JsonResponse({'error': 'Loan application not found'}, status=404)
    
    def get_progress_percentage(self, status):
        """Get progress percentage based on status"""
        progress_map = {
            "Application Started": 33,
            "Pending": 66,
            "Completed": 100,
        }
        return progress_map.get(status, 0)


class LoanManagementView(View):
    """Base view for loan management operations"""
    
    def get_user_context(self, user_id, user_type):
        """Get user context based on user type"""
        try:
            if user_type == 'admin':
                user = AdminModel.objects.get(admin_id=user_id)
                username = f"{user.admin_first_name} {user.admin_last_name}" if user.admin_last_name else f"{user.admin_first_name}"
                
            elif user_type == 'staff':
                user = StaffModel.objects.get(staff_id=user_id)
                username = f"{user.first_name} {user.last_name if user.last_name else ''}"
                
            elif user_type == 'franchise':
                user = Franchise.objects.get(franchise_id=user_id)
                username = user.franchise_name
                
            else:
                return None, None
                
            return user, username
            
        except Exception as e:
            logger.error(f"Error fetching user details: {e}")
            return None, None


class AddLoanView(LoanManagementView):
    """View for adding new loan types"""
    
    def get(self, request):
        """Handle GET request for add loan form"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if user_type not in ['admin', 'staff', 'franchise']:
            return JsonResponse({"error": "Unauthorized access"}, status=403)
        
        user, username = self.get_user_context(user_id, user_type)
        if not user:
            return JsonResponse({"error": "User not found"}, status=403)
        
        all_loans = LoanModel.objects.all()
        form = LoanForm()
        
        context = {
            'username': username,
            'form': form,
            'all_loans': all_loans
        }
        return render(request, 'add-loan.html', context)
    
    def post(self, request):
        """Handle POST request for adding new loan"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if user_type not in ['admin', 'staff', 'franchise']:
            messages.error(request, "Unauthorized access")
            return redirect('/login/')
        
        user, username = self.get_user_context(user_id, user_type)
        if not user:
            messages.error(request, "User not found")
            return redirect('/login/')
        
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save()
            messages.success(request, f"Loan '{loan.loan_name}' added successfully!")
            return redirect('addloan')  # Redirect back to the add loan page
        else:
            messages.error(request, "Please correct the errors below.")
        
        # If form is invalid, re-render with errors
        all_loans = LoanModel.objects.all()
        context = {
            'username': username,
            'form': form,
            'all_loans': all_loans
        }
        return render(request, 'add-loan.html', context)


class AddStatusView(LoanManagementView):
    """View for adding new status types"""
    
    def get(self, request):
        """Handle GET request for add status form"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if user_type not in ['admin', 'staff']:
            return redirect('/login')
        
        user, username = self.get_user_context(user_id, user_type)
        if not user:
            return redirect('/login')
        
        all_status = StatusModel.objects.all()
        form = StatusForm()
        
        context = {
            'username': username,
            'form': form,
            'all_status': all_status
        }
        return render(request, 'add-status.html', context)
    
    def post(self, request):
        """Handle POST request for adding new status"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if user_type not in ['admin', 'staff']:
            return redirect('/login')
        
        user, username = self.get_user_context(user_id, user_type)
        if not user:
            return redirect('/login')
        
        form = StatusForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Status added successfully!")
            return redirect('addstatus')
        
        all_status = StatusModel.objects.all()
        context = {
            'username': username,
            'form': form,
            'all_status': all_status
        }
        return render(request, 'add-status.html', context)


class AddBankView(LoanManagementView):
    """View for adding new banks"""
    
    def get(self, request):
        """Handle GET request for add bank form"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if user_type not in ['admin', 'staff']:
            return redirect('/login')
        
        user, username = self.get_user_context(user_id, user_type)
        if not user:
            return redirect('/login')
        
        all_banks = BankModel.objects.all()
        form = BankForm()
        
        context = {
            'username': username,
            'form': form,
            'all_banks': all_banks
        }
        return render(request, 'add-bank.html', context)
    
    def post(self, request):
        """Handle POST request for adding new bank"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if user_type not in ['admin', 'staff']:
            return redirect('/login')
        
        user, username = self.get_user_context(user_id, user_type)
        if not user:
            return redirect('/login')
        
        form = BankForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Bank added successfully!")
            return redirect('addbank')
        
        all_banks = BankModel.objects.all()
        context = {
            'username': username,
            'form': form,
            'all_banks': all_banks
        }
        return render(request, 'add-bank.html', context)


# Legacy function-based views for backward compatibility
def loanform(request):
    """Legacy loan form view - delegates to optimized class-based view"""
    view = LoanApplicationView()
    if request.method == 'GET':
        return view.get(request)
    else:
        return view.post(request)

def loan_page(request, form_id):
    """Legacy loan page view - delegates to optimized class-based view"""
    view = LoanDetailView()
    if request.method == 'GET':
        return view.get(request, form_id)
    else:
        return view.post(request, form_id)

def all_app(request):
    """Legacy loan list view - delegates to optimized class-based view"""
    view = LoanListView()
    return view.get(request)

def loan_application_status(request):
    """Legacy loan status view - delegates to optimized class-based view"""
    view = LoanStatusView()
    return view.get(request)

def addloan(request):
    """Legacy add loan view - delegates to optimized class-based view"""
    view = AddLoanView()
    if request.method == 'GET':
        return view.get(request)
    else:
        return view.post(request)

def addstatus(request):
    """Legacy add status view - delegates to optimized class-based view"""
    view = AddStatusView()
    if request.method == 'GET':
        return view.get(request)
    else:
        return view.post(request)

def addbank(request):
    """Legacy add bank view - delegates to optimized class-based view"""
    view = AddBankView()
    if request.method == 'GET':
        return view.get(request)
    else:
        return view.post(request)
