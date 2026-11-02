from django.contrib import admin

from .models import ConnectionFeedback, ConnectionRequest


@admin.register(ConnectionRequest)
class ConnectionRequestAdmin(admin.ModelAdmin):
    list_display = ["opportunity", "kind", "sender", "recipient", "status", "created_at", "responded_at"]
    list_filter = ["kind", "status"]
    search_fields = ["opportunity__title", "sender__email", "recipient__email"]
    autocomplete_fields = ["sender", "recipient"]
    raw_id_fields = ["opportunity", "opportunity_role"]
    readonly_fields = ["created_at", "updated_at", "responded_at"]


@admin.register(ConnectionFeedback)
class ConnectionFeedbackAdmin(admin.ModelAdmin):
    list_display = ["connection_request", "user", "was_useful", "created_at"]
    list_filter = ["was_useful"]
    raw_id_fields = ["connection_request", "user"]
