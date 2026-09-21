from django.urls import path

from .views import TagSelectionView

urlpatterns = [
    path("", TagSelectionView.as_view(), name="tag-selection"),
]
