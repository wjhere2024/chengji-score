"""
毕业生归档模型
"""
from django.db import models


class GraduatedStudent(models.Model):
    """
    毕业生归档模型
    用于存储已毕业学生的信息
    """
    class Gender(models.TextChoices):
        MALE = 'male', '男'
        FEMALE = 'female', '女'

    # 原学生信息
    student_id = models.CharField(max_length=20, verbose_name='学号')
    name = models.CharField(max_length=50, verbose_name='姓名')
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        verbose_name='性别'
    )
    birth_date = models.DateField(blank=True, null=True, verbose_name='出生日期')
    id_number = models.CharField(max_length=18, blank=True, null=True, verbose_name='身份证号')

    # 毕业时的班级信息
    graduation_year = models.CharField(max_length=20, verbose_name='毕业学年')
    graduation_class_name = models.CharField(max_length=50, verbose_name='毕业班级')
    graduation_grade = models.IntegerField(default=6, verbose_name='毕业年级')

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
        upload_to='graduated/avatars/',
        blank=True,
        null=True,
        verbose_name='头像'
    )

    # 备注
    notes = models.TextField(blank=True, null=True, verbose_name='备注')

    # 毕业信息
    graduation_date = models.DateField(auto_now_add=True, verbose_name='归档日期')

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'graduated_students'
        verbose_name = '毕业生'
        verbose_name_plural = verbose_name
        ordering = ['-graduation_year', 'student_id']
        indexes = [
            models.Index(fields=['graduation_year']),
            models.Index(fields=['student_id']),
        ]

    def __str__(self):
        return f"{self.name}({self.student_id}) - {self.graduation_year}届"
