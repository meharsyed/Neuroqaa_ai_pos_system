from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import ActivityLogView, ChangeOwnPasswordView, LoginView, MeView, UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("change-password/", ChangeOwnPasswordView.as_view(), name="auth-change-password"),
    path("activity/", ActivityLogView.as_view(), name="auth-activity"),
    path("", include(router.urls)),
]
