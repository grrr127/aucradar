from django.urls import path

from .views import CrawlItemLogListView, CrawlJobDetailView, CrawlJobListCreateView

urlpatterns = [
    path("crawls/jobs/", CrawlJobListCreateView.as_view()),
    path("crawls/jobs/<int:pk>/", CrawlJobDetailView.as_view()),
    path("crawls/logs/", CrawlItemLogListView.as_view()),
]
