from django.contrib import admin

from .models import Setting


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ["key", "label", "value"]
    search_fields = ["key", "label"]
    readonly_fields = ["key", "label", "description"]
    fields = ["key", "label", "description", "value"]