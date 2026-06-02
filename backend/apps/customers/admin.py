from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["id", "display_name", "phone", "gender", "created_at"]
    search_fields = ["name", "phone"]
    list_filter = ["gender"]
    readonly_fields = ["created_at", "updated_at"]
