from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import School
from .serializers import SchoolSerializer


class SchoolViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = School.objects.filter(is_active=True).order_by("name")
    serializer_class = SchoolSerializer
    permission_classes = [IsAuthenticated]
