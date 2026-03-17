"""
科目Admin配置
"""
from django.contrib import admin
from .models import Subject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """科目管理"""
    list_display = ['name', 'code', 'full_score', 'pass_score', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['order', 'id']
    list_editable = ['order', 'is_active']
