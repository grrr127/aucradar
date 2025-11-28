from rest_framework import serializers

from .models import AuctionItem, CategoryLarge, CategoryMiddle, CategorySmall


class CategoryLargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryLarge
        fields = ["id", "code", "name"]


class CategoryMiddleSerializer(serializers.ModelSerializer):
    large = CategoryLargeSerializer(read_only=True)
    large_id = serializers.PrimaryKeyRelatedField(
        source="large",
        queryset=CategoryLarge.objects.all(),
        write_only=True,
        required=True,
    )

    class Meta:
        model = CategoryMiddle
        fields = ["id", "code", "name", "large", "large_id"]


class CategorySmallSerializer(serializers.ModelSerializer):
    middle = CategoryMiddleSerializer(read_only=True)
    middle_id = serializers.PrimaryKeyRelatedField(
        source="middle",
        queryset=CategoryMiddle.objects.all(),
        write_only=True,
        required=True,
    )

    class Meta:
        model = CategorySmall
        fields = ["id", "code", "name", "middle", "middle_id"]


class AuctionItemListSerializer(serializers.ModelSerializer):
    large_name = serializers.CharField(source="large.name", read_only=True)
    middle_name = serializers.CharField(source="middle.name", read_only=True)
    small_name = serializers.CharField(source="small.name", read_only=True)

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    bid_method_display = serializers.CharField(
        source="get_bid_method_display",
        read_only=True,
    )

    class Meta:
        model = AuctionItem
        fields = [
            "id",
            "source",
            "title",
            "location",
            "area",
            "min_bid_price",
            "auction_date",
            "status",
            "status_display",
            "bid_method_display",
            "num_failures",
            "large_name",
            "middle_name",
            "small_name",
        ]


class AuctionItemDetailSerializer(serializers.ModelSerializer):
    large = CategoryLargeSerializer(read_only=True)
    middle = CategoryMiddleSerializer(read_only=True)
    small = CategorySmallSerializer(read_only=True)

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    bid_method_display = serializers.CharField(
        source="get_bid_method_display",
        read_only=True,
    )

    class Meta:
        model = AuctionItem
        fields = [
            "id",
            "source",
            "raw_source",
            "title",
            "location",
            "area",
            "min_bid_price",
            "deposit_price",
            "appraisal_price",
            "auction_date",
            "bid_method",
            "bid_method_display",
            "raw_bid_method",
            "status",
            "status_display",
            "raw_status",
            "num_failures",
            "large",
            "middle",
            "small",
            "external_id",
            "detail_url",
            "created_at",
            "updated_at",
        ]


class AuctionItemUpsertSerializer(serializers.ModelSerializer):

    class Meta:
        model = AuctionItem
        fields = [
            "source",
            "raw_source",
            "external_id",
            "title",
            "location",
            "area",
            "min_bid_price",
            "deposit_price",
            "appraisal_price",
            "auction_date",
            "bid_method",
            "raw_bid_method",
            "status",
            "raw_status",
            "num_failures",
            "large",
            "middle",
            "small",
            "detail_url",
        ]
