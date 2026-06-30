from django.urls import path
from . import views

app_name = "chatbot"

urlpatterns = [
    path('', views.chat_view, name='home'),
    path('chat/', views.chat_view, name='chat'),
    path('chat/send/', views.send_message, name='send_message'),
    path('chat/new/', views.new_chat, name='new_chat'),
]
