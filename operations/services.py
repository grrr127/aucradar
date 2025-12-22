from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote as urlquote

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from auctions.models import AuctionItem, CategoryLarge, CategoryMiddle, CategorySmall
from operations.models import CrawlItemLog, CrawlJob


def _parse_int(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    t = re.sub(r"[^\d]", "", str(text))
    return int(t) if t else None


def _parse_date(text: Optional[str]) -> Optional[date]:
    if not text:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_fail_count(raw: Optional[str]) -> int:
    if not raw:
        return 0
    num = _parse_int(raw)
    return num or 0


def resolve_category(usage_raw: str):
    # large 고정(건물)
    large, _ = CategoryLarge.objects.get_or_create(
        code="B",
        defaults={"name": "건물"},
    )

    # middle 고정(주거용건물)
    middle, _ = CategoryMiddle.objects.get_or_create(
        large=large,
        code="RESIDENTIAL_BUILDING",
        defaults={"name": "주거용건물"},
    )

    text = (usage_raw or "").replace(" ", "")

    # small 매핑
    if "아파트" in text:
        sm_code, sm_name = "APT", "아파트"
    elif "오피스텔" in text:
        sm_code, sm_name = "OFFICETEL", "오피스텔"
    elif "주상복합" in text:
        sm_code, sm_name = "MIXED_RESIDENTIAL", "주상복합"
    elif "연립" in text:
        sm_code, sm_name = "ROW_HOUSE", "연립주택"
    elif "다세대" in text:
        sm_code, sm_name = "MULTI_FAMILY", "다세대주택"
    elif "다가구" in text:
        sm_code, sm_name = "MULTI_HOUSE", "다가구주택"
    elif "단독" in text:
        sm_code, sm_name = "DETACHED", "단독주택"
    elif "빌라" in text:
        sm_code, sm_name = "VILLA", "빌라"
    elif "기숙사" in text:
        sm_code, sm_name = "DORM", "기숙사"
    else:
        sm_code, sm_name = "ETC", (usage_raw or "기타주거용건물")

    small, _ = CategorySmall.objects.get_or_create(
        middle=middle,
        code=sm_code,
        defaults={"name": sm_name},
    )

    return large, middle, small


def map_court_status(
    mul_statcd: Optional[str],
    auction_date: Optional[date],
) -> str:
    """
    mulStatcd 코드 → AuctionItem.Status 매핑 (임시 추정 버전).
    """
    code = (mul_statcd or "").strip()

    if not code:
        return AuctionItem.Status.UNKNOWN

    if code == "01":
        if auction_date and auction_date >= date.today():
            return AuctionItem.Status.PLANNED
        return AuctionItem.Status.ACTIVE

    if code in {"02", "03"}:
        return AuctionItem.Status.SOLD

    if code in {"04", "05"}:
        return AuctionItem.Status.FAILED

    return AuctionItem.Status.UNKNOWN


def build_court_detail_url(jiwon_nm: str, srn_sa_no: str) -> Optional[str]:
    if not (jiwon_nm and srn_sa_no and "타경" in srn_sa_no):
        return None

    try:
        encoded_court = urlquote(jiwon_nm.encode("euc-kr"))
    except Exception:
        encoded_court = urlquote(jiwon_nm)

    sa_year, sa_ser = srn_sa_no.split("타경", 1)

    base = "https://www.courtauction.go.kr/RetrieveRealEstDetailInqSaList.laf"
    return (
        f"{base}?jiwonNm={encoded_court}"
        f"&saYear={sa_year}"
        f"&saSer={sa_ser}"
        f"&_CUR_CMD=InitMulSrch.laf"
        f"&_SRCH_SRNID=PNO102014"
        f"&_NEXT_CMD=RetrieveRealEstDetailInqSaList.laf"
    )


# 법원경매 HTTP

COURT_SEARCH_URL = (
    "https://www.courtauction.go.kr/pgj/pgjsearch/searchControllerMain.on"
)


def _create_court_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; AucRadarBot/1.0)",
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
        }
    )
    try:
        s.get(
            "https://www.courtauction.go.kr/pgj/index.on"
            "?w2xPath=/pgj/ui/pgj100/PGJ151F00.xml",
            timeout=10,
        )
    except Exception:
        pass
    return s


