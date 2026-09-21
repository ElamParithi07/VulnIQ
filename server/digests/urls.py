from django.urls import path

from .views import LatestDigestView

urlpatterns = [
    path("", LatestDigestView.as_view(), name="latest"),
]
