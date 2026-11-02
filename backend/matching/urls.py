from django.urls import path

from . import views

urlpatterns = [
    path("opportunities/<uuid:pk>/matches/", views.OpportunityMatchesView.as_view(), name="opportunity-matches"),
]
