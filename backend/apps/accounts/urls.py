from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityLogView,
    ChangeOwnPasswordView,
    CookieTokenRefreshView,
    LoginView,
    LogoutView,
    MeView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", CookieTokenRefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("change-password/", ChangeOwnPasswordView.as_view(), name="auth-change-password"),
    path("activity/", ActivityLogView.as_view(), name="auth-activity"),
    path("", include(router.urls)),
]
