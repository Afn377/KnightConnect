from django.urls import path

from . import views

urlpatterns = [
    path("blocks/", views.BlockListView.as_view(), name="block-list"),
]
