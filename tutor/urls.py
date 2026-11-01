from django.urls import path

from .views import (
    chat_view,
    export_view,
    intake_view,
    main_menu_view,
    reset_confirm_view,
    reset_view,
    terms_view,
)

urlpatterns = [
    # The intake form owns the root (ticket #37): registration facts and
    # consent before the first turn, so every ledger row has a named
    # participant. The chat moved to /chat/ behind that gate.
    path("", intake_view, name="intake"),
    path("chat/", chat_view, name="chat"),
    path("terms/", terms_view, name="terms"),
    path("menu/", main_menu_view, name="main_menu"),
    path("export/", export_view, name="export"),
    path("reset/", reset_view, name="reset"),
    path("reset/confirm/", reset_confirm_view, name="reset_confirm"),
]
