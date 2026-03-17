"""
成绩序列化器
"""
from rest_framework import serializers

from .models import Score
from apps.exams.serializers import ExamSerializer
from apps.students.serializers import StudentSerializer
from apps.subjects.serializers import SubjectSerializer


class ScoreSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name", read_only=True)
    student_id = serializers.CharField(source="student.student_id", read_only=True)
    exam_name = serializers.CharField(source="exam.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    class_name = serializers.CharField(source="student.class_obj.name", read_only=True)
    is_pass = serializers.BooleanField(read_only=True)
    is_excellent = serializers.BooleanField(read_only=True)
    created_by_name = serializers.CharField(source="created_by.real_name", read_only=True)

    class Meta:
        model = Score
        fields = [
            "id",
            "student",
            "student_name",
            "student_id",
            "exam",
            "exam_name",
            "subject",
            "subject_name",
            "class_name",
            "score",
            "class_rank",
            "grade_rank",
            "is_pass",
            "is_excellent",
            "notes",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ScoreDetailSerializer(ScoreSerializer):
    student_info = StudentSerializer(source="student", read_only=True)
    exam_info = ExamSerializer(source="exam", read_only=True)
    subject_info = SubjectSerializer(source="subject", read_only=True)

    class Meta(ScoreSerializer.Meta):
        fields = ScoreSerializer.Meta.fields + ["student_info", "exam_info", "subject_info"]


class ScoreCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Score
        fields = ["student", "exam", "subject", "score", "notes"]

    def validate(self, attrs):
        student = attrs.get("student")
        exam = attrs.get("exam")
        subject = attrs.get("subject")
        score = attrs.get("score")

        if score > subject.full_score:
            raise serializers.ValidationError({"score": f"分数不能超过满分 {subject.full_score}"})

        instance = self.instance
        queryset = Score.objects.filter(student=student, exam=exam, subject=subject)
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("该学生在本次考试的该科成绩已存在")

        return attrs


class ScoreImportSerializer(serializers.Serializer):
    file = serializers.FileField(required=True, help_text="Excel or CSV file")
    exam_id = serializers.IntegerField(required=True, help_text="exam id")
    subject_id = serializers.IntegerField(required=False, allow_null=True, help_text="optional subject id")

    def validate_file(self, value):
        if not value.name.endswith((".xlsx", ".xls", ".csv")):
            raise serializers.ValidationError("只支持 Excel 或 CSV 文件")
        return value


class ScoreTextParseSerializer(serializers.Serializer):
    text = serializers.CharField(required=True, help_text="score lines such as '张三 95'")
    exam_id = serializers.IntegerField(required=True, help_text="exam id")
    subject_id = serializers.IntegerField(required=True, help_text="subject id")
    class_id = serializers.IntegerField(required=False, allow_null=True, help_text="optional class id")


class ScoreTextImportConfirmSerializer(serializers.Serializer):
    exam_id = serializers.IntegerField(required=True, help_text="exam id")
    subject_id = serializers.IntegerField(required=True, help_text="subject id")
    records = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
        help_text="confirmed parsed records",
    )


class ScoreStatisticsSerializer(serializers.Serializer):
    total_count = serializers.IntegerField(help_text="record count")
    average_score = serializers.DecimalField(max_digits=5, decimal_places=2, help_text="average score")
    max_score = serializers.DecimalField(max_digits=5, decimal_places=1, help_text="max score")
    min_score = serializers.DecimalField(max_digits=5, decimal_places=1, help_text="min score")
    pass_count = serializers.IntegerField(help_text="pass count")
    pass_rate = serializers.DecimalField(max_digits=5, decimal_places=2, help_text="pass rate")
    excellent_count = serializers.IntegerField(help_text="excellent count")
    excellent_rate = serializers.DecimalField(max_digits=5, decimal_places=2, help_text="excellent rate")
