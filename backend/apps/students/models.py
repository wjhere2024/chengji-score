"""
学生模型
"""
from django.db import models
from apps.classes.models import Class
from .models_graduated import GraduatedStudent
import uuid


class Student(models.Model):
    """
    学生模型
    """
    class Gender(models.TextChoices):
        MALE = 'male', '男'
        FEMALE = 'female', '女'

    # 基本信息
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, null=True, verbose_name='唯一标识')
    student_id = models.CharField(max_length=20, verbose_name='学号')
    name = models.CharField(max_length=50, verbose_name='姓名')

    # 关联用户账号（学生绑定后）
    user = models.OneToOneField(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile',
        verbose_name='关联账号'
    )
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        default=Gender.MALE,
        verbose_name='性别'
    )
    birth_date = models.DateField(blank=True, null=True, verbose_name='出生日期')
    id_number = models.CharField(max_length=18, blank=True, null=True, verbose_name='身份证号')

    # 班级信息
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='students',
        verbose_name='班级'
    )

    # 联系信息
    phone = models.CharField(max_length=11, blank=True, null=True, verbose_name='联系电话')
    parent_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='家长姓名')
    parent_phone = models.CharField(max_length=11, blank=True, null=True, verbose_name='家长电话')
    address = models.CharField(max_length=200, blank=True, null=True, verbose_name='家庭住址')

    # 学籍信息
    admission_date = models.DateField(blank=True, null=True, verbose_name='入学日期')
    admission_year = models.IntegerField(blank=True, null=True, verbose_name='入学年份')
    enrollment_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='入学方式'
    )

    # 头像
    avatar = models.ImageField(
        upload_to='students/avatars/',
        blank=True,
        null=True,
        verbose_name='头像'
    )

    # 奖励体系
    learning_beans = models.IntegerField(default=0, verbose_name='学习豆')

    # 备注
    notes = models.TextField(blank=True, null=True, verbose_name='备注')

    # 状态
    is_active = models.BooleanField(default=True, verbose_name='是否在读')

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'students'
        verbose_name = '学生'
        verbose_name_plural = verbose_name
        ordering = ['class_obj__grade', 'class_obj__class_number', 'student_id']

    def __str__(self):
        return f"{self.name}({self.student_id})"

    def save(self, *args, **kwargs):
        """保存时更新班级学生人数"""
        super().save(*args, **kwargs)
        if self.class_obj:
            self.class_obj.update_student_count()


class VacationSetting(models.Model):
    """
    假期配置
    管理员可设置每学年的寒暑假时间
    """
    VACATION_TYPE_CHOICES = (
        ('winter', '寒假'),
        ('summer', '暑假'),
    )
    
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='vacation_settings',
        verbose_name='学校'
    )
    academic_year = models.CharField(max_length=20, verbose_name='学年', help_text='如：2024-2025')
    vacation_type = models.CharField(max_length=10, choices=VACATION_TYPE_CHOICES, verbose_name='假期类型')
    start_date = models.DateField(verbose_name='开始日期')
    end_date = models.DateField(verbose_name='结束日期')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'vacation_settings'
        verbose_name = '假期设置'
        verbose_name_plural = verbose_name
        unique_together = ['school', 'academic_year', 'vacation_type']
        ordering = ['-academic_year', 'vacation_type']
    
    def __str__(self):
        return f"{self.school.name} {self.academic_year} {self.get_vacation_type_display()}"
    
    @classmethod
    def is_in_vacation(cls, check_date, school=None):
        """检查指定日期是否在假期内"""
        queryset = cls.objects.filter(
            start_date__lte=check_date,
            end_date__gte=check_date
        )
        if school:
            queryset = queryset.filter(school=school)
        return queryset.exists()


