from django.urls import path

from . import views

urlpatterns = [
    path("blocks/", views.BlockListView.as_view(), name="block-list"),
    path("blocks/<uuid:user_id>/", views.BlockDetailView.as_view(), name="block-detail"),
]
