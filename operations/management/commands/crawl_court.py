from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from operations.models import CrawlJob
from operations.services import run_crawl_job


class Command(BaseCommand):
    help = "법원경매 매물 크롤링 (입찰 가능/예정 물건)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="오늘부터 며칠 뒤까지의 매물만 수집할지 (기본 30)",
        )
        parser.add_argument(
            "--note",
            type=str,
            default="",
            help="CrawlJob.note에 남길 메모",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="DB 저장 없이 호출/응답만 확인(services에서 지원할 때만 의미 있음)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        note = options.get("note") or ""
        dry_run = bool(options.get("dry_run"))

        job = run_crawl_job(
            source=CrawlJob.Source.COURT,
            note=note,
            days=days,
            dry_run=dry_run,
        )

        msg = (
            f"Court crawl job #{job.id} finished: "
            f"status={job.status}, total={job.total_fetched}, "
            f"created={job.created_count}, updated={job.updated_count}, "
            f"failed={job.failed_count}"
        )

        if job.status == CrawlJob.Status.FAILED:
            raise CommandError(f"{msg} | error={job.error_message or '-'}")

        self.stdout.write(self.style.SUCCESS(msg))
