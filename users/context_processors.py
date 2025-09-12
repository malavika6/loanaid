from .utils import get_user_context 
from django.urls import reverse
from .models import AdminModel, StaffModel, Franchise
import time

def base_dropdown_items(request):
    dropdown_items = []
    user_profile = None
    username = request.session.get('username', 'User')

    # Get user profile based on user type
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    
    if user_id and user_type:
        try:
            if user_type == 'admin':
                user_profile = AdminModel.objects.get(admin_id=user_id)
                username = f"{user_profile.admin_first_name} {user_profile.admin_last_name or ''}".strip()
            elif user_type == 'staff':
                user_profile = StaffModel.objects.get(staff_id=user_id)
                username = f"{user_profile.first_name} {user_profile.last_name or ''}".strip()
            elif user_type == 'franchise':
                user_profile = Franchise.objects.get(franchise_id=user_id)
                username = user_profile.franchise_name
        except (AdminModel.DoesNotExist, StaffModel.DoesNotExist, Franchise.DoesNotExist):
            pass

    # Add Profile link for all user types
    if user_type == 'staff':
        dropdown_items.append({
            'url': reverse('update_profile'),
            'label': 'Profile',
            'icon': 'fas fa-user fa-sm fa-fw mr-2 text-gray-400'
        })
    elif user_type == 'franchise':
        dropdown_items.append({
            'url': reverse('profile'),
            'label': 'Profile',
            'icon': 'fas fa-user fa-sm fa-fw mr-2 text-gray-400'
        })
    elif user_type == 'admin':
        dropdown_items.append({
            'url': reverse('profile'),
            'label': 'Profile',
            'icon': 'fas fa-user fa-sm fa-fw mr-2 text-gray-400'
        })

    return {
        'dropdown_items': dropdown_items,
        'is_staff': user_type == 'staff',
        'username': username,
        'user_profile': user_profile,
    }

def sidebar_context(request):
    sidebar_menu, username = get_user_context(request)
    return {
        'sidebar_menu': sidebar_menu,
        'username': username,
        'timestamp': int(time.time()),
    }
