from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('admins/', views.manage_admins, name='manage_admins'),
    path('unanswered/', views.unanswered_list, name='unanswered_list'),
    path('unanswered/<int:pk>/answer/', views.answer_question, name='answer_question'),
    path('unanswered/<int:pk>/ignore/', views.ignore_question, name='ignore_question'),
    path('knowledge-base/', views.knowledge_base_list, name='kb_list'),
    path('knowledge-base/create/', views.kb_create, name='kb_create'),
    path('knowledge-base/<int:pk>/toggle/', views.kb_toggle_active, name='kb_toggle_active'),
    path('logs/', views.conversation_logs, name='logs'),
]
