from django.urls import path

from . import views

urlpatterns = [
    path("", views.chat_view, name="chat"),
    path("export/", views.export_view, name="export"),
]
