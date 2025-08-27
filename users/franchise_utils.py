from typing import Dict, Any, List
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from datetime import timedelta
import logging

from .models import Franchise
from loan.models import LoanApplicationModel, Payment

logger = logging.getLogger(__name__)


def get_franchise_context(franchise: Franchise) -> Dict[str, Any]:
    """Get common context for franchise templates"""
    try:
        return {
            'username': franchise.franchise_name,
            'franchise': franchise,
            'sidebar_menu': get_franchise_sidebar_menu(),
            'dropdown_items': get_franchise_dropdown_items(),
        }
    except Exception as e:
        logger.error(f"Error getting franchise context: {e}")
        return {}


def get_franchise_sidebar_menu() -> List[Dict[str, str]]:
    """Get sidebar menu items for franchise users"""
    return [
        {'name': 'Dashboard', 'url': '/franchise_dashboard', 'icon': 'fas fa-tachometer-alt'},
        {'name': 'My Loans', 'url': '/franchise_loans', 'icon': 'fas fa-money-bill-wave'},
        {'name': 'Payment History', 'url': '/franchise_payment', 'icon': 'fas fa-credit-card'},
        {'name': 'Profile', 'url': '/franchise_profile', 'icon': 'fas fa-user'},
        {'name': 'Documents', 'url': '/franchise_documents', 'icon': 'fas fa-file-alt'},
        {'name': 'Support', 'url': '/franchise_support', 'icon': 'fas fa-question-circle'},
    ]


def get_franchise_dropdown_items() -> List[Dict[str, str]]:
    """Get dropdown menu items for franchise users"""
    return [
        {'name': 'Profile Settings', 'url': '/franchise_profile', 'icon': 'fas fa-cog'},
        {'name': 'Change Password', 'url': '/change_password', 'icon': 'fas fa-key'},
        {'name': 'Activity Log', 'url': '/activity_log', 'icon': 'fas fa-history'},
        {'name': 'Help & Support', 'url': '/support', 'icon': 'fas fa-question-circle'},
        {'name': 'Logout', 'url': '/logout', 'icon': 'fas fa-sign-out-alt'},
    ]


def get_franchise_dashboard_stats(franchise: Franchise, days: int = 30) -> Dict[str, Any]:
    """Get optimized dashboard statistics for franchise"""
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get loan statistics with efficient queries
        base_loan_query = LoanApplicationModel.objects.filter(
            franchise=franchise,
            created_at__date__range=[start_date, end_date]
        )
        
        loan_stats = base_loan_query.aggregate(
            total_applications=Count('form_id'),
            pending_applications=Count('form_id', filter=Q(status_name__isnull=True)),
            approved_applications=Count('form_id', filter=Q(status_name__status_name='Approved')),
            rejected_applications=Count('form_id', filter=Q(status_name__status_name='Rejected')),
            total_amount=Sum('loan_amount', default=0),
            average_amount=Avg('loan_amount', default=0)
        )
        
        # Get payment statistics
        payment_stats = Payment.objects.filter(
            franchise=franchise,
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total_payments=Count('id'),
            pending_payments=Count('id', filter=Q(status='pending')),
            completed_payments=Count('id', filter=Q(status='completed')),
            total_amount_paid=Sum('amount', default=0)
        )
        
        # Get recent activity
        recent_activity = get_franchise_recent_activity(franchise, days)
        
        # Get loan summary
        loan_summary = get_franchise_loan_summary(franchise)
        
        return {
            'loan_stats': loan_stats,
            'payment_stats': payment_stats,
            'loan_count': loan_stats['total_applications'],
            'recent_activity': recent_activity,
            'loan_summary': loan_summary,
            'period_days': days
        }
        
    except Exception as e:
        logger.error(f"Error getting franchise dashboard stats: {e}")
        return {
            'loan_stats': {},
            'payment_stats': {},
            'loan_count': 0,
            'recent_activity': [],
            'loan_summary': {},
            'period_days': days
        }


def get_franchise_recent_activity(franchise: Franchise, days: int = 7) -> List[Dict[str, Any]]:
    """Get recent activity for franchise user"""
    try:
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get recent loan applications
        recent_loans = LoanApplicationModel.objects.filter(
            franchise=franchise,
            created_at__range=[start_date, end_date]
        ).select_related('loan_name', 'status_name').order_by('-created_at')[:10]
        
        # Get recent payments
        recent_payments = Payment.objects.filter(
            franchise=franchise,
            created_at__range=[start_date, end_date]
        ).order_by('-created_at')[:5]
        
        activity = []
        
        # Add loan activities
        for loan in recent_loans:
            activity.append({
                'type': 'loan_application',
                'title': f'Loan application submitted',
                'description': f'Amount: ₹{loan.loan_amount}, Type: {loan.loan_name.loan_name}',
                'timestamp': loan.created_at,
                'status': loan.status_name.status_name if loan.status_name else 'Pending',
                'url': f'/loan-page/{loan.form_id}'
            })
        
        # Add payment activities
        for payment in recent_payments:
            activity.append({
                'type': 'payment',
                'title': f'Payment {payment.status}',
                'description': f'Transaction ID: {payment.transaction_id}, Amount: ₹{payment.amount}',
                'timestamp': payment.created_at,
                'status': payment.status,
                'url': f'/franchise_payment'
            })
        
        # Sort by timestamp
        activity.sort(key=lambda x: x['timestamp'], reverse=True)
        return activity[:15]  # Return top 15 activities
        
    except Exception as e:
        logger.error(f"Error getting franchise recent activity: {e}")
        return []


