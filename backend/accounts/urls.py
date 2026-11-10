from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.csrf, name="auth-csrf"),
    path("auth/request-code/", views.RequestCodeView.as_view(), name="auth-request-code"),
    path("auth/verify-code/", views.VerifyCodeView.as_view(), name="auth-verify-code"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/avatar/", views.AvatarView.as_view(), name="me-avatar"),
    path("me/contact-methods/", views.ContactMethodListView.as_view(), name="contact-method-list"),
    path(
        "me/contact-methods/<int:pk>/",
        views.ContactMethodDetailView.as_view(),
        name="contact-method-detail",
    ),
    path("users/<uuid:pk>/", views.PublicProfileView.as_view(), name="user-detail"),
]
