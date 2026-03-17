"""
科目序列化器
"""
from rest_framework import serializers
from .models import Subject


class SubjectSerializer(serializers.ModelSerializer):
    """科目序列化器"""

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'description', 'applicable_grades',
            'full_score', 'pass_score', 'order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_applicable_grades(self, value):
        """验证适用年级"""
        if not isinstance(value, list):
            raise serializers.ValidationError('适用年级必须是列表格式')

        valid_grades = [1, 2, 3, 4, 5, 6]
        for grade in value:
            if grade not in valid_grades:
                raise serializers.ValidationError(f'无效的年级：{grade}，只能是1-6')

        return value
