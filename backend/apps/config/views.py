from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.activity import log_activity
from apps.accounts.permissions import IsOwnerOrManager

from .models import Setting
from .serializers import SettingSerializer


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
            return [IsOwnerOrManager()]
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        """
        Record what changed.

        The tax rate, the credit-limit default and the receipt-sharing kill
        switch all live here, and until now a change to any of them left no
        trace at all — Action.SETTING_CHANGED was defined and never written.
        """
        before = serializer.instance.value
        setting = serializer.save()
        if before != setting.value:
            log_activity(
                "setting_changed",
                user=self.request.user,
                details={"key": setting.key, "from": before, "to": setting.value},
                request=self.request,
            )
