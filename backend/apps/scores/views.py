import csv
from decimal import Decimal, InvalidOperation
from io import BytesIO, TextIOWrapper

from django.db.models import Avg, Count, Max, Min, Q
from django.http import HttpResponse
from openpyxl import Workbook, load_workbook
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.classes.models import Class
from apps.exams.models import Exam, ExamGradeSubject
from apps.students.models import Student
from apps.subjects.models import Subject
from .models import Score
from .serializers import (
    ScoreCreateUpdateSerializer,
    ScoreDetailSerializer,
    ScoreImportSerializer,
    ScoreSerializer,
)


class ScoreViewSet(viewsets.ModelViewSet):
    queryset = Score.objects.select_related("student", "exam", "subject", "created_by", "student__class_obj").all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["student", "exam", "subject", "student__class_obj"]
    search_fields = ["student__name", "student__student_id"]
    ordering_fields = ["score", "created_at"]
    ordering = ["-exam__exam_date", "student__class_obj__grade", "student__class_obj__class_number"]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if getattr(user, "school", None):
            queryset = queryset.filter(student__class_obj__school=user.school)
        if user.is_admin:
            return queryset
        return queryset.filter(student__class_obj__head_teacher=user)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ScoreDetailSerializer
        if self.action in ["create", "update", "partial_update"]:
            return ScoreCreateUpdateSerializer
        if self.action == "import_scores":
            return ScoreImportSerializer
        return ScoreSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def download_template(self, request):
        exam_id = request.query_params.get("exam_id")
        template_type = request.query_params.get("type", "single")

        workbook = Workbook()
        sheet = workbook.active

        if template_type == "multi":
            headers = ["学号", "姓名", "班级"]
            if exam_id:
                exam = Exam.objects.filter(id=exam_id).first()
                if exam:
                    names = ExamGradeSubject.objects.filter(exam=exam).select_related("subject")
                    headers.extend(sorted({item.subject.name for item in names}))
            if len(headers) == 3:
                headers.extend(["语文", "数学", "英语"])
            sheet.title = "scores_multi"
            sheet.append(headers)
            sheet.append(["2024001", "张三", "一年级1班", 95, 96, 97][: len(headers)])
        else:
            sheet.title = "scores_single"
            sheet.append(["学号", "姓名", "班级", "成绩"])
            sheet.append(["2024001", "张三", "一年级1班", 95])

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="score_import_template.xlsx"'
        return response

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def import_scores(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file = serializer.validated_data["file"]
        exam = Exam.objects.filter(id=serializer.validated_data["exam_id"]).first()
        if not exam:
            return Response({"error": "考试不存在"}, status=status.HTTP_400_BAD_REQUEST)

        subject_id = serializer.validated_data.get("subject_id")
        rows = self._read_rows(file)
        columns = list(rows[0].keys()) if rows else []
        subject_map = self._resolve_subject_columns(columns, subject_id)
        if isinstance(subject_map, Response):
            return subject_map

        result = self._save_rows(request, exam, rows, subject_map)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def import_workbook(self, request):
        file = request.FILES.get("file")
        exam_id = request.data.get("exam_id")
        if not file or not exam_id:
            return Response({"error": "file 和 exam_id 必填"}, status=status.HTTP_400_BAD_REQUEST)

        exam = Exam.objects.filter(id=exam_id).first()
        if not exam:
            return Response({"error": "考试不存在"}, status=status.HTTP_400_BAD_REQUEST)

        workbook = load_workbook(file, data_only=True)
        all_classes = list(self._class_queryset(request.user))

        success_count = 0
        errors = []
        processed_sheets = 0

        for sheet_name in workbook.sheetnames:
            class_obj = self._match_class(sheet_name, all_classes)
            if not class_obj:
                continue
            sheet = workbook[sheet_name]
            headers = [cell.value for cell in sheet[3]]
            rows = [{headers[i]: row[i] for i in range(len(headers))} for row in sheet.iter_rows(min_row=4, values_only=True)]
            subject_map = self._resolve_subject_columns(headers, None)
            if isinstance(subject_map, Response):
                continue
            result = self._save_rows(request, exam, rows, subject_map, class_obj=class_obj)
            success_count += result["success_count"]
            errors.extend(result["errors"])
            processed_sheets += 1

        return Response(
            {
                "message": "导入完成",
                "processed_sheets": processed_sheets,
                "success_count": success_count,
                "errors": errors[:50],
            }
        )

    def _read_rows(self, file):
        if file.name.endswith(".csv"):
            file.seek(0)
            return list(csv.DictReader(TextIOWrapper(file.file, encoding="utf-8-sig")))

        workbook = load_workbook(file, data_only=True)
        sheet = workbook.active
        headers = [cell.value for cell in sheet[1]]
        return [{headers[i]: row[i] for i in range(len(headers))} for row in sheet.iter_rows(min_row=2, values_only=True)]

    def _resolve_subject_columns(self, columns, subject_id):
        if subject_id:
            subject = Subject.objects.filter(id=subject_id).first()
            if not subject:
                return Response({"error": "科目不存在"}, status=status.HTTP_400_BAD_REQUEST)
            return [{"name": subject.name, "subject": subject, "column": "成绩"}]

        subject_columns = []
        ignored = {"学号", "考号", "姓名", "班级", "性别", "序号", None, ""}
        for column in columns:
            if column in ignored:
                continue
            subject = Subject.objects.filter(name=str(column).strip()).first()
            if subject:
                subject_columns.append({"name": subject.name, "subject": subject, "column": column})

        if not subject_columns:
            return Response({"error": "未识别到有效科目列"}, status=status.HTTP_400_BAD_REQUEST)
        return subject_columns

    def _save_rows(self, request, exam, rows, subject_columns, class_obj=None):
        success_count = 0
        errors = []

        for index, row in enumerate(rows, start=2):
            student = self._find_student(request.user, row, class_obj)
            if not student:
                errors.append(f"第{index}行: 未找到学生")
                continue

            for subject_info in subject_columns:
                raw_value = row.get(subject_info["column"])
                if raw_value in [None, "", "None"]:
                    continue
                try:
                    score_value = Decimal(str(raw_value).strip())
                except (InvalidOperation, AttributeError):
                    errors.append(f"第{index}行: {subject_info['name']} 分数格式错误")
                    continue

                if score_value < 0 or score_value > subject_info["subject"].full_score:
                    errors.append(f"第{index}行: {subject_info['name']} 分数超范围")
                    continue

                Score.objects.update_or_create(
                    student=student,
                    exam=exam,
                    subject=subject_info["subject"],
                    defaults={"score": score_value, "created_by": request.user},
                )
                success_count += 1

        return {"message": "导入完成", "success_count": success_count, "errors": errors}

    def _class_queryset(self, user):
        queryset = Class.objects.all()
        if getattr(user, "school", None):
            queryset = queryset.filter(school=user.school)
        if user.is_admin:
            return queryset
        return queryset.filter(head_teacher=user)

    def _find_student(self, user, row, matched_class=None):
        queryset = Student.objects.select_related("class_obj").all()
        if getattr(user, "school", None):
            queryset = queryset.filter(class_obj__school=user.school)
        if not user.is_admin:
            queryset = queryset.filter(class_obj__head_teacher=user)

        student_id = str(row.get("学号") or row.get("考号") or "").strip()
        if student_id:
            student = queryset.filter(student_id=student_id).first()
            if student:
                return student

        student_name = str(row.get("姓名") or "").strip()
        if not student_name:
            return None

        class_name = str(row.get("班级") or "").strip()
        class_obj = matched_class or self._match_class(class_name, list(self._class_queryset(user)))
        if class_obj:
            return queryset.filter(name=student_name, class_obj=class_obj).first()

        students = queryset.filter(name=student_name)
        if students.count() == 1:
            return students.first()
        return None

    def _match_class(self, class_name, all_classes):
        class_name = str(class_name or "").strip()
        if not class_name:
            return None
        for class_obj in all_classes:
            if class_obj.name == class_name or class_name in class_obj.name or class_obj.name.startswith(class_name):
                return class_obj
        return None

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        exam_id = request.query_params.get("exam_id")
        subject_id = request.query_params.get("subject_id")
        class_id = request.query_params.get("class_id")
        queryset = self.get_queryset()
        if exam_id:
            queryset = queryset.filter(exam_id=exam_id)
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if class_id:
            queryset = queryset.filter(student__class_obj_id=class_id)

        stats = queryset.aggregate(
            total_count=Count("id"),
            average_score=Avg("score"),
            max_score=Max("score"),
            min_score=Min("score"),
            pass_count=Count("id", filter=Q(score__gte=60)),
            excellent_count=Count("id", filter=Q(score__gte=90)),
        )
        total_count = stats["total_count"] or 0
        pass_count = stats["pass_count"] or 0
        excellent_count = stats["excellent_count"] or 0

        return Response(
            {
                "total_count": total_count,
                "average_score": stats["average_score"] or 0,
                "max_score": stats["max_score"] or 0,
                "min_score": stats["min_score"] or 0,
                "pass_count": pass_count,
                "pass_rate": round(pass_count * 100 / total_count, 2) if total_count else 0,
                "excellent_count": excellent_count,
                "excellent_rate": round(excellent_count * 100 / total_count, 2) if total_count else 0,
            }
        )

    @action(detail=False, methods=["get"])
    def student_history(self, request):
        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response({"error": "student_id 必填"}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset().filter(student_id=student_id).order_by("-exam__exam_date")
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
