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
                {'name': 'Dashboard', 'url': reverse('home')},  # Pass a valid user_id (e.g., 1)
                {'name': 'Application', 'url': reverse('form')},
                {'name': 'All Applications', 'url': reverse('all-application')},
                {'name': 'Create Staff', 'url': reverse('create_staff')},
                {'name': 'All Staffs', 'url': reverse('list_staff')},
                {'name': 'Staff Assignment', 'url': reverse('assign_staff')},
                {'name': 'All Assignment', 'url': reverse('staff_assignments')},
                {'name': 'Add Bank', 'url': reverse('addbank')},
                {'name': 'Add Franchise', 'url': reverse('add_franchise')},
                {'name': 'List Franchise', 'url': reverse('list_franchise')},
                {'name': 'Add Loan', 'url': reverse('addloan')},
                {'name': 'Add Status', 'url': reverse('addstatus')},
            ],
            'franchise': [
                {'name': 'Dashboard', 'url': reverse('franchise_dashboard')},
                {'name': 'Apply Loan', 'url': reverse('form')},
                {'name': 'List Loan', 'url': reverse('all-application')},
                # {'name': 'Profile', 'url': reverse('profile')},
            ],
            'staff': [
                {'name': 'Dashboard', 'url': reverse('home')},
                {'name': 'Application', 'url': reverse('form')},
                {'name': 'All Applications', 'url': reverse('all-application')},
                {'name': 'Add Bank', 'url': reverse('addbank')},
                {'name': 'Add Franchise', 'url': reverse('add_franchise')},
                {'name': 'List Franchise', 'url': reverse('list_franchise')},
                {'name': 'Add Loan', 'url': reverse('addloan')},
                {'name': 'Add Status', 'url': reverse('addstatus')},
                # {'name': 'Profile Update', 'url': reverse('update_profile')},
            ],
            # 'executive': [
            #     {'name': 'Dashboard', 'url': reverse('index', args=[1])},  # Pass a valid user_id (e.g., 1)
            #     {'name': 'Apply Loan', 'url': reverse('apply-loan')},
            #     {'name': 'List Loan', 'url': reverse('list-loan')},
            #     {'name': 'Profile', 'url': reverse('update_profile')},
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

    logger.debug(f"Session user_id: {user_id}, user_type: {user_type}")

    if not user_id or not user_type:
        logger.warning("Missing user_id or user_type in session.")
        return None, None

    username = None
    if user_type == 'admin':
        try:
            admin = AdminModel.objects.get(admin_id=user_id)
            username = f"{admin.admin_first_name} {admin.admin_last_name or ''}".strip()
        except AdminModel.DoesNotExist:
            logger.error(f"Admin with ID {user_id} does not exist.")
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
            staff = StaffModel.objects.get(staff_id=user_id)
            username = f"{staff.first_name} {staff.last_name or ''}".strip()
        except StaffModel.DoesNotExist:
            logger.error(f"Staff with ID {user_id} does not exist.")
            return None, None
    elif user_type == 'executive':
        try:
            executive = UserModel.objects.get(user_id=user_id)
            username = executive.name
        except UserModel.DoesNotExist:
            logger.error(f"Executive with ID {user_id} does not exist.")
            return None, None

    sidebar_menu = get_sidebar_menu(user_type)
    logger.debug(f"Sidebar menu for user_type {user_type}: {sidebar_menu}")
    return sidebar_menu, username