from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import UserProfile


@login_required
def onboarding_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile.matric_number = request.POST.get("matric_number", "")
        profile.faculty = request.POST.get("faculty", "")
        profile.is_onboarded = True
        profile.save()
        return redirect('chatbot:chat')
    return render(request, "accounts/onboarding.html", {"profile": profile})


def login_landing(request):
    if request.user.is_authenticated:
        return redirect('chatbot:chat')
    return render(request, "accounts/login_landing.html")
