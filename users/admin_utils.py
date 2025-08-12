from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional

from .models import AdminModel, StaffModel, Franchise
from loan.models import LoanApplicationModel, StaffAssignmentModel

logger = logging.getLogger(__name__)


def get_admin_context(request) -> Dict[str, Any]:
    """
    Get common admin context for templates
    """
    try:
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or user_type != 'admin':
            return {}
        
        admin = AdminModel.objects.get(admin_id=user_id, is_active=True)
        
        # Get sidebar menu based on admin type
        sidebar_menu = get_admin_sidebar_menu(admin)
        
        # Get dropdown items
        dropdown_items = get_admin_dropdown_items(admin)
        
        return {
            'sidebar_menu': sidebar_menu,
            'dropdown_items': dropdown_items,
            'admin_user': admin,
            'is_superadmin': admin.is_superadmin,
        }
        
    except Exception as e:
        logger.error(f"Error getting admin context: {e}")
        return {}


def get_admin_sidebar_menu(admin: AdminModel) -> List[Dict[str, str]]:
    """
    Generate admin sidebar menu based on permissions
    """
    base_menu = [
        {'name': 'Dashboard', 'url': '/', 'icon': 'fas fa-tachometer-alt'},
    ]
    
    # Add menu items based on permissions
    if admin.is_superadmin or has_admin_permission(admin, 'can_manage_franchises'):
        base_menu.append({
            'name': 'Manage Franchises', 
            'url': '/list_franchise', 
            'icon': 'fas fa-building'
        })
    
    if admin.is_superadmin or has_admin_permission(admin, 'can_manage_staff'):
        base_menu.append({
            'name': 'Manage Staff', 
            'url': '/list_staff', 
            'icon': 'fas fa-users'
        })
    
    if admin.is_superadmin or has_admin_permission(admin, 'can_manage_loans'):
        base_menu.append({
            'name': 'Add Loan', 
            'url': '/add-loan', 
            'icon': 'fas fa-plus-circle'
        })
    
    if admin.is_superadmin:
        base_menu.extend([
            {
                'name': 'System Settings', 
                'url': '/admin/settings', 
                'icon': 'fas fa-cog'
            },
            {
                'name': 'Activity Logs', 
                'url': '/admin/activity-logs', 
                'icon': 'fas fa-history'
            },
        ])
    
    return base_menu


def get_admin_dropdown_items(admin: AdminModel) -> List[Dict[str, str]]:
    """
    Generate admin dropdown menu items
    """
    items = [
        {
            'label': 'Profile', 
            'url': '/admin/profile', 
            'icon': 'fas fa-user'
        },
        {
            'label': 'Settings', 
            'url': '/admin/settings', 
            'icon': 'fas fa-cog'
        },
    ]
    
    if admin.is_superadmin:
        items.append({
            'label': 'System Admin', 
            'url': '/admin/system', 
            'icon': 'fas fa-shield-alt'
        })
    
    items.append({
        'label': 'Logout', 
        'url': '/logout', 
        'icon': 'fas fa-sign-out-alt'
    })
    
    return items


def has_admin_permission(admin: AdminModel, permission: str) -> bool:
    """
    Check if admin has specific permission
    """
    permissions = get_admin_permissions(admin)
    return permissions.get(permission, False)


def get_admin_permissions(admin: AdminModel) -> Dict[str, bool]:
    """
    Get admin permissions dictionary
    """
    return {
        'can_manage_staff': True,
        'can_manage_franchises': True,
        'can_manage_loans': True,
        'can_view_reports': True,
        'can_delete_records': admin.is_superadmin,
        'can_manage_system': admin.is_superadmin,
        'can_manage_admins': admin.is_superadmin,
        'can_view_activity_logs': admin.is_superadmin,
    }


def get_dashboard_statistics(admin: AdminModel, days: int = 30) -> Dict[str, Any]:
    """
    Get comprehensive dashboard statistics
    """
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Base queryset for loans
        base_loan_query = LoanApplicationModel.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        
        # Filter based on admin type
        if not admin.is_superadmin:
            # For regular admins, only show assigned data
            base_loan_query = base_loan_query.filter(franchise__staff=admin)
        
        # Loan statistics
        loan_stats = base_loan_query.aggregate(
            total_applications=Count('form_id'),
            pending_applications=Count('form_id', filter=Q(status_name__isnull=True)),
            approved_applications=Count('form_id', filter=Q(status_name__status_name='Approved')),
            rejected_applications=Count('form_id', filter=Q(status_name__status_name='Rejected')),
            total_amount=Sum('loan_amount', default=0)
        )
        
        # Franchise statistics
        franchise_query = Franchise.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        if not admin.is_superadmin:
            franchise_query = franchise_query.filter(staff=admin)
        
        franchise_stats = franchise_query.aggregate(
            total_franchises=Count('franchise_id'),
            active_franchises=Count('franchise_id', filter=Q(is_active=True)),
            pending_payments=Count('franchise_id', filter=Q(payment_status=False))
        )
        
        # Staff statistics
        staff_query = StaffModel.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        if not admin.is_superadmin:
            staff_query = staff_query.filter(staff=admin)
        
        staff_stats = staff_query.aggregate(
            total_staff=Count('staff_id'),
            active_staff=Count('staff_id', filter=Q(is_active=True))
        )
        
        # Recent activity
        recent_loans = base_loan_query.select_related(
            'franchise', 'status_name'
        ).order_by('-created_at')[:10]
        
        return {
            'loan_stats': loan_stats,
            'franchise_stats': franchise_stats,
            'staff_stats': staff_stats,
            'recent_loans': recent_loans,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard statistics: {e}")
        return {}


def send_staff_credentials_email(staff_id: int, plain_password: str) -> bool:
    """
    Send staff credentials email (can be made async with Celery)
    """
    try:
        staff = StaffModel.objects.get(pk=staff_id)
        
        subject = "Staff Account Created - Loan Aid"
        message = f"""
Hello {staff.get_full_name()},

Your staff account has been created successfully!

Account Details:
- Employee ID: {staff.employee_id}
- Email: {staff.email}
- Password: {plain_password}

Please log in and change your password after first login.

Login URL: {settings.SITE_URL}/login

Regards,
Admin Team
Loan Aid
        """.strip()
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[staff.email],
            fail_silently=False,
        )
        
        logger.info(f"Staff credentials email sent to {staff.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending staff credentials email: {e}")
        return False


