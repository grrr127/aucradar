from rest_framework import serializers

from .models import CrawlItemLog, CrawlJob


class CrawlItemLogSerializer(serializers.ModelSerializer):
    auction_item_title = serializers.CharField(
        source="auction_item.title", read_only=True
    )

    class Meta:
        model = CrawlItemLog
        fields = [
            "id",
            "job",
            "auction_item",
            "auction_item_title",
            "external_id",
            "result",
            "message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "job",
            "auction_item",
            "external_id",
            "result",
            "message",
            "created_at",
            "updated_at",
        ]


class CrawlJobListSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CrawlJob
        fields = [
            "id",
            "source",
            "source_display",
            "status",
            "status_display",
            "triggered_by",
            "started_at",
            "finished_at",
            "total_fetched",
            "created_count",
            "updated_count",
            "failed_count",
            "error_message",
            "note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "triggered_by",
            "started_at",
            "finished_at",
            "total_fetched",
            "created_count",
            "updated_count",
            "failed_count",
            "error_message",
            "created_at",
            "updated_at",
        ]


class CrawlJobDetailSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    item_logs = CrawlItemLogSerializer(many=True, read_only=True)

    class Meta:
        model = CrawlJob
        fields = [
            "id",
            "source",
            "source_display",
            "status",
            "status_display",
            "triggered_by",
            "started_at",
            "finished_at",
            "total_fetched",
            "created_count",
            "updated_count",
            "failed_count",
            "error_message",
            "note",
            "item_logs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "triggered_by",
            "started_at",
            "finished_at",
            "total_fetched",
            "created_count",
            "updated_count",
            "failed_count",
            "error_message",
            "item_logs",
            "created_at",
            "updated_at",
        ]


class CrawlJobCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = CrawlJob
        fields = ["id", "source", "note", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        return CrawlJob.objects.create(triggered_by=user, **validated_data)
