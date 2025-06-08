from .utils import get_user_context 
from django.urls import reverse

def base_dropdown_items(request):
    dropdown_items = []

    if request.session.get('user_type') == 'staff':
        dropdown_items.append({
            'url': reverse('update_profile'),
            'label': 'Profile',
            'icon': 'fas fa-user fa-sm fa-fw mr-2 text-gray-400'
        })

    dropdown_items.append({
        'url': reverse('logout'),
        'label': 'Logout',
        'icon': 'fas fa-sign-out-alt fa-sm fa-fw mr-2 text-gray-400'
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
    }