def get_franchise_loan_summary(franchise: Franchise) -> Dict[str, Any]:
    """Get loan summary for franchise"""
    try:
        # Get all loans for the franchise
        all_loans = LoanApplicationModel.objects.filter(franchise=franchise)
        
        # Get loan status distribution
        status_distribution = all_loans.values('status_name__status_name').annotate(
            count=Count('form_id')
        ).order_by('status_name__status_name')
        
        # Get loan amount distribution
        amount_distribution = all_loans.aggregate(
            min_amount=Sum('loan_amount', filter=Q(loan_amount__gt=0)),
            max_amount=Sum('loan_amount', filter=Q(loan_amount__gt=0)),
            total_amount=Sum('loan_amount', default=0),
            average_amount=Avg('loan_amount', default=0)
        )
        
        # Get loan type distribution
        loan_type_distribution = all_loans.values('loan_name__loan_name').annotate(
            count=Count('form_id'),
            total_amount=Sum('loan_amount', default=0)
        ).order_by('-count')
        
        return {
            'status_distribution': list(status_distribution),
            'amount_distribution': amount_distribution,
            'loan_type_distribution': list(loan_type_distribution),
            'total_loans': all_loans.count(),
            'active_loans': all_loans.filter(status_name__status_name='Approved').count()
        }
        
    except Exception as e:
        logger.error(f"Error getting franchise loan summary: {e}")
        return {}


def get_franchise_performance_metrics(franchise: Franchise, days: int = 30) -> Dict[str, Any]:
    """Get performance metrics for franchise"""
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get loan performance
        loan_performance = LoanApplicationModel.objects.filter(
            franchise=franchise,
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total_loans=Count('form_id'),
            approved_loans=Count('form_id', filter=Q(status_name__status_name='Approved')),
            rejected_loans=Count('form_id', filter=Q(status_name__status_name='Rejected')),
            pending_loans=Count('form_id', filter=Q(status_name__isnull=True)),
            total_amount=Sum('loan_amount', default=0)
        )
        
        # Calculate success rate
        total_processed = loan_performance['approved_loans'] + loan_performance['rejected_loans']
        success_rate = (loan_performance['approved_loans'] / total_processed * 100) if total_processed > 0 else 0
        
        # Get payment performance
        payment_performance = Payment.objects.filter(
            franchise=franchise,
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total_payments=Count('id'),
            completed_payments=Count('id', filter=Q(status='completed')),
            pending_payments=Count('id', filter=Q(status='pending')),
            total_amount_paid=Sum('amount', default=0)
        )
        
        # Calculate efficiency score
        efficiency_score = calculate_franchise_efficiency_score(franchise, days)
        
        return {
            'loan_performance': loan_performance,
            'payment_performance': payment_performance,
            'success_rate': round(success_rate, 2),
            'efficiency_score': efficiency_score,
            'period_days': days
        }
        
    except Exception as e:
        logger.error(f"Error getting franchise performance metrics: {e}")
        return {}


def calculate_franchise_efficiency_score(franchise: Franchise, days: int = 30) -> float:
    """Calculate efficiency score for franchise based on various metrics"""
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get base metrics
        total_loans = LoanApplicationModel.objects.filter(
            franchise=franchise,
            created_at__date__range=[start_date, end_date]
        ).count()
        
        approved_loans = LoanApplicationModel.objects.filter(
            franchise=franchise,
            created_at__date__range=[start_date, end_date],
            status_name__status_name='Approved'
        ).count()
        
        total_payments = Payment.objects.filter(
            franchise=franchise,
            created_at__date__range=[start_date, end_date],
            status='completed'
        ).count()
        
        # Calculate score components (0-100 scale)
        loan_efficiency = min(100, (total_loans / max(days, 1)) * 5)  # 5 loans per day = 100 points
        approval_rate = (approved_loans / max(total_loans, 1)) * 100
        payment_efficiency = min(100, (total_payments / max(days, 1)) * 10)  # 10 payments per day = 100 points
        
        # Weighted average
        efficiency_score = (loan_efficiency * 0.5 + approval_rate * 0.3 + payment_efficiency * 0.2)
        
        return round(efficiency_score, 2)
        
    except Exception as e:
        logger.error(f"Error calculating franchise efficiency score: {e}")
        return 0.0


