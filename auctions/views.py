from django.db.models import Q
from rest_framework import generics, permissions, status
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


class AuctionItemListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = AuctionItemListSerializer

    def get_queryset(self):
        qs = (
            AuctionItem.objects.select_related("large", "middle", "small")
            .all()
            .order_by("-created_at")
        )

        params = self.request.query_params

        source = params.get("source")
        status_param = params.get("status")
        large_id = params.get("large_id")
        middle_id = params.get("middle_id")
        small_id = params.get("small_id")
        min_price = params.get("min_price")
        max_price = params.get("max_price")
        keyword = params.get("keyword")

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
            qs = qs.filter(min_bid_price__gte=min_price)
        if max_price:
            qs = qs.filter(min_bid_price__lte=max_price)

        if keyword:
            qs = qs.filter(Q(title__icontains=keyword) | Q(location__icontains=keyword))

        return qs


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
