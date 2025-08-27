from django.core.cache import cache
from .models import AdminModel,Franchise,StaffModel
import logging
from django.urls import reverse

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('debug.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


def get_sidebar_menu(user_type):
    """
    Generate sidebar menu items based on user type.
    """
    # Check if the menu is cached
    cache_key = f"sidebar_menu_{user_type}"
    menu = cache.get(cache_key)

    if menu is None:
        # Define menu items based on user type
        menu_config = {
            'admin': [
                {'name': 'Dashboard', 'url': reverse('home'), 'icon': 'fas fa-tachometer-alt'},
                {'name': 'Applications', 'url': reverse('all-application'), 'icon': 'fas fa-file-alt'},
                {'name': 'Staffs', 'url': reverse('list_staff'), 'icon': 'fas fa-users'},
                {'name': 'Staff Assignment', 'url': reverse('assign_staff'), 'icon': 'fas fa-user-plus'},
                {'name': 'Assignments', 'url': reverse('staff_assignments'), 'icon': 'fas fa-tasks'},
                {'name': 'Banks', 'url': reverse('addbank'), 'icon': 'fas fa-university'},
                {'name': 'Franchises', 'url': reverse('list_franchise'), 'icon': 'fas fa-building'},
                {'name': 'Loan Types', 'url': reverse('addloan'), 'icon': 'fas fa-plus-circle'},
                {'name': 'Status', 'url': reverse('addstatus'), 'icon': 'fas fa-flag'},
            ],
            'franchise': [
                {'name': 'Dashboard', 'url': reverse('franchise_dashboard'), 'icon': 'fas fa-tachometer-alt'},
                {'name': 'Apply Loan', 'url': reverse('form'), 'icon': 'fas fa-file-signature'},
                {'name': 'Loans', 'url': reverse('all-application'), 'icon': 'fas fa-file-alt'},
                # {'name': 'Profile', 'url': reverse('profile'), 'icon': 'fas fa-user'},
            ],
            'staff': [
                {'name': 'Dashboard', 'url': reverse('home'), 'icon': 'fas fa-tachometer-alt'},
                {'name': 'Application', 'url': reverse('form'), 'icon': 'fas fa-file-signature'},
                {'name': 'Applications', 'url': reverse('all-application'), 'icon': 'fas fa-file-alt'},
                {'name': 'Banks', 'url': reverse('addbank'), 'icon': 'fas fa-university'},
                {'name': 'Franchises', 'url': reverse('list_franchise'), 'icon': 'fas fa-building'},
                {'name': 'Loan Types', 'url': reverse('addloan'), 'icon': 'fas fa-plus-circle'},
                {'name': 'Status', 'url': reverse('addstatus'), 'icon': 'fas fa-flag'},
                # {'name': 'Profile Update', 'url': reverse('update_profile'), 'icon': 'fas fa-user-edit'},
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

    print(f"=== DEBUG: get_user_context ===")
    print(f"user_id: {user_id}, user_type: {user_type}, session_username: {session_username}")

    if not user_id or not user_type:
        print("Missing user_id or user_type in session.")
        return None, None

    username = None
    if user_type == 'admin':
        try:
            print(f"Looking for admin with admin_id: {user_id}")
            admin = AdminModel.objects.get(admin_id=user_id)
            username = f"{admin.admin_first_name} {admin.admin_last_name or ''}".strip()
            print(f"Found admin: {username}")
        except AdminModel.DoesNotExist:
            print(f"Admin with ID {user_id} does not exist.")
            return None, None
    elif user_type == 'franchise':
        try:
            franchise = Franchise.objects.get(franchise_id=user_id)
            username = franchise.franchise_name
        except Franchise.DoesNotExist:
            logger.error(f"Franchise with ID {user_id} does not exist.")
            return None, None
    elif user_type == 'staff':
        try:
            print(f"Looking for staff with staff_id: {user_id}")
            staff = StaffModel.objects.get(staff_id=user_id)
            username = f"{staff.first_name} {staff.last_name or ''}".strip()
            print(f"Found staff: {username}")
        except StaffModel.DoesNotExist:
            print(f"Staff with ID {user_id} does not exist.")
            return None, None
    elif user_type == 'executive':
        try:
            executive = UserModel.objects.get(user_id=user_id)
            username = executive.name
        except UserModel.DoesNotExist:
            logger.error(f"Executive with ID {user_id} does not exist.")
            return None, None

    # If username is still None, use session username as fallback
    if not username and session_username:
        username = session_username
        print(f"Using session username as fallback: {username}")
    
    sidebar_menu = get_sidebar_menu(user_type)
    print(f"Sidebar menu for user_type {user_type}: {len(sidebar_menu) if sidebar_menu else 0} items")
    print(f"=== END DEBUG: get_user_context, returning username: '{username}' ===")
    return sidebar_menu, username