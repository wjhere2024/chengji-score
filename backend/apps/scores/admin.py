"""
成绩Admin配置
"""
from django.contrib import admin
from .models import Score


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    """成绩管理"""
    list_display = ['student', 'exam', 'subject', 'score', 'class_rank', 'grade_rank', 'created_by', 'created_at']
    list_filter = ['exam', 'subject', 'student__class_obj__grade', 'created_at']
    search_fields = ['student__name', 'student__student_id']
    ordering = ['-exam__exam_date', 'student__class_obj__grade', 'student__class_obj__class_number']
    list_per_page = 50

    def get_queryset(self, request):
        """根据用户角色过滤数据"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(created_by=request.user)