class StudentRecord(models.Model):
    """
    学生日常表现记录
    用于教师快速记录学生日常好的/需改进的表现，作为期末评语素材
    """
    RECORD_TYPE_CHOICES = (
        ('positive', '正面表现'),
        ('negative', '需改进'),
        ('neutral', '中性记录'),
    )
    CATEGORY_CHOICES = (
        ('recite', '背诵'),
        ('dictation', '默写'),
        ('reading', '认读'),
        ('discipline', '纪律'),
        ('labor', '劳动'),
        ('morality', '品德'),
        ('study', '学习'),
        ('other', '其他'),
    )
    SOURCE_CHOICES = (
        ('manual', '手动录入'),
        ('system', '系统生成'),
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='daily_records',
        verbose_name='学生'
    )
    record_type = models.CharField(
        max_length=20,
        choices=RECORD_TYPE_CHOICES,
        default='positive',
        verbose_name='记录类型'
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other',
        verbose_name='分类'
    )
    content = models.TextField(verbose_name='内容描述')

    # 来源
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='manual',
        verbose_name='来源'
    )
    source_detail = models.JSONField(
        null=True,
        blank=True,
        verbose_name='来源详情',
        help_text='系统来源的详细信息，如关联的默写场次ID等'
    )

    # 记录信息
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_records',
        verbose_name='记录人'
    )
    record_date = models.DateField(verbose_name='记录日期')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'student_daily_records'
        verbose_name = '学生日常记录'
        verbose_name_plural = verbose_name
        ordering = ['-record_date', '-created_at']
        indexes = [
            models.Index(fields=['student', 'record_date']),
            models.Index(fields=['record_type', 'record_date']),
        ]

    def __str__(self):
        return f"{self.student.name} - {self.get_category_display()} - {self.record_date}"


class StudentSpotlight(models.Model):
    """
    学生之星记录
    支持每日/每周/每月之星，自动选取或教师推荐
    """
    PERIOD_CHOICES = (
        ('daily', '每日之星'),
        ('weekly', '每周之星'),
        ('monthly', '每月之星'),
    )
    SOURCE_CHOICES = (
        ('auto', '系统自动'),
        ('recommend', '教师推荐'),
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='spotlights',
        verbose_name='学生'
    )
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='spotlights',
        verbose_name='班级'
    )

    period = models.CharField(
        max_length=20,
        choices=PERIOD_CHOICES,
        default='daily',
        verbose_name='周期类型'
    )
    spotlight_date = models.DateField(verbose_name='生效日期')

    # 选取来源
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='auto',
        verbose_name='选取来源'
    )
    recommend_reason = models.TextField(
        blank=True,
        verbose_name='推荐理由',
        help_text='教师推荐时填写的理由'
    )

    # 系统聚合的亮点数据
    achievements = models.JSONField(
        default=list,
        verbose_name='亮点列表',
        help_text='格式: [{"type": "recite", "title": "背诵达人", "detail": "本周完成3篇古诗"}]'
    )

    # 教师寄语
    teacher_comment = models.TextField(
        blank=True,
        verbose_name='教师寄语'
    )

    # 展示状态
    is_displayed = models.BooleanField(
        default=False,
        verbose_name='是否已展示'
    )
    displayed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='展示时间'
    )

    # 记录信息
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_spotlights',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'student_spotlights'
        verbose_name = '学生之星'
        verbose_name_plural = verbose_name
        ordering = ['-spotlight_date', '-created_at']
        # 同一天同周期同班级同学生只能有一条
        unique_together = ['student', 'class_obj', 'period', 'spotlight_date']
        indexes = [
            models.Index(fields=['class_obj', 'spotlight_date', 'period']),
            models.Index(fields=['student', 'spotlight_date']),
        ]

    def __str__(self):
        return f"{self.student.name} - {self.get_period_display()} ({self.spotlight_date})"


class BeanLog(models.Model):
    """学豆变动日志 - 追踪每次学豆变化的来源"""
    SOURCE_CHOICES = (
        ('dictation', '听写'),
        ('reading', '认读'),
        ('comment', '课堂点评'),
        ('correction', '数据修正'),
    )
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='bean_logs',
        verbose_name='学生'
    )
    amount = models.IntegerField(verbose_name='变动数量')  # 正数加分，负数扣分
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, verbose_name='来源')
    detail = models.CharField(max_length=200, blank=True, verbose_name='详情')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'student_bean_logs'
        verbose_name = '学豆变动日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'created_at']),
            models.Index(fields=['source', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.student.name}: {self.amount:+d} ({self.get_source_display()})"
