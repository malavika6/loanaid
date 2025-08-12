from typing import Dict, Any, List
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from datetime import timedelta
import logging

from .models import StaffModel, Franchise
from loan.models import LoanApplicationModel, StaffAssignmentModel

logger = logging.getLogger(__name__)


def get_staff_context(staff: StaffModel) -> Dict[str, Any]:
    """Get common context for staff templates"""
    try:
        return {
            'username': staff.get_full_name(),
            'staff': staff,
            'sidebar_menu': get_staff_sidebar_menu(),
            'dropdown_items': get_staff_dropdown_items(),
        }
    except Exception as e:
        logger.error(f"Error getting staff context: {e}")
        return {}


def get_staff_sidebar_menu() -> List[Dict[str, str]]:
    """Get sidebar menu items for staff users"""
    return [
        {'name': 'Dashboard', 'url': '/dashboard', 'icon': 'fas fa-tachometer-alt'},
        {'name': 'My Assignments', 'url': '/staff_assignments', 'icon': 'fas fa-tasks'},
        {'name': 'My Franchises', 'url': '/my_franchises', 'icon': 'fas fa-building'},
        {'name': 'My Loans', 'url': '/my_loans', 'icon': 'fas fa-money-bill-wave'},
        {'name': 'Profile', 'url': '/profile', 'icon': 'fas fa-user'},
        {'name': 'Reports', 'url': '/staff_reports', 'icon': 'fas fa-chart-bar'},
    ]


def get_staff_dropdown_items() -> List[Dict[str, str]]:
    """Get dropdown menu items for staff users"""
    return [
        {'name': 'Profile Settings', 'url': '/profile', 'icon': 'fas fa-cog'},
        {'name': 'Change Password', 'url': '/change_password', 'icon': 'fas fa-key'},
        {'name': 'Activity Log', 'url': '/activity_log', 'icon': 'fas fa-history'},
        {'name': 'Help & Support', 'url': '/support', 'icon': 'fas fa-question-circle'},
        {'name': 'Logout', 'url': '/logout', 'icon': 'fas fa-sign-out-alt'},
    ]


