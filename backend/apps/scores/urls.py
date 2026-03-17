"""
成绩URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScoreViewSet

router = DefaultRouter()
router.register(r'', ScoreViewSet, basename='score')

urlpatterns = [
    path('', include(router.urls)),
]
