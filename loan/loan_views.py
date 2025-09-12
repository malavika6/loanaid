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
from users.decorators import admin_required, staff_required, franchise_required, login_required
from .models import (
    LoanApplicationModel, LoanModel, StatusModel, BankModel, 
    UploadedFile, StaffAssignmentModel
)
from .forms import LoanApplicationForm, LoanForm, StatusForm, BankForm
from .loan_utils import get_loan_context, get_loan_stats, get_loan_filters

logger = logging.getLogger(__name__)


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
                user = StaffModel.objects.get(staff_id=user_id)
                username = f"{user.first_name} {user.last_name or ''}".strip()
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
            return LoanApplicationModel.objects.select_related(
                'franchise', 'loan_name', 'status_name', 'bank_name'
            ).prefetch_related('uploaded_files')
        
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
                ).prefetch_related('uploaded_files')
            return LoanApplicationModel.objects.none()
            
        elif user_type == 'franchise':
            return LoanApplicationModel.objects.filter(
                franchise=user
            ).select_related(
                'franchise', 'loan_name', 'status_name', 'bank_name'
            ).prefetch_related('uploaded_files')
            
        elif user_type == 'executive':
            return LoanApplicationModel.objects.filter(
                executive=user
            ).select_related(
                'franchise', 'loan_name', 'status_name', 'bank_name'
            ).prefetch_related('uploaded_files')
            
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
            hide_fields = ['followup_date', 'status_name', 'executive_name', 'mobileno_1', 'mobileno_2']
        
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
        
        if not user_id or not user_type:
            return redirect('/login')
        
        user, username, can_access_all = self.get_user_context(user_id, user_type)
        if not user:
            return redirect('/login')
        
        files = request.FILES.getlist('files')
        form = LoanApplicationForm(request.POST, request.FILES, user_type=user_type)
        
        # Hide fields for franchise users
        if user_type == 'franchise':
            hide_fields = ['followup_date', 'status_name', 'executive_name', 'mobileno_1', 'mobileno_2']
            for field in hide_fields:
                if field in form.fields:
                    form.fields.pop(field)
        
        if form.is_valid():
            loan_form = form.save(commit=False)
            
            # Assign franchise based on user type
            if user_type == 'admin' and not can_access_all:
                loan_form.franchise = user
            elif user_type == 'staff':
                assignment = StaffAssignmentModel.objects.filter(staff_name=user).first()
                if assignment:
                    franchise = assignment.franchise_name.first()
                    loan_form.franchise = franchise
            elif user_type == 'franchise':
                loan_form.franchise = user
            elif user_type == 'executive':
                loan_form.executive = user
            
            loan_form.save()
            
            # Handle file uploads
            for file in files:
                UploadedFile.objects.create(
                    file=file, 
                    loan_application=loan_form
                )
            
            messages.success(request, "Loan application submitted successfully!")
            return redirect('all-application')
        
        # If form is invalid, re-render with errors
        status = StatusModel.objects.all()
        bank = BankModel.objects.all()
        hide_fields = ['followup_date', 'status_name', 'executive_name', 'mobileno_1', 'mobileno_2'] if user_type == 'franchise' else []
        
        context = get_loan_context(username, None, status, bank, form, hide_fields)
        return render(request, 'loan-form.html', context)


class LoanDetailView(View):
    """Optimized loan detail view with role-based access control"""
    
    def get_user_context(self, user_id):
        """Get admin user context"""
        try:
            admin = AdminModel.objects.get(admin_id=user_id)
            admin_name = f"{admin.admin_first_name} {admin.admin_last_name}" if admin.admin_last_name else f"{admin.admin_first_name}"
            return admin, admin_name
        except AdminModel.DoesNotExist:
            return None, None
    
    def get(self, request, form_id):
        """Handle GET request for loan detail page"""
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('/login')
        
        admin, admin_name = self.get_user_context(user_id)
        if not admin:
            return redirect('/login')
        
        # Get loan application with optimization
        form_instance = get_object_or_404(
            LoanApplicationModel.objects.select_related(
                'franchise', 'loan_name', 'status_name', 'bank_name'
            ), 
            form_id=form_id
        )
        
        # Check access permissions
        if not admin.is_superadmin and not admin.is_staff:
            if form_instance.franchise != admin:
                return redirect('/')
        
        # Get files with optimization
        files = UploadedFile.objects.filter(loan_application=form_instance)
        
        form = LoanApplicationForm(instance=form_instance)
        
        context = {
            'username': admin_name,
            'admin': admin,
            'form': form,
            'files': files
        }
        return render(request, 'loan-page.html', context)
    
    def post(self, request, form_id):
        """Handle POST request for loan updates"""
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('/login')
        
        admin, admin_name = self.get_user_context(user_id)
        if not admin:
            return redirect('/login')
        
        form_instance = get_object_or_404(LoanApplicationModel, form_id=form_id)
        
        # Check access permissions
        if not admin.is_superadmin and not admin.is_staff:
            if form_instance.franchise != admin:
                return redirect('/')
        
        if request.POST.get('submit-form'):
            # Update loan application fields
            self.update_loan_fields(request, form_instance)
            form_instance.save()
            messages.success(request, "Loan application updated successfully!")
            return redirect('/')
        
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
    
    def update_loan_fields(self, request, form_instance):
        """Update loan application fields from POST data"""
        fields_to_update = [
            'first_name', 'last_name', 'district', 'place', 'phone_no',
            'loan_amount', 'executive_name', 'mobileno_1', 'mobileno_2',
            'followup_date', 'description', 'application_description'
        ]
        
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
        
        status_id = request.POST.get('status_name')
        if status_id:
            try:
                form_instance.status_name = StatusModel.objects.get(status_id=status_id)
            except StatusModel.DoesNotExist:
                pass


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
                username = f"{user.first_name} {user.last_name or ''}".strip()
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
            ).prefetch_related('uploaded_files')
        else:
            queryset = LoanApplicationModel.objects.filter(
                franchise=user
            ).select_related(
                'franchise', 'loan_name', 'status_name', 'bank_name'
            ).prefetch_related('uploaded_files')
        
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
        paginator = Paginator(loan_app, 20)  # 20 items per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'username': username,
            'loan_applications': page_obj,
            'loan_name_filter': request.GET.get('loan_name', ''),
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
            return JsonResponse({"error": "Unauthorized access"}, status=403)
        
        user, username = self.get_user_context(user_id, user_type)
        if not user:
            return JsonResponse({"error": "User not found"}, status=403)
        
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save()
            return JsonResponse({
                "success": True,
                "loan_id": loan.loan_id,
                "loan_name": loan.loan_name
            })
        
        return JsonResponse({"error": form.errors}, status=400)


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
    return view.get(request)

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
