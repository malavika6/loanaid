from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from datetime import timedelta
import logging

from .models import StaffModel, Franchise
from .forms import StaffModelForm
from .decorators import staff_required
from .staff_utils import get_staff_context, get_staff_dashboard_stats
from loan.models import LoanApplicationModel, StaffAssignmentModel

logger = logging.getLogger(__name__)


class StaffDashboardView(View):
    """Optimized staff dashboard view with efficient database queries"""
    template_name = 'dashboard.html'
    
    def get(self, request):
        try:
            staff = self._get_staff_user(request)
            if not staff:
                return redirect('/login')
            
            context = self._build_dashboard_context(staff)
            return render(request, self.template_name, context)
            
        except Exception as e:
            logger.error(f"Error in staff dashboard: {e}")
            messages.error(request, "An error occurred while loading the dashboard.")
            return redirect('/login')
    
    def _get_staff_user(self, request):
        """Get the authenticated staff user"""
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or user_type != 'staff':
            return None
            
        try:
            return StaffModel.objects.get(staff_id=user_id)
        except StaffModel.DoesNotExist:
            return None
    
    def _build_dashboard_context(self, staff):
        """Build optimized dashboard context with efficient queries"""
        # Get assigned franchises with prefetch_related to avoid N+1 queries
        assigned_franchises = Franchise.objects.filter(
            staffassignmentmodel__staff_name=staff
        ).select_related('staff').prefetch_related('loanapplicationmodel_set')
        
        # Get loans with optimized queries
        staff_loans = LoanApplicationModel.objects.filter(
            assigned_to=staff
        ).select_related('franchise', 'loan_name', 'status_name')
        
        franchise_loans = LoanApplicationModel.objects.filter(
            franchise__in=assigned_franchises
        ).select_related('franchise', 'loan_name', 'status_name')
        
        # Combine and get distinct loans
        all_loans = (staff_loans | franchise_loans).distinct()
        
        # Get dashboard statistics
        stats = get_staff_dashboard_stats(staff)
        
        context = get_staff_context(staff)
        context.update({
            'all_loans': all_loans[:10],  # Limit to recent 10 loans
            'franchise_loans': stats['franchise_loan_count'],
            'assigned_franchise_count': stats['assigned_franchise_count'],
            'assigned_franchises': assigned_franchises[:5],  # Limit to 5 franchises
            'recent_activity': stats['recent_activity'],
            'performance_metrics': stats['performance_metrics']
        })
        
        return context


class StaffProfileView(View):
    """Staff profile management view"""
    template_name = 'profile.html'
    
    def get(self, request):
        staff = self._get_staff_user(request)
        if not staff:
            return redirect('/login')
        
        context = get_staff_context(staff)
        context['staff'] = staff
        return render(request, self.template_name, context)
    
    def post(self, request):
        staff = self._get_staff_user(request)
        if not staff:
            return redirect('/login')
        
        form = StaffModelForm(request.POST, request.FILES, instance=staff)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('staff_profile')
            except Exception as e:
                logger.error(f"Error updating staff profile: {e}")
                messages.error(request, "An error occurred while updating profile.")
        else:
            messages.error(request, "Please correct the errors in the form.")
        
        context = get_staff_context(staff)
        context['staff'] = staff
        context['form'] = form
        return render(request, self.template_name, context)
    
    def _get_staff_user(self, request):
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or user_type != 'staff':
            return None
            
        try:
            return StaffModel.objects.get(staff_id=user_id)
        except StaffModel.DoesNotExist:
            return None


class StaffAssignmentsView(View):
    """View for staff to see their franchise assignments"""
    template_name = 'staff_assignments.html'
    
    def get(self, request):
        staff = self._get_staff_user(request)
        if not staff:
            return redirect('/login')
        
        # Get assignments with optimized queries
        assignments = StaffAssignmentModel.objects.filter(
            staff_name=staff
        ).select_related('assigned_by').prefetch_related(
            'franchise_name'
        ).order_by('-created_at')
        
        # Get assigned franchises
        assigned_franchises = Franchise.objects.filter(
            staffassignmentmodel__staff_name=staff
        ).select_related('staff').prefetch_related(
            'loanapplicationmodel_set'
        )
        
        context = get_staff_context(staff)
        context.update({
            'assignments': assignments,
            'assigned_franchises': assigned_franchises,
            'total_franchises': assigned_franchises.count(),
            'total_loans': LoanApplicationModel.objects.filter(
                franchise__in=assigned_franchises
            ).count()
        })
        
        return render(request, self.template_name, context)
    
    def _get_staff_user(self, request):
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or user_type != 'staff':
            return None
            
        try:
            return StaffModel.objects.get(staff_id=user_id)
        except StaffModel.DoesNotExist:
            return None


# Function-based views for backward compatibility
@staff_required
def staff_dashboard_legacy(request):
    """Legacy staff dashboard function - delegates to StaffDashboardView"""
    view = StaffDashboardView()
    return view.get(request)


@staff_required
def staff_profile_legacy(request):
    """Legacy staff profile function - delegates to StaffProfileView"""
    view = StaffProfileView()
    if request.method == 'POST':
        return view.post(request)
    return view.get(request)


@staff_required
def staff_assignments_legacy(request):
    """Legacy staff assignments function - delegates to StaffAssignmentsView"""
    view = StaffAssignmentsView()
    return view.get(request)
