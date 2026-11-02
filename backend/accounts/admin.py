from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ContactMethod, User, UserSkill


class UserSkillInline(admin.TabularInline):
    model = UserSkill
    extra = 0
    autocomplete_fields = ["skill"]


class ContactMethodInline(admin.TabularInline):
    model = ContactMethod
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-created_at"]
    list_display = ["email", "display_name", "open_to_requests", "is_active", "is_staff", "created_at"]
    list_filter = ["open_to_requests", "is_active", "is_staff"]
    search_fields = ["email", "display_name"]
    readonly_fields = ["created_at", "updated_at", "last_login", "last_seen_at"]
    filter_horizontal = ["preferred_roles", "interests", "groups", "user_permissions"]
    inlines = [UserSkillInline, ContactMethodInline]

    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Profile", {"fields": ["display_name", "bio", "open_to_requests", "availability", "commitment", "preferred_roles", "interests"]}),
        ("Permissions", {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
        ("Activity", {"fields": ["last_login", "last_seen_at", "created_at", "updated_at"]}),
    ]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["email", "password1", "password2"]}),
    ]
