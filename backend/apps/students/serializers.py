"""
学生序列化器
"""
from rest_framework import serializers
from .models import Student
from apps.classes.serializers import ClassSerializer


class StudentSerializer(serializers.ModelSerializer):
    """学生序列化器"""
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    bound_username = serializers.CharField(source='user.username', read_only=True, default=None)

    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'name', 'gender', 'gender_display',
            'birth_date', 'id_number', 'class_obj', 'class_name',
            'phone', 'parent_name', 'parent_phone', 'address',
            'admission_date', 'admission_year', 'enrollment_type', 'avatar', 'notes',
            'is_active', 'learning_beans', 'bound_username', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StudentDetailSerializer(StudentSerializer):
    """学生详情序列化器"""
    class_info = ClassSerializer(source='class_obj', read_only=True)

    class Meta(StudentSerializer.Meta):
        fields = StudentSerializer.Meta.fields + ['class_info']


class StudentCreateUpdateSerializer(serializers.ModelSerializer):
    """学生创建/更新序列化器"""

    class Meta:
        model = Student
        fields = [
            'student_id', 'name', 'gender', 'birth_date', 'id_number',
            'class_obj', 'phone', 'parent_name', 'parent_phone', 'address',
            'admission_date', 'admission_year', 'enrollment_type', 'notes', 'is_active'
        ]
        extra_kwargs = {
            'student_id': {'required': False, 'allow_null': True, 'allow_blank': True},  # 学号可选，自动生成
            'birth_date': {'required': False, 'allow_null': True},
            'id_number': {'required': False, 'allow_null': True, 'allow_blank': True},
            'phone': {'required': False, 'allow_null': True, 'allow_blank': True},
            'parent_name': {'required': False, 'allow_null': True, 'allow_blank': True},
            'parent_phone': {'required': False, 'allow_null': True, 'allow_blank': True},
            'address': {'required': False, 'allow_null': True, 'allow_blank': True},
            'admission_date': {'required': False, 'allow_null': True},
            'admission_year': {'required': False, 'allow_null': True},
            'enrollment_type': {'required': False, 'allow_null': True, 'allow_blank': True},
            'notes': {'required': False, 'allow_null': True, 'allow_blank': True},
        }

    def validate(self, attrs):
        """验证学号唯一性（按学校/班主任隔离）"""
        student_id = attrs.get('student_id')
        class_obj = attrs.get('class_obj')
        instance = self.instance

        # 如果提供了学号，检查唯一性（在相同隔离范围内）
        if student_id:
            queryset = Student.objects.filter(student_id=student_id)
            
            # 按班级所属学校或班主任隔离
            if class_obj:
                if class_obj.school:
                    # 有学校，检查学校内唯一
                    queryset = queryset.filter(class_obj__school=class_obj.school)
                elif class_obj.head_teacher:
                    # 独立教师，检查该教师班级内唯一
                    queryset = queryset.filter(class_obj__head_teacher=class_obj.head_teacher)
            
            if instance:
                queryset = queryset.exclude(pk=instance.pk)

            if queryset.exists():
                raise serializers.ValidationError({'student_id': f'学号 {student_id} 已存在'})

        return attrs

    def create(self, validated_data):
        """创建学生时自动生成学号"""
        student_id = validated_data.get('student_id')
        
        # 如果没有学号，自动生成
        if not student_id:
            class_obj = validated_data.get('class_obj')
            admission_year = validated_data.get('admission_year')
            
            if not admission_year:
                from datetime import datetime
                admission_year = datetime.now().year
            
            if class_obj:
                # 生成学号格式：年份后2位+班级2位+序号2位
                class_key = f'{admission_year % 100:02d}{class_obj.class_number:02d}'
                
                # 在同一隔离范围内查找最大学号
                existing_queryset = Student.objects.filter(student_id__startswith=class_key)
                if class_obj.school:
                    existing_queryset = existing_queryset.filter(class_obj__school=class_obj.school)
                elif class_obj.head_teacher:
                    existing_queryset = existing_queryset.filter(class_obj__head_teacher=class_obj.head_teacher)
                
                max_student = existing_queryset.order_by('-student_id').first()
                
                if max_student and len(max_student.student_id) == 6:
                    try:
                        last_seq = int(max_student.student_id[-2:])
                    except:
                        last_seq = 0
                else:
                    last_seq = 0
                
                validated_data['student_id'] = f'{class_key}{last_seq + 1:02d}'
            else:
                # 没有班级时使用时间戳
                from datetime import datetime
                validated_data['student_id'] = datetime.now().strftime('%Y%m%d%H%M%S')
        
        return super().create(validated_data)



