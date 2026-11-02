from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # The research surface over the session ledger (ticket #35, ADR-0007
    # decision 9): stock Django admin, staff-gated, mounted beside the learner
    # routes. The learner pages own the root; the admin lives under /admin/.
    path("admin/", admin.site.urls),
    path("", include("tutor.urls")),
]
