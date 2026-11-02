from django.contrib import admin

from .models import MatchResult


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ["batch_id", "direction", "rank", "opportunity", "candidate", "score", "generated_at"]
    list_filter = ["direction"]
    search_fields = ["opportunity__title", "candidate__email", "batch_id"]
    raw_id_fields = ["opportunity", "candidate"]
    readonly_fields = ["generated_at"]
