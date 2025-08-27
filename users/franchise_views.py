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

from .models import Franchise
from .forms import FranchiseForm
from .decorators import franchise_required
from .franchise_utils import get_franchise_context, get_franchise_dashboard_stats
from loan.models import LoanApplicationModel, Payment

logger = logging.getLogger(__name__)


class FranchiseDashboardView(View):
    """Optimized franchise dashboard view with efficient database queries"""
    template_name = 'franchise_dashboard.html'
    
    def get(self, request):
        try:
            franchise = self._get_franchise_user(request)
            if not franchise:
                return redirect('/login')
            
            context = self._build_dashboard_context(franchise)
            return render(request, self.template_name, context)
            
        except Exception as e:
            logger.error(f"Error in franchise dashboard: {e}")
            messages.error(request, "An error occurred while loading the dashboard.")
            return redirect('/login')
    
    def _get_franchise_user(self, request):
        """Get the authenticated franchise user"""
        franchise_id = request.session.get('franchise_id')
        user_type = request.session.get('user_type')
        
        if not franchise_id or user_type != 'franchise':
            return None
            
        try:
            return Franchise.objects.get(franchise_id=franchise_id)
        except Franchise.DoesNotExist:
            return None
    
    def _build_dashboard_context(self, franchise):
        """Build optimized dashboard context with efficient queries"""
        # Get loans with optimized queries
        loans = LoanApplicationModel.objects.filter(
            franchise=franchise
        ).select_related('loan_name', 'status_name').order_by('-created_at')
        
        # Get dashboard statistics
        stats = get_franchise_dashboard_stats(franchise)
        
        context = get_franchise_context(franchise)
        context.update({
            'franchise': franchise,
            'loans': loans[:10],  # Limit to recent 10 loans
            'loan_count': stats['loan_count'],
            'wallet_balance': franchise.wallet_balance,
            'recent_activity': stats['recent_activity'],
            'loan_summary': stats['loan_summary'],
            'payment_status': franchise.payment_status
        })
        
        return context


class FranchiseProfileView(View):
    """Franchise profile management view"""
    template_name = 'profile.html'
    
    def get(self, request):
        franchise = self._get_franchise_user(request)
        if not franchise:
            return redirect('/login')
        
        context = get_franchise_context(franchise)
        context['franchise'] = franchise
        return render(request, self.template_name, context)
    
    def post(self, request):
        franchise = self._get_franchise_user(request)
        if not franchise:
            return redirect('/login')
        
        form = FranchiseForm(request.POST, request.FILES, instance=franchise)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('franchise_profile')
            except Exception as e:
                logger.error(f"Error updating franchise profile: {e}")
                messages.error(request, "An error occurred while updating profile.")
        else:
            messages.error(request, "Please correct the errors in the form.")
        
        context = get_franchise_context(franchise)
        context['franchise'] = franchise
        context['form'] = form
        return render(request, self.template_name, context)
    
    def _get_franchise_user(self, request):
        franchise_id = request.session.get('franchise_id')
        user_type = request.session.get('user_type')
        
        if not franchise_id or user_type != 'franchise':
            return None
            
        try:
            return Franchise.objects.get(franchise_id=franchise_id)
        except Franchise.DoesNotExist:
            return None


class FranchiseLoansView(View):
    """View for franchise to see their loans"""
    template_name = 'franchise_loans.html'
    
    def get(self, request):
        franchise = self._get_franchise_user(request)
        if not franchise:
            return redirect('/login')
        
        # Get loans with pagination and optimized queries
        loans = LoanApplicationModel.objects.filter(
            franchise=franchise
        ).select_related('loan_name', 'status_name').order_by('-created_at')
        
        # Pagination
        paginator = Paginator(loans, 20)  # 20 loans per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get loan statistics
        loan_stats = loans.aggregate(
            total_loans=Count('form_id'),
            pending_loans=Count('form_id', filter=Q(status_name__isnull=True)),
            approved_loans=Count('form_id', filter=Q(status_name__status_name='Approved')),
            rejected_loans=Count('form_id', filter=Q(status_name__status_name='Rejected')),
            total_amount=Sum('loan_amount', default=0),
            average_amount=Avg('loan_amount', default=0)
        )
        
        context = get_franchise_context(franchise)
        context.update({
            'franchise': franchise,
            'page_obj': page_obj,
            'loans': page_obj,
            'loan_stats': loan_stats,
            'total_loans': loan_stats['total_loans']
        })
        
        return render(request, self.template_name, context)
    
    def _get_franchise_user(self, request):
        franchise_id = request.session.get('franchise_id')
        user_type = request.session.get('user_type')
        
        if not franchise_id or user_type != 'franchise':
            return None
            
        try:
            return Franchise.objects.get(franchise_id=franchise_id)
        except Franchise.DoesNotExist:
            return None


class FranchisePaymentView(View):
    """View for franchise payment management"""
    template_name = 'franchise_payment.html'
    
    def get(self, request):
        franchise = self._get_franchise_user(request)
        if not franchise:
            return redirect('/login')
        
        # Get payment history
        payments = Payment.objects.filter(
            franchise=franchise
        ).order_by('-created_at')
        
        context = get_franchise_context(franchise)
        context.update({
            'franchise': franchise,
            'payments': payments,
            'payment_status': franchise.payment_status,
            'wallet_balance': franchise.wallet_balance
        })
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        franchise = self._get_franchise_user(request)
        if not franchise:
            return redirect('/login')
        
        # Handle payment screenshot upload
        screenshot = request.FILES.get('payment_screenshot')
        transaction_id = request.POST.get('transaction_id')
        
        if screenshot and transaction_id:
            try:
                # Create payment record
                payment = Payment.objects.create(
                    franchise=franchise,
                    transaction_id=transaction_id,
                    payment_screenshot=screenshot,
                    status='pending'
                )
                
                messages.success(request, "Payment receipt uploaded successfully! We will verify it soon.")
                return redirect('franchise_payment')
                
            except Exception as e:
                logger.error(f"Error creating payment record: {e}")
                messages.error(request, "An error occurred while uploading payment receipt.")
        else:
            messages.error(request, "Please provide both payment screenshot and transaction ID.")
        
        return redirect('franchise_payment')
    
    def _get_franchise_user(self, request):
        franchise_id = request.session.get('franchise_id')
        user_type = request.session.get('user_type')
        
        if not franchise_id or user_type != 'franchise':
            return None
            
        try:
            return Franchise.objects.get(franchise_id=franchise_id)
        except Franchise.DoesNotExist:
            return None


# Function-based views for backward compatibility
@franchise_required
def franchise_dashboard_legacy(request):
    """Legacy franchise dashboard function - delegates to FranchiseDashboardView"""
    view = FranchiseDashboardView()
    return view.get(request)


@franchise_required
def franchise_profile_legacy(request):
    """Legacy franchise profile function - delegates to FranchiseProfileView"""
    view = FranchiseProfileView()
    if request.method == 'POST':
        return view.post(request)
    return view.get(request)


@franchise_required
def franchise_loans_legacy(request):
    """Legacy franchise loans function - delegates to FranchiseLoansView"""
    view = FranchiseLoansView()
    return view.get(request)


@franchise_required
def franchise_payment_legacy(request):
    """Legacy franchise payment function - delegates to FranchisePaymentView"""
    view = FranchisePaymentView()
    if request.method == 'POST':
        return view.post(request)
    return view.get(request)
