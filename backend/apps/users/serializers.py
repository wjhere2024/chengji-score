"""
用户序列化器
"""
from rest_framework import serializers
from .models import User, OperationLog, LoginQRCode, RemoteDevice


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    # 添加角色显示名称列表
    roles_display = serializers.SerializerMethodField()
    current_role_display = serializers.SerializerMethodField()
    has_multiple_roles = serializers.BooleanField(read_only=True)
    school_name = serializers.SerializerMethodField()
    school_code = serializers.SerializerMethodField()
    teaching_subjects = serializers.SerializerMethodField()

    # explicitly declare roles as SerializerMethodField to override model field
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'real_name', 'email', 'phone',
            'employee_id', 'role', 'roles', 'current_role',
            'roles_display', 'current_role_display', 'has_multiple_roles',
            'school_name', 'school_code', 'teaching_subjects',
            'avatar', 'is_active', 'created_at', 'updated_at',
            'wechat_openid', 'dashboard_cards'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'has_multiple_roles']

    def _get_filtered_roles(self, obj):
        """Helper to get filtered roles based on actual assignments"""
        roles = obj.roles
        # Filter out head_teacher if not assigned to any class
        if User.Role.HEAD_TEACHER in roles:
            # Check if user manages any active classes
            # Use local import to avoid circular dependency
            from apps.classes.models import Class
            has_class = Class.objects.filter(head_teacher=obj, is_active=True).exists()
            if not has_class:
                roles = [r for r in roles if r != User.Role.HEAD_TEACHER]
        return roles

    def get_roles(self, obj):
        """Get filtered roles"""
        return self._get_filtered_roles(obj)

    def get_roles_display(self, obj):
        """获取所有角色的显示名称"""
        roles = self._get_filtered_roles(obj)
        return [
            {
                'value': role,
                'label': dict(User.Role.choices).get(role, role)
            }
            for role in roles
        ]

    def get_current_role_display(self, obj):
        """获取当前角色的显示名称"""
        return obj.get_role_display_name()

    def get_school_name(self, obj):
        """获取学校名称"""
        if obj.school:
            return obj.school.name
        return None

    def get_school_code(self, obj):
        """获取学校编号"""
        if obj.school:
            return obj.school.code
        return None

    def get_teaching_subjects(self, obj):
        return []


class UserCreateSerializer(serializers.ModelSerializer):
    """用户创建序列化器"""
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = [
            'username', 'password', 'password_confirm', 'real_name',
            'email', 'phone', 'employee_id', 'role'
        ]

    def validate_username(self, value):
        """验证用户名唯一性"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('该用户名已被使用')
        return value

    def validate(self, attrs):
        """验证密码一致性"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password': '两次密码不一致'})
        attrs.pop('password_confirm')
        return attrs

    def create(self, validated_data):
        """创建用户"""
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """用户更新序列化器"""

    class Meta:
        model = User
        fields = [
            'real_name', 'email', 'phone', 'employee_id',
            'role', 'roles', 'current_role', 'avatar', 'is_active'
        ]

    def validate_roles(self, value):
        """验证角色列表"""
        if not value:
            raise serializers.ValidationError('角色列表不能为空')
        # 验证所有角色都是有效的
        valid_roles = [choice[0] for choice in User.Role.choices]
        for role in value:
            if role not in valid_roles:
                raise serializers.ValidationError(f'无效的角色: {role}')
        return value

    def validate_current_role(self, value):
        """验证当前角色在角色列表中"""
        if value and 'roles' in self.initial_data:
            if value not in self.initial_data['roles']:
                raise serializers.ValidationError('当前角色必须在角色列表中')
        return value

    def validate_username(self, value):
        """验证用户名唯一性（更新时排除当前用户）"""
        instance = self.instance
        # 如果用户名在更新的字段中
        if instance and hasattr(instance, 'username') and instance.username == value:
            # 用户名没有变化，不需要验证
            return value

        # 检查用户名是否已被其他用户使用
        if User.objects.filter(username=value).exclude(id=instance.id if instance else None).exists():
            raise serializers.ValidationError('该用户名已被使用')

        return value


class PasswordChangeSerializer(serializers.Serializer):
    """修改密码序列化器"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=6)
    new_password_confirm = serializers.CharField(required=True, write_only=True, min_length=6)

    def validate(self, attrs):
        """验证新密码一致性"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password': '两次密码不一致'})
        return attrs

    def validate_old_password(self, value):
        """验证旧密码"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('旧密码错误')
        return value


class OperationLogSerializer(serializers.ModelSerializer):
    """操作日志序列化器"""
    user_name = serializers.CharField(source='user.real_name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = OperationLog
        fields = [
            'id', 'user', 'user_name', 'action', 'action_display',
            'target_model', 'target_id', 'description',
            'ip_address', 'user_agent', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class LoginQRCodeSerializer(serializers.ModelSerializer):
    """扫码登录序列化器"""
    class Meta:
        model = LoginQRCode
        fields = ['token', 'status', 'created_at']


class RemoteDeviceSerializer(serializers.ModelSerializer):
    """远程设备序列化器"""
    is_online = serializers.SerializerMethodField()
    is_agent_online = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    real_name = serializers.CharField(source='user.real_name', read_only=True)

    class Meta:
        model = RemoteDevice
        fields = [
            'id', 'device_id', 'name', 'is_locked', 
            'media_server_url', 'file_server_url',
            'is_online', 'is_agent_online', 'last_heartbeat',
            'username', 'real_name'
        ]

    def get_is_online(self, obj):
        from django.utils import timezone
        import datetime
        now = timezone.now()
        return obj.last_heartbeat and (now - obj.last_heartbeat) < datetime.timedelta(seconds=30)

    def get_is_agent_online(self, obj):
        from django.utils import timezone
        import datetime
        now = timezone.now()
        return obj.last_agent_heartbeat and (now - obj.last_agent_heartbeat) < datetime.timedelta(seconds=10)
