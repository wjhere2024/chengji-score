"""
班级模型
"""
import random
import string
from django.db import models
from apps.users.models import User
from apps.schools.models import School


def generate_invite_code():
    """生成6位数字邀请码"""
    return ''.join(random.choices(string.digits, k=6))


class Class(models.Model):
    """
    班级模型
    """
    class Grade(models.IntegerChoices):
        GRADE_1 = 1, '一年级'
        GRADE_2 = 2, '二年级'
        GRADE_3 = 3, '三年级'
        GRADE_4 = 4, '四年级'
        GRADE_5 = 5, '五年级'
        GRADE_6 = 6, '六年级'

    name = models.CharField(max_length=50, verbose_name='班级名称')
    grade = models.IntegerField(choices=Grade.choices, verbose_name='年级')
    class_number = models.IntegerField(verbose_name='班号')
    
    # 所属学校
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='classes',
        verbose_name='所属学校',
        null=True, # Allow null for migration
        blank=True
    )

    # 班主任
    head_teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='head_teacher_classes',
        limit_choices_to={'role': User.Role.HEAD_TEACHER},
        verbose_name='班主任'
    )

    # 班级信息
    student_count = models.IntegerField(default=0, verbose_name='学生人数')
    classroom = models.CharField(max_length=50, blank=True, null=True, verbose_name='教室位置')
    description = models.TextField(blank=True, null=True, verbose_name='班级描述')

    # 学生邀请码
    student_invite_code = models.CharField(
        max_length=6,
        unique=True,
        blank=True,
        verbose_name='学生邀请码',
        help_text='学生通过此邀请码绑定账号'
    )

    # 状态
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'classes'
        verbose_name = '班级'
        verbose_name_plural = verbose_name
        ordering = ['grade', 'class_number']
        unique_together = ['school', 'grade', 'class_number']

    def __str__(self):
        return f"{self.get_grade_display()}{self.class_number}班"

    def save(self, *args, **kwargs):
        if not self.student_invite_code:
            # 生成唯一的6位邀请码
            for _ in range(100):
                code = generate_invite_code()
                if not Class.objects.filter(student_invite_code=code).exists():
                    self.student_invite_code = code
                    break
        super().save(*args, **kwargs)

    def reset_student_invite_code(self):
        """重置学生邀请码"""
        for _ in range(100):
            code = generate_invite_code()
            if not Class.objects.filter(student_invite_code=code).exists():
                self.student_invite_code = code
                self.save(update_fields=['student_invite_code'])
                return code
        return None

    def update_student_count(self):
        """更新学生人数"""
        self.student_count = self.students.filter(is_active=True).count()
        self.save(update_fields=['student_count'])


class ClassInvitation(models.Model):
    """
    班级邀请码模型
    用于邀请其他教师加入班级
    """
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='invitations',
        verbose_name='班级'
    )
    invite_code = models.CharField(max_length=8, unique=True, verbose_name='邀请码')
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_invitations',
        verbose_name='创建者'
    )
    # 可选：指定邀请加入的科目
    subject_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='科目名称')
    
    # 有效期和使用限制
    expires_at = models.DateTimeField(verbose_name='过期时间')
    max_uses = models.IntegerField(default=10, verbose_name='最大使用次数')
    used_count = models.IntegerField(default=0, verbose_name='已使用次数')
    
    # 状态
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'class_invitations'
        verbose_name = '班级邀请码'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.class_obj} - {self.invite_code}"
    
    def is_valid(self):
        """检查邀请码是否有效"""
        from django.utils import timezone
        if not self.is_active:
            return False
        if self.expires_at < timezone.now():
            return False
        if self.used_count >= self.max_uses:
            return False
        return True


class StudentGroup(models.Model):
    """
    学生分组
    允许教师对班级学生进行小组划分，用于小组竞赛
    """
    name = models.CharField(max_length=50, verbose_name='小组名称')
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='groups',
        verbose_name='班级'
    )
    color = models.CharField(
        max_length=20,
        default='#409EFF',
        verbose_name='小组颜色',
        help_text='用于UI展示的颜色标识'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_groups',
        verbose_name='创建人'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'student_groups'
        verbose_name = '学生分组'
        verbose_name_plural = verbose_name
        ordering = ['class_obj', 'name']
        unique_together = ['class_obj', 'name']
    
    def __str__(self):
        return f"{self.class_obj} - {self.name}"
    
    @property
    def member_count(self):
        """成员数量"""
        return self.members.count()


class StudentGroupMember(models.Model):
    """
    小组成员
    记录学生与小组的多对一关系（一个学生在一个班级只能属于一个分组）
    """
    group = models.ForeignKey(
        StudentGroup,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name='所属小组'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='group_memberships',
        verbose_name='学生'
    )
    
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='加入时间')
    
    class Meta:
        db_table = 'student_group_members'
        verbose_name = '小组成员'
        verbose_name_plural = verbose_name
        # 一个学生在同一个班级只能属于一个分组
        unique_together = ['group', 'student']
    
    def __str__(self):
        return f"{self.group.name} - {self.student.name}"
