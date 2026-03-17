"""
成绩序列化器
"""
from rest_framework import serializers
from .models import Score
from apps.students.serializers import StudentSerializer
from apps.exams.serializers import ExamSerializer
from apps.subjects.serializers import SubjectSerializer


class ScoreSerializer(serializers.ModelSerializer):
    """成绩序列化器"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    class_name = serializers.CharField(source='student.class_obj.name', read_only=True)
    is_pass = serializers.BooleanField(read_only=True)
    is_excellent = serializers.BooleanField(read_only=True)
    created_by_name = serializers.CharField(source='created_by.real_name', read_only=True)

    class Meta:
        model = Score
        fields = [
            'id', 'student', 'student_name', 'student_id', 'exam', 'exam_name',
            'subject', 'subject_name', 'class_name', 'score', 'class_rank',
            'grade_rank', 'is_pass', 'is_excellent', 'notes',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ScoreDetailSerializer(ScoreSerializer):
    """成绩详情序列化器"""
    student_info = StudentSerializer(source='student', read_only=True)
    exam_info = ExamSerializer(source='exam', read_only=True)
    subject_info = SubjectSerializer(source='subject', read_only=True)

    class Meta(ScoreSerializer.Meta):
        fields = ScoreSerializer.Meta.fields + ['student_info', 'exam_info', 'subject_info']


class ScoreCreateUpdateSerializer(serializers.ModelSerializer):
    """成绩创建/更新序列化器"""

    class Meta:
        model = Score
        fields = ['student', 'exam', 'subject', 'score', 'notes']

    def validate(self, attrs):
        """验证成绩"""
        student = attrs.get('student')
        exam = attrs.get('exam')
        subject = attrs.get('subject')
        score = attrs.get('score')

        # 验证成绩范围
        if score > subject.full_score:
            raise serializers.ValidationError({
                'score': f'分数不能超过满分{subject.full_score}'
            })

        # 验证成绩唯一性
        instance = self.instance
        queryset = Score.objects.filter(
            student=student,
            exam=exam,
            subject=subject
        )

        if instance:
            queryset = queryset.exclude(pk=instance.pk)

        if queryset.exists():
            raise serializers.ValidationError('该学生在此考试的该科目成绩已存在')

        return attrs


class ScoreImportSerializer(serializers.Serializer):
    """
    成绩批量导入序列化器

    支持两种导入模式：
    1. 单科目导入：需要提供 subject_id，Excel中包含"学号/姓名"和"成绩"列
    2. 多科目导入：不提供 subject_id，Excel中包含"学号/姓名"和多个科目列
    """
    file = serializers.FileField(required=True, help_text='Excel文件')
    exam_id = serializers.IntegerField(required=True, help_text='考试ID')
    subject_id = serializers.IntegerField(required=False, allow_null=True, help_text='科目ID（单科目导入时必填）')

    def validate_file(self, value):
        """验证文件格式"""
        if not value.name.endswith(('.xlsx', '.xls', '.csv')):
            raise serializers.ValidationError('只支持Excel文件(.xlsx, .xls)或CSV文件(.csv)')
        return value


class ScoreStatisticsSerializer(serializers.Serializer):
    """成绩统计序列化器"""
    total_count = serializers.IntegerField(help_text='总人数')
    average_score = serializers.DecimalField(max_digits=5, decimal_places=2, help_text='平均分')
    max_score = serializers.DecimalField(max_digits=5, decimal_places=1, help_text='最高分')
    min_score = serializers.DecimalField(max_digits=5, decimal_places=1, help_text='最低分')
    pass_count = serializers.IntegerField(help_text='及格人数')
    pass_rate = serializers.DecimalField(max_digits=5, decimal_places=2, help_text='及格率')
    excellent_count = serializers.IntegerField(help_text='优秀人数')
    excellent_rate = serializers.DecimalField(max_digits=5, decimal_places=2, help_text='优秀率')
