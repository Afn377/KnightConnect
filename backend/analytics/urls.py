from django.urls import path

from . import views

urlpatterns = [
    path("analytics/track/", views.TrackEventView.as_view(), name="analytics-track"),
    path("analytics/funnel/", views.FunnelReportView.as_view(), name="analytics-funnel"),
]
