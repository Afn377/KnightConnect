from django.urls import path

from . import views

urlpatterns = [
    path("skills/", views.SkillListView.as_view(), name="skill-list"),
]
