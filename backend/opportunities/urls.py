from django.urls import path

from . import views

urlpatterns = [
    path("opportunities/", views.OpportunityListView.as_view(), name="opportunity-list"),
]