def _request_court_page(
    session: requests.Session,
    cort_ofc_cd: str,
    from_date: date,
    to_date: date,
    page_no: int,
) -> Dict[str, Any]:
    payload = {
        "dma_pageInfo": {
            "pageNo": page_no,
            "pageSize": 40,
            "bfPageNo": "",
            "startRowNo": "",
            "totalCnt": "",
            "totalYn": "Y",
            "groupTotalCount": "",
        },
        "dma_srchGdsDtlSrchInfo": {
            "bidDvsCd": "000331",
            "mvprpRletDvsCd": "00031R",
            "cortAuctnSrchCondCd": "0004601",
            "cortOfcCd": cort_ofc_cd,
            "pgmId": "PGJ151F01",
            "cortStDvs": "1",
            "statNum": 1,
            "bidBgngYmd": from_date.strftime("%Y%m%d"),
            "bidEndYmd": to_date.strftime("%Y%m%d"),
        },
    }

    resp = session.post(COURT_SEARCH_URL, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


# 법원경매


def _normalize_court_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    court_code = item.get("boCd")
    docid = item.get("docid")

    if not (court_code and docid):
        return None

    external_id = f"{court_code}-{docid}"
    srn_sa_no = item.get("srnSaNo") or ""
    jiwon_nm = item.get("jiwonNm") or ""

    usage_raw = item.get("dspslUsgNm") or ""
    title_base = item.get("buldNm") or srn_sa_no or "법원경매"
    title = f"{usage_raw} {title_base}".strip() if usage_raw else title_base

    auction_date = _parse_date(item.get("maeGiil"))
    status = map_court_status(item.get("mulStatcd"), auction_date)
    num_failures = parse_fail_count(item.get("yuchalCnt"))

    appraisal_price = _parse_int(item.get("gamevalAmt"))
    min_bid_price = _parse_int(item.get("minmaePrice"))

    large, middle, small = resolve_category(usage_raw)

    location = " ".join(
        filter(
            None,
            [
                item.get("hjguSido"),
                item.get("hjguSigu"),
                item.get("hjguDong"),
                item.get("daepyoLotno"),
            ],
        )
    ).strip()

    area = _parse_int(item.get("minArea"))
    detail_url = build_court_detail_url(jiwon_nm, srn_sa_no)

    data = {
        "source": AuctionItem.Source.COURT,
        "raw_source": "court_json",
        "external_id": external_id,
        "title": title,
        "location": location,
        "area": area,
        "min_bid_price": min_bid_price,
        "deposit_price": None,
        "appraisal_price": appraisal_price,
        "auction_date": auction_date,
        "bid_method": AuctionItem.BidMethod.DATE,
        "raw_bid_method": "",
        "status": status,
        "raw_status": item.get("jinstatCd") or "",
        "num_failures": num_failures,
        "large": large,
        "middle": middle,
        "small": small,
        "detail_url": detail_url,
    }
    return data


def fetch_court_items(from_date: date, to_date: date) -> Iterable[Dict[str, Any]]:
    session = _create_court_session()

    COURT_LIST = [
        "B000210",
        "B000211",
        "B000215",
        "B000212",
        "B000213",
        "B000214",
        "B214807",
        "B214804",
        "B000240",
        "B000241",
        "B000250",
        "B000251",
        "B000252",
        "B000253",
        "B250826",
        "B000254",
        "B000260",
        "B000261",
        "B000262",
        "B000263",
        "B000264",
        "B000270",
        "B000271",
        "B000272",
        "B000273",
        "B000280",
        "B000281",
        "B000282",
        "B000283",
        "B000284",
        "B000285",
        "B000310",
        "B000311",
        "B000312",
        "B000313",
        "B000314",
        "B000315",
        "B000316",
        "B000317",
        "B000320",
        "B000410",
        "B000412",
        "B000414",
        "B000411",
        "B000420",
        "B000431",
        "B000421",
        "B000422",
        "B000423",
        "B000424",
        "B000510",
        "B000511",
        "B000512",
        "B000513",
        "B000514",
        "B000520",
        "B000521",
        "B000522",
        "B000523",
        "B000530",
    ]

    for court_code in COURT_LIST:
        page_no = 1
        while True:
            result = _request_court_page(
                session, court_code, from_date, to_date, page_no
            )
            info = result.get("data") or {}
            result_list: List[Dict[str, Any]] = info.get("dlt_srchResult") or []

            if not result_list:
                break

            for row in result_list:
                norm = _normalize_court_item(row)
                if norm:
                    yield norm

            page_info = info.get("dma_pageInfo") or {}
            total_cnt = int(page_info.get("totalCnt") or 0)

            if page_no * 40 >= total_cnt:
                break
            page_no += 1


# 온비드 OpenAPI (부동산 카테고리)

ONBID_BASE_URL = "https://openapi.onbid.co.kr/openapi/services"
ONBID_REAL_ESTATE_PATH = "/OnbidBidRealEstateInquireService/getBidRealEstateInquireList"


def _onbid_get_with_retry(
    url: str, params: Dict[str, Any], timeout: int = 25, retries: int = 3
) -> requests.Response:
    last_exc: Exception | None = None
    for i in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_exc = e
            print(f"[Onbid Retry] {url} 실 패 ({i+1}/{retries}) : {e}")
    raise RuntimeError(f"Onbid request failed after {retries} retries: {last_exc}")


def _request_onbid_page(
    page_no: int,
    from_date: date,
    to_date: date,
    num_rows: int = 100,
) -> Dict[str, Any]:
    service_key = getattr(settings, "ONBID_SERVICE_KEY", None)
    if not service_key:
        raise RuntimeError("ONBID_SERVICE_KEY is not set in settings.")

    url = ONBID_BASE_URL + ONBID_REAL_ESTATE_PATH

    params = {
        "serviceKey": service_key,
        "pageNo": page_no,
        "numOfRows": num_rows,
        "DPSL_MTD_CD": "0001",
        "CTGR_HIRK_ID": "10000",
        "PBCT_BEGN_DTM": from_date.strftime("%Y%m%d"),
        "PBCT_CLS_DTM": to_date.strftime("%Y%m%d"),
    }

    resp = _onbid_get_with_retry(url, params=params, timeout=25, retries=3)

    root = ET.fromstring(resp.content)

    items: List[Dict[str, Any]] = []
    for item_el in root.findall(".//item"):
        row: Dict[str, Any] = {}
        for child in item_el:
            row[child.tag] = (child.text or "").strip()
        items.append(row)

    total_count_text = root.findtext(".//totalCount", default="0")
    total_count = int(re.sub(r"[^\d]", "", total_count_text) or 0)

    return {"items": items, "totalCount": total_count}


def _map_onbid_status(raw_status: str) -> str:
    txt = (raw_status or "").strip()
    if not txt:
        return AuctionItem.Status.UNKNOWN
    if "진행" in txt or "공고" in txt or "입찰" in txt:
        return AuctionItem.Status.ACTIVE
    if "예정" in txt:
        return AuctionItem.Status.PLANNED
    if "매각" in txt or "낙찰" in txt:
        return AuctionItem.Status.SOLD
    if "유찰" in txt:
        return AuctionItem.Status.FAILED
    return AuctionItem.Status.UNKNOWN


def _normalize_onbid_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    pbct_no = item.get("PBCT_NO")
    cltr_no = item.get("CLTR_NO")
    if not (pbct_no and cltr_no):
        return None

    external_id = f"ONBID-{pbct_no}-{cltr_no}"

    title = (item.get("CLTR_NM") or "").strip()
    location = (
        item.get("NMRD_ADRS") or item.get("LDNM_ADRS") or item.get("CLTR_ADRS") or ""
    ).strip()

    appraisal_price = _parse_int(item.get("APSL_ASES_AVG_AMT"))
    min_bid_price = _parse_int(item.get("MIN_BID_PRC"))
    auction_date = _parse_date(item.get("PBCT_BEGN_DTM"))

    raw_status = (item.get("PBCT_CLTR_STAT_NM") or "").strip()
    status = _map_onbid_status(raw_status)

    num_failures = parse_fail_count(item.get("USCBD_CNT"))

    usage_raw = (
        item.get("CTGR_SML_NM") or item.get("CTGR_FULL_NM") or item.get("CLTR_NM") or ""
    )
    large, middle, small = resolve_category(usage_raw)

    data = {
        "source": AuctionItem.Source.ONBID,
        "raw_source": "onbid_openapi",
        "external_id": external_id,
        "title": title or external_id,
        "location": location,
        "area": None,
        "min_bid_price": min_bid_price,
        "deposit_price": None,
        "appraisal_price": appraisal_price,
        "auction_date": auction_date,
        "bid_method": AuctionItem.BidMethod.DATE,
        "raw_bid_method": item.get("BID_MTD_NM") or "",
        "status": status,
        "raw_status": raw_status,
        "num_failures": num_failures,
        "large": large,
        "middle": middle,
        "small": small,
        "detail_url": None,
    }
    return data


def fetch_onbid_items(from_date: date, to_date: date) -> Iterable[Dict[str, Any]]:
    page_no = 1
    num_rows = 100

    while True:
        result = _request_onbid_page(page_no, from_date, to_date, num_rows=num_rows)
        items = result.get("items") or []
        total = result.get("totalCount") or 0

        if not items:
            break

        for row in items:
            norm = _normalize_onbid_item(row)
            if norm:
                yield norm

        if page_no * num_rows >= total:
            break
        page_no += 1


#  1. 크롤링 Job 실행 (법원 / 온비드)


def run_crawl_job(source: str, triggered_by=None) -> CrawlJob:
    job = CrawlJob.objects.create(
        source=source,
        status=CrawlJob.Status.PENDING,
        triggered_by=triggered_by,
    )

    job.status = CrawlJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    try:
        today = date.today()
        from_date = today
        to_date = today + timedelta(days=30)

        if source == CrawlJob.Source.COURT:
            raw_items = list(fetch_court_items(from_date, to_date))
        elif source == CrawlJob.Source.ONBID:
            raw_items = list(fetch_onbid_items(from_date, to_date))
        else:
            raise ValueError(f"알 수 없는 source: {source}")

        for raw in raw_items:
            process_single_item(job, raw)

        job.status = CrawlJob.Status.SUCCESS

    except Exception as e:
        job.status = CrawlJob.Status.FAILED
        job.error_message = str(e)[:1000]

    finally:
        job.finished_at = timezone.now()
        job.save()

    return job


#  2. 개별 매물 처리 (upsert + 로그)


@transaction.atomic
def process_single_item(job: CrawlJob, data: Dict[str, Any]) -> None:
    external_id = data.get("external_id")
    if not external_id:
        CrawlItemLog.objects.create(
            job=job,
            auction_item=None,
            external_id=None,
            result=CrawlItemLog.Result.FAILED,
            message="external_id 누락",
        )
        job.failed_count += 1
        job.total_fetched += 1
        job.save(update_fields=["failed_count", "total_fetched"])
        return

    job.total_fetched += 1

    try:
        item, created = AuctionItem.objects.get_or_create(
            external_id=external_id,
            defaults=data,
        )

        if not created:
            for field, value in data.items():
                setattr(item, field, value)
            item.save()
            result = CrawlItemLog.Result.UPDATED
            job.updated_count += 1
        else:
            result = CrawlItemLog.Result.CREATED
            job.created_count += 1

        CrawlItemLog.objects.create(
            job=job,
            auction_item=item,
            external_id=external_id,
            result=result,
            message="",
        )

        if created:
            try:
                from alerts.services import create_notification_logs_for_new_item

                create_notification_logs_for_new_item(item)
            except Exception:
                pass

    except Exception as e:
        CrawlItemLog.objects.create(
            job=job,
            auction_item=None,
            external_id=external_id,
            result=CrawlItemLog.Result.FAILED,
            message=str(e)[:1000],
        )
        job.failed_count += 1

    job.save(
        update_fields=[
            "total_fetched",
            "created_count",
            "updated_count",
            "failed_count",
        ]
    )


#  3. 상태 리프레시 Job (매각/유찰 반영)


def run_status_refresh_job(source: Optional[str] = None) -> CrawlJob:
    job = CrawlJob.objects.create(
        source=source or CrawlJob.Source.COURT,
        status=CrawlJob.Status.RUNNING,
        note="상태 리프레시 작업",
    )

    try:
        today = date.today()
        near_past = today - timedelta(days=90)
        near_future = today + timedelta(days=30)

        qs = AuctionItem.objects.all()

        if source:
            qs = qs.filter(source=source)

        unfinished_statuses = [
            AuctionItem.Status.PLANNED,
            AuctionItem.Status.ACTIVE,
            AuctionItem.Status.FAILED,
        ]

        qs = qs.filter(
            status__in=unfinished_statuses,
            auction_date__gte=near_past,
            auction_date__lte=near_future,
        )

        for item in qs:
            refresh_single_item_status(job, item)

        job.status = CrawlJob.Status.SUCCESS

    except Exception as e:
        job.status = CrawlJob.Status.FAILED
        job.error_message = str(e)[:1000]

    finally:
        job.finished_at = timezone.now()
        job.save()

    return job


def refresh_single_item_status(job: CrawlJob, item: AuctionItem) -> None:
    try:
        if item.source == AuctionItem.Source.COURT:
            new_status_data = fetch_court_item_status(item.external_id)
        elif item.source == AuctionItem.Source.ONBID:
            new_status_data = fetch_onbid_item_status(item.external_id)
        else:
            return

        changed = False

        status_code = new_status_data.get("status")
        if status_code and status_code != item.status:
            item.status = status_code
            changed = True

        raw_status = new_status_data.get("raw_status")
        if raw_status is not None and raw_status != getattr(item, "raw_status", None):
            item.raw_status = raw_status
            changed = True

        num_failures = new_status_data.get("num_failures")
        if num_failures is not None and num_failures != item.num_failures:
            item.num_failures = num_failures
            changed = True

        if changed:
            item.save()
            CrawlItemLog.objects.create(
                job=job,
                auction_item=item,
                external_id=item.external_id,
                result=CrawlItemLog.Result.UPDATED,
                message="상태 리프레시",
            )

    except Exception as e:
        CrawlItemLog.objects.create(
            job=job,
            auction_item=item,
            external_id=item.external_id,
            result=CrawlItemLog.Result.FAILED,
            message=f"상태 리프레시 실패: {str(e)[:200]}",
        )


def fetch_court_item_status(external_id: str) -> Dict[str, Any]:
    return {}


def fetch_onbid_item_status(external_id: str) -> Dict[str, Any]:
    return {}
