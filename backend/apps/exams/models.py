"""
考试模型
"""
from django.db import models
from apps.subjects.models import Subject
from apps.schools.models import School


class Exam(models.Model):
    """
    考试模型
    """
    class ExamType(models.TextChoices):
        MONTHLY = 'monthly', '月考'
        MIDTERM = 'midterm', '期中考试'
        FINAL = 'final', '期末考试'
        QUIZ = 'quiz', '测验'
        OTHER = 'other', '其他'

    name = models.CharField(max_length=100, verbose_name='考试名称')
    exam_type = models.CharField(
        max_length=20,
        choices=ExamType.choices,
        default=ExamType.MONTHLY,
        verbose_name='考试类型'
    )

    # 所属学校
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='exams',
        verbose_name='所属学校',
        null=True, # Allow null for migration
        blank=True
    )

    # 学年学期
    academic_year = models.CharField(max_length=20, default='2024-2025', verbose_name='学年')
    semester = models.CharField(max_length=10, default='第二学期', verbose_name='学期')

    # 考试时间
    exam_date = models.DateField(verbose_name='考试日期')
    start_time = models.TimeField(blank=True, null=True, verbose_name='开始时间')
    end_time = models.TimeField(blank=True, null=True, verbose_name='结束时间')

    # 适用年级（可多选）
    applicable_grades = models.JSONField(
        default=list,
        verbose_name='适用年级',
        help_text='例如：[1,2,3,4,5,6] 表示适用于所有年级'
    )

    # 考试科目（可多选）
    subjects = models.ManyToManyField(
        Subject,
        related_name='exams',
        verbose_name='考试科目'
    )

    # 成绩录入截止时间
    score_deadline = models.DateTimeField(blank=True, null=True, verbose_name='成绩录入截止时间')

    # 描述
    description = models.TextField(blank=True, null=True, verbose_name='考试说明')

    # 状态
    is_published = models.BooleanField(default=False, verbose_name='是否公布')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    # 创建者(用于区分管理员创建的统考和教师创建的小测验)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_exams',
        verbose_name='创建者'
    )

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'exams'
        verbose_name = '考试'
        verbose_name_plural = verbose_name
        ordering = ['-exam_date', '-created_at']

    def __str__(self):
        return f"{self.academic_year}{self.semester} - {self.name}"

    @property
    def score_count(self):
        """已录入成绩数量"""
        return self.scores.count()


class ExamGradeSubject(models.Model):
    """
    考试-年级-科目关系模型
    用于存储每个考试中，哪些年级需要考哪些科目
    例如：一二年级只考语文数学，三到六年级考语文数学英语科学
    """
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='grade_subjects',
        verbose_name='考试'
    )
    grade = models.IntegerField(
        verbose_name='年级',
        help_text='1-6年级'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        verbose_name='科目'
    )

    class Meta:
        db_table = 'exam_grade_subjects'
        verbose_name = '考试年级科目'
        verbose_name_plural = verbose_name
        unique_together = ['exam', 'grade', 'subject']  # 同一考试的同一年级不能重复添加同一科目
        ordering = ['exam', 'grade', 'subject']

    def __str__(self):
        return f"{self.exam.name} - {self.grade}年级 - {self.subject.name}"
