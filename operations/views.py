from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination

from .models import CrawlItemLog, CrawlJob
from .serializers import (
    CrawlItemLogSerializer,
    CrawlJobCreateSerializer,
    CrawlJobDetailSerializer,
    CrawlJobListSerializer,
)


class AdminOnly(permissions.IsAdminUser):
    pass


class CrawlJobListCreateView(generics.ListCreateAPIView):
    permission_classes = [AdminOnly]

    def get_queryset(self):
        return CrawlJob.objects.select_related("triggered_by").all()

    def get_serializer_class(self):
        if self.request.method.lower() == "post":
            return CrawlJobCreateSerializer
        return CrawlJobListSerializer


class CrawlJobDetailView(generics.RetrieveAPIView):
    permission_classes = [AdminOnly]
    serializer_class = CrawlJobDetailSerializer
    queryset = CrawlJob.objects.all()


class CrawlItemLogPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class CrawlItemLogListView(generics.ListAPIView):
    permission_classes = [AdminOnly]
    serializer_class = CrawlItemLogSerializer
    pagination_class = CrawlItemLogPagination

    def get_queryset(self):
        qs = CrawlItemLog.objects.select_related("job", "auction_item")
        job_id = self.request.query_params.get("job_id")
        if job_id:
            qs = qs.filter(job_id=job_id)
        return qs.order_by("-created_at")
