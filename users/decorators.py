from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import AdminModel, StaffModel, Franchise
import logging

logger = logging.getLogger(__name__)


def admin_required(view_func):
    """Decorator to check if user is an active admin"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or user_type != 'admin':
            messages.error(request, "Access denied. Admin privileges required.")
            return redirect('/login')
        
        try:
            admin = AdminModel.objects.get(admin_id=user_id, is_active=True)
            if not admin:
                messages.error(request, "Admin account is inactive.")
                return redirect('/login')
            
            request.admin_user = admin
            return view_func(request, *args, **kwargs)
            
        except AdminModel.DoesNotExist:
            messages.error(request, "Admin account not found.")
            return redirect('/login')
        except Exception as e:
            logger.error(f"Error in admin_required decorator: {e}")
            messages.error(request, "Authentication error occurred.")
            return redirect('/login')
    return wrapper


def superadmin_required(view_func):
    """Decorator to check if user is a superadmin"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or user_type != 'admin':
            messages.error(request, "Access denied. Superadmin privileges required.")
            return redirect('/login')
        
        try:
            admin = AdminModel.objects.get(admin_id=user_id, is_active=True, is_superadmin=True)
            if not admin:
                messages.error(request, "Superadmin privileges required.")
                return redirect('/login')
            
            request.admin_user = admin
            return view_func(request, *args, **kwargs)
            
        except AdminModel.DoesNotExist:
            messages.error(request, "Superadmin account not found.")
            return redirect('/login')
        except Exception as e:
            logger.error(f"Error in superadmin_required decorator: {e}")
            messages.error(request, "Authentication error occurred.")
            return redirect('/login')
    return wrapper


def admin_permission_required(permission):
    """Decorator to check specific admin permissions"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_id = request.session.get('user_id')
            user_type = request.session.get('user_type')
            
            if not user_id or user_type != 'admin':
                messages.error(request, "Access denied. Admin privileges required.")
                return redirect('/login')
            
            try:
                admin = AdminModel.objects.get(admin_id=user_id, is_active=True)
                if not admin:
                    messages.error(request, "Admin account is inactive.")
                    return redirect('/login')
                
                # Check specific permission
                if not hasattr(admin, permission) or not getattr(admin, permission):
                    messages.error(request, f"Permission denied. {permission} required.")
                    return redirect('/login')
                
                request.admin_user = admin
                return view_func(request, *args, **kwargs)
                
            except AdminModel.DoesNotExist:
                messages.error(request, "Admin account not found.")
                return redirect('/login')
            except Exception as e:
                logger.error(f"Error in admin_permission_required decorator: {e}")
                messages.error(request, "Authentication error occurred.")
                return redirect('/login')
        return wrapper
    return decorator


def get_admin_permissions(admin):
    """
    Get admin permissions based on role
    """
    permissions = {
        'can_manage_staff': True,
        'can_manage_franchises': True,
        'can_manage_loans': True,
        'can_view_reports': True,
        'can_delete_records': admin.is_superadmin,
        'can_manage_system': admin.is_superadmin,
        'can_manage_admins': admin.is_superadmin,
        'can_view_activity_logs': admin.is_superadmin,
    }
    return permissions


def ajax_admin_required(view_func):
    """Decorator for AJAX views requiring admin access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or user_type != 'admin':
            return JsonResponse({'error': 'Access denied. Admin privileges required.'}, status=403)
        
        try:
            admin = AdminModel.objects.get(admin_id=user_id, is_active=True)
            if not admin:
                return JsonResponse({'error': 'Admin account is inactive.'}, status=403)
            
            request.admin_user = admin
            return view_func(request, *args, **kwargs)
            
        except AdminModel.DoesNotExist:
            return JsonResponse({'error': 'Admin account not found.'}, status=403)
        except Exception as e:
            logger.error(f"Error in ajax_admin_required decorator: {e}")
            return JsonResponse({'error': 'Authentication error occurred.'}, status=500)
    return wrapper


