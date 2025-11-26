from django.conf import settings
from django.db import models

from auctions.models import AuctionItem, CategoryLarge, CategoryMiddle, CategorySmall
from core.models import TimeStampedModel


class AlertPreference(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="alert_preferences",
        verbose_name="유저",
    )

    region = models.CharField("지역 필터", max_length=200, blank=True, null=True)

    large_category = models.ForeignKey(
        CategoryLarge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alert_preferences",
        verbose_name="대분류",
    )
    mid_category = models.ForeignKey(
        CategoryMiddle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alert_preferences",
        verbose_name="중분류",
    )
    small_categories = models.ManyToManyField(
        CategorySmall,
        blank=True,
        related_name="alert_preferences",
        verbose_name="소분류",
    )

    min_price = models.BigIntegerField("최소 희망 입찰가", null=True, blank=True)
    max_price = models.BigIntegerField("최대 희망 입찰가", null=True, blank=True)

    min_failures = models.IntegerField("최소 유찰 횟수", null=True, blank=True)

    notify_email = models.BooleanField("이메일 알림 여부", default=True)
    notify_telegram = models.BooleanField("텔레그램 알림 여부", default=False)

    frequency = models.CharField("알림 빈도", max_length=20, default="immediate")
    is_active = models.BooleanField("알림 사용 여부", default=True)

    class Meta:
        db_table = "alert_preferences"
        verbose_name = "알림 설정"
        verbose_name_plural = "알림 설정 목록"

    def __str__(self):
        return f"{self.user.email} 알림 설정 #{self.id}"


class NotificationLog(TimeStampedModel):
    class Channel(models.TextChoices):
        EMAIL = "email", "이메일"
        TELEGRAM = "telegram", "텔레그램"

    class Status(models.TextChoices):
        PENDING = "pending", "발송 대기"
        SUCCESS = "success", "발송 성공"
        FAILED = "failed", "발송 실패"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_logs",
        verbose_name="유저",
    )
    alert = models.ForeignKey(
        AlertPreference,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
        verbose_name="알림 설정",
    )
    auction_item = models.ForeignKey(
        AuctionItem,
        on_delete=models.CASCADE,
        related_name="notification_logs",
        verbose_name="매물",
    )
    channel = models.CharField("채널", max_length=20, choices=Channel.choices)
    status = models.CharField(
        "상태", max_length=20, choices=Status.choices, default=Status.PENDING
    )

    message_title = models.CharField("제목", max_length=200, null=True, blank=True)
    message_body = models.TextField("본문", null=True, blank=True)
    error_message = models.CharField(
        "에러 메시지", max_length=255, null=True, blank=True
    )

    sent_at = models.DateTimeField("실제 발송 시각", null=True, blank=True)

    class Meta:
        db_table = "notification_logs"
        verbose_name = "알림 발송 로그"
        verbose_name_plural = "알림 발송 로그 목록"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email}-[{self.channel}] : {self.status}"
