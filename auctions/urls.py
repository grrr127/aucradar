from django.urls import path

from .views import (
    AuctionItemDetailView,
    AuctionItemListView,
    AuctionItemUpsertView,
    CategoryLargeListView,
    CategoryMiddleListView,
    CategorySmallListView,
)

app_name = "auctions"

urlpatterns = [
    path("categories/large/", CategoryLargeListView.as_view()),
    path("categories/middle/", CategoryMiddleListView.as_view()),
    path("categories/small/", CategorySmallListView.as_view()),
    path("items/", AuctionItemListView.as_view()),
    path("items/<int:pk>/", AuctionItemDetailView.as_view()),
    path("items/upsert/", AuctionItemUpsertView.as_view()),
]
