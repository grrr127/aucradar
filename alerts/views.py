from rest_framework import generics, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AlertPreference, NotificationLog
from .serializers import (
    AlertPreferenceSerializer,
    AlertPreviewItemSerializer,
    NotificationLogSerializer,
)
from .services import find_matching_items_for_alert


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


class AlertPreferencePreviewItemsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            alert = AlertPreference.objects.get(pk=pk, user=request.user)
        except AlertPreference.DoesNotExist:
            return Response(
                {"detail": "알림 설정을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = find_matching_items_for_alert(alert)[:50]
        ser = AlertPreviewItemSerializer(qs, many=True)
        return Response(ser.data)
