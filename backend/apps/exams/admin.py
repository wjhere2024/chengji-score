"""
考试Admin配置
"""
from django.contrib import admin
from .models import Exam, ExamGradeSubject


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    """考试管理"""
    list_display = ['name', 'exam_type', 'academic_year', 'semester', 'exam_date', 'is_published', 'is_active']
    list_filter = ['exam_type', 'academic_year', 'semester', 'is_published', 'is_active', 'exam_date']
    search_fields = ['name', 'description']
    ordering = ['-exam_date', '-created_at']
    filter_horizontal = ['subjects']
    list_per_page = 30


@admin.register(ExamGradeSubject)
class ExamGradeSubjectAdmin(admin.ModelAdmin):
    """考试年级科目关系管理"""
    list_display = ['exam', 'grade', 'subject']
    list_filter = ['exam', 'grade', 'subject']
    search_fields = ['exam__name', 'subject__name']
    ordering = ['exam', 'grade', 'subject']
    list_per_page = 50
