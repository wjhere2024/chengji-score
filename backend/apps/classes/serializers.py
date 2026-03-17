"""
班级序列化器
"""
from rest_framework import serializers
from .models import Class, StudentGroup, StudentGroupMember
from apps.users.serializers import UserSerializer


class ClassSerializer(serializers.ModelSerializer):
    """班级序列化器"""
    grade_display = serializers.CharField(source='get_grade_display', read_only=True)
    head_teacher_name = serializers.CharField(source='head_teacher.real_name', read_only=True)

    class Meta:
        model = Class
        fields = [
            'id', 'name', 'grade', 'grade_display', 'class_number',
            'head_teacher', 'head_teacher_name',
            'student_count', 'classroom', 'description', 'is_active',
            'student_invite_code',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'student_count', 'created_at', 'updated_at']


class ClassDetailSerializer(ClassSerializer):
    """班级详情序列化器"""
    head_teacher_info = UserSerializer(source='head_teacher', read_only=True)

    class Meta(ClassSerializer.Meta):
        fields = ClassSerializer.Meta.fields + ['head_teacher_info']


class ClassCreateUpdateSerializer(serializers.ModelSerializer):
    """班级创建/更新序列化器"""

    class Meta:
        model = Class
        fields = [
            'name', 'grade', 'class_number', 'head_teacher',
            'classroom', 'description', 'is_active'
        ]

    def validate(self, attrs):
        """验证班级唯一性（考虑学校隔离）"""
        grade = attrs.get('grade')
        class_number = attrs.get('class_number')

        # 获取当前用户
        request = self.context.get('request')
        user = request.user if request else None

        # 检查是否是更新操作
        instance = self.instance

        # 构建查询条件
        queryset = Class.objects.filter(
            grade=grade,
            class_number=class_number,
        )

        # 根据用户类型添加隔离条件
        if user:
            if hasattr(user, 'school') and user.school:
                queryset = queryset.filter(school=user.school)
            else:
                queryset = queryset.filter(head_teacher=user)

        if instance:
            queryset = queryset.exclude(pk=instance.pk)

        if queryset.exists():
            raise serializers.ValidationError({
                'class_number': f'{Class.Grade(grade).label}{class_number}班已存在'
            })

        # 生成班级名称
        if not attrs.get('name'):
            attrs['name'] = f"{Class.Grade(grade).label}{class_number}班"

        return attrs


class StudentGroupMemberSerializer(serializers.ModelSerializer):
    """小组成员序列化器"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    
    class Meta:
        model = StudentGroupMember
        fields = ['id', 'student', 'student_name', 'student_id', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class StudentGroupSerializer(serializers.ModelSerializer):
    """小组序列化器"""
    member_count = serializers.IntegerField(read_only=True)
    members = StudentGroupMemberSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.real_name', read_only=True)
    
    class Meta:
        model = StudentGroup
        fields = ['id', 'name', 'color', 'class_obj', 'member_count', 'members', 
                  'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class StudentGroupCreateSerializer(serializers.ModelSerializer):
    """小组创建序列化器"""
    class Meta:
        model = StudentGroup
        fields = ['name', 'color', 'class_obj']
    
    def validate(self, attrs):
        # 检查同班级下小组名是否重复
        class_obj = attrs.get('class_obj')
        name = attrs.get('name')
        
        if StudentGroup.objects.filter(class_obj=class_obj, name=name).exists():
            raise serializers.ValidationError({
                'name': f'该班级已存在名为"{name}"的小组'
            })
        return attrs
