from django.contrib import admin
from django.utils import timezone

from .models import Block, Report


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ["blocker", "blocked", "created_at"]
    search_fields = ["blocker__email", "blocked__email"]
    raw_id_fields = ["blocker", "blocked"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Moderation queue: open reports are listed first."""

    list_display = ["reported_user", "reason", "status", "reporter", "created_at", "reviewed_at"]
    list_filter = ["status", "reason"]
    search_fields = ["reported_user__email", "reporter__email", "details"]
    raw_id_fields = ["reporter", "reported_user", "opportunity"]
    readonly_fields = ["reporter", "reported_user", "opportunity", "reason", "details", "created_at", "reviewed_by", "reviewed_at"]
    fields = ["reported_user", "reporter", "opportunity", "reason", "details", "status", "moderator_notes", "reviewed_by", "reviewed_at", "created_at"]
    actions = ["mark_actioned", "mark_dismissed"]

    def save_model(self, request, obj, form, change):
        if change and "status" in form.changed_data and obj.status != Report.Status.OPEN:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)

    def _resolve(self, request, queryset, status):
        queryset.update(status=status, reviewed_by=request.user, reviewed_at=timezone.now())

    @admin.action(description="Mark selected reports as actioned")
    def mark_actioned(self, request, queryset):
        self._resolve(request, queryset, Report.Status.ACTIONED)

    @admin.action(description="Dismiss selected reports")
    def mark_dismissed(self, request, queryset):
        self._resolve(request, queryset, Report.Status.DISMISSED)
