from django.urls import path

from . import views

urlpatterns = [
    path("", views.chat_view, name="chat"),
    path("menu/", views.main_menu_view, name="main_menu"),
    path("export/", views.export_view, name="export"),
    path("reset/", views.reset_view, name="reset"),
    path("reset/confirm/", views.reset_confirm_view, name="reset_confirm"),
]
