from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

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

# ── Refresh-token cookie ─────────────────────────────────────────────────────
#
# The refresh token never reaches JavaScript. It travels only as an httpOnly
# cookie scoped to /api/auth/, set here and read by CookieTokenRefreshView —
# so an XSS anywhere in the app can steal the access token (30 min, low value)
# but not the refresh token that would let it keep coming back for days.


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=settings.JWT_REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.JWT_REFRESH_COOKIE_SECURE,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )


# ── Login lockout ────────────────────────────────────────────────────────────
#
# The `login` throttle scope (10/min, see REST_FRAMEWORK settings) limits how
# fast anyone can hit this endpoint at all. This is a second, narrower guard
# on top of it: it locks the one account being guessed at, using the
# login_failed activity log that already exists — no new table, no cache
# backend to configure, and it works correctly across every gunicorn worker
# because it reads from the database.
LOGIN_LOCKOUT_THRESHOLD = 5
LOGIN_LOCKOUT_WINDOW = timedelta(minutes=15)


def _recent_failed_attempts(email: str) -> int:
    if not email:
        return 0
    since = timezone.now() - LOGIN_LOCKOUT_WINDOW
    return ActivityLog.objects.filter(
        action="login_failed",
        details__email__iexact=email,
        created_at__gte=since,
    ).count()


class LoginView(TokenObtainPairView):
    serializer_class = POSTokenObtainPairSerializer
    throttle_scope = "login"
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Login",
        description=(
            "Returns an access token plus the authenticated user object. "
            "The refresh token is set as an httpOnly cookie, not returned in the body."
        ),
    )
    def post(self, request, *args, **kwargs):
        attempted_email = str(request.data.get("email", ""))[:150].strip()

        failures = _recent_failed_attempts(attempted_email)
        if failures >= LOGIN_LOCKOUT_THRESHOLD:
            log_activity(
                "login_locked", user=None, details={"email": attempted_email}, request=request,
            )
            return Response(
                {
                    "detail": (
                        "Too many failed attempts for this account. "
                        f"Try again in {LOGIN_LOCKOUT_WINDOW.seconds // 60} minutes, "
                        "or ask an owner to reset the password."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            refresh_token = response.data.pop("refresh", None)
            if refresh_token:
                _set_refresh_cookie(response, refresh_token)

            user_data = response.data.get("user", {})
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


class CookieTokenRefreshView(TokenRefreshView):
    """
    Same as SimpleJWT's TokenRefreshView, except the refresh token comes from
    the httpOnly cookie instead of the request body, and the (rotated) refresh
    token goes back out the same way rather than in the JSON response.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        cookie_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not cookie_token:
            return Response(
                {"detail": "No refresh token cookie — please sign in again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data["refresh"] = cookie_token
        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            response = Response(
                {"detail": "Your session has expired — please sign in again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _clear_refresh_cookie(response)
            return response

        result = dict(serializer.validated_data)
        rotated_refresh = result.pop("refresh", None)
        response = Response(result, status=status.HTTP_200_OK)
        if rotated_refresh:
            _set_refresh_cookie(response, rotated_refresh)
        return response


class LogoutView(APIView):
    """
    Blacklists the refresh token (so it cannot be replayed even if it leaked)
    and clears the cookie. Always succeeds from the client's point of view —
    there is nothing useful to do differently if the cookie is already gone
    or the token already expired.
    """

    permission_classes = [AllowAny]

    @extend_schema(summary="Log out — blacklists the refresh token")
    def post(self, request):
        cookie_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if cookie_token:
            try:
                RefreshToken(cookie_token).blacklist()
            except TokenError:
                pass

        if request.user and request.user.is_authenticated:
            log_activity("logout", user=request.user, details={}, request=request)

        response = Response({"detail": "Logged out."})
        _clear_refresh_cookie(response)
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
        # Any access token issued before this still works until it naturally
        # expires (up to 30 min) — it is signed, not stored, so nothing short
        # of that expiry invalidates it early. Refresh tokens *can* now be
        # revoked (LogoutView blacklists one on sign-out), but a password
        # change does not automatically blacklist every outstanding refresh
        # token for this user — only an explicit sign-out on each device does.
        # Worth revisiting if "someone else is on my account" ever comes up.
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