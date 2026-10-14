from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import LoginAudit, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "first_name", "last_name", "user_type", "school", "is_active")
    list_filter = ("user_type", "is_active", "school")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("School ERP", {"fields": ("user_type", "school", "phone_number", "date_of_birth", "address", "profile_picture")}),
    )


@admin.register(LoginAudit)
class LoginAuditAdmin(admin.ModelAdmin):
    list_display = ("username", "success", "ip_address", "created_at")
