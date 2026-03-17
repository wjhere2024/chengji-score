"""
考试序列化器
"""
from rest_framework import serializers
from .models import Exam, ExamGradeSubject
from apps.subjects.serializers import SubjectSerializer
from apps.subjects.models import Subject


class ExamSerializer(serializers.ModelSerializer):
    """考试序列化器"""
    exam_type_display = serializers.CharField(source='get_exam_type_display', read_only=True)
    subjects_info = SubjectSerializer(source='subjects', many=True, read_only=True)
    score_count = serializers.IntegerField(read_only=True)
    created_by_id = serializers.IntegerField(source='created_by.id', read_only=True, allow_null=True)

    class Meta:
        model = Exam
        fields = [
            'id', 'name', 'exam_type', 'exam_type_display', 'academic_year', 'semester',
            'exam_date', 'start_time', 'end_time', 'applicable_grades',
            'subjects', 'subjects_info', 'score_deadline', 'description',
            'is_published', 'is_active', 'score_count', 'created_by_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'score_count', 'created_by_id', 'created_at', 'updated_at']


class ExamCreateUpdateSerializer(serializers.ModelSerializer):
    """考试创建/更新序列化器"""

    class Meta:
        model = Exam
        fields = [
            'name', 'exam_type', 'academic_year', 'semester',
            'exam_date', 'start_time', 'end_time', 'applicable_grades',
            'subjects', 'score_deadline', 'description',
            'is_published', 'is_active'
        ]
        extra_kwargs = {
            'start_time': {'required': False, 'allow_null': True},
            'end_time': {'required': False, 'allow_null': True},
            'score_deadline': {'required': False, 'allow_null': True},
            'description': {'required': False, 'allow_null': True, 'allow_blank': True},
        }

    def validate_applicable_grades(self, value):
        """验证适用年级"""
        if not isinstance(value, list):
            raise serializers.ValidationError('适用年级必须是列表格式')

        if not value:
            raise serializers.ValidationError('请至少选择一个年级')

        valid_grades = [1, 2, 3, 4, 5, 6]
        for grade in value:
            if grade not in valid_grades:
                raise serializers.ValidationError(f'无效的年级：{grade}，只能是1-6')

        return value

    def validate_subjects(self, value):
        """验证考试科目"""
        if not value:
            raise serializers.ValidationError('请至少选择一个考试科目')
        return value

    def create(self, validated_data):
        """
        创建考试时，自动创建年级-科目关系
        规则：一二年级只考语文和数学，三到六年级考所有选定科目
        """
        # 提取科目和年级数据
        subjects_data = validated_data.pop('subjects', [])
        grades = validated_data.get('applicable_grades', [])

        # 创建考试
        exam = Exam.objects.create(**validated_data)

        # 设置考试科目
        exam.subjects.set(subjects_data)

        # 获取科学和英语科目的ID
        excluded_subject_names = ['科学', '英语']
        excluded_subjects = Subject.objects.filter(name__in=excluded_subject_names)
        excluded_subject_ids = set(excluded_subjects.values_list('id', flat=True))

        # 为每个年级创建科目关系
        for grade in grades:
            for subject in subjects_data:
                # 如果是一二年级，跳过科学和英语
                if grade in [1, 2] and subject.id in excluded_subject_ids:
                    continue

                # 创建年级-科目关系
                ExamGradeSubject.objects.create(
                    exam=exam,
                    grade=grade,
                    subject=subject
                )

        return exam

    def update(self, instance, validated_data):
        """
        更新考试时，重新创建年级-科目关系
        """
        # 提取科目和年级数据
        subjects_data = validated_data.pop('subjects', None)
        grades = validated_data.get('applicable_grades', instance.applicable_grades)

        # 更新考试基本信息
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # 如果更新了科目，重新设置
        if subjects_data is not None:
            instance.subjects.set(subjects_data)

            # 删除旧的年级-科目关系
            ExamGradeSubject.objects.filter(exam=instance).delete()

            # 获取科学和英语科目的ID
            excluded_subject_names = ['科学', '英语']
            excluded_subjects = Subject.objects.filter(name__in=excluded_subject_names)
            excluded_subject_ids = set(excluded_subjects.values_list('id', flat=True))

            # 重新创建年级-科目关系
            for grade in grades:
                for subject in subjects_data:
                    # 如果是一二年级，跳过科学和英语
                    if grade in [1, 2] and subject.id in excluded_subject_ids:
                        continue

                    # 创建年级-科目关系
                    ExamGradeSubject.objects.create(
                        exam=instance,
                        grade=grade,
                        subject=subject
                    )

        return instance
