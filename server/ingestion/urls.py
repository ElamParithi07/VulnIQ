from django.urls import path

from .views import TriggerPipelineView

urlpatterns = [
    path("trigger-pipeline/", TriggerPipelineView.as_view(), name="trigger-pipeline"),
]