def staff_required(view_func):
    """Decorator to check if user is an active staff member"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or user_type != 'staff':
            messages.error(request, "Access denied. Staff privileges required.")
            return redirect('/login')
        
        try:
            staff = StaffModel.objects.get(staff_id=user_id)
            if not staff:
                messages.error(request, "Staff account not found.")
                return redirect('/login')
            
            # Check if staff is active (if the field exists)
            if hasattr(staff, 'is_active') and not staff.is_active:
                messages.error(request, "Staff account is inactive.")
                return redirect('/login')
            
            request.staff_user = staff
            return view_func(request, *args, **kwargs)
            
        except StaffModel.DoesNotExist:
            messages.error(request, "Staff account not found.")
            return redirect('/login')
        except Exception as e:
            logger.error(f"Error in staff_required decorator: {e}")
            messages.error(request, "Authentication error occurred.")
            return redirect('/login')
    return wrapper


def staff_permission_required(permission):
    """Decorator to check specific staff permissions"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_id = request.session.get('user_id')
            user_type = request.session.get('user_type')
            
            if not user_id or user_type != 'staff':
                messages.error(request, "Access denied. Staff privileges required.")
                return redirect('/login')
            
            try:
                staff = StaffModel.objects.get(staff_id=user_id)
                if not staff:
                    messages.error(request, "Staff account not found.")
                    return redirect('/login')
                
                # Check if staff is active
                if hasattr(staff, 'is_active') and not staff.is_active:
                    messages.error(request, "Staff account is inactive.")
                    return redirect('/login')
                
                # Check specific permission
                if not hasattr(staff, permission) or not getattr(staff, permission):
                    messages.error(request, f"Permission denied. {permission} required.")
                    return redirect('/login')
                
                request.staff_user = staff
                return view_func(request, *args, **kwargs)
                
            except StaffModel.DoesNotExist:
                messages.error(request, "Staff account not found.")
                return redirect('/login')
            except Exception as e:
                logger.error(f"Error in staff_permission_required decorator: {e}")
                messages.error(request, "Authentication error occurred.")
                return redirect('/login')
        return wrapper
    return decorator


def franchise_required(view_func):
    """Decorator to check if user is an active franchise"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        franchise_id = request.session.get('franchise_id')
        user_type = request.session.get('user_type')
        
        if not franchise_id or user_type != 'franchise':
            messages.error(request, "Access denied. Franchise privileges required.")
            return redirect('/login')
        
        try:
            franchise = Franchise.objects.get(franchise_id=franchise_id, is_active=True)
            if not franchise:
                messages.error(request, "Franchise account is inactive.")
                return redirect('/login')
            
            # Check payment status for certain operations
            if not franchise.payment_status:
                messages.warning(request, "Payment verification required for full access.")
                # Allow access but with limited functionality
            
            request.franchise_user = franchise
            return view_func(request, *args, **kwargs)
            
        except Franchise.DoesNotExist:
            messages.error(request, "Franchise account not found.")
            return redirect('/login')
        except Exception as e:
            logger.error(f"Error in franchise_required decorator: {e}")
            messages.error(request, "Authentication error occurred.")
            return redirect('/login')
    return wrapper


def franchise_payment_verified(view_func):
    """Decorator to check if franchise payment is verified"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        franchise_id = request.session.get('franchise_id')
        user_type = request.session.get('user_type')
        
        if not franchise_id or user_type != 'franchise':
            messages.error(request, "Access denied. Franchise privileges required.")
            return redirect('/login')
        
        try:
            franchise = Franchise.objects.get(franchise_id=franchise_id, is_active=True)
            if not franchise:
                messages.error(request, "Franchise account is inactive.")
                return redirect('/login')
            
            if not franchise.payment_status:
                messages.error(request, "Payment verification required for this operation.")
                return redirect('/franchise_dashboard')
            
            request.franchise_user = franchise
            return view_func(request, *args, **kwargs)
            
        except Franchise.DoesNotExist:
            messages.error(request, "Franchise account not found.")
            return redirect('/login')
        except Exception as e:
            logger.error(f"Error in franchise_payment_verified decorator: {e}")
            messages.error(request, "Authentication error occurred.")
            return redirect('/login')
    return wrapper


