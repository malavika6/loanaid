from .utils import get_user_context 
from django.urls import reverse
import time

def base_dropdown_items(request):
    dropdown_items = []

    # Add Profile link for all user types
    if request.session.get('user_type') == 'staff':
        dropdown_items.append({
            'url': reverse('update_profile'),
            'label': 'Profile',
            'icon': 'fas fa-user fa-sm fa-fw mr-2 text-gray-400'
        })
    elif request.session.get('user_type') == 'franchise':
        dropdown_items.append({
            'url': reverse('profile'),
            'label': 'Profile',
            'icon': 'fas fa-user fa-sm fa-fw mr-2 text-gray-400'
        })
    elif request.session.get('user_type') == 'admin':
        dropdown_items.append({
            'url': reverse('profile'),
            'label': 'Profile',
            'icon': 'fas fa-user fa-sm fa-fw mr-2 text-gray-400'
        })

    return {
        'dropdown_items': dropdown_items,
        'is_staff': request.session.get('user_type') == 'staff',
        'username': request.session.get('username'),
    }

def sidebar_context(request):
    sidebar_menu, username = get_user_context(request)
    return {
        'sidebar_menu': sidebar_menu,
        'username': username,
        'timestamp': int(time.time()),
    }
