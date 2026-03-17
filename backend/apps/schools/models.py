from django.db import models

class School(models.Model):
    """
    学校模型
    """
    name = models.CharField(max_length=100, verbose_name='学校名称')
    code = models.CharField(max_length=20, unique=True, verbose_name='学校代码', help_text='系统自动生成或自定义')
    address = models.CharField(max_length=200, blank=True, null=True, verbose_name='地址')
    province = models.CharField(max_length=50, blank=True, null=True, verbose_name='省份')
    city = models.CharField(max_length=50, blank=True, null=True, verbose_name='城市')
    district = models.CharField(max_length=50, blank=True, null=True, verbose_name='区县')
    
    CATEGORY_CHOICES = (
        ('primary', '小学'),
        ('middle', '初中'),
        ('high', '高中'),
        ('university', '大学'),
        ('other', '其他'),
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', verbose_name='学校类型')
    
    contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='联系电话')
    
    # 状态
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'schools'
        verbose_name = '学校'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name