def get_franchise_financial_summary(franchise: Franchise) -> Dict[str, Any]:
    """Get financial summary for franchise"""
    try:
        # Get loan amounts
        loan_amounts = LoanApplicationModel.objects.filter(
            franchise=franchise
        ).aggregate(
            total_requested=Sum('loan_amount', default=0),
            total_approved=Sum('loan_amount', filter=Q(status_name__status_name='Approved'), default=0),
            total_pending=Sum('loan_amount', filter=Q(status_name__isnull=True), default=0)
        )
        
        # Get payment amounts
        payment_amounts = Payment.objects.filter(
            franchise=franchise
        ).aggregate(
            total_paid=Sum('amount', filter=Q(status='completed'), default=0),
            total_pending=Sum('amount', filter=Q(status='pending'), default=0)
        )
        
        # Calculate net position
        net_position = (franchise.wallet_balance + 
                       payment_amounts['total_paid'] - 
                       loan_amounts['total_approved'])
        
        return {
            'loan_amounts': loan_amounts,
            'payment_amounts': payment_amounts,
            'wallet_balance': franchise.wallet_balance,
            'net_position': net_position,
            'credit_limit': getattr(franchise, 'credit_limit', 0),
            'available_credit': max(0, getattr(franchise, 'credit_limit', 0) - net_position)
        }
        
    except Exception as e:
        logger.error(f"Error getting franchise financial summary: {e}")
        return {}


def validate_franchise_action(franchise: Franchise, action: str, **kwargs) -> Dict[str, Any]:
    """Validate if franchise can perform a specific action"""
    try:
        validation_result = {
            'can_perform': True,
            'message': '',
            'restrictions': []
        }
        
        # Check if franchise is active
        if not franchise.is_active:
            validation_result['can_perform'] = False
            validation_result['message'] = 'Franchise account is inactive'
            validation_result['restrictions'].append('Account deactivated')
        
        # Check payment status for certain actions
        if action == 'apply_loan' and not franchise.payment_status:
            validation_result['can_perform'] = False
            validation_result['message'] = 'Payment verification required'
            validation_result['restrictions'].append('Payment not verified')
        
        elif action == 'withdraw_funds':
            if franchise.wallet_balance <= 0:
                validation_result['can_perform'] = False
                validation_result['message'] = 'Insufficient wallet balance'
                validation_result['restrictions'].append('Zero balance')
        
        elif action == 'update_profile':
            # Check if required fields are filled
            required_fields = ['aadhar', 'GST', 'pan', 'ac_no', 'ifsc_code']
            missing_fields = [field for field in required_fields if not getattr(franchise, field, None)]
            if missing_fields:
                validation_result['restrictions'].extend([f'Missing {field}' for field in missing_fields])
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating franchise action: {e}")
        return {
            'can_perform': False,
            'message': 'Validation error occurred',
            'restrictions': ['System error']
        }


def get_franchise_notifications(franchise: Franchise) -> List[Dict[str, Any]]:
    """Get notifications for franchise user"""
    try:
        notifications = []
        
        # Check for pending loan applications
        pending_loans = LoanApplicationModel.objects.filter(
            franchise=franchise,
            status_name__isnull=True
        ).count()
        
        if pending_loans > 0:
            notifications.append({
                'type': 'info',
                'title': 'Pending Loan Applications',
                'message': f'You have {pending_loans} loan application(s) pending approval',
                'priority': 'medium'
            })
        
        # Check for payment verification
        if not franchise.payment_status:
            notifications.append({
                'type': 'warning',
                'title': 'Payment Verification Required',
                'message': 'Please complete payment verification to access all features',
                'priority': 'high'
            })
        
        # Check for low wallet balance
        if franchise.wallet_balance < 1000:  # Threshold can be configurable
            notifications.append({
                'type': 'warning',
                'title': 'Low Wallet Balance',
                'message': f'Your wallet balance is ₹{franchise.wallet_balance}. Consider adding funds.',
                'priority': 'medium'
            })
        
        # Check for profile completion
        required_fields = ['aadhar', 'GST', 'pan', 'ac_no', 'ifsc_code']
        missing_fields = [field for field in required_fields if not getattr(franchise, field, None)]
        if missing_fields:
            notifications.append({
                'type': 'info',
                'title': 'Profile Incomplete',
                'message': f'Please complete your profile by adding: {", ".join(missing_fields)}',
                'priority': 'low'
            })
        
        return notifications
        
    except Exception as e:
        logger.error(f"Error getting franchise notifications: {e}")
        return []
