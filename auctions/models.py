from django.db import models

from core.models import TimeStampedModel


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
    source = models.CharField(max_length=20)

    title = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    area = models.FloatField(null=True, blank=True)

    min_bid_price = models.BigIntegerField()
    deposit_price = models.BigIntegerField(null=True, blank=True)
    appraisal_price = models.BigIntegerField(null=True, blank=True)
    auction_date = models.DateField(null=True, blank=True)
    bid_method = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        help_text="입찰방법(예: 기일입찰, 기간입찰 등)",
    )
    status = models.CharField(max_length=50, null=True, blank=True)
    num_failures = models.IntegerField(default=0)

    large = models.ForeignKey(
        CategoryLarge, on_delete=models.SET_NULL, related_name="items", null=True
    )
    middle = models.ForeignKey(
        CategoryMiddle, on_delete=models.SET_NULL, related_name="items", null=True
    )
    small = models.ForeignKey(
        CategorySmall, on_delete=models.SET_NULL, related_name="items", null=True
    )

    external_id = models.CharField(max_length=100, unique=True)
    detail_url = models.URLField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "auction_items"
        verbose_name = "매물"
        verbose_name_plural = "매물 목록"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title}/{self.source}"
