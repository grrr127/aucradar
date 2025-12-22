from __future__ import annotations

from datetime import date
from typing import Iterable, List

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from alerts.models import AlertPreference, NotificationLog
from auctions.models import AuctionItem


def find_matching_items_for_alert(alert: AlertPreference) -> Iterable[AuctionItem]:
    """
    - 지역
    - 카테고리(대/중/소)
    - 가격 범위
    - 최소 유찰 횟수
    - 경매일(오늘 이후)
    - 이미 알림 보낸 매물은 제외
    """
    qs = AuctionItem.objects.all()

    # 경매일
    qs = qs.filter(auction_date__gte=date.today())

    # 지역
    if alert.region:
        qs = qs.filter(location__icontains=alert.region)

    # 카테고리 필터
    if alert.large_category:
        qs = qs.filter(large=alert.large_category)
    if alert.mid_category:
        qs = qs.filter(middle=alert.mid_category)
    if alert.small_categories.exists():
        qs = qs.filter(small__in=alert.small_categories.all())

    # 가격 범위
    if alert.min_price is not None:
        qs = qs.filter(min_bid_price__gte=alert.min_price)
    if alert.max_price is not None:
        qs = qs.filter(min_bid_price__lte=alert.max_price)

    # 최소 유찰 횟수
    if alert.min_failures:
        qs = qs.filter(num_failures__gte=alert.min_failures)

    # 이미 이 알림 + 유저 기준으로 성공적으로 보낸 매물은 제외
    already_notified_ids = NotificationLog.objects.filter(
        user=alert.user,
        alert=alert,
        status=NotificationLog.Status.SUCCESS,
    ).values_list("auction_item_id", flat=True)

    if already_notified_ids:
        qs = qs.exclude(id__in=list(already_notified_ids))

    return qs


def _build_email_subject(alert: AlertPreference, count: int) -> str:
    base = "[AucRadar] 신규 매물 알림"
    if alert.region:
        base += f" - {alert.region}"
    if count > 1:
        return f"{base} ({count}건)"
    return base


def _build_email_body(alert: AlertPreference, items: Iterable[AuctionItem]) -> str:
    lines = []
    # user.name 없으면 username/email로 바꿔도 됨
    user_label = (
        getattr(alert.user, "name", None)
        or getattr(alert.user, "username", None)
        or alert.user.email
        or "사용자"
    )
    lines.append(f"{user_label}님, 설정하신 조건에 맞는 신규 매물이 발견되었습니다.\n")

    for item in items:
        min_price = item.min_bid_price
        min_price_str = (
            f"{min_price:,}원" if isinstance(min_price, int) else str(min_price)
        )

        line = (
            f"- [{item.get_source_display()}] {item.title}\n"
            f"  위치: {item.location}\n"
            f"  최저 입찰가: {min_price_str}\n"
            f"  입찰일: {item.auction_date}\n"
            f"  링크: {item.detail_url or '상세 링크 없음'}\n"
        )
        lines.append(line)

    lines.append("\nAucRadar 알림 설정에서 조건을 변경하거나 해제할 수 있습니다.")
    return "\n".join(lines)


def _send_email_for_alert(alert: AlertPreference, items: List[AuctionItem]) -> bool:
    if not alert.user.email:
        return False

    subject = _build_email_subject(alert, len(items))
    body = _build_email_body(alert, items)

    try:
        send_mail(
            subject,
            body,
            getattr(settings, "DEFAULT_FROM_EMAIL", None),
            [alert.user.email],
        )
        return True
    except Exception:
        return False


def _send_telegram_for_alert(alert: AlertPreference, items: List[AuctionItem]) -> bool:
    try:
        profile = getattr(alert.user, "telegram_profile", None)
        if not profile or not getattr(profile, "is_active", False):
            return False

        # TODO: 텔레그램 Bot API 호출 구현
        return True
    except Exception:
        return False


def send_notifications_for_alert(alert: AlertPreference) -> int:
    """
    알림 설정 하나에 대해:
    - 매칭되는 매물 찾고
    - 이메일 / 텔레그램 발송 시도
    - NotificationLog 남기기

    반환값: 발송 시도한 매물 수
    """
    if not alert.is_active:
        return 0

    items_qs = find_matching_items_for_alert(alert)
    items = list(items_qs)
    if not items:
        return 0

    now = timezone.now()
    sent_count = 0

    for item in items:
        # 이메일
        if alert.notify_email:
            success = _send_email_for_alert(alert, [item])
            NotificationLog.objects.create(
                user=alert.user,
                alert=alert,
                auction_item=item,
                channel=NotificationLog.Channel.EMAIL,
                status=(
                    NotificationLog.Status.SUCCESS
                    if success
                    else NotificationLog.Status.FAILED
                ),
                message_title=item.title,
                message_body="이메일 알림 발송(배치형)",
                error_message=None if success else "이메일 발송 실패",
                sent_at=now if success else None,
            )

        # 텔레그램
        if alert.notify_telegram:
            success = _send_telegram_for_alert(alert, [item])
            NotificationLog.objects.create(
                user=alert.user,
                alert=alert,
                auction_item=item,
                channel=NotificationLog.Channel.TELEGRAM,
                status=(
                    NotificationLog.Status.SUCCESS
                    if success
                    else NotificationLog.Status.FAILED
                ),
                message_title=item.title,
                message_body="텔레그램 알림 발송(배치형)",
                error_message=None if success else "텔레그램 발송 실패",
                sent_at=now if success else None,
            )

        sent_count += 1

    return sent_count