def get_staff_dashboard_stats(staff: StaffModel, days: int = 30) -> Dict[str, Any]:
    """Get optimized dashboard statistics for staff"""
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get assigned franchises
        assigned_franchises = Franchise.objects.filter(
            staffassignmentmodel__staff_name=staff
        )
        
        # Get loan statistics with efficient queries
        base_loan_query = LoanApplicationModel.objects.filter(
            Q(assigned_to=staff) | Q(franchise__in=assigned_franchises),
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
        
        # Get franchise statistics
        franchise_stats = assigned_franchises.aggregate(
            total_franchises=Count('franchise_id'),
            active_franchises=Count('franchise_id', filter=Q(is_active=True)),
            payment_verified=Count('franchise_id', filter=Q(payment_status=True))
        )
        
        # Get recent activity
        recent_activity = get_staff_recent_activity(staff, days)
        
        # Get performance metrics
        performance_metrics = get_staff_performance_metrics(staff, days)
        
        return {
            'loan_stats': loan_stats,
            'franchise_stats': franchise_stats,
            'assigned_franchise_count': franchise_stats['total_franchises'],
            'franchise_loan_count': loan_stats['total_applications'],
            'recent_activity': recent_activity,
            'performance_metrics': performance_metrics,
            'period_days': days
        }
        
    except Exception as e:
        logger.error(f"Error getting staff dashboard stats: {e}")
        return {
            'loan_stats': {},
            'franchise_stats': {},
            'assigned_franchise_count': 0,
            'franchise_loan_count': 0,
            'recent_activity': [],
            'performance_metrics': {},
            'period_days': days
        }


def get_staff_recent_activity(staff: StaffModel, days: int = 7) -> List[Dict[str, Any]]:
    """Get recent activity for staff user"""
    try:
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get recent loan applications
        recent_loans = LoanApplicationModel.objects.filter(
            Q(assigned_to=staff) | Q(franchise__staffassignmentmodel__staff_name=staff),
            created_at__range=[start_date, end_date]
        ).select_related('franchise', 'loan_name', 'status_name').order_by('-created_at')[:10]
        
        # Get recent franchise assignments
        recent_assignments = StaffAssignmentModel.objects.filter(
            staff_name=staff,
            created_at__range=[start_date, end_date]
        ).select_related('assigned_by').prefetch_related('franchise_name').order_by('-created_at')[:5]
        
        activity = []
        
        # Add loan activities
        for loan in recent_loans:
            activity.append({
                'type': 'loan_application',
                'title': f'New loan application from {loan.franchise.franchise_name}',
                'description': f'Amount: ₹{loan.loan_amount}, Type: {loan.loan_name.loan_name}',
                'timestamp': loan.created_at,
                'status': loan.status_name.status_name if loan.status_name else 'Pending',
                'url': f'/loan-page/{loan.form_id}'
            })
        
        # Add assignment activities
        for assignment in recent_assignments:
            for franchise in assignment.franchise_name.all():
                activity.append({
                    'type': 'franchise_assignment',
                    'title': f'Assigned to {franchise.franchise_name}',
                    'description': f'Assigned by {assignment.assigned_by.get_full_name()}',
                    'timestamp': assignment.created_at,
                    'status': 'Active',
                    'url': f'/franchise/{franchise.franchise_id}'
                })
        
        # Sort by timestamp
        activity.sort(key=lambda x: x['timestamp'], reverse=True)
        return activity[:15]  # Return top 15 activities
        
    except Exception as e:
        logger.error(f"Error getting staff recent activity: {e}")
        return []


def get_staff_performance_metrics(staff: StaffModel, days: int = 30) -> Dict[str, Any]:
    """Get performance metrics for staff user"""
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get loan performance
        loan_performance = LoanApplicationModel.objects.filter(
            Q(assigned_to=staff) | Q(franchise__staffassignmentmodel__staff_name=staff),
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
        
        # Get franchise performance
        franchise_performance = Franchise.objects.filter(
            staffassignmentmodel__staff_name=staff,
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            new_franchises=Count('franchise_id'),
            active_franchises=Count('franchise_id', filter=Q(is_active=True)),
            payment_verified=Count('franchise_id', filter=Q(payment_status=True))
        )
        
        return {
            'loan_performance': loan_performance,
            'franchise_performance': franchise_performance,
            'success_rate': round(success_rate, 2),
            'efficiency_score': calculate_efficiency_score(staff, days),
            'period_days': days
        }
        
    except Exception as e:
        logger.error(f"Error getting staff performance metrics: {e}")
        return {}


def calculate_efficiency_score(staff: StaffModel, days: int = 30) -> float:
    """Calculate efficiency score for staff based on various metrics"""
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get base metrics
        total_loans = LoanApplicationModel.objects.filter(
            Q(assigned_to=staff) | Q(franchise__staffassignmentmodel__staff_name=staff),
            created_at__date__range=[start_date, end_date]
        ).count()
        
        approved_loans = LoanApplicationModel.objects.filter(
            Q(assigned_to=staff) | Q(franchise__staffassignmentmodel__staff_name=staff),
            created_at__date__range=[start_date, end_date],
            status_name__status_name='Approved'
        ).count()
        
        total_franchises = Franchise.objects.filter(
            staffassignmentmodel__staff_name=staff,
            created_at__date__range=[start_date, end_date]
        ).count()
        
        # Calculate score components (0-100 scale)
        loan_efficiency = min(100, (total_loans / max(days, 1)) * 10)  # 10 loans per day = 100 points
        approval_rate = (approved_loans / max(total_loans, 1)) * 100
        franchise_efficiency = min(100, (total_franchises / max(days, 1)) * 20)  # 5 franchises per month = 100 points
        
        # Weighted average
        efficiency_score = (loan_efficiency * 0.4 + approval_rate * 0.4 + franchise_efficiency * 0.2)
        
        return round(efficiency_score, 2)
        
    except Exception as e:
        logger.error(f"Error calculating efficiency score: {e}")
        return 0.0


def get_staff_assignment_summary(staff: StaffModel) -> Dict[str, Any]:
    """Get summary of staff assignments"""
    try:
        assignments = StaffAssignmentModel.objects.filter(
            staff_name=staff
        ).select_related('assigned_by').prefetch_related('franchise_name')
        
        assignment_summary = {
            'total_assignments': assignments.count(),
            'assigned_franchises': [],
            'assigned_by': None,
            'last_assignment_date': None
        }
        
        if assignments.exists():
            latest_assignment = assignments.order_by('-created_at').first()
            assignment_summary['assigned_by'] = latest_assignment.assigned_by
            assignment_summary['last_assignment_date'] = latest_assignment.created_at
            
            # Get unique franchises
            unique_franchises = set()
            for assignment in assignments:
                unique_franchises.update(assignment.franchise_name.all())
            
            assignment_summary['assigned_franchises'] = list(unique_franchises)
        
        return assignment_summary
        
    except Exception as e:
        logger.error(f"Error getting staff assignment summary: {e}")
        return {}


def validate_staff_action(staff: StaffModel, action: str, **kwargs) -> Dict[str, Any]:
    """Validate if staff can perform a specific action"""
    try:
        validation_result = {
            'can_perform': True,
            'message': '',
            'restrictions': []
        }
        
        # Check if staff is active
        if not hasattr(staff, 'is_active') or not staff.is_active:
            validation_result['can_perform'] = False
            validation_result['message'] = 'Staff account is inactive'
            validation_result['restrictions'].append('Account deactivated')
        
        # Check action-specific permissions
        if action == 'create_loan':
            # Check if staff can create loans
            if not hasattr(staff, 'can_create_loans') or not staff.can_create_loans:
                validation_result['can_perform'] = False
                validation_result['restrictions'].append('Loan creation not permitted')
        
        elif action == 'assign_franchise':
            # Check if staff can assign franchises
            if not hasattr(staff, 'can_assign_franchises') or not staff.can_assign_franchises:
                validation_result['can_perform'] = False
                validation_result['restrictions'].append('Franchise assignment not permitted')
        
        elif action == 'view_reports':
            # Check if staff can view reports
            if not hasattr(staff, 'can_view_reports') or not staff.can_view_reports:
                validation_result['can_perform'] = False
                validation_result['restrictions'].append('Report access not permitted')
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating staff action: {e}")
        return {
            'can_perform': False,
            'message': 'Validation error occurred',
            'restrictions': ['System error']
        }
