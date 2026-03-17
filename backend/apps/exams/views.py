from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Exam, ExamGradeSubject
from .serializers import ExamCreateUpdateSerializer, ExamSerializer
from apps.subjects.serializers import SubjectSerializer


class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.prefetch_related("subjects", "grade_subjects__subject").all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["exam_type", "academic_year", "semester", "is_published", "is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["exam_date", "created_at"]
    ordering = ["-exam_date", "-created_at"]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if getattr(user, "school", None):
            queryset = queryset.filter(school__in=[user.school, None])
        if user.is_admin:
            return queryset
        return queryset.filter(created_by=user) | queryset.exclude(exam_type="quiz")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ExamCreateUpdateSerializer
        return ExamSerializer

    def perform_create(self, serializer):
        exam = serializer.save(created_by=self.request.user, school=getattr(self.request.user, "school", None))
        self._sync_grade_subjects(exam)

    def perform_update(self, serializer):
        exam = serializer.save()
        self._sync_grade_subjects(exam)

    def _sync_grade_subjects(self, exam):
        ExamGradeSubject.objects.filter(exam=exam).delete()
        subjects = list(exam.subjects.all())
        for grade in exam.applicable_grades or []:
            for subject in subjects:
                ExamGradeSubject.objects.get_or_create(exam=exam, grade=grade, subject=subject)

    @action(detail=True, methods=["get"])
    def grade_subjects(self, request, pk=None):
        exam = self.get_object()
        grade = request.query_params.get("grade")
        queryset = exam.grade_subjects.select_related("subject").all()
        if grade:
            queryset = queryset.filter(grade=grade)
        serializer = SubjectSerializer([item.subject for item in queryset], many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def current_semester(self, request):
        today = timezone.now().date()
        queryset = self.get_queryset().filter(exam_date__year=today.year)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        exam = self.get_object()
        exam.is_published = True
        exam.save(update_fields=["is_published"])
        return Response({"message": "考试已发布"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def unpublish(self, request, pk=None):
        exam = self.get_object()
        exam.is_published = False
        exam.save(update_fields=["is_published"])
        return Response({"message": "考试已取消发布"}, status=status.HTTP_200_OK)