class StudentImportSerializer(serializers.Serializer):
    """学生批量导入序列化器"""
    file = serializers.FileField(required=True, help_text='Excel文件')
    class_id = serializers.IntegerField(required=False, help_text='默认班级ID（可选）')

    def validate_file(self, value):
        """验证文件格式"""
        if not value.name.endswith(('.xlsx', '.xls', '.csv')):
            raise serializers.ValidationError('只支持Excel文件(.xlsx, .xls)或CSV文件(.csv)')
        return value


# ==================== 日常记录与学生之星序列化器 ====================

from .models import StudentRecord, StudentSpotlight


class StudentRecordSerializer(serializers.ModelSerializer):
    """学生日常记录序列化器"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    class_name = serializers.CharField(source='student.class_obj.name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.username', read_only=True)
    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = StudentRecord
        fields = [
            'id', 'student', 'student_name', 'class_name',
            'record_type', 'record_type_display',
            'category', 'category_display',
            'content', 'source', 'source_detail',
            'recorded_by', 'recorded_by_name', 'record_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'recorded_by', 'created_at', 'updated_at']


class StudentRecordCreateSerializer(serializers.ModelSerializer):
    """学生日常记录创建序列化器"""
    class Meta:
        model = StudentRecord
        fields = ['student', 'record_type', 'category', 'content', 'record_date']
        extra_kwargs = {
            'record_date': {'required': False}
        }
    
    def create(self, validated_data):
        from datetime import date
        if 'record_date' not in validated_data or not validated_data['record_date']:
            validated_data['record_date'] = date.today()
        validated_data['recorded_by'] = self.context['request'].user
        return super().create(validated_data)


class BatchRecordParseSerializer(serializers.Serializer):
    """批量文本解析序列化器"""
    text = serializers.CharField(help_text='批量点评文本，如"张三背诵流利，李四帮助同学"')
    class_id = serializers.IntegerField(required=False, help_text='限定班级ID（可选）')


class BatchRecordCreateSerializer(serializers.Serializer):
    """批量创建记录序列化器"""
    records = serializers.ListField(
        child=serializers.DictField(),
        help_text='解析后的记录列表'
    )


class StudentSpotlightSerializer(serializers.ModelSerializer):
    """学生之星序列化器"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_avatar = serializers.ImageField(source='student.avatar', read_only=True)
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    period_display = serializers.CharField(source='get_period_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = StudentSpotlight
        fields = [
            'id', 'student', 'student_name', 'student_avatar',
            'class_obj', 'class_name',
            'period', 'period_display', 'spotlight_date',
            'source', 'source_display', 'recommend_reason',
            'achievements', 'teacher_comment',
            'is_displayed', 'displayed_at',
            'created_by', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at']


class SpotlightGenerateSerializer(serializers.Serializer):
    """生成今日之星序列化器"""
    class_id = serializers.IntegerField(help_text='班级ID')
    period = serializers.ChoiceField(
        choices=['daily', 'weekly', 'monthly'],
        default='daily',
        help_text='周期类型'
    )
    count = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=5,
        help_text='生成数量（可选，默认根据班级人数自动计算）'
    )


class SpotlightRecommendSerializer(serializers.Serializer):
    """教师推荐之星序列化器"""
    student_id = serializers.IntegerField(help_text='学生ID')
    reason = serializers.CharField(help_text='推荐理由')
    teacher_comment = serializers.CharField(required=False, help_text='教师寄语（可选）')
    period = serializers.ChoiceField(
        choices=['daily', 'weekly', 'monthly'],
        default='daily',
        help_text='周期类型'
    )

