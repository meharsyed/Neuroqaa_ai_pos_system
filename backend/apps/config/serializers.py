from rest_framework import serializers

from .models import Setting


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = ["id", "key", "value", "label", "description"]
        read_only_fields = ["key", "label", "description"]
