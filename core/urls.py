from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing_page, name="landing"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("api/chat/", views.chat_api, name="chat_api"),
    path("api/chat/reset/", views.chat_reset, name="chat_reset"),
]