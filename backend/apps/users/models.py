"""
用户模型
支持多角色：校级管理员、班主任、任课教师
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.schools.models import School


class User(AbstractUser):
    """
    自定义用户模型
    扩展Django默认用户模型，添加角色和额外字段
    支持多身份切换功能
    支持多学校SaaS架构
    """
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', '超级管理员'
        ADMIN = 'admin', '普通管理员'
        HEAD_TEACHER = 'head_teacher', '班主任'
        SUBJECT_TEACHER = 'subject_teacher', '任课教师'
        STUDENT = 'student', '学生'

    # 所属学校（SaaS架构核心字段）
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True,
        verbose_name='所属学校'
    )

    # 角色字段（保留用于兼容性，主要角色）
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SUBJECT_TEACHER,
        verbose_name='主要角色'
    )

    # 多角色字段（JSONField存储角色列表）
    roles = models.JSONField(
        default=list,
        blank=True,
        verbose_name='所有角色',
        help_text='用户拥有的所有角色列表，如 ["admin", "head_teacher"]'
    )

    # 当前激活的角色
    current_role = models.CharField(
        max_length=20,
        choices=Role.choices,
        blank=True,
        null=True,
        verbose_name='当前角色',
        help_text='用户当前激活使用的角色'
    )

    # 桌面卡片配置（按角色存储）
    dashboard_cards = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='桌面卡片配置',
        help_text='按角色存储的桌面快捷卡片，如 {"admin": ["card-id-1", "card-id-2"]}'
    )

    # 教师信息
    real_name = models.CharField(max_length=50, verbose_name='真实姓名')
    phone = models.CharField(max_length=11, blank=True, null=True, verbose_name='手机号')
    employee_id = models.CharField(max_length=20, blank=True, null=True, verbose_name='工号')
    
    # 微信集成
    wechat_openid = models.CharField(
        max_length=64, 
        blank=True, 
        null=True, 
        unique=True, 
        verbose_name='微信OpenID'
    )

    # 头像
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='头像'
    )

    # 演示账号标记（演示账号不能修改密码，其数据不能被删除）
    is_demo_account = models.BooleanField(
        default=False,
        verbose_name='演示账号',
        help_text='演示账号不能修改密码，其班级和学生数据不能被删除'
    )

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.real_name}({self.username})"

    def save(self, *args, **kwargs):
        """保存时自动处理角色列表"""
        # 如果roles为空，则使用role字段初始化
        if not self.roles:
            self.roles = [self.role]

        # 确保role在roles列表中
        if self.role not in self.roles:
            self.roles.append(self.role)

        # 如果current_role为空，使用role作为默认值
        if not self.current_role:
            self.current_role = self.role

        # 确保current_role在roles列表中
        if self.current_role not in self.roles:
            self.current_role = self.role

        super().save(*args, **kwargs)

    def get_active_role(self):
        """获取当前激活的角色"""
        return self.current_role or self.role

    def has_role(self, role):
        """检查用户是否拥有指定角色"""
        return role in self.roles

    def switch_role(self, role):
        """切换到指定角色"""
        if role in self.roles:
            self.current_role = role
            self.save(update_fields=['current_role'])
            return True
        return False

    def get_role_display_name(self, role=None):
        """获取角色的显示名称"""
        target_role = role or self.get_active_role()
        return dict(self.Role.choices).get(target_role, '')

    @property
    def is_super_admin(self):
        """是否是超级管理员（基于当前激活角色）"""
        return self.get_active_role() == self.Role.SUPER_ADMIN

    @property
    def is_admin(self):
        """是否是管理员（包括超级管理员和普通管理员，基于当前激活角色）"""
        return self.get_active_role() in [self.Role.SUPER_ADMIN, self.Role.ADMIN]

    @property
    def is_head_teacher(self):
        """是否是班主任（基于当前激活角色）"""
        return self.get_active_role() == self.Role.HEAD_TEACHER

    @property
    def is_subject_teacher(self):
        """是否是任课教师（基于当前激活角色）"""
        return self.get_active_role() == self.Role.SUBJECT_TEACHER

    @property
    def has_multiple_roles(self):
        """是否拥有多个角色"""
        return len(self.roles) > 1


class OperationLog(models.Model):
    """
    操作日志模型
    记录用户的所有重要操作
    """
    class Action(models.TextChoices):
        CREATE = 'create', '创建'
        UPDATE = 'update', '修改'
        DELETE = 'delete', '删除'
        IMPORT = 'import', '导入'
        EXPORT = 'export', '导出'
        LOGIN = 'login', '登录'
        LOGOUT = 'logout', '登出'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='operation_logs',
        verbose_name='操作用户'
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name='操作类型'
    )
    target_model = models.CharField(max_length=50, verbose_name='目标模型')
    target_id = models.IntegerField(blank=True, null=True, verbose_name='目标ID')
    description = models.TextField(verbose_name='操作描述')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')
    user_agent = models.CharField(max_length=255, blank=True, null=True, verbose_name='用户代理')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')

    class Meta:
        db_table = 'operation_logs'
        verbose_name = '操作日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.real_name} - {self.get_action_display()} - {self.target_model}"


class LoginQRCode(models.Model):
    """
    扫码登录二维码模型
    """
    TOKEN_STATUS = (
        ('waiting', '等待扫描'),
        ('scanned', '已扫描'),
        ('confirmed', '已确认'),
        ('expired', '已过期'),
    )

    token = models.UUIDField(unique=True, verbose_name='Token')
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='确认用户'
    )
    status = models.CharField(
        max_length=20,
        choices=TOKEN_STATUS,
        default='waiting',
        verbose_name='状态'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'login_qrcodes'
        verbose_name = '登录二维码'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']


class RemoteDevice(models.Model):
    """
    远程设备绑定的模型
    用于手机控制PC端登录
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='remote_devices',
        verbose_name='绑定用户'
    )
    device_id = models.CharField(max_length=64, unique=True, verbose_name='设备唯一标识')
    name = models.CharField(max_length=50, verbose_name='设备名称')
    last_heartbeat = models.DateTimeField(auto_now=True, verbose_name='网页活跃时间')
    last_agent_heartbeat = models.DateTimeField(null=True, blank=True, verbose_name='助手活跃时间')
    
    # 待消费的登录Token
    pending_token = models.CharField(max_length=255, blank=True, null=True, verbose_name='登录Token')
    # 待消费的指令
    # 待消费的指令
    pending_command = models.CharField(max_length=50, blank=True, null=True, verbose_name='控制指令')
    
    # 锁定状态
    is_locked = models.BooleanField(default=False, verbose_name='是否锁定')
    
    # 媒体与文件共享服务地址
    media_server_url = models.CharField(max_length=255, blank=True, null=True, verbose_name='媒体服务器地址')
    file_server_url = models.CharField(max_length=255, blank=True, null=True, verbose_name='文件服务器地址')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'remote_devices'
        verbose_name = '远程设备'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.user.real_name})"


