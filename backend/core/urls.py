from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("internal/maintenance/", views.MaintenanceView.as_view(), name="maintenance"),
]
