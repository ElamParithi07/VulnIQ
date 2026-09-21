from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path

from ingestion.models import IngestionRun, IngestionRunType
from ingestion.services.locking import PipelineAlreadyRunningError


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    change_list_template = "admin/ingestion/ingestionrun/change_list.html"
    list_display = (
        "id",
        "run_type",
        "status",
        "is_degraded",
        "started_at",
        "completed_at",
        "nvd_count",
        "kev_count",
        "epss_count",
        "candidate_count",
        "digest_count",
    )
    list_filter = ("run_type", "status", "is_degraded")
    search_fields = ("degraded_reason", "error_message")
    readonly_fields = ("started_at", "created_at", "updated_at")

    def get_urls(self):
        custom_urls = [
            path("trigger/", self.admin_site.admin_view(self.trigger_pipeline), name="ingestion_ingestionrun_trigger"),
        ]
        return custom_urls + super().get_urls()

    def trigger_pipeline(self, request):
        """Admin 'run now' trigger. Calls the same canonical, lock-protected
        pipeline path as the scheduler and the CLI — never a separate
        implementation."""
        if request.method != "POST":
            return render(request, "admin/ingestion/ingestionrun/trigger_confirm.html")

        from ingestion.services.daily_pipeline import run_daily_digest_pipeline

        try:
            run = run_daily_digest_pipeline(run_type=IngestionRunType.MANUAL)
        except PipelineAlreadyRunningError:
            self.message_user(request, "Daily pipeline is already running; try again shortly.", level="warning")
            return redirect("admin:ingestion_ingestionrun_changelist")

        self.message_user(
            request,
            f"Pipeline run #{run.pk} completed: status={run.status}, "
            f"nvd={run.nvd_count}, kev={run.kev_count}, epss={run.epss_count}, "
            f"candidates={run.candidate_count}, digests={run.digest_count}.",
        )
        return redirect("admin:ingestion_ingestionrun_changelist")
