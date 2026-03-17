"""
科目模型
"""
from django.db import models
from apps.schools.models import School


class Subject(models.Model):
    """
    科目模型
    """
    name = models.CharField(max_length=50, unique=True, verbose_name='科目名称')
    code = models.CharField(max_length=20, unique=True, verbose_name='科目代码')
    description = models.TextField(blank=True, null=True, verbose_name='科目描述')

    # 所属学校（为空表示系统通用科目）
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='subjects',
        verbose_name='所属学校',
        null=True,
        blank=True
    )

    # 适用年级（可多选）
    applicable_grades = models.JSONField(
        default=list,
        verbose_name='适用年级',
        help_text='例如：[1,2,3,4,5,6] 表示适用于所有年级'
    )

    # 满分
    full_score = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=100.0,
        verbose_name='满分'
    )

    # 及格分数
    pass_score = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=60.0,
        verbose_name='及格分数'
    )

    # 优秀分数
    excellent_score = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=90.0,
        verbose_name='优秀分数'
    )

    # 排序
    order = models.IntegerField(default=0, verbose_name='排序')

    # 状态
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'subjects'
        verbose_name = '科目'
        verbose_name_plural = verbose_name
        ordering = ['order', 'id']

    def __str__(self):
        return self.name
