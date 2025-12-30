from django.urls import path

from .views import (
    AlertPreferenceDetailView,
    AlertPreferenceListCreateView,
    AlertPreferencePreviewItemsView,
    NotificationLogListView,
)

app_name = "alerts"

urlpatterns = [
    path("preferences/", AlertPreferenceListCreateView.as_view(), name="list"),
    path("preferences/<int:pk>/", AlertPreferenceDetailView.as_view(), name="detail"),
    path(
        "preferences/<int:pk>/preview-items/",
        AlertPreferencePreviewItemsView.as_view(),
        name="alert-preference-preview",
    ),
    path("logs/", NotificationLogListView.as_view(), name="log-list"),
]