def get_admin_activity_summary(admin: AdminModel, days: int = 7) -> Dict[str, Any]:
    """
    Get admin activity summary for the specified period
    """
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get loans created/updated by this admin
        loan_activities = LoanApplicationModel.objects.filter(
            Q(created_at__date__range=[start_date, end_date]) |
            Q(updated_at__date__range=[start_date, end_date])
        )
        
        if not admin.is_superadmin:
            loan_activities = loan_activities.filter(franchise__staff=admin)
        
        # Get staff changes
        staff_changes = StaffModel.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        
        if not admin.is_superadmin:
            staff_changes = staff_changes.filter(staff=admin)
        
        # Get franchise changes
        franchise_changes = Franchise.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        
        if not admin.is_superadmin:
            franchise_changes = franchise_changes.filter(staff=admin)
        
        return {
            'loan_activities': loan_activities.count(),
            'staff_changes': staff_changes.count(),
            'franchise_changes': franchise_changes.count(),
            'total_activities': (
                loan_activities.count() + 
                staff_changes.count() + 
                franchise_changes.count()
            ),
            'period_days': days
        }
        
    except Exception as e:
        logger.error(f"Error getting admin activity summary: {e}")
        return {}


def validate_admin_action(admin: AdminModel, action: str, target_object=None) -> Dict[str, Any]:
    """
    Validate if admin can perform specific action
    """
    try:
        permissions = get_admin_permissions(admin)
        
        # Check basic permission
        if not permissions.get(action, False):
            return {
                'allowed': False,
                'reason': f'Permission denied: {action} not allowed'
            }
        
        # Additional validation for specific actions
        if action == 'delete_staff' and target_object:
            # Check if staff has active assignments
            active_assignments = StaffAssignmentModel.objects.filter(
                staff_name=target_object
            ).exists()
            
            if active_assignments:
                return {
                    'allowed': False,
                    'reason': 'Cannot delete staff with active franchise assignments'
                }
        
        elif action == 'delete_franchise' and target_object:
            # Check if franchise has active loans
            active_loans = LoanApplicationModel.objects.filter(
                franchise=target_object
            ).exists()
            
            if active_loans:
                return {
                    'allowed': False,
                    'reason': 'Cannot delete franchise with active loan applications'
                }
        
        return {'allowed': True, 'reason': 'Action allowed'}
        
    except Exception as e:
        logger.error(f"Error validating admin action: {e}")
        return {
            'allowed': False,
            'reason': 'Error occurred during validation'
        }


def get_admin_performance_metrics(admin: AdminModel, period_days: int = 30) -> Dict[str, Any]:
    """
    Get admin performance metrics
    """
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=period_days)
        
        # Get loans processed by this admin
        processed_loans = LoanApplicationModel.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        
        if not admin.is_superadmin:
            processed_loans = processed_loans.filter(franchise__staff=admin)
        
        # Calculate metrics
        total_loans = processed_loans.count()
        approved_loans = processed_loans.filter(
            status_name__status_name='Approved'
        ).count()
        rejected_loans = processed_loans.filter(
            status_name__status_name='Rejected'
        ).count()
        pending_loans = total_loans - approved_loans - rejected_loans
        
        # Calculate approval rate
        approval_rate = (approved_loans / total_loans * 100) if total_loans > 0 else 0
        
        # Get average processing time
        completed_loans = processed_loans.exclude(status_name__isnull=True)
        if completed_loans.exists():
            avg_processing_time = completed_loans.aggregate(
                avg_time=Avg('updated_at' - 'created_at')
            )['avg_time']
        else:
            avg_processing_time = None
        
        return {
            'total_loans': total_loans,
            'approved_loans': approved_loans,
            'rejected_loans': rejected_loans,
            'pending_loans': pending_loans,
            'approval_rate': round(approval_rate, 2),
            'avg_processing_time': avg_processing_time,
            'period_days': period_days
        }
        
    except Exception as e:
        logger.error(f"Error getting admin performance metrics: {e}")
        return {}
