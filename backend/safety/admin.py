from django.contrib import admin, messages
from django.utils import timezone

from opportunities.models import Opportunity
from opportunities.services import close_opportunity

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
    actions = ["mark_actioned", "mark_dismissed", "close_reported_opportunities"]

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

    @admin.action(description="Close the reported opportunity and mark the report actioned")
    def close_reported_opportunities(self, request, queryset):
        closed = skipped = 0
        for report in queryset.select_related("opportunity"):
            opportunity = report.opportunity
            if opportunity is None or opportunity.status != Opportunity.Status.OPEN:
                skipped += 1
                continue
            close_opportunity(opportunity, Opportunity.CloseReason.MODERATION, actor=request.user)
            report.status = Report.Status.ACTIONED
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
            closed += 1
        self.message_user(request, f"Closed {closed} opportunit{'y' if closed == 1 else 'ies'}.")
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} report(s) with no open opportunity attached.",
                level=messages.WARNING,
            )
