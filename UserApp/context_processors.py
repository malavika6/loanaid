from .utils import get_user_context 

def sidebar_context(request):
    sidebar_menu, username = get_user_context(request)
    return {
        'sidebar_menu': sidebar_menu,
        'username': username,
    }
