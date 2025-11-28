from django.urls import path

from users.views import (
    CookieRefreshView,
    EmailSendCodeView,
    EmailVerifyCodeView,
    LoginView,
    LogoutView,
    MeView,
    SignUpView,
)

urlpatterns = [
    path("email/send-code/", EmailSendCodeView.as_view()),
    path("email/verify-code/", EmailVerifyCodeView.as_view()),
    path("signup/", SignUpView.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("token/refresh/", CookieRefreshView.as_view()),
    path("me/", MeView.as_view()),
]
