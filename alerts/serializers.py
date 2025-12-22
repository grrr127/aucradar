from rest_framework import serializers

from auctions.models import AuctionItem, CategoryLarge, CategoryMiddle, CategorySmall

from .models import AlertPreference, NotificationLog


class AlertPreferenceSerializer(serializers.ModelSerializer):
    large_category_id = serializers.PrimaryKeyRelatedField(
        source="large_category",
        queryset=CategoryLarge.objects.all(),
        required=False,
        allow_null=True,
    )
    mid_category_id = serializers.PrimaryKeyRelatedField(
        source="mid_category",
        queryset=CategoryMiddle.objects.all(),
        required=False,
        allow_null=True,
    )
    small_category_ids = serializers.PrimaryKeyRelatedField(
        source="small_categories",
        queryset=CategorySmall.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = AlertPreference
        fields = [
            "id",
            "region",
            "large_category_id",
            "mid_category_id",
            "small_category_ids",
            "min_price",
            "max_price",
            "min_failures",
            "notify_email",
            "notify_telegram",
            "frequency",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        validated_data["user"] = user
        small_categories = validated_data.pop("small_categories", [])
        instance = super().create(validated_data)
        if small_categories:
            instance.small_categories.set(small_categories)
        return instance

    def update(self, instance, validated_data):
        small_categories = validated_data.pop("small_categories", None)
        instance = super().update(instance, validated_data)
        if small_categories is not None:
            instance.small_categories.set(small_categories)
        return instance


class NotificationLogSerializer(serializers.ModelSerializer):
    auction_item_title = serializers.CharField(
        source="auction_item.title", read_only=True
    )

    class Meta:
        model = NotificationLog
        fields = [
            "id",
            "user",
            "alert",
            "auction_item",
            "auction_item_title",
            "channel",
            "status",
            "message_title",
            "message_body",
            "error_message",
            "sent_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "alert",
            "auction_item",
            "status",
            "error_message",
            "sent_at",
            "created_at",
            "updated_at",
        ]


class AlertPreviewItemSerializer(serializers.ModelSerializer):
    large_name = serializers.CharField(source="large.name", read_only=True)
    middle_name = serializers.CharField(source="middle.name", read_only=True)
    small_name = serializers.CharField(source="small.name", read_only=True)

    class Meta:
        model = AuctionItem
        fields = [
            "id",
            "source",
            "title",
            "location",
            "auction_date",
            "min_bid_price",
            "num_failures",
            "large_name",
            "middle_name",
            "small_name",
        ]
