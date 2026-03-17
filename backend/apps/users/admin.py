"""
用户Admin配置
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OperationLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """用户管理"""
    list_display = ['username', 'real_name', 'role', 'employee_id', 'phone', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['username', 'real_name', 'employee_id', 'phone']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('额外信息', {'fields': ('role', 'real_name', 'phone', 'employee_id', 'avatar')}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('额外信息', {'fields': ('role', 'real_name', 'phone', 'employee_id')}),
    )


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    """操作日志管理"""
    list_display = ['user', 'action', 'target_model', 'target_id', 'description', 'created_at']
    list_filter = ['action', 'target_model', 'created_at']
    search_fields = ['user__real_name', 'description']
    ordering = ['-created_at']
    readonly_fields = ['user', 'action', 'target_model', 'target_id', 'description', 'ip_address', 'user_agent', 'created_at']

    def has_add_permission(self, request):
        """禁止手动添加日志"""
        return False

    def has_delete_permission(self, request, obj=None):
        """禁止删除日志"""
        return False
