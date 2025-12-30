from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from auctions.models import AuctionItem
from users.forms import CustomUserCreationForm


def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


def home(request):
    return render(request, "core/home.html")


def about(request):
    return render(request, "core/about.html")


def features(request):
    return render(request, "core/features.html")


def pricing(request):
    return render(request, "core/pricing.html")


def contact(request):
    return render(request, "core/contact.html")


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html")


@login_required
def watchlist(request):
    query = request.GET.get("q", "")
    items = AuctionItem.objects.all().select_related("large", "middle", "small")

    if query:
        items = items.filter(location__icontains=query)

    items = items.order_by("-created_at")[:100]
    return render(request, "core/watchlist.html", {"items": items, "query": query})


@login_required
def alerts(request):
    from alerts.models import AlertPreference

    alerts = AlertPreference.objects.filter(user=request.user)
    return render(request, "core/alerts.html", {"alerts": alerts})


@login_required
def profile(request):
    return render(request, "core/profile.html")
