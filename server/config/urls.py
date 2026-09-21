from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from accounts.views import DashboardHomeView, DigestSettingsView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("dashboard/", DashboardHomeView.as_view(), name="dashboard-home"),
    path("dashboard/settings/", DigestSettingsView.as_view(), name="dashboard-settings"),
    path("dashboard/tags/", include(("taxonomy.urls", "taxonomy"), namespace="taxonomy")),
    path("dashboard/digest/", include(("digests.urls", "digests"), namespace="digests")),
    path("internal/", include(("ingestion.urls", "ingestion"), namespace="ingestion")),
    path("", RedirectView.as_view(pattern_name="dashboard-home"), name="index"),
]
