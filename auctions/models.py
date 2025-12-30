from django.db import models

from core.models import TimeStampedModel


class AuctionSource(models.TextChoices):
    COURT = "court", "법원경매"
    ONBID = "onbid", "온비드공매"
    OTHER = "other", "기타"


class AuctionStatus(models.TextChoices):
    ACTIVE = "active", "진행중"
    END = "end", "종료"
    FAIL = "fail", "유찰"
    UNKNOWN = "unknown", "알 수 없음"


class BidMethod(models.TextChoices):
    DAY = "day", "기일입찰"
    PERIOD = "period", "기간입찰"
    UNKNOWN = "unknown", "알 수 없음"


class CategoryLarge(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "categories_large"
        verbose_name = "대분류"
        verbose_name_plural = "대분류 목록"

    def __str__(self):
        return self.name


class CategoryMiddle(models.Model):
    large = models.ForeignKey(
        CategoryLarge, on_delete=models.CASCADE, related_name="middles"
    )

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=50)

    class Meta:
        db_table = "categories_middle"
        unique_together = (("large", "code"),)
        verbose_name = "중분류"
        verbose_name_plural = "중분류 목록"

    def __str__(self):
        return f"{self.large.name}-{self.name}"


class CategorySmall(models.Model):
    middle = models.ForeignKey(
        CategoryMiddle, on_delete=models.CASCADE, related_name="smalls"
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=50)

    class Meta:
        db_table = "categories_small"
        unique_together = (("middle", "code"),)
        verbose_name = "소분류"
        verbose_name_plural = "소분류 목록"

    def __str__(self):
        return f"{self.middle.name}-{self.name}"


class AuctionItem(TimeStampedModel):
    class Source(models.TextChoices):
        COURT = "court", "법원경매"
        ONBID = "onbid", "온비드"

    class Status(models.TextChoices):
        PLANNED = "planned", "입찰 예정"
        ACTIVE = "active", "진행 중"
        SOLD = "sold", "매각/낙찰"
        FAILED = "failed", "유찰/종료"
        UNKNOWN = "unknown", "알 수 없음"

    class BidMethod(models.TextChoices):
        DATE = "date", "기일입찰"
        PERIOD = "period", "기간입찰"
        ETC = "etc", "기타"
        UNKNOWN = "unknown", "알 수 없음"

    source = models.CharField(
        max_length=20, choices=Source.choices, verbose_name="데이터 출처"
    )
    raw_source = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="원본 출처 코드/텍스트"
    )

    title = models.CharField("제목", max_length=255)
    location = models.CharField("소재지", max_length=255)
    area = models.FloatField("면적", null=True, blank=True)

    min_bid_price = models.BigIntegerField("최저입찰가")
    deposit_price = models.BigIntegerField("입찰보증금", null=True, blank=True)
    appraisal_price = models.BigIntegerField("감정가", null=True, blank=True)
    auction_date = models.DateField("입찰/매각 예정일", null=True, blank=True)
    bid_method = models.CharField(
        "입찰 방식",
        max_length=30,
        choices=BidMethod.choices,
        default=BidMethod.UNKNOWN,
    )
    raw_bid_method = models.CharField(
        "원본 입찰 방식", max_length=100, null=True, blank=True
    )
    status = models.CharField(
        "상태",
        max_length=50,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    raw_status = models.CharField(
        "원본 상태 문자열", max_length=100, null=True, blank=True
    )
    num_failures = models.IntegerField("유찰 횟수", default=0)

    large = models.ForeignKey(
        CategoryLarge, on_delete=models.SET_NULL, related_name="items", null=True
    )
    middle = models.ForeignKey(
        CategoryMiddle, on_delete=models.SET_NULL, related_name="items", null=True
    )
    small = models.ForeignKey(
        CategorySmall, on_delete=models.SET_NULL, related_name="items", null=True
    )

    external_id = models.CharField("외부 매물 ID", max_length=100, unique=True)
    detail_url = models.URLField(
        "상세 페이지 URL", max_length=500, null=True, blank=True
    )
    ai_predicted_price = models.BigIntegerField("AI 예상 낙찰가", null=True, blank=True)
    ai_analysis = models.TextField("AI 분석 코멘트", null=True, blank=True)

    class Meta:
        db_table = "auction_items"
        verbose_name = "매물"
        verbose_name_plural = "매물 목록"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title}/{self.source}"
