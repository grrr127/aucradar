from django.conf import settings
from django.db import models

from auctions.models import AuctionItem
from core.models import TimeStampedModel


class CrawlJob(TimeStampedModel):
    class Source(models.TextChoices):
        COURT = "court", "법원경매"
        ONBID = "onbid", "온비드"

    class Status(models.TextChoices):
        PENDING = "pending", "대기"
        RUNNING = "running", "진행중"
        SUCCESS = "success", "성공"
        FAILED = "failed", "실패"

    source = models.CharField("데이터 출처", max_length=20, choices=Source.choices)
    status = models.CharField(
        "작업 상태", max_length=20, choices=Status.choices, default=Status.PENDING
    )

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crawl_jobs",
        verbose_name="실행 유저",
    )

    started_at = models.DateTimeField("작업 시작 시각", null=True, blank=True)
    finished_at = models.DateTimeField("작업 종료 시각", null=True, blank=True)

    total_fetched = models.IntegerField("총 건수", default=0)
    created_count = models.IntegerField("신규 건수", default=0)
    updated_count = models.IntegerField("업데이트 건수", default=0)
    failed_count = models.IntegerField("실패 건수", default=0)

    error_message = models.TextField("에러 메시지", null=True, blank=True)
    note = models.CharField("비고", max_length=200, null=True, blank=True)

    class Meta:
        db_table = "crawl_jobs"
        verbose_name = "크롤링 작업"
        verbose_name_plural = "크롤링 작업 목록"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_source_display()}] {self.get_status_display()} - #{self.id}"


class CrawlItemLog(TimeStampedModel):
    class Result(models.TextChoices):
        CREATED = "created", "신규 생성"
        UPDATED = "updated", "업데이트"
        SKIPPED = "skipped", "변경 없음"
        FAILED = "failed", "실패"

    job = models.ForeignKey(
        CrawlJob,
        on_delete=models.CASCADE,
        related_name="item_logs",
        verbose_name="크롤링 작업",
    )
    auction_item = models.ForeignKey(
        AuctionItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crawl_logs",
        verbose_name="매물",
    )

    external_id = models.CharField(
        "외부 매물 ID", max_length=100, null=True, blank=True
    )
    result = models.CharField("결과", max_length=20, choices=Result.choices)
    message = models.TextField("메모/에러 내용", null=True, blank=True)

    class Meta:
        db_table = "crawl_item_logs"
        verbose_name = "크롤링 아이템 로그"
        verbose_name_plural = "크롤링 아이템 로그 목록"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job #{self.job_id} - {self.external_id} ({self.get_result_display()})"
