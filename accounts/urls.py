from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('welcome/', views.login_landing, name='login_landing'),
]
