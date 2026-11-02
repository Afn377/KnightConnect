from django.urls import path

from . import views

urlpatterns = [
    path("requests/", views.ConnectionRequestListView.as_view(), name="request-list"),
    path("requests/<uuid:pk>/", views.ConnectionRequestDetailView.as_view(), name="request-detail"),
    path("requests/<uuid:pk>/accept/", views.AcceptRequestView.as_view(), name="request-accept"),
    path("requests/<uuid:pk>/decline/", views.DeclineRequestView.as_view(), name="request-decline"),
    path("requests/<uuid:pk>/cancel/", views.CancelRequestView.as_view(), name="request-cancel"),
    path("requests/<uuid:pk>/feedback/", views.ConnectionFeedbackView.as_view(), name="request-feedback"),
]
