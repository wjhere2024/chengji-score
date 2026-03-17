"""
成绩模型
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.students.models import Student
from apps.exams.models import Exam
from apps.subjects.models import Subject


class Score(models.Model):
    """
    成绩模型
    """
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='scores',
        verbose_name='学生'
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='scores',
        verbose_name='考试'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='scores',
        verbose_name='科目'
    )

    # 成绩
    score = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(0)],
        verbose_name='分数'
    )

    # 排名
    class_rank = models.IntegerField(blank=True, null=True, verbose_name='班级排名')
    grade_rank = models.IntegerField(blank=True, null=True, verbose_name='年级排名')

    # 备注
    notes = models.TextField(blank=True, null=True, verbose_name='备注')

    # 录入信息
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_scores',
        verbose_name='录入人'
    )

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='录入时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'scores'
        verbose_name = '成绩'
        verbose_name_plural = verbose_name
        ordering = ['-exam__exam_date', 'student__class_obj__grade', 'student__class_obj__class_number']
        unique_together = ['student', 'exam', 'subject']

    def __str__(self):
        return f"{self.student.name} - {self.exam.name} - {self.subject.name}: {self.score}"

    @property
    def is_pass(self):
        """是否及格"""
        return self.score >= self.subject.pass_score

    @property
    def is_excellent(self):
        """是否优秀（90分以上）"""
        return self.score >= 90

    def save(self, *args, **kwargs):
        """保存时自动计算排名"""
        super().save(*args, **kwargs)
        # TODO: 在后台任务中计算排名
