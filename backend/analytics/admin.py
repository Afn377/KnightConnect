from django.contrib import admin

from .models import FunnelEvent


@admin.register(FunnelEvent)
class FunnelEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "user", "opportunity", "occurred_at"]
    list_filter = ["event_type"]
    date_hierarchy = "occurred_at"
    raw_id_fields = ["user", "opportunity", "match_result", "connection_request"]

    def has_change_permission(self, request, obj=None):
        return False
