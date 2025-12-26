from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("features/", views.features, name="features"),
    path("pricing/", views.pricing, name="pricing"),
    path("contact/", views.contact, name="contact"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
