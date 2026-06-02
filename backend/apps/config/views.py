from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Setting
from .serializers import SettingSerializer


class _IsOwnerOrManager(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.role in ("owner", "manager")


class SettingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    lookup_field = "key"
    pagination_class = None  # always small; return full list as array

    def get_permissions(self):
        if self.action in ("update", "partial_update"):
            return [_IsOwnerOrManager()]
        return [IsAuthenticated()]
