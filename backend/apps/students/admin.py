"""
学生Admin配置
"""
from django.contrib import admin
from .models import Student, VacationSetting


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """学生管理"""
    list_display = ['student_id', 'name', 'gender', 'class_obj', 'parent_name', 'parent_phone', 'is_active']
    list_filter = ['gender', 'class_obj__grade', 'is_active', 'created_at']
    search_fields = ['student_id', 'name', 'parent_name', 'phone', 'parent_phone']
    ordering = ['class_obj__grade', 'class_obj__class_number', 'student_id']
    list_per_page = 50

    fieldsets = (
        ('基本信息', {
            'fields': ('student_id', 'name', 'gender', 'birth_date', 'id_number', 'class_obj')
        }),
        ('联系信息', {
            'fields': ('phone', 'parent_name', 'parent_phone', 'address')
        }),
        ('学籍信息', {
            'fields': ('admission_date', 'enrollment_type', 'avatar', 'notes')
        }),
        ('状态', {
            'fields': ('is_active',)
        }),
    )


@admin.register(VacationSetting)
class VacationSettingAdmin(admin.ModelAdmin):
    """假期设置管理"""
    list_display = ['school', 'academic_year', 'vacation_type', 'start_date', 'end_date']
    list_filter = ['school', 'academic_year', 'vacation_type']
    ordering = ['-academic_year', 'vacation_type']
    list_per_page = 20

