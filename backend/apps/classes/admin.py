"""
班级Admin配置
"""
from django.contrib import admin
from .models import Class


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    """班级管理"""
    list_display = ['name', 'grade', 'class_number', 'head_teacher', 'student_count', 'is_active']
    list_filter = ['grade', 'is_active']
    search_fields = ['name', 'classroom', 'head_teacher__real_name']
    ordering = ['grade', 'class_number']
    list_per_page = 20

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'grade', 'class_number', 'head_teacher')
        }),
        ('其他信息', {
            'fields': ('student_count', 'classroom', 'description', 'is_active')
        }),
    )

    readonly_fields = ['student_count']
