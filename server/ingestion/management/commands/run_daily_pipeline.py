from django.core.management.base import BaseCommand

from ingestion.models import IngestionRunType
from ingestion.services.daily_pipeline import run_daily_digest_pipeline
from ingestion.services.locking import PipelineAlreadyRunningError


class Command(BaseCommand):
    help = (
        "Canonical VulnIQ daily pipeline entrypoint: ingest NVD/KEV/EPSS, then "
        "build, enrich, and send one digest snapshot per eligible organization. "
        "This is the single execution path used by the scheduler, this CLI "
        "command, and the admin 'run now' trigger."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--backfill",
            action="store_true",
            help="Run as a manual historical backfill instead of a scheduled run.",
        )

    def handle(self, *args, **options):
        run_type = IngestionRunType.BACKFILL if options["backfill"] else IngestionRunType.SCHEDULED

        try:
            run = run_daily_digest_pipeline(run_type=run_type)
        except PipelineAlreadyRunningError as exc:
            self.stderr.write(self.style.WARNING(str(exc)))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Pipeline run #{run.pk} completed: status={run.status}, degraded={run.is_degraded}, "
                f"nvd={run.nvd_count}, kev={run.kev_count}, epss={run.epss_count}, "
                f"candidates={run.candidate_count}, digests={run.digest_count}"
            )
        )
