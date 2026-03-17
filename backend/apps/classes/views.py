from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Class
from .serializers import ClassCreateUpdateSerializer, ClassDetailSerializer, ClassSerializer


class ClassViewSet(viewsets.ModelViewSet):
    queryset = Class.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["grade", "head_teacher", "is_active"]
    search_fields = ["name", "classroom"]
    ordering_fields = ["grade", "class_number", "student_count", "created_at"]
    ordering = ["grade", "class_number"]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if getattr(user, "school", None):
            queryset = queryset.filter(school=user.school)

        if user.is_admin:
            return queryset

        return queryset.filter(head_teacher=user)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ClassDetailSerializer
        if self.action in ["create", "update", "partial_update"]:
            return ClassCreateUpdateSerializer
        return ClassSerializer

    def perform_create(self, serializer):
        user = self.request.user
        kwargs = {}
        if getattr(user, "school", None):
            kwargs["school"] = user.school
        if user.is_head_teacher and not serializer.validated_data.get("head_teacher"):
            kwargs["head_teacher"] = user
        serializer.save(**kwargs)

    @action(detail=False, methods=["get"])
    def my_classes(self, request):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def update_student_count(self, request, pk=None):
        class_obj = self.get_object()
        class_obj.update_student_count()
        return Response({"student_count": class_obj.student_count})

    @action(detail=True, methods=["post"])
    def reset_student_invite_code(self, request, pk=None):
        class_obj = self.get_object()
        code = class_obj.reset_student_invite_code()
        return Response({"student_invite_code": code}, status=status.HTTP_200_OK)
