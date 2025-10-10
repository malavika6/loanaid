def send_staff_credentials_email(staff, password):
    """Stub for sending staff credentials email. Replace with actual logic as needed."""
    pass
def get_admin_context(request):
    """Stub for get_admin_context. Replace with actual logic as needed."""
    return {}
from django.core.cache import cache
from .models import AdminModel,Franchise,StaffModel
import logging
from django.urls import reverse
from typing import Dict, Any, List
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from loan.models import LoanApplicationModel

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('debug.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


def get_sidebar_menu(user_type, request=None):
    """
    Generate sidebar menu items based on user type.
    For franchises, check if profile is complete before showing menu.
    """
    # For franchises, check profile completion status
    if user_type == 'franchise' and request:
        franchise_id = request.session.get('franchise_id')
        if franchise_id:
            try:
                from .models import Franchise
                franchise = Franchise.objects.get(franchise_id=franchise_id)
                if not franchise.is_profile_complete():
                    # Profile not complete - return empty menu
                    return []
            except Franchise.DoesNotExist:
                return []
    
    # Check if the menu is cached
    cache_key = f"v5_sidebar_menu_{user_type}"
    menu = cache.get(cache_key)

    if menu is None:
        # Define menu items based on user type
        menu_config = {
            'admin': [
                {'name': 'Dashboard', 'url': reverse('home'), 'icon': 'fas fa-tachometer-alt'},
                {'name': 'Applications', 'url': reverse('all-application'), 'icon': 'fas fa-file-alt'},
                {'name': 'Staff List', 'url': reverse('list_staff'), 'icon': 'fas fa-users'},
                {'name': 'Assignments', 'url': reverse('staff_assignments'), 'icon': 'fas fa-tasks'},
                {'name': 'Wallet', 'url': reverse('wallet_manage'), 'icon': 'fas fa-wallet'},
                {'name': 'Banks', 'url': reverse('addbank'), 'icon': 'fas fa-university'},
                {'name': 'Franchises', 'url': reverse('list_franchise'), 'icon': 'fas fa-building'},
                {'name': 'Loan Types', 'url': reverse('addloan'), 'icon': 'fas fa-plus-circle'},
                {'name': 'Status', 'url': reverse('addstatus'), 'icon': 'fas fa-flag'},
                {'name': 'Logout', 'url': reverse('logout'), 'icon': 'fas fa-sign-out-alt'},
            ],
            'franchise': [
                {'name': 'Dashboard', 'url': reverse('home'), 'icon': 'fas fa-tachometer-alt'},
                {'name': 'Franchise List', 'url': reverse('franchise_list'), 'icon': 'fas fa-building'},
                {'name': 'Wallet', 'url': reverse('franchise_wallet'), 'icon': 'fas fa-wallet'},
                {'name': 'Loans', 'url': reverse('all-application'), 'icon': 'fas fa-file-alt'},
                {'name': 'Logout', 'url': reverse('logout'), 'icon': 'fas fa-sign-out-alt'},
            ],
            'staff': [
                {'name': 'Dashboard', 'url': reverse('home'), 'icon': 'fas fa-tachometer-alt'},
                {'name': 'Applications', 'url': reverse('all-application'), 'icon': 'fas fa-file-alt'},
                {'name': 'Wallet', 'url': reverse('wallet_manage'), 'icon': 'fas fa-wallet'},
                {'name': 'Banks', 'url': reverse('addbank'), 'icon': 'fas fa-university'},
                {'name': 'Franchises', 'url': reverse('list_franchise'), 'icon': 'fas fa-building'},
                {'name': 'Loan Types', 'url': reverse('addloan'), 'icon': 'fas fa-plus-circle'},
                {'name': 'Status', 'url': reverse('addstatus'), 'icon': 'fas fa-flag'},
                {'name': 'Logout', 'url': reverse('logout'), 'icon': 'fas fa-sign-out-alt'},
            ],
            # 'executive': [
            #     {'name': 'Dashboard', 'url': reverse('index', args=[1]), 'icon': 'fas fa-tachometer-alt'},
            #     {'name': 'Apply Loan', 'url': reverse('apply-loan'), 'icon': 'fas fa-file-signature'},
            #     {'name': 'List Loan', 'url': reverse('list-loan'), 'icon': 'fas fa-file-alt'},
            #     {'name': 'Profile', 'url': reverse('update_profile'), 'icon': 'fas fa-user'},
            # ],
        }

        # Fetch menu for the given user type
        menu = menu_config.get(user_type, [])

        # Cache the menu for future use
        cache.set(cache_key, menu, timeout=3600)  # Cache for 1 hour

    return menu

def get_user_context(request):
    """
    Utility function to fetch sidebar menu and username for the logged-in user.
    """
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    session_username = request.session.get('username')

    # Debug logs removed

    if not user_id or not user_type:
        # Debug logs removed
        return None, None

    username = None
    if user_type == 'admin':
        try:
            # Debug logs removed
            admin = AdminModel.objects.get(admin_id=user_id)
            username = f"{admin.admin_first_name} {admin.admin_last_name or ''}".strip()
            
        except AdminModel.DoesNotExist:
            print(f"Admin with ID {user_id} does not exist.")
            return None, None
    elif user_type == 'franchise':
        try:
            franchise = Franchise.objects.get(franchise_id=user_id)
            username = franchise.franchise_owner
        except Franchise.DoesNotExist:
            logger.error(f"Franchise with ID {user_id} does not exist.")
            return None, None
    elif user_type == 'staff':
        try:
            # Debug logs removed
            staff = StaffModel.objects.get(staff_id=user_id)
            username = f"{staff.first_name} {staff.last_name or ''}".strip()
            
        except StaffModel.DoesNotExist:
            print(f"Staff with ID {user_id} does not exist.")
            return None, None
    elif user_type == 'executive':
        # Executive functionality removed - UserModel was deleted
        logger.warning(f"Executive user type is no longer supported. User ID: {user_id}")
        return None, None

    # If username is still None, use session username as fallback
    if not username and session_username:
        username = session_username
        # Debug logs removed
    
    sidebar_menu = get_sidebar_menu(user_type, request)
    # Debug logs removed
    return sidebar_menu, username

# ============================================================================
# ADMIN UTILITIES
# ============================================================================

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
            'icon': 'fas fa-user fa-sm fa-fw mr-2 text-gray-400'
        },
        {
            'label': 'Settings', 
            'url': '/admin/settings', 
            'icon': 'fas fa-cog fa-sm fa-fw mr-2 text-gray-400'
        },
        {
            'label': 'Activity Log', 
            'url': '/admin/activity-logs', 
            'icon': 'fas fa-history fa-sm fa-fw mr-2 text-gray-400'
        },
    ]
    
    if admin.is_superadmin:
        items.append({
            'label': 'System Admin', 
            'url': '/admin/system', 
            'icon': 'fas fa-shield-alt fa-sm fa-fw mr-2 text-gray-400'
        })
    
    return items


