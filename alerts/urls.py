from django.urls import path

from .views import (
    AlertPreferenceDetailView,
    AlertPreferenceListCreateView,
    AlertPreferencePreviewItemsView,
    NotificationLogListView,
)

urlpatterns = [
    path("preferences/", AlertPreferenceListCreateView.as_view()),
    path("preferences/<int:pk>/", AlertPreferenceDetailView.as_view()),
    path(
        "preferences/<int:pk>/preview-items/",
        AlertPreferencePreviewItemsView.as_view(),
        name="alert-preference-preview",
    ),
    path("logs/", NotificationLogListView.as_view()),
]
