from django.contrib.auth.decorators import login_required
from django.shortcuts import render


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
