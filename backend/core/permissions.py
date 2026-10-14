"""Role based access control primitives.

Permissions are enforced server side for every protected endpoint. Hiding a
button in the UI is never enough.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

SUPER_ADMIN = "SUPERADMIN"
SCHOOL_ADMIN = "SCHOOL_ADMIN"
PRINCIPAL = "PRINCIPAL"
TEACHER = "TEACHER"
STUDENT = "STUDENT"
PARENT = "PARENT"
ACCOUNTANT = "ACCOUNTANT"
LIBRARIAN = "LIBRARIAN"
TRANSPORT_MANAGER = "TRANSPORT_MANAGER"
HR_MANAGER = "HR_MANAGER"

ALL_ROLES = [
    SUPER_ADMIN, SCHOOL_ADMIN, PRINCIPAL, TEACHER, STUDENT,
    PARENT, ACCOUNTANT, LIBRARIAN, TRANSPORT_MANAGER, HR_MANAGER,
]

ADMIN_ROLES = [SUPER_ADMIN, SCHOOL_ADMIN]
ACADEMIC_ROLES = [SUPER_ADMIN, SCHOOL_ADMIN, PRINCIPAL, TEACHER]
FINANCE_ROLES = [SUPER_ADMIN, SCHOOL_ADMIN, ACCOUNTANT]
HR_ROLES = [SUPER_ADMIN, SCHOOL_ADMIN, HR_MANAGER]
LIBRARY_ROLES = [SUPER_ADMIN, SCHOOL_ADMIN, LIBRARIAN]
TRANSPORT_ROLES = [SUPER_ADMIN, SCHOOL_ADMIN, TRANSPORT_MANAGER]


class HasRole(BasePermission):
    """Allow access when the authenticated user has one of ``allowed_roles``."""

    allowed_roles = tuple(ADMIN_ROLES)
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.user_type == SUPER_ADMIN:
            return True
        return user.user_type in self.allowed_roles


def role_permission(*roles):
    return type("HasRoles", (HasRole,), {"allowed_roles": tuple(roles)})


IsSuperAdmin = role_permission(SUPER_ADMIN)
IsSchoolAdmin = role_permission(SUPER_ADMIN, SCHOOL_ADMIN)
IsAcademicStaff = role_permission(*ACADEMIC_ROLES)
IsFinance = role_permission(*FINANCE_ROLES)
IsHR = role_permission(*HR_ROLES)
IsLibrarian = role_permission(*LIBRARY_ROLES)
IsTransportManager = role_permission(*TRANSPORT_ROLES)
IsAnyRole = role_permission(*ALL_ROLES)


class IsSchoolMember(BasePermission):
    """Requires an authenticated user attached to a school."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and (user.is_superuser or user.school_id))


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsOwnerOrStaff(BasePermission):
    """Object level guard used for student/parent private data."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.user_type in ADMIN_ROLES or user.is_superuser:
            return True
        owner = getattr(obj, "user_id", None)
        if owner and owner == user.id:
            return True
        student_user = getattr(getattr(obj, "student", None), "user_id", None)
        if student_user and student_user == user.id:
            return True
        school_id = getattr(obj, "school_id", None)
        if school_id:
            return school_id == user.school_id
        return False