def has_admin_permission(admin: AdminModel, permission: str) -> bool:
    """
    Check if admin has specific permission
    """
    if admin.is_superadmin:
        return True
    
    # Add permission checking logic here based on your admin model
    # For now, return False for non-superadmin users
    return False


def get_admin_dashboard_stats(admin: AdminModel, days: int = 30) -> Dict[str, Any]:
    """
    Get admin dashboard statistics
    """
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get franchise statistics
        franchise_stats = Franchise.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total_franchises=Count('franchise_id'),
            active_franchises=Count('franchise_id', filter=Q(is_active=True)),
            inactive_franchises=Count('franchise_id', filter=Q(is_active=False))
        )
        
        # Get staff statistics
        staff_stats = StaffModel.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total_staff=Count('staff_id'),
            active_staff=Count('staff_id', filter=Q(is_active=True)),
            inactive_staff=Count('staff_id', filter=Q(is_active=False))
        )
        
        # Get loan statistics
        loan_stats = LoanApplicationModel.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total_applications=Count('form_id'),
            pending_applications=Count('form_id', filter=Q(status_name__isnull=True)),
            approved_applications=Count('form_id', filter=Q(status_name__status_name='Approved')),
            rejected_applications=Count('form_id', filter=Q(status_name__status_name='Rejected'))
        )
        
        return {
            'franchise_stats': franchise_stats,
            'staff_stats': staff_stats,
            'loan_stats': loan_stats,
            'period_days': days
        }
        
    except Exception as e:
        logger.error(f"Error getting admin dashboard stats: {e}")
        return {}


def get_admin_recent_activity(admin: AdminModel, days: int = 7) -> List[Dict[str, Any]]:
    """
    Get recent admin activity
    """
    try:
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        activity = []
        
        # Get recent franchise registrations
        recent_franchises = Franchise.objects.filter(
            created_at__range=[start_date, end_date]
        ).order_by('-created_at')[:5]
        
        for franchise in recent_franchises:
            activity.append({
                'type': 'franchise_registration',
                'title': f'New franchise registered: {franchise.franchise_name}',
                'timestamp': franchise.created_at,
                'url': f'/franchise/{franchise.franchise_id}'
            })
        
        # Get recent staff registrations
        recent_staff = StaffModel.objects.filter(
            created_at__range=[start_date, end_date]
        ).order_by('-created_at')[:5]
        
        for staff in recent_staff:
            activity.append({
                'type': 'staff_registration',
                'title': f'New staff member: {staff.first_name} {staff.last_name}',
                'timestamp': staff.created_at,
                'url': f'/staff/{staff.staff_id}'
            })
        
        # Get recent loan applications
        recent_loans = LoanApplicationModel.objects.filter(
            created_at__range=[start_date, end_date]
        ).order_by('-created_at')[:5]
        
        for loan in recent_loans:
            activity.append({
                'type': 'loan_application',
                'title': f'New loan application: ₹{loan.loan_amount}',
                'timestamp': loan.created_at,
                'url': f'/loan/{loan.form_id}'
            })
        
        # Sort by timestamp
        activity.sort(key=lambda x: x['timestamp'], reverse=True)
        return activity[:10]
        
    except Exception as e:
        logger.error(f"Error getting admin recent activity: {e}")
        return []