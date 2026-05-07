from __future__ import annotations

import csv
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_COMPANY_CSV_PATH = REPO_ROOT / "data" / "BusinessCards_Export.csv"
MAX_COMPANY_SEARCH_LIMIT = 100
DEFAULT_COMPANY_SEARCH_LIMIT = 50

SEARCH_COLUMNS = [
    "Company",
    "Name",
    "NameRoman",
    "TEL",
    "Mobile",
    "Email",
    "Postal",
    "Region",
    "Address1",
    "Branches",
    "Notes",
]


@dataclass(frozen=True)
class CompanyRecord:
    item: dict[str, str]
    search_text: str
    phone_text: str


@dataclass
class CompanyDataset:
    path: Path
    mtime_ns: int
    records: list[CompanyRecord]


_DATASET_CACHE: dict[Path, CompanyDataset] = {}


def search_company_cards(
    q: str,
    *,
    limit: int = DEFAULT_COMPANY_SEARCH_LIMIT,
    csv_path: Path = DEFAULT_COMPANY_CSV_PATH,
) -> dict[str, Any]:
    normalized_query = normalize_text(q)
    if not normalized_query:
        return {"items": [], "count": 0}

    dataset = load_company_dataset(csv_path)
    if dataset is None:
        return {
            "items": [],
            "count": 0,
            "message": "企業データCSVが見つかりません",
        }

    max_results = clamp_limit(limit)
    query_digits = digits_only(q)
    items: list[dict[str, str]] = []
    for record in dataset.records:
        if matches_record(record, normalized_query, query_digits):
            items.append(record.item)
            if len(items) >= max_results:
                break

    return {"items": items, "count": len(items)}


def load_company_dataset(csv_path: Path = DEFAULT_COMPANY_CSV_PATH) -> Optional[CompanyDataset]:
    path = csv_path.resolve()
    if not path.exists() or not path.is_file():
        return None

    mtime_ns = path.stat().st_mtime_ns
    cached = _DATASET_CACHE.get(path)
    if cached and cached.mtime_ns == mtime_ns:
        return cached

    try:
        records = read_company_records(path)
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        logger.warning("Company CSV load failed error_type=%s", exc.__class__.__name__)
        return CompanyDataset(path=path, mtime_ns=mtime_ns, records=[])

    dataset = CompanyDataset(path=path, mtime_ns=mtime_ns, records=records)
    _DATASET_CACHE[path] = dataset
    return dataset


def read_company_records(path: Path) -> list[CompanyRecord]:
    records: list[CompanyRecord] = []
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            item = company_item_from_row(row)
            normalized_text = normalize_text(" ".join(safe_get(row, column) for column in SEARCH_COLUMNS))
            search_text = f"{normalized_text} {normalized_text.replace(' ', '')}".strip()
            phone_text = digits_only(
                " ".join(
                    [
                        item["tel"],
                        item["mobile"],
                        item["fax"],
                        item["toll_free"],
                    ]
                )
            )
            records.append(CompanyRecord(item=item, search_text=search_text, phone_text=phone_text))
    return records


def company_item_from_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "company": safe_get(row, "Company"),
        "title": safe_get(row, "Title"),
        "name": safe_get(row, "Name"),
        "name_roman": safe_get(row, "NameRoman"),
        "tel": safe_get(row, "TEL"),
        "mobile": safe_get(row, "Mobile"),
        "fax": safe_get(row, "FAX"),
        "toll_free": safe_get(row, "TollFree"),
        "email": safe_get(row, "Email"),
        "postal": safe_get(row, "Postal"),
        "region": safe_get(row, "Region"),
        "address1": safe_get(row, "Address1"),
        "branches": safe_get(row, "Branches"),
        "address3": safe_get(row, "Address3"),
        "url": safe_get(row, "URL"),
        "line_url": safe_get(row, "LineURL"),
        "notes": safe_get(row, "Notes"),
    }


def safe_get(row: dict[str, str], key: str) -> str:
    value = row.get(key)
    return value.strip() if isinstance(value, str) else ""


def matches_record(record: CompanyRecord, normalized_query: str, query_digits: str) -> bool:
    if normalized_query in record.search_text:
        return True
    return bool(query_digits and query_digits in record.phone_text)


def normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def digits_only(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\D", "", unicodedata.normalize("NFKC", value))


def clamp_limit(limit: int) -> int:
    if limit < 1:
        return DEFAULT_COMPANY_SEARCH_LIMIT
    return min(limit, MAX_COMPANY_SEARCH_LIMIT)
