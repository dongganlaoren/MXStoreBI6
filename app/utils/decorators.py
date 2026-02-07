from functools import wraps

from flask import abort
from flask_login import current_user

from app.models.enums import RoleType


def role_required(*roles):
    """
    Decorator to ensure current user has one of the required roles.

    :param roles: List of role names (strings) or RoleType enum members.
    Example usages:
      @role_required('ADMIN')
      @role_required(RoleType.ADMIN.name)
      @role_required('ADMIN', 'HEAD_MANAGER')
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(401)

            # Determine current user's role name
            user_role = getattr(current_user, 'role', None)
            current_role_name = None

            if isinstance(user_role, RoleType):
                current_role_name = user_role.name
            elif isinstance(user_role, str):
                current_role_name = user_role
            elif user_role is None:
                # User has no role assigned? Treat as lowest privilege or deny.
                pass

            # Normalize required roles to a set of strings
            required_role_names = set()
            for r in roles:
                if isinstance(r, RoleType):
                    required_role_names.add(r.name)
                else:
                    required_role_names.add(str(r))

            if current_role_name not in required_role_names:
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator
