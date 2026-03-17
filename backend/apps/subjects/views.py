from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsAdmin
from .models import Subject
from .serializers import SubjectSerializer


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_active"]
    search_fields = ["name", "code"]
    ordering_fields = ["order", "created_at"]
    ordering = ["order", "id"]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if getattr(user, "school", None):
            queryset = queryset.filter(school__in=[user.school, None])
        return queryset

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "batch_create"]:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(school=getattr(user, "school", None))

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsAdmin])
    def batch_create(self, request):
        names = request.data.get("subjects", [])
        created = []
        skipped = []
        next_order = Subject.objects.order_by("-order").first()
        current_order = next_order.order if next_order else 0

        for name in names:
            name = str(name).strip()
            if not name:
                continue
            if Subject.objects.filter(name=name).exists():
                skipped.append(name)
                continue
            current_order += 10
            code = name[:4].upper()
            Subject.objects.create(
                name=name,
                code=code,
                order=current_order,
                school=getattr(request.user, "school", None),
            )
            created.append(name)

        return Response({"created": created, "skipped": skipped}, status=status.HTTP_200_OK)
