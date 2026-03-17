from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/users/", include("apps.users.urls")),
    path("api/schools/", include("apps.schools.api_urls")),
    path("api/classes/", include("apps.classes.urls")),
    path("api/students/", include("apps.students.urls")),
    path("api/subjects/", include("apps.subjects.urls")),
    path("api/exams/", include("apps.exams.urls")),
    path("api/scores/", include("apps.scores.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