class EmailVerification(models.Model):
    """
    邮箱验证码模型
    """
    TYPE_CHOICES = (
        ('register', '注册'),
        ('reset_password', '重置密码'),
    )

    email = models.EmailField(verbose_name='邮箱')
    code = models.CharField(max_length=6, verbose_name='验证码')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='register', verbose_name='验证类型')
    is_verified = models.BooleanField(default=False, verbose_name='是否已验证')
    expires_at = models.DateTimeField(verbose_name='过期时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'email_verifications'
        verbose_name = '邮箱验证码'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']


class WechatVerification(models.Model):
    """
    微信公众号验证码模型
    用户在网页端请求验证码后，在公众号发送手机号获取验证码
    """
    TYPE_CHOICES = (
        ('register', '注册'),
        ('reset_password', '重置密码'),
        ('bind', '绑定账号'),
    )

    phone = models.CharField(max_length=11, null=True, blank=True, verbose_name='手机号')
    code = models.CharField(max_length=6, blank=True, default='', verbose_name='验证码')
    openid = models.CharField(max_length=64, blank=True, default='', verbose_name='微信OpenID')
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='wechat_verifications',
        verbose_name='关联用户'
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='register', verbose_name='验证类型')
    is_verified = models.BooleanField(default=False, verbose_name='是否已验证')
    expires_at = models.DateTimeField(verbose_name='过期时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'wechat_verifications'
        verbose_name = '微信验证码'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']


class TeacherSchoolMembership(models.Model):
    """
    教师-学校多对多关系
    记录教师所属的所有学校
    """
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='school_memberships',
        verbose_name='教师'
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='teacher_memberships',
        verbose_name='学校'
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='加入时间')
    is_active = models.BooleanField(default=True, verbose_name='是否有效')

    class Meta:
        db_table = 'teacher_school_memberships'
        unique_together = ['teacher', 'school']
        verbose_name = '教师学校关系'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.teacher.real_name} - {self.school.name}"


class SchoolJoinRequest(models.Model):
    """
    学校加入申请
    教师申请加入某个学校，需要管理员审批
    """
    STATUS_CHOICES = (
        ('pending', '待审批'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
        ('blocked', '已封禁'),  # 拒绝超过2次
    )

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='join_requests',
        verbose_name='申请教师'
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='join_requests',
        verbose_name='目标学校'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态'
    )

    # 数据迁移选项
    migrate_classes = models.BooleanField(default=False, verbose_name='迁移班级')
    migrate_students = models.BooleanField(default=False, verbose_name='迁移学生')

    # 审批信息
    reject_count = models.IntegerField(default=0, verbose_name='拒绝次数')
    reject_reason = models.TextField(blank=True, default='', verbose_name='拒绝原因')
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_requests',
        verbose_name='审批人'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审批时间')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='申请时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'school_join_requests'
        verbose_name = '学校加入申请'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.teacher.real_name} 申请加入 {self.school.name}"