def ajax_staff_required(view_func):
    """Decorator for AJAX views requiring staff access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id or user_type != 'staff':
            return JsonResponse({'error': 'Access denied. Staff privileges required.'}, status=403)
        
        try:
            staff = StaffModel.objects.get(staff_id=user_id)
            if not staff:
                return JsonResponse({'error': 'Staff account not found.'}, status=403)
            
            if hasattr(staff, 'is_active') and not staff.is_active:
                return JsonResponse({'error': 'Staff account is inactive.'}, status=403)
            
            request.staff_user = staff
            return view_func(request, *args, **kwargs)
            
        except StaffModel.DoesNotExist:
            return JsonResponse({'error': 'Staff account not found.'}, status=403)
        except Exception as e:
            logger.error(f"Error in ajax_staff_required decorator: {e}")
            return JsonResponse({'error': 'Authentication error occurred.'}, status=500)
    return wrapper


def ajax_franchise_required(view_func):
    """Decorator for AJAX views requiring franchise access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        franchise_id = request.session.get('franchise_id')
        user_type = request.session.get('user_type')
        
        if not franchise_id or user_type != 'franchise':
            return JsonResponse({'error': 'Access denied. Franchise privileges required.'}, status=403)
        
        try:
            franchise = Franchise.objects.get(franchise_id=franchise_id, is_active=True)
            if not franchise:
                return JsonResponse({'error': 'Franchise account is inactive.'}, status=403)
            
            request.franchise_user = franchise
            return view_func(request, *args, **kwargs)
            
        except Franchise.DoesNotExist:
            return JsonResponse({'error': 'Franchise account not found.'}, status=403)
        except Exception as e:
            logger.error(f"Error in ajax_franchise_required decorator: {e}")
            return JsonResponse({'error': 'Authentication error occurred.'}, status=500)
    return wrapper


def user_type_required(allowed_types):
    """Decorator to check if user is of specific type(s)"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_type = request.session.get('user_type')
            
            if not user_type or user_type not in allowed_types:
                messages.error(request, f"Access denied. {', '.join(allowed_types)} privileges required.")
                return redirect('/login')
            
            # Set the appropriate user object based on type
            try:
                if user_type == 'admin':
                    user_id = request.session.get('user_id')
                    user = AdminModel.objects.get(admin_id=user_id, is_active=True)
                    request.admin_user = user
                elif user_type == 'staff':
                    user_id = request.session.get('user_id')
                    user = StaffModel.objects.get(staff_id=user_id)
                    request.staff_user = user
                elif user_type == 'franchise':
                    franchise_id = request.session.get('franchise_id')
                    user = Franchise.objects.get(franchise_id=franchise_id, is_active=True)
                    request.franchise_user = user
                else:
                    messages.error(request, "Invalid user type.")
                    return redirect('/login')
                
                return view_func(request, *args, **kwargs)
                
            except (AdminModel.DoesNotExist, StaffModel.DoesNotExist, Franchise.DoesNotExist):
                messages.error(request, "User account not found.")
                return redirect('/login')
            except Exception as e:
                logger.error(f"Error in user_type_required decorator: {e}")
                messages.error(request, "Authentication error occurred.")
                return redirect('/login')
        return wrapper
    return decorator


def login_required(view_func):
    """Decorator to check if user is logged in (any type)"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_type = request.session.get('user_type')
        
        if not user_type:
            messages.error(request, "Please log in to access this page.")
            return redirect('/login')
        
        try:
            if user_type == 'admin':
                user_id = request.session.get('user_id')
                user = AdminModel.objects.get(admin_id=user_id, is_active=True)
                request.admin_user = user
            elif user_type == 'staff':
                user_id = request.session.get('user_id')
                user = StaffModel.objects.get(staff_id=user_id)
                request.staff_user = user
            elif user_type == 'franchise':
                franchise_id = request.session.get('franchise_id')
                user = Franchise.objects.get(franchise_id=franchise_id, is_active=True)
                request.franchise_user = user
            else:
                messages.error(request, "Invalid user type.")
                return redirect('/login')
            
            return view_func(request, *args, **kwargs)
            
        except (AdminModel.DoesNotExist, StaffModel.DoesNotExist, Franchise.DoesNotExist):
            messages.error(request, "User account not found.")
            return redirect('/login')
        except Exception as e:
            logger.error(f"Error in login_required decorator: {e}")
            messages.error(request, "Authentication error occurred.")
            return redirect('/login')
    return wrapper
