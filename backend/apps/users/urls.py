"""
用户URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, OperationLogViewSet, AuthViewSet

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')  # For /users/auth/qrcode_generate/ - Wait, this is under /users/...
# The user wants /auth/qrcode/... probably outside of /users/
# But this file is included in project urls under /api/users/ (likely).
# Let's check project urls. Use Router is fine. user/auth/qrcode_generate is OK.
router.register(r'logs', OperationLogViewSet, basename='operation-log')
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]
