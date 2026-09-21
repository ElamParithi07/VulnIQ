from django.urls import path

from .views import EmailLoginView, EmailLogoutView, SignUpView, VerifyEmailView


urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", EmailLoginView.as_view(), name="login"),
    path("logout/", EmailLogoutView.as_view(), name="logout"),
    path("verify/<str:token>/", VerifyEmailView.as_view(), name="verify-email"),
]
