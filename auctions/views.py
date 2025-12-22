from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import generics, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuctionItem, CategoryLarge, CategoryMiddle, CategorySmall
from .serializers import (
    AuctionItemDetailSerializer,
    AuctionItemListSerializer,
    AuctionItemUpsertSerializer,
    CategoryLargeSerializer,
    CategoryMiddleSerializer,
    CategorySmallSerializer,
)


class CategoryLargeListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CategoryLargeSerializer
    queryset = CategoryLarge.objects.all().order_by("code")


class CategoryMiddleListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CategoryMiddleSerializer

    def get_queryset(self):
        qs = CategoryMiddle.objects.select_related("large").order_by("code")
        large_id = self.request.query_params.get("large_id")
        if large_id:
            qs = qs.filter(large_id=large_id)
        return qs


class CategorySmallListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySmallSerializer

    def get_queryset(self):
        qs = CategorySmall.objects.select_related("middle", "middle__large").order_by(
            "code"
        )
        middle_id = self.request.query_params.get("middle_id")
        if middle_id:
            qs = qs.filter(middle_id=middle_id)
        return qs


class AuctionItemPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AuctionItemListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = AuctionItemListSerializer
    pagination_class = AuctionItemPagination

    def get_queryset(self):
        qs = AuctionItem.objects.select_related("large", "middle", "small").all()

        params = self.request.query_params

        source = params.get("source")
        status_param = params.get("status")
        large_id = params.get("large_id")
        middle_id = params.get("middle_id")
        small_id = params.get("small_id")
        min_price = params.get("min_price")
        max_price = params.get("max_price")
        keyword = params.get("keyword")

        auction_date_from = params.get("auction_date_from")
        auction_date_to = params.get("auction_date_to")

        if source:
            qs = qs.filter(source=source)

        if status_param:
            qs = qs.filter(status=status_param)

        if large_id:
            qs = qs.filter(large_id=large_id)
        if middle_id:
            qs = qs.filter(middle_id=middle_id)
        if small_id:
            qs = qs.filter(small_id=small_id)

        if min_price:
            try:
                qs = qs.filter(min_bid_price__gte=int(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                qs = qs.filter(min_bid_price__lte=int(max_price))
            except ValueError:
                pass

        if auction_date_from:
            d_from = parse_date(auction_date_from)
            if d_from:
                qs = qs.filter(auction_date__gte=d_from)

        if auction_date_to:
            d_to = parse_date(auction_date_to)
            if d_to:
                qs = qs.filter(auction_date__lte=d_to)

        if keyword:
            qs = qs.filter(Q(title__icontains=keyword) | Q(location__icontains=keyword))

        ordering = params.get("ordering") or "-auction_date"
        allowed_orderings = {
            "auction_date",
            "-auction_date",
            "min_bid_price",
            "-min_bid_price",
            "created_at",
            "-created_at",
        }
        if ordering not in allowed_orderings:
            ordering = "-auction_date"

        return qs.order_by(ordering)


class AuctionItemDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = AuctionItemDetailSerializer
    queryset = AuctionItem.objects.select_related("large", "middle", "small").all()


class AuctionItemUpsertView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = AuctionItemUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        external_id = data["external_id"]

        item, created = AuctionItem.objects.get_or_create(
            external_id=external_id,
            defaults=data,
        )

        if not created:
            for field, value in data.items():
                setattr(item, field, value)
            item.save()

        response_serializer = AuctionItemDetailSerializer(item)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(response_serializer.data, status=status_code)
