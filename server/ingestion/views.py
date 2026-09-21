import hmac

from django.conf import settings
from django.http import JsonResponse
from django.views import View

from ingestion.models import IngestionRunType
from ingestion.services.daily_pipeline import run_daily_digest_pipeline
from ingestion.services.locking import PipelineAlreadyRunningError


class TriggerPipelineView(View):
    """Token-protected HTTP entrypoint for the canonical daily pipeline.

    Exists so a free external cron service (no shell/SSH access, GET-only)
    can trigger the same run_daily_digest_pipeline() path as the management
    command and the admin "run now" button. GET is intentionally accepted
    despite being a state-changing action, since that's what free cron
    services support; the token is what actually guards it, not the method.
    """

    def get(self, request):
        return self._trigger(request)

    def post(self, request):
        return self._trigger(request)

    def _trigger(self, request):
        token = request.GET.get("token") or request.POST.get("token") or ""
        expected = settings.PIPELINE_TRIGGER_TOKEN

        if not expected or not hmac.compare_digest(token, expected):
            return JsonResponse({"error": "unauthorized"}, status=401)

        try:
            run = run_daily_digest_pipeline(run_type=IngestionRunType.SCHEDULED)
        except PipelineAlreadyRunningError:
            return JsonResponse({"error": "pipeline already running"}, status=409)

        return JsonResponse(
            {
                "run_id": run.pk,
                "status": run.status,
                "is_degraded": run.is_degraded,
                "nvd_count": run.nvd_count,
                "kev_count": run.kev_count,
                "epss_count": run.epss_count,
                "candidate_count": run.candidate_count,
                "digest_count": run.digest_count,
            }
        )
