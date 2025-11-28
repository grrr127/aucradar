from django.urls import path

from .views import (
    AlertPreferenceDetailView,
    AlertPreferenceListCreateView,
    NotificationLogListView,
)

urlpatterns = [
    path("preferences/", AlertPreferenceListCreateView.as_view()),
    path("preferences/<int:pk>/", AlertPreferenceDetailView.as_view()),
    path("logs/", NotificationLogListView.as_view()),
]
