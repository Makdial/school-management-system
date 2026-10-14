"""Role gates for the reporting endpoints.

Reports aggregate sensitive data (money, salaries, private student records),
so each endpoint declares the narrowest role set that may read it.
"""
from rest_framework.permissions import BasePermission

from core.permissions import (
    ALL_ROLES, FINANCE_ROLES, HR_ROLES, LIBRARY_ROLES, TRANSPORT_ROLES,
    ACADEMIC_ROLES, role_permission,
)

CanViewReports = role_permission(*ALL_ROLES)
CanViewFinanceReports = role_permission(*FINANCE_ROLES)
CanViewHRReports = role_permission(*HR_ROLES)
CanViewLibraryReports = role_permission(*LIBRARY_ROLES)
CanViewTransportReports = role_permission(*TRANSPORT_ROLES)
CanViewAcademicReports = role_permission(*ACADEMIC_ROLES)


class CanExportDataset(BasePermission):
    """Object-type level guard for the CSV export endpoint.

    The view calls :meth:`allowed` so the same permission object can enforce
    a *per dataset* rule instead of a single global role.
    """

    DATASET_ROLES = {
        "students": {"SUPERADMIN", "SCHOOL_ADMIN", "PRINCIPAL"},
        "attendance": {"SUPERADMIN", "SCHOOL_ADMIN", "PRINCIPAL", "TEACHER"},
        "staff": {"SUPERADMIN", "SCHOOL_ADMIN", "HR_MANAGER"},
        "invoices": {"SUPERADMIN", "SCHOOL_ADMIN", "ACCOUNTANT"},
        "payments": {"SUPERADMIN", "SCHOOL_ADMIN", "ACCOUNTANT"},
        "admissions": {"SUPERADMIN", "SCHOOL_ADMIN", "PRINCIPAL"},
        "library": {"SUPERADMIN", "SCHOOL_ADMIN", "LIBRARIAN"},
    }

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        dataset = request.query_params.get("dataset", "")
        return self.allowed(user, dataset)

    @classmethod
    def allowed(cls, user, dataset):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        roles = cls.DATASET_ROLES.get(dataset)
        return bool(roles and user.user_type in roles)
