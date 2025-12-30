from django.urls import path

from .views import (
    CrawlItemLogListView,
    CrawlJobDetailView,
    CrawlJobListView,
    RunCourtCrawlJobView,
    RunStatusRefreshJobView,
)

app_name = "operations"

urlpatterns = [
    path("jobs/", CrawlJobListView.as_view(), name="crawljob-list"),
    path("jobs/<int:pk>/", CrawlJobDetailView.as_view(), name="crawljob-detail"),
    path("item-logs/", CrawlItemLogListView.as_view(), name="crawlitemlog-list"),
    path("crawl/court/", RunCourtCrawlJobView.as_view(), name="crawl-court"),
    path("status-refresh/", RunStatusRefreshJobView.as_view(), name="status-refresh"),
]
