from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination

from .models import AlertPreference, NotificationLog
from .serializers import AlertPreferenceSerializer, NotificationLogSerializer


class AlertPreferenceListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AlertPreferenceSerializer

    def get_queryset(self):
        return AlertPreference.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )


class AlertPreferenceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AlertPreferenceSerializer

    def get_queryset(self):
        return AlertPreference.objects.filter(user=self.request.user)


class NotificationLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class NotificationLogListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationLogSerializer
    pagination_class = NotificationLogPagination

    def get_queryset(self):
        qs = NotificationLog.objects.filter(user=self.request.user).select_related(
            "alert", "auction_item"
        )

        params = self.request.query_params
        channel = params.get("channel")
        status_param = params.get("status")
        alert_id = params.get("alert_id")

        if channel:
            qs = qs.filter(channel=channel)
        if status_param:
            qs = qs.filter(status=status_param)
        if alert_id:
            qs = qs.filter(alert_id=alert_id)

        return qs.order_by("-created_at")
