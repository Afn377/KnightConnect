from django.urls import path

from . import views

urlpatterns = [
    path("opportunities/", views.OpportunityListView.as_view(), name="opportunity-list"),
    path("opportunities/mine/", views.MyOpportunitiesView.as_view(), name="opportunity-mine"),
    path("opportunities/<uuid:pk>/", views.OpportunityDetailView.as_view(), name="opportunity-detail"),
    path("opportunities/<uuid:pk>/close/", views.OpportunityCloseView.as_view(), name="opportunity-close"),
]
