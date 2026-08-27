from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .activity import log_activity
from .models import ActivityLog
from .serializers import POSTokenObtainPairSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    serializer_class = POSTokenObtainPairSerializer

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