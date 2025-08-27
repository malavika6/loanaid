from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .models import AdminModel, StaffModel, Franchise
from .forms import StaffModelForm, AdminForm
from loan.models import LoanApplicationModel, StaffAssignmentModel
from .decorators import admin_required, superadmin_required
from .utils import get_admin_context, send_staff_credentials_email

logger = logging.getLogger(__name__)


class AdminDashboardView(View):
    """Optimized admin dashboard view with caching and efficient queries"""
    
    template_name = 'index.html'
    
    def get(self, request):
        """Handle GET request for admin dashboard"""
        try:
            admin = self._get_admin_user(request)
            if not admin:
                return redirect('/login')
            
            context = self._build_dashboard_context(admin)
            return render(request, self.template_name, context)
            
        except Exception as e:
            logger.error(f"Error in admin dashboard: {e}")
            messages.error(request, "An error occurred while loading the dashboard.")
            return redirect('/login')
    
    def _get_admin_user(self, request):
        """Get admin user from session"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or user_type != 'admin':
            return None
            
        try:
            return AdminModel.objects.get(admin_id=user_id, is_active=True)
        except AdminModel.DoesNotExist:
            return None
    
    def _build_dashboard_context(self, admin):
        """Build optimized dashboard context with efficient queries"""
        today = timezone.now().date()
        
        # Use select_related and prefetch_related for efficient queries
        base_loan_query = LoanApplicationModel.objects.select_related(
            'loan_name', 'status_name', 'bank_name', 'franchise'
        ).prefetch_related('uploaded_files')
        
        # Get today's follow-up loans
        today_loans = base_loan_query.filter(followup_date=today)
        
        # Get recent loan applications (last 10)
        recent_loans = base_loan_query.order_by('-form_id')[:10]
        
        # Get counts using efficient database queries
        franchise_count = Franchise.objects.count()
        staff_count = StaffModel.objects.count()
        loan_count = LoanApplicationModel.objects.count()
        
        # Get all franchises and staff for superadmin
        if admin.is_superadmin:
            franchises = Franchise.objects.select_related('staff').all()
            staff_members = StaffModel.objects.all().order_by('-created_at')
        else:
            # For regular admins, only show assigned data
            franchises = Franchise.objects.filter(staff=admin).select_related('staff')
            staff_members = StaffModel.objects.filter(staff=admin)
        
        context = {
            'admin': admin,
            'username': admin.get_full_name(),
            'forms': recent_loans,
            'loans': today_loans,
            'total_franchise_count': franchise_count,
            'total_staff_count': staff_count,
            'loan_app_count': loan_count,
            'all_franchises': franchises,
            'all_staff': staff_members,
            'can_add_loan': True,
            'today': today,
        }
        
        return context


@admin_required
def admin_stats_view(request):
    """AJAX endpoint for admin dashboard statistics"""
    try:
        # Get date range for statistics
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Get loan statistics
        loan_stats = LoanApplicationModel.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total_applications=Count('form_id'),
            pending_applications=Count('form_id', filter=Q(status_name__isnull=True)),
            approved_applications=Count('form_id', filter=Q(status_name__status_name='Approved')),
            rejected_applications=Count('form_id', filter=Q(status_name__status_name='Rejected'))
        )
        
        # Get franchise statistics
        franchise_stats = Franchise.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total_franchises=Count('franchise_id'),
            active_franchises=Count('franchise_id', filter=Q(is_active=True)),
            pending_payments=Count('franchise_id', filter=Q(payment_status=False))
        )
        
        # Get staff statistics
        staff_stats = StaffModel.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total_staff=Count('staff_id'),
            active_staff=Count('staff_id', filter=Q(is_active=True))
        )
        
        return JsonResponse({
            'success': True,
            'loan_stats': loan_stats,
            'franchise_stats': franchise_stats,
            'staff_stats': staff_stats,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to retrieve statistics'
        }, status=500)


@admin_required
def create_staff_view(request):
    """Optimized staff creation view"""
    if request.method == "POST":
        form = StaffModelForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                staff = form.save(commit=False)
                plain_password = form.cleaned_data.get("password")
                
                # Hash password and save
                staff.password = plain_password  # Model's save method will hash it
                staff.save()
                
                # Send credentials email asynchronously
                send_staff_credentials_email.delay(staff.pk, plain_password)
                
                messages.success(request, "Staff member added successfully! Credentials will be sent via email.")
                return redirect("list_staff")
                
            except Exception as e:
                logger.error(f"Error creating staff: {e}")
                messages.error(request, "Failed to create staff member. Please try again.")
        else:
            messages.error(request, "Please correct the errors in the form.")
            logger.warning(f"Staff form errors: {form.errors}")
    else:
        form = StaffModelForm()
    
    return render(request, "create-staff.html", {"form": form})


@admin_required
def list_staff_view(request):
    """Optimized staff listing view with pagination and search"""
    try:
        # Get search parameters
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        page_number = request.GET.get('page', 1)
        
        # Build queryset with efficient queries
        staff_queryset = StaffModel.objects.select_related().all()
        
        # Apply filters
        if search_query:
            staff_queryset = staff_queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(employee_id__icontains=search_query)
            )
        
        if status_filter:
            if status_filter == 'active':
                staff_queryset = staff_queryset.filter(is_active=True)
            elif status_filter == 'inactive':
                staff_queryset = staff_queryset.filter(is_active=False)
        
        # Order by creation date
        staff_queryset = staff_queryset.order_by('-created_at')
        
        # Pagination
        paginator = Paginator(staff_queryset, 20)  # 20 items per page
        page_obj = paginator.get_page(page_number)
        
        context = {
            'staff_list': page_obj,
            'search_query': search_query,
            'status_filter': status_filter,
            'total_count': paginator.count,
        }
        
        return render(request, 'all_staffs.html', context)
        
    except Exception as e:
        logger.error(f"Error listing staff: {e}")
        messages.error(request, "An error occurred while loading staff list.")
        return redirect('/')


@admin_required
def view_staff_detail(request, staff_id):
    """Optimized staff detail view"""
    try:
        staff_member = get_object_or_404(
            StaffModel.objects.select_related().prefetch_related(
                'staffassignmentmodel_set__franchise_name'
            ),
            pk=staff_id
        )
        
        # Get assigned franchises
        assigned_franchises = staff_member.staffassignmentmodel_set.all()
        
        # Get loan statistics for this staff
        loan_stats = LoanApplicationModel.objects.filter(
            assigned_to=staff_member
        ).aggregate(
            total_loans=Count('form_id'),
            pending_loans=Count('form_id', filter=Q(status_name__isnull=True)),
            completed_loans=Count('form_id', filter=Q(status_name__status_name='Completed'))
        )
        
        context = {
            'staff_member': staff_member,
            'assigned_franchises': assigned_franchises,
            'loan_stats': loan_stats,
        }
        
        return render(request, 'staff_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error viewing staff detail: {e}")
        messages.error(request, "Failed to load staff details.")
        return redirect('list_staff')


@admin_required
def delete_staff_view(request, staff_id):
    """Optimized staff deletion view"""
    if request.method != 'POST':
        messages.warning(request, "Invalid request method.")
        return redirect('list_staff')
    
    try:
        staff_member = get_object_or_404(StaffModel, pk=staff_id)
        
        # Check if staff has active assignments
        active_assignments = StaffAssignmentModel.objects.filter(staff_name=staff_member).exists()
        if active_assignments:
            messages.error(request, "Cannot delete staff member with active franchise assignments.")
            return redirect('list_staff')
        
        # Unassign all related loan applications
        LoanApplicationModel.objects.filter(assigned_to=staff_member).update(assigned_to=None)
        
        # Delete staff member
        staff_member.delete()
        
        messages.success(request, "Staff member deleted successfully.")
        logger.info(f"Staff member {staff_id} deleted by admin")
        
    except Exception as e:
        logger.error(f"Error deleting staff: {e}")
        messages.error(request, "Failed to delete staff member.")
    
    return redirect('list_staff')


@admin_required
def admin_profile_view(request):
    """Admin profile management view"""
    try:
        admin = get_object_or_404(AdminModel, admin_id=request.session.get('user_id'))
        
        if request.method == 'POST':
            form = AdminForm(request.POST, instance=admin)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('admin_profile')
        else:
            form = AdminForm(instance=admin)
        
        context = {
            'form': form,
            'admin': admin,
        }
        
        return render(request, 'admin_profile.html', context)
        
    except Exception as e:
        logger.error(f"Error in admin profile: {e}")
        messages.error(request, "Failed to load profile.")
        return redirect('/')


@admin_required
def admin_activity_log(request):
    """Admin activity log view"""
    try:
        # Get recent admin activities (you can implement an activity log model)
        # For now, showing recent loan applications and staff changes
        
        recent_loans = LoanApplicationModel.objects.select_related(
            'franchise', 'status_name'
        ).order_by('-created_at')[:50]
        
        recent_staff_changes = StaffModel.objects.select_related().order_by('-created_at')[:20]
        
        context = {
            'recent_loans': recent_loans,
            'recent_staff_changes': recent_staff_changes,
        }
        
        return render(request, 'admin_activity_log.html', context)
        
    except Exception as e:
        logger.error(f"Error loading activity log: {e}")
        messages.error(request, "Failed to load activity log.")
        return redirect('/')


# Utility functions for admin operations
def get_admin_permissions(admin):
    """Get admin permissions based on role"""
    permissions = {
        'can_manage_staff': True,
        'can_manage_franchises': True,
        'can_manage_loans': True,
        'can_view_reports': True,
        'can_delete_records': admin.is_superadmin,
        'can_manage_system': admin.is_superadmin,
    }
    return permissions


def validate_admin_action(admin, action):
    """Validate if admin can perform specific action"""
    permissions = get_admin_permissions(admin)
    return permissions.get(action, False)
