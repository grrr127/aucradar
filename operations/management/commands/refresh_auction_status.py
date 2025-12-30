from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from operations.models import CrawlJob
from operations.services import run_status_refresh_job


class Command(BaseCommand):
    help = "DB에 있는 경매/공매 매물의 현재 상태를 재조회해서 업데이트"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            choices=["court"],
            help="court 또는 생략 (생략시 기본값 court)",
        )
        parser.add_argument(
            "--note",
            type=str,
            default="",
            help="CrawlJob.note에 남길 메모",
        )

    def handle(self, *args, **options):
        source = options.get("source")
        note = options.get("note") or ""

        if source == "court":
            source_value = CrawlJob.Source.COURT
        else:
            source_value = None

        job = run_status_refresh_job(source=source_value, note=note)

        msg = (
            f"Status refresh job #{job.id} finished: "
            f"status={job.status}, error={job.error_message or '-'}"
        )

        if job.status == CrawlJob.Status.FAILED:
            raise CommandError(msg)

        self.stdout.write(self.style.SUCCESS(msg))
