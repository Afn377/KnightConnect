from django.contrib import admin

from .models import Event, Interest, Role, Skill


@admin.register(Skill, Role, Interest)
class SluggedNameAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["name", "starts_at", "ends_at", "recruiting_ends_at", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}
