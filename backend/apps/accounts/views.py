from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .activity import log_activity
from .models import ActivityLog, User
from .permissions import IsOwner
from .serializers import (
    ChangeOwnPasswordSerializer,
    CreateUserSerializer,
    POSTokenObtainPairSerializer,
    SetPasswordSerializer,
    UpdateUserSerializer,
    UserSerializer,
)


class LoginView(TokenObtainPairView):
    serializer_class = POSTokenObtainPairSerializer
    throttle_scope = "login"

    @extend_schema(
        summary="Login",
        description="Returns access + refresh tokens plus the authenticated user object.",
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            user_data = response.data.get("user", {})
            ip = (
                request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                or request.META.get("REMOTE_ADDR", "")
            )
            # Look up the user object to pass to log_activity
            from apps.accounts.models import User
            try:
                user_obj = User.objects.get(email=user_data.get("email", ""))
                log_activity(
                    "login",
                    user=user_obj,
                    details={"email": user_data.get("email"), "role": user_data.get("role")},
                    request=request,
                )
            except User.DoesNotExist:
                pass
        return response

    def handle_exception(self, exc):
        """
        Record failures as well as successes.

        Only successful logins were ever logged, so a password-guessing run
        against this endpoint left no trace at all. The email attempted is
        recorded; the password never is.
        """
        response = super().handle_exception(exc)
        if response is not None and response.status_code in (400, 401):
            request = self.request
            attempted = ""
            try:
                attempted = str(request.data.get("email", ""))[:150]
            except Exception:
                pass
            log_activity(
                "login_failed",
                user=None,
                details={"email": attempted},
                request=request,
            )
        return response


class ChangeOwnPasswordView(APIView):
    """
    Any signed-in user changing their own password.

    Without this the only way to change a password was a command line, which on
    a hosted deployment means telephoning the developer.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Change your own password", request=ChangeOwnPasswordSerializer)
    def post(self, request):
        serializer = ChangeOwnPasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])

        log_activity("password_changed", user=user, details={"self": True}, request=request)
        # The old tokens still work — they are signed, not stored. Say so rather
        # than implying every other device has been signed out.
        return Response({"detail": "Password changed."})


class UserViewSet(viewsets.ModelViewSet):
    """
    Staff accounts. Owner only.

    A manager must not manage users: if he could, he could promote himself and
    the difference between the roles would mean nothing.
    """

    queryset = User.objects.order_by("-is_active", "first_name", "email")
    permission_classes = [IsOwner]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["email", "first_name", "last_name", "phone"]
    ordering_fields = ["created_at", "last_login", "email"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateUserSerializer
        if self.action in ("update", "partial_update"):
            return UpdateUserSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_activity(
            "user_created", user=request.user,
            details={"email": user.email, "role": user.role}, request=request,
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        target = self.get_object()
        before = {"role": target.role, "is_active": target.is_active}

        # The owner is the account that can undo everything else. Locking it out
        # or demoting it would leave nobody able to put it back.
        if target.pk == request.user.pk:
            if request.data.get("role") not in (None, target.role):
                return Response(
                    {"detail": "You cannot change your own role."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if request.data.get("is_active") is False:
                return Response(
                    {"detail": "You cannot deactivate your own account."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if (
            target.role == "owner"
            and request.data.get("role") not in (None, "owner")
            and User.objects.filter(role="owner", is_active=True).count() <= 1
        ):
            return Response(
                {"detail": "This is the last owner. Make somebody else an owner first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = super().partial_update(request, *args, **kwargs)
        target.refresh_from_db()
        after = {"role": target.role, "is_active": target.is_active}
        if before != after:
            log_activity(
                "user_updated", user=request.user,
                details={"email": target.email, "before": before, "after": after},
                request=request,
            )
        return Response(UserSerializer(target).data, status=response.status_code)

    @extend_schema(
        summary="Set a staff member's password — owner only",
        request=SetPasswordSerializer,
    )
    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        target = self.get_object()
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target.set_password(serializer.validated_data["password"])
        # Temporary by definition — they choose their own on next sign-in.
        target.must_change_password = True
        target.save(update_fields=["password", "must_change_password", "updated_at"])

        log_activity(
            "password_reset", user=request.user,
            details={"email": target.email}, request=request,
        )
        return Response({"detail": f"Password set for {target.email}."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Current user", responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ── Activity log API ───────────────────────────────────────────────────────────

class ActivityLogSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            "id", "action", "user", "user_email",
            "details", "ip_address", "created_at",
        ]

    def get_user_email(self, obj) -> str:
        return obj.user.email if obj.user else "system"


class ActivityLogView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Activity log — owner/manager only")
    def get(self, request):
        if request.user.role not in ("owner", "manager"):
            return Response(
                {"detail": "Only owner or manager can view the activity log."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = ActivityLog.objects.select_related("user").order_by("-created_at")

        action = request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        user_id = request.query_params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)

        # Simple pagination
        page_size = 50
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1

        offset = (page - 1) * page_size
        total = qs.count()
        items = qs[offset: offset + page_size]

        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": ActivityLogSerializer(items, many=True).data,
        })