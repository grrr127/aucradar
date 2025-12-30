from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("features/", views.features, name="features"),
    path("pricing/", views.pricing, name="pricing"),
    path("contact/", views.contact, name="contact"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("accounts/signup/", views.signup, name="signup"),
    path("watchlist/", views.watchlist, name="watchlist"),
    path("alerts/", views.alerts, name="alerts"),
    path("profile/", views.profile, name="profile"),
]