def run_alert_batch(frequency: str | None = None) -> int:
    qs = AlertPreference.objects.filter(is_active=True)
    if frequency:
        qs = qs.filter(frequency=frequency)

    processed = 0
    for alert in qs.select_related("user"):
        send_notifications_for_alert(alert)
        processed += 1

    return processed


def _alert_matches_item(alert: AlertPreference, item: AuctionItem) -> bool:
    """
    AlertPreference 1개가 AuctionItem 1개와 매칭되는지
    """
    if not alert.is_active:
        return False

    # 경매일(기본: 오늘 이후)
    if item.auction_date and item.auction_date < date.today():
        return False

    # 지역
    if alert.region:
        if not item.location:
            return False
        if alert.region not in item.location:
            if alert.region.lower() not in item.location.lower():
                return False

    # 카테고리
    if alert.large_category and alert.large_category_id != getattr(
        item, "large_id", None
    ):
        return False
    if alert.mid_category and alert.mid_category_id != getattr(item, "middle_id", None):
        return False

    # 소분류: alert가 소분류를 지정했으면 item.small이 포함돼야 함
    if alert.small_categories.exists():
        if getattr(item, "small_id", None) is None:
            return False
        if not alert.small_categories.filter(id=item.small_id).exists():
            return False

    # 가격
    if alert.min_price is not None:
        if item.min_bid_price is None or item.min_bid_price < alert.min_price:
            return False
    if alert.max_price is not None:
        if item.min_bid_price is None or item.min_bid_price > alert.max_price:
            return False

    # 유찰
    if alert.min_failures:
        if item.num_failures is None or item.num_failures < alert.min_failures:
            return False

    return True


@transaction.atomic
def create_notification_logs_for_new_item(item: AuctionItem) -> int:
    """
    크롤링 직후 item 1개 기준으로 매칭되는 AlertPreference들을 찾아
    NotificationLog를 'PENDING'으로 생성한다.
    - 실제 발송은 send_pending_notifications()가 담당.
    반환: 생성된 로그 개수
    """
    # 여기서 PENDING enum이 없다면 모델에 맞춰 수정:
    # - 예: NotificationLog.Status.QUEUED / NotificationLog.Status.PENDING 등
    pending_status = NotificationLog.Status.PENDING

    alerts = (
        AlertPreference.objects.filter(is_active=True)
        .select_related("user", "large_category", "mid_category")
        .prefetch_related("small_categories")
        .order_by("id")
    )

    created = 0

    for alert in alerts:
        if not _alert_matches_item(alert, item):
            continue

        # 이메일 로그 (중복 방지: alert+item+channel)
        if alert.notify_email:
            if not NotificationLog.objects.filter(
                alert=alert,
                auction_item=item,
                channel=NotificationLog.Channel.EMAIL,
            ).exists():
                NotificationLog.objects.create(
                    user=alert.user,
                    alert=alert,
                    auction_item=item,
                    channel=NotificationLog.Channel.EMAIL,
                    status=pending_status,
                    message_title=item.title,
                    message_body="이메일 알림 대기",
                    error_message=None,
                    sent_at=None,
                )
                created += 1

        # 텔레그램 로그
        if alert.notify_telegram:
            if not NotificationLog.objects.filter(
                alert=alert,
                auction_item=item,
                channel=NotificationLog.Channel.TELEGRAM,
            ).exists():
                NotificationLog.objects.create(
                    user=alert.user,
                    alert=alert,
                    auction_item=item,
                    channel=NotificationLog.Channel.TELEGRAM,
                    status=pending_status,
                    message_title=item.title,
                    message_body="텔레그램 알림 대기",
                    error_message=None,
                    sent_at=None,
                )
                created += 1

    return created


def send_pending_notifications(limit: int = 200) -> int:
    """
    PENDING 상태의 NotificationLog를 실제 발송 처리한다.
    반환: 처리한 로그 개수
    """
    pending_status = NotificationLog.Status.PENDING

    qs = (
        NotificationLog.objects.filter(status=pending_status)
        .select_related("user", "alert", "auction_item")
        .order_by("created_at")[:limit]
    )

    processed = 0
    now = timezone.now()

    for log in qs:
        alert = log.alert
        item = log.auction_item

        try:
            ok = False

            if log.channel == NotificationLog.Channel.EMAIL:
                ok = _send_email_for_alert(alert, [item])
            elif log.channel == NotificationLog.Channel.TELEGRAM:
                ok = _send_telegram_for_alert(alert, [item])

            if ok:
                log.status = NotificationLog.Status.SUCCESS
                log.sent_at = now
                log.error_message = None
                log.message_body = "발송 성공"
            else:
                log.status = NotificationLog.Status.FAILED
                log.error_message = "발송 실패"
                log.message_body = "발송 실패"

            log.save(
                update_fields=[
                    "status",
                    "sent_at",
                    "error_message",
                    "message_body",
                    "updated_at",
                ]
            )
            processed += 1

        except Exception as e:
            log.status = NotificationLog.Status.FAILED
            log.error_message = str(e)[:500]
            log.message_body = "예외로 발송 실패"
            log.save(
                update_fields=["status", "error_message", "message_body", "updated_at"]
            )
            processed += 1

    return processed
