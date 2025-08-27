import jwt
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone

def generate_activation_token(email, user_type='staff', staff_id=None):
    """
    Generate JWT token for user activation (staff or franchise)
    """
    payload = {
        'email': email,
        'user_type': user_type,
        'type': 'activation',
        'exp': datetime.utcnow() + timedelta(seconds=settings.JWT_EXPIRATION_DELTA),
        'iat': datetime.utcnow()
    }
    
    # Add staff_id if provided (for staff activation)
    if staff_id:
        payload['staff_id'] = staff_id
    
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token

def verify_activation_token(token, user_type=None):
    """
    Verify and decode JWT activation token
    Returns: email if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        # Check if it's an activation token
        if payload.get('type') != 'activation':
            return None
        
        # Check if token is expired
        exp_timestamp = payload.get('exp')
        if exp_timestamp and datetime.utcnow().timestamp() > exp_timestamp:
            return None
        
        # Check user type if specified
        if user_type and payload.get('user_type') != user_type:
            return None
        
        return payload.get('email')
        
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

def generate_password_reset_token(staff_id, email):
    """
    Generate JWT token for password reset
    """
    payload = {
        'staff_id': staff_id,
        'email': email,
        'type': 'password_reset',
        'exp': datetime.utcnow() + timedelta(hours=1),  # 1 hour expiry
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token
