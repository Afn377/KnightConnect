from django.contrib import admin

from .models import Opportunity, OpportunityRole, OpportunitySkill


class OpportunityRoleInline(admin.TabularInline):
    model = OpportunityRole
    extra = 0
    autocomplete_fields = ["role"]


class OpportunitySkillInline(admin.TabularInline):
    model = OpportunitySkill
    extra = 0
    autocomplete_fields = ["skill"]


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "event", "opportunity_type", "status", "expires_at", "created_at"]
    list_filter = ["status", "opportunity_type", "event"]
    search_fields = ["title", "description", "owner__email"]
    autocomplete_fields = ["owner"]
    filter_horizontal = ["interests"]
    readonly_fields = ["created_at", "updated_at", "closed_at"]
    inlines = [OpportunityRoleInline, OpportunitySkillInline]
