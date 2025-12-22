from rest_framework import generics, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CrawlItemLog, CrawlJob
from .serializers import (
    CrawlItemLogSerializer,
    CrawlJobDetailSerializer,
    CrawlJobListSerializer,
)
from .services import run_crawl_job, run_status_refresh_job


class AdminOnly(permissions.IsAdminUser):
    pass


class CrawlJobListView(generics.ListAPIView):
    permission_classes = [AdminOnly]
    serializer_class = CrawlJobListSerializer

    def get_queryset(self):
        return CrawlJob.objects.select_related("triggered_by").all()


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


class RunCourtCrawlJobView(APIView):
    permission_classes = [AdminOnly]

    def post(self, request):
        user = request.user if request.user.is_authenticated else None
        job = run_crawl_job(source="court", triggered_by=user)
        data = CrawlJobDetailSerializer(job).data
        return Response(data, status=status.HTTP_201_CREATED)


class RunOnbidCrawlJobView(APIView):
    permission_classes = [AdminOnly]

    def post(self, request):
        user = request.user if request.user.is_authenticated else None
        job = run_crawl_job(source="onbid", triggered_by=user)
        data = CrawlJobDetailSerializer(job).data
        return Response(data, status=status.HTTP_201_CREATED)


class RunStatusRefreshJobView(APIView):

    permission_classes = [AdminOnly]

    def post(self, request):
        source = request.data.get("source")
        if source not in (None, "", "court", "onbid"):
            return Response(
                {"detail": "source는 'court', 'onbid' 또는 생략 가능"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized_source = source or None
        job = run_status_refresh_job(source=normalized_source)
        data = CrawlJobDetailSerializer(job).data
        return Response(data, status=status.HTTP_201_CREATED)
