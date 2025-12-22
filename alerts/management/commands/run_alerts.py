from __future__ import annotations

from django.core.management.base import BaseCommand

from alerts.services import run_alert_batch


class Command(BaseCommand):
    help = "AlertPreference 기준으로 경매 매물 알림을 발송합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--frequency",
            type=str,
            choices=["immediate", "daily", "weekly"],
            help="immediate / daily / weekly 중 하나를 선택하면 해당 주기만 실행",
        )

    def handle(self, *args, **options):
        freq = options.get("frequency")
        count = run_alert_batch(freq)

        if freq:
            self.stdout.write(self.style.SUCCESS(f"{freq} 알림 {count}개 처리 완료"))
        else:
            self.stdout.write(self.style.SUCCESS(f"전체 알림 {count}개 처리 완료"))
