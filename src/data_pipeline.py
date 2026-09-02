"""Data ingestion for DXBinteract PDFs and simple CSV/XLSX exports.

The pipeline is deliberately separate from Streamlit so it can be tested and run
from GitHub Actions.  It accepts any number of source files and preserves a
canonical transaction history in ``data/processed``.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable, Literal, Sequence

import pandas as pd
import pymupdf as fitz

DataKind = Literal["sales", "rentals"]

SQM_TO_SQFT = 10.7639104167097
NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
DATE_RANGE_RE = re.compile(
    r"(\d{1,2})\s+([A-Za-z]{3}),?\s+(\d{4})\s*-\s*"
    r"(\d{1,2})\s+([A-Za-z]{3}),?\s+(\d{4})",
    re.I,
)

SALES_COLUMNS = [
    "cluster",
    "location",
    "status",
    "property_type",
    "price",
    "capital_gain_pct",
    "price_per_sqft",
    "area_sqft",
    "bedrooms",
    "date",
    "sold_by",
    "possible_partial_or_nonstandard_sale",
    "source_file",
    "source_page",
    "record_uid",
]

RENTAL_COLUMNS = [
    "cluster",
    "location",
    "property_type",
    "bedrooms",
    "area_sqft",
    "contract_rent",
    "duration_months",
    "annualised_rent",
    "annualised_rent_per_sqft",
    "rental_yield_pct",
    "contract_type",
    "start_date",
    "end_date",
    "purchase_price",
    "source_file",
    "source_page",
    "record_uid",
]


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def normalise_space(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalise_column(value: object) -> str:
    text = normalise_space(value).lower()
    text = text.replace("%", " pct ").replace("/", " per ")
    text = text.replace("sq. ft", "sqft").replace("sq ft", "sqft")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def cluster_name(location: object) -> str:
    text = normalise_space(location)
    return normalise_space(text.split(",", 1)[0]) if text else ""


def cluster_from_filename(path: Path) -> str:
    name = path.stem
    name = re.sub(
        r"(?i)\b(the\s+valley|al\s+yufrah\s*\d*|sales?|rentals?|transactions?|history|report|data|market|dxbinteract|export|all\s+phases)\b",
        " ",
        name,
    )
    name = re.sub(r"[_\-()]+", " ", name)
    name = normalise_space(name)
    return name.title() if name else ""


def number(value: object) -> float | None:
    text = normalise_space(value).replace("AED", "").replace("aed", "")
    match = NUMBER_RE.search(text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def abbreviated_money(value: object) -> float | None:
    text = normalise_space(value).upper().replace("AED", "")
    match = re.search(r"(-?\d[\d,]*(?:\.\d+)?)\s*([MK]?)", text)
    if not match:
        return None
    amount = float(match.group(1).replace(",", ""))
    multiplier = {"M": 1_000_000, "K": 1_000}.get(match.group(2), 1)
    return amount * multiplier


def integer(value: object) -> int | None:
    parsed = number(value)
    return int(parsed) if parsed is not None else None


def parse_date(value: object) -> pd.Timestamp:
    text = normalise_space(value).replace(",", " ")
    parsed = pd.to_datetime(text, format="%d %b %Y", errors="coerce")
    if pd.isna(parsed):
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    return parsed


def parse_date_range(value: object) -> tuple[pd.Timestamp, pd.Timestamp]:
    text = normalise_space(value)
    match = DATE_RANGE_RE.search(text)
    if not match:
        return pd.NaT, pd.NaT
    return (
        parse_date(f"{match.group(1)} {match.group(2)} {match.group(3)}"),
        parse_date(f"{match.group(4)} {match.group(5)} {match.group(6)}"),
    )


def extract_bedrooms(value: object) -> int | None:
    text = normalise_space(value)
    match = re.search(r"(\d+)\s*(?:bed|beds|bedroom|bedrooms)\b", text, re.I)
    return int(match.group(1)) if match else integer(text)


def extract_area(value: object) -> float | None:
    text = normalise_space(value)
    match = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(?:sq\.?\s*ft|sqft)", text, re.I)
    return float(match.group(1).replace(",", "")) if match else number(text)


def empty_frame(kind: DataKind) -> pd.DataFrame:
    return pd.DataFrame(columns=SALES_COLUMNS if kind == "sales" else RENTAL_COLUMNS)


# ---------------------------------------------------------------------------
# DXBinteract PDF extraction
# ---------------------------------------------------------------------------


def box_text(
    words: Sequence[tuple], x0: float, x1: float, y0: float, y1: float
) -> str:
    selected = [w for w in words if x0 <= w[0] < x1 and y0 <= w[1] <= y1]
    selected.sort(key=lambda w: (round(w[1], 1), w[0]))
    return " ".join(str(w[4]) for w in selected).strip()


def line_text(
    words: Sequence[tuple], x0: float, x1: float, y: float, tolerance: float = 2.5
) -> str:
    selected = [w for w in words if x0 <= w[0] < x1 and abs(w[1] - y) <= tolerance]
    selected.sort(key=lambda w: w[0])
    return " ".join(str(w[4]) for w in selected).strip()


def row_anchors(words: Sequence[tuple]) -> list[float]:
    anchors: list[float] = []
    for word in words:
        if word[0] < 280 and str(word[4]).lower().startswith("valley"):
            y = float(word[1])
            if not any(abs(y - prior) < 1 for prior in anchors):
                anchors.append(y)
    return sorted(anchors)


def identification_text(path: Path) -> str:
    try:
        with fitz.open(path) as doc:
            return "\n".join(
                doc[index].get_text("text") for index in range(min(doc.page_count, 2))
            ).lower()
    except Exception:
        return ""


def identify_pdf_kind(path: Path) -> DataKind | None:
    text = identification_text(path)
    if "property sales history" in text or "sales performance summary" in text:
        return "sales"
    if "rental transactions history" in text or "rentals performance summary" in text:
        return "rentals"
    return None


def parse_sales_pdf(path: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    with fitz.open(path) as doc:
        for page_index in range(1, doc.page_count):
            words = doc[page_index].get_text("words")
            for row_number, y in enumerate(row_anchors(words), start=1):
                location = line_text(words, 35, 280, y)
                price_text = box_text(words, 300, 470, y - 6, y + 9)
                status_text = box_text(words, 35, 210, y + 15, y + 34)
                gain_match = re.search(r"\(([+-]?\d+(?:\.\d+)?)%\)", price_text)
                status_match = re.search(r"\b(Ready|Offplan|Off-plan)\b", status_text, re.I)
                rows.append(
                    {
                        "cluster": cluster_name(location),
                        "location": location,
                        "status": (
                            status_match.group(1).replace("-", "").title()
                            if status_match
                            else "Unknown"
                        ),
                        "property_type": "Villa" if "villa" in status_text.lower() else "",
                        "price": number(price_text),
                        "capital_gain_pct": float(gain_match.group(1)) if gain_match else None,
                        "price_per_sqft": number(box_text(words, 315, 455, y + 15, y + 34)),
                        "area_sqft": number(box_text(words, 470, 565, y - 6, y + 9)),
                        "bedrooms": integer(box_text(words, 470, 565, y + 15, y + 34)),
                        "date": parse_date(box_text(words, 570, 710, y - 6, y + 9)),
                        "sold_by": box_text(words, 565, 710, y + 15, y + 36),
                        "source_file": path.name,
                        "source_page": page_index + 1,
                        "source_row": row_number,
                    }
                )

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError(f"No sales transactions were extracted from {path.name}.")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["bedrooms"] = pd.array(frame["bedrooms"], dtype="Int64")
    frame["possible_partial_or_nonstandard_sale"] = (
        frame["price_per_sqft"].notna()
        & ((frame["price_per_sqft"] < 300) | (frame["price_per_sqft"] > 5_000))
    )
    frame = frame[frame["cluster"].ne("") & frame["date"].notna()].copy()
    return restore_types(frame, "sales")


def parse_rentals_pdf(path: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    with fitz.open(path) as doc:
        for page_index in range(1, doc.page_count):
            words = doc[page_index].get_text("words")
            for row_number, y in enumerate(row_anchors(words), start=1):
                location = line_text(words, 35, 270, y)
                rent = number(box_text(words, 390, 510, y - 12, y + 5))
                months = integer(box_text(words, 545, 710, y + 15, y + 29))
                start, end = parse_date_range(box_text(words, 510, 710, y - 12, y + 5))
                contract_text = box_text(words, 390, 510, y + 15, y + 38)
                contract_type = (
                    "Renewed"
                    if "renewed" in contract_text.lower()
                    else "New"
                    if re.search(r"\bnew\b", contract_text, re.I)
                    else "Unknown"
                )
                annualised = rent * 12 / months if rent is not None and months else rent
                area = number(box_text(words, 270, 370, y + 15, y + 29))
                rows.append(
                    {
                        "cluster": cluster_name(location),
                        "location": location,
                        "property_type": (
                            "Villa"
                            if "villa" in box_text(words, 35, 150, y + 15, y + 29).lower()
                            else ""
                        ),
                        "bedrooms": integer(line_text(words, 270, 370, y)),
                        "area_sqft": area,
                        "contract_rent": rent,
                        "duration_months": months,
                        "annualised_rent": annualised,
                        "annualised_rent_per_sqft": (
                            annualised / area if annualised is not None and area else None
                        ),
                        "rental_yield_pct": number(box_text(words, 390, 510, y + 4, y + 18)),
                        "contract_type": contract_type,
                        "start_date": start,
                        "end_date": end,
                        "purchase_price": abbreviated_money(
                            box_text(words, 710, 825, y + 4, y + 18)
                        ),
                        "source_file": path.name,
                        "source_page": page_index + 1,
                        "source_row": row_number,
                    }
                )

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError(f"No rental transactions were extracted from {path.name}.")
    frame = frame[frame["cluster"].ne("") & frame["start_date"].notna()].copy()
    return restore_types(frame, "rentals")


# ---------------------------------------------------------------------------
# CSV and Excel ingestion
# ---------------------------------------------------------------------------


SALES_ALIASES: dict[str, tuple[str, ...]] = {
    "cluster": (
        "cluster",
        "community",
        "neighbourhood",
        "neighborhood",
        "project",
        "project_name",
        "master_project",
    ),
    "location": ("location", "property_location", "project_location"),
    "status": (
        "status",
        "sale_status",
        "completion_status",
        "ready_offplan",
        "registration_type",
    ),
    "property_type": ("property_type", "type", "unit_type", "property_sub_type"),
    "price": ("price", "sale_price", "transaction_price", "amount", "transaction_value"),
    "capital_gain_pct": ("capital_gain_pct", "capital_gain", "gain_pct", "price_change_pct"),
    "price_per_sqft": (
        "price_per_sqft",
        "price_per_sq_ft",
        "price_psf",
        "aed_per_sqft",
        "median_price_per_sqft",
    ),
    "area_sqft": ("area_sqft", "size_sqft", "area", "size", "actual_area"),
    "area_sqm": (
        "transaction_size_sq_m",
        "transaction_size_sqm",
        "property_size_sq_m",
        "property_size_sqm",
    ),
    "bedrooms": ("bedrooms", "beds", "bed", "room_s", "number_of_rooms", "room_type"),
    "date": ("date", "sale_date", "transaction_date", "registration_date"),
    "sold_by": (
        "sold_by",
        "seller_type",
        "transaction_party",
        "sale_type",
        "transaction_type",
        "registration_type",
    ),
    "specs": ("specs", "specification", "details"),
}

RENTAL_ALIASES: dict[str, tuple[str, ...]] = {
    "cluster": (
        "cluster",
        "community",
        "neighbourhood",
        "neighborhood",
        "project",
        "project_name",
        "master_project",
    ),
    "location": ("location", "property_location", "project_location"),
    "property_type": ("property_type", "type", "unit_type", "property_sub_type"),
    "bedrooms": ("bedrooms", "beds", "bed", "number_of_rooms", "room_s", "room_type"),
    "area_sqft": ("area_sqft", "size_sqft", "area", "size", "actual_area"),
    "area_sqm": ("property_size_sq_m", "property_size_sqm"),
    "contract_rent": (
        "contract_rent",
        "contract_amount",
        "rent",
        "rental",
        "rental_aed",
        "annual_rent",
        "rent_aed",
    ),
    "annual_amount": ("annual_amount", "annual_rent_amount"),
    "duration_months": ("duration_months", "duration", "lease_months", "contract_months"),
    "rental_yield_pct": ("rental_yield_pct", "rental_yield", "yield", "yield_pct"),
    "contract_type": ("contract_type", "rental_type", "status", "new_renewed", "version"),
    "start_date": ("start_date", "contract_start", "lease_start", "date", "transaction_date"),
    "end_date": ("end_date", "contract_end", "lease_end"),
    "date_range": ("date_range", "contract_period", "lease_period"),
    "purchase_price": ("purchase_price", "property_price", "purchase_value"),
    "specs": ("specs", "specification", "details"),
}


def _column_lookup(frame: pd.DataFrame) -> dict[str, object]:
    return {normalise_column(column): column for column in frame.columns}


def _series(frame: pd.DataFrame, lookup: dict[str, object], aliases: Iterable[str]) -> pd.Series:
    for alias in aliases:
        key = normalise_column(alias)
        if key in lookup:
            return frame[lookup[key]]
    return pd.Series(pd.NA, index=frame.index, dtype="object")


def _numeric_series(series: pd.Series, *, money: bool = False) -> pd.Series:
    parser = abbreviated_money if money else number
    return pd.to_numeric(series.map(parser), errors="coerce")


def _fill_text(primary: pd.Series, fallback: pd.Series) -> pd.Series:
    left = primary.map(normalise_space)
    right = fallback.map(normalise_space)
    return left.where(left.ne(""), right)


def detect_table_kind(frame: pd.DataFrame, path: Path, sheet_name: str = "") -> DataKind | None:
    columns = {normalise_column(column) for column in frame.columns}
    label = f"{path.stem} {sheet_name}".lower()
    rental_signals = {
        "rent",
        "rental",
        "rental_aed",
        "contract_rent",
        "contract_amount",
        "annual_rent",
        "annual_amount",
        "rental_yield",
        "rental_yield_pct",
        "duration",
        "duration_months",
    }
    sales_signals = {
        "sale_price",
        "price_per_sqft",
        "price_psf",
        "capital_gain",
        "sold_by",
        "sale_date",
    }
    if columns & rental_signals or re.search(r"\b(rent|rental|lease)\b", label):
        return "rentals"
    if columns & sales_signals or re.search(r"\b(sale|sales|sold)\b", label):
        return "sales"
    if {"transaction_date", "amount"}.issubset(columns):
        return "sales"
    if "price" in columns and ("date" in columns or "transaction_date" in columns):
        return "sales"
    return None


def canonicalise_sales_table(frame: pd.DataFrame, path: Path, sheet_name: str = "") -> pd.DataFrame:
    lookup = _column_lookup(frame)
    specs = _series(frame, lookup, SALES_ALIASES["specs"])
    location = _series(frame, lookup, SALES_ALIASES["location"])
    cluster = _series(frame, lookup, SALES_ALIASES["cluster"])
    filename_cluster = cluster_from_filename(path)
    cluster = _fill_text(cluster, location.map(cluster_name))
    if filename_cluster:
        cluster = cluster.where(cluster.map(normalise_space).ne(""), filename_cluster)
    location = _fill_text(location, cluster)

    status_raw = _series(frame, lookup, SALES_ALIASES["status"]).map(normalise_space)
    status = status_raw.map(
        lambda value: "Ready"
        if re.search(r"\b(ready|existing|title[ -]?deed)\b", value, re.I)
        else "Offplan"
        if re.search(r"\b(off[ -]?plan|oqood|pre[ -]?registration)\b", value, re.I)
        else "Unknown"
    )
    property_type = _series(frame, lookup, SALES_ALIASES["property_type"]).map(normalise_space)
    property_type = property_type.where(
        property_type.ne(""),
        status_raw.map(lambda value: "Villa" if "villa" in value.lower() else ""),
    )

    bedrooms_raw = _series(frame, lookup, SALES_ALIASES["bedrooms"])
    area_raw = _series(frame, lookup, SALES_ALIASES["area_sqft"])
    area_sqm_raw = _series(frame, lookup, SALES_ALIASES["area_sqm"])
    bedrooms = bedrooms_raw.map(extract_bedrooms)
    bedrooms = bedrooms.where(bedrooms.notna(), specs.map(extract_bedrooms))
    area = _numeric_series(area_raw)
    area_from_sqm = _numeric_series(area_sqm_raw) * SQM_TO_SQFT
    area = area.where(area.notna(), area_from_sqm)
    area = area.where(area.notna(), specs.map(extract_area))
    price = _numeric_series(_series(frame, lookup, SALES_ALIASES["price"]), money=True)
    price_per_sqft = _numeric_series(
        _series(frame, lookup, SALES_ALIASES["price_per_sqft"])
    )
    implied_price_per_sqft = price / area.where(area.ne(0))
    price_per_sqft = price_per_sqft.where(price_per_sqft.notna(), implied_price_per_sqft)

    output = pd.DataFrame(
        {
            "cluster": cluster.map(normalise_space),
            "location": location.map(normalise_space),
            "status": status,
            "property_type": property_type,
            "price": price,
            "capital_gain_pct": _numeric_series(
                _series(frame, lookup, SALES_ALIASES["capital_gain_pct"])
            ),
            "price_per_sqft": price_per_sqft,
            "area_sqft": area,
            "bedrooms": bedrooms,
            "date": _series(frame, lookup, SALES_ALIASES["date"]).map(parse_date),
            "sold_by": _series(frame, lookup, SALES_ALIASES["sold_by"]).map(normalise_space),
            "source_file": path.name,
            "source_page": [f"{sheet_name or 'CSV'}:{index + 2}" for index in range(len(frame))],
            "source_row": range(1, len(frame) + 1),
        }
    )
    output["possible_partial_or_nonstandard_sale"] = (
        output["price_per_sqft"].notna()
        & ((output["price_per_sqft"] < 300) | (output["price_per_sqft"] > 5_000))
    )
    output = output[
        output["cluster"].ne("")
        & output["date"].notna()
        & (output["price"].notna() | output["price_per_sqft"].notna())
    ].copy()
    return restore_types(output, "sales")


def canonicalise_rentals_table(frame: pd.DataFrame, path: Path, sheet_name: str = "") -> pd.DataFrame:
    lookup = _column_lookup(frame)
    specs = _series(frame, lookup, RENTAL_ALIASES["specs"])
    location = _series(frame, lookup, RENTAL_ALIASES["location"])
    cluster = _series(frame, lookup, RENTAL_ALIASES["cluster"])
    filename_cluster = cluster_from_filename(path)
    cluster = _fill_text(cluster, location.map(cluster_name))
    if filename_cluster:
        cluster = cluster.where(cluster.map(normalise_space).ne(""), filename_cluster)
    location = _fill_text(location, cluster)

    property_type = _series(frame, lookup, RENTAL_ALIASES["property_type"]).map(normalise_space)
    bedrooms_raw = _series(frame, lookup, RENTAL_ALIASES["bedrooms"])
    area_raw = _series(frame, lookup, RENTAL_ALIASES["area_sqft"])
    area_sqm_raw = _series(frame, lookup, RENTAL_ALIASES["area_sqm"])
    bedrooms = bedrooms_raw.map(extract_bedrooms)
    bedrooms = bedrooms.where(bedrooms.notna(), specs.map(extract_bedrooms))
    area = _numeric_series(area_raw)
    area_from_sqm = _numeric_series(area_sqm_raw) * SQM_TO_SQFT
    area = area.where(area.notna(), area_from_sqm)
    area = area.where(area.notna(), specs.map(extract_area))

    duration = _numeric_series(_series(frame, lookup, RENTAL_ALIASES["duration_months"]))
    rent = _numeric_series(_series(frame, lookup, RENTAL_ALIASES["contract_rent"]), money=True)
    annual_amount = _numeric_series(
        _series(frame, lookup, RENTAL_ALIASES["annual_amount"]), money=True
    )
    rent = rent.where(rent.notna(), annual_amount)
    start = _series(frame, lookup, RENTAL_ALIASES["start_date"]).map(parse_date)
    end = _series(frame, lookup, RENTAL_ALIASES["end_date"]).map(parse_date)
    date_range = _series(frame, lookup, RENTAL_ALIASES["date_range"])
    if date_range.notna().any():
        parsed_ranges = date_range.map(parse_date_range)
        range_start = parsed_ranges.map(lambda item: item[0])
        range_end = parsed_ranges.map(lambda item: item[1])
        start = start.where(start.notna(), range_start)
        end = end.where(end.notna(), range_end)

    contract_raw = _series(frame, lookup, RENTAL_ALIASES["contract_type"]).map(normalise_space)
    contract_type = contract_raw.map(
        lambda value: "Renewed"
        if re.search(r"\brenew", value, re.I)
        else "New"
        if re.search(r"\bnew\b", value, re.I)
        else "Unknown"
    )
    calculated_duration = ((end - start).dt.days / 30.4375).round().clip(lower=1)
    duration = duration.where(duration.notna(), calculated_duration)
    annualised = rent * 12 / duration.where(duration.ne(0))
    annualised = annualised.where(duration.notna(), rent)
    annualised = annual_amount.where(annual_amount.notna(), annualised)

    output = pd.DataFrame(
        {
            "cluster": cluster.map(normalise_space),
            "location": location.map(normalise_space),
            "property_type": property_type,
            "bedrooms": bedrooms,
            "area_sqft": area,
            "contract_rent": rent,
            "duration_months": duration,
            "annualised_rent": annualised,
            "annualised_rent_per_sqft": annualised / area.where(area.ne(0)),
            "rental_yield_pct": _numeric_series(
                _series(frame, lookup, RENTAL_ALIASES["rental_yield_pct"])
            ),
            "contract_type": contract_type,
            "start_date": start,
            "end_date": end,
            "purchase_price": _numeric_series(
                _series(frame, lookup, RENTAL_ALIASES["purchase_price"]), money=True
            ),
            "source_file": path.name,
            "source_page": [f"{sheet_name or 'CSV'}:{index + 2}" for index in range(len(frame))],
            "source_row": range(1, len(frame) + 1),
        }
    )
    output = output[
        output["cluster"].ne("")
        & output["start_date"].notna()
        & output["annualised_rent"].notna()
    ].copy()
    return restore_types(output, "rentals")


def read_tabular_sources(path: Path) -> list[tuple[DataKind, pd.DataFrame]]:
    tables: list[tuple[str, pd.DataFrame]] = []
    if path.suffix.lower() == ".csv":
        try:
            frame = pd.read_csv(path)
        except UnicodeDecodeError:
            frame = pd.read_csv(path, encoding="latin-1")
        tables.append(("", frame))
    elif path.suffix.lower() in {".xlsx", ".xlsm"}:
        workbook = pd.ExcelFile(path)
        for sheet in workbook.sheet_names:
            frame = pd.read_excel(workbook, sheet_name=sheet)
            if not frame.dropna(how="all").empty:
                tables.append((sheet, frame))
    else:
        return []

    results: list[tuple[DataKind, pd.DataFrame]] = []
    for sheet_name, frame in tables:
        kind = detect_table_kind(frame, path, sheet_name)
        if kind == "sales":
            parsed = canonicalise_sales_table(frame, path, sheet_name)
        elif kind == "rentals":
            parsed = canonicalise_rentals_table(frame, path, sheet_name)
        else:
            continue
        if not parsed.empty:
            results.append((kind, parsed))
    return results


# ---------------------------------------------------------------------------
# History, discovery and canonical output
# ---------------------------------------------------------------------------


def restore_types(frame: pd.DataFrame, kind: DataKind) -> pd.DataFrame:
    result = frame.copy()
    date_columns = ["date"] if kind == "sales" else ["start_date", "end_date"]
    for column in date_columns:
        if column in result:
            result[column] = pd.to_datetime(result[column], errors="coerce")

    for column in ["bedrooms", "duration_months"]:
        if column in result:
            result[column] = pd.array(pd.to_numeric(result[column], errors="coerce"), dtype="Int64")

    numeric_columns = (
        ["price", "capital_gain_pct", "price_per_sqft", "area_sqft"]
        if kind == "sales"
        else [
            "area_sqft",
            "contract_rent",
            "annualised_rent",
            "annualised_rent_per_sqft",
            "rental_yield_pct",
            "purchase_price",
        ]
    )
    for column in numeric_columns:
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce")

    if kind == "sales" and "possible_partial_or_nonstandard_sale" in result:
        result["possible_partial_or_nonstandard_sale"] = (
            result["possible_partial_or_nonstandard_sale"]
            .astype(str)
            .str.lower()
            .map({"true": True, "false": False, "1": True, "0": False})
            .fillna(False)
            .astype(bool)
        )
    return result


def natural_key_columns(kind: DataKind) -> list[str]:
    if kind == "sales":
        return [
            "date",
            "cluster",
            "status",
            "bedrooms",
            "area_sqft",
            "price",
            "price_per_sqft",
            "capital_gain_pct",
            "sold_by",
        ]
    return [
        "start_date",
        "end_date",
        "cluster",
        "contract_type",
        "bedrooms",
        "area_sqft",
        "contract_rent",
        "duration_months",
        "rental_yield_pct",
        "purchase_price",
    ]


def uid_value(value: object) -> str:
    if value is None or pd.isna(value):
        return "<NA>"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float):
        return f"{value:.8f}".rstrip("0").rstrip(".")
    return normalise_space(value).lower()


def add_record_uids(frame: pd.DataFrame, kind: DataKind) -> pd.DataFrame:
    result = restore_types(frame, kind)
    if result.empty:
        result["record_uid"] = pd.Series(dtype="object")
        return result

    keys = natural_key_columns(kind)
    normalised = pd.DataFrame({key: result[key].map(uid_value) for key in keys}, index=result.index)
    natural_key = normalised.astype(str).agg("|".join, axis=1)
    source_group = result.get("source_file", pd.Series("", index=result.index)).map(normalise_space)
    occurrence = (
        pd.DataFrame({"source": source_group, "natural_key": natural_key}, index=result.index)
        .groupby(["source", "natural_key"], sort=False, dropna=False)
        .cumcount()
    )
    payload = natural_key + "|occurrence=" + occurrence.astype(str)
    result["record_uid"] = payload.map(lambda value: hashlib.sha1(value.encode("utf-8")).hexdigest())
    return result


def merge_history(existing: pd.DataFrame, current: pd.DataFrame, kind: DataKind) -> pd.DataFrame:
    old = restore_types(existing, kind) if not existing.empty else empty_frame(kind)
    new = add_record_uids(current, kind) if not current.empty else empty_frame(kind)
    if not old.empty and "record_uid" not in old:
        old = add_record_uids(old, kind)
    nonempty = [part for part in (old, new) if not part.empty]
    if not nonempty:
        return empty_frame(kind)
    combined = nonempty[0].copy() if len(nonempty) == 1 else pd.concat(nonempty, ignore_index=True, sort=False)
    if "record_uid" not in combined:
        combined = add_record_uids(combined, kind)
    combined = combined.drop_duplicates("record_uid", keep="last")
    combined = restore_types(combined, kind)
    date_column = "date" if kind == "sales" else "start_date"
    combined = combined.sort_values(date_column, ascending=False, na_position="last").reset_index(drop=True)
    ordered = SALES_COLUMNS if kind == "sales" else RENTAL_COLUMNS
    for column in ordered:
        if column not in combined:
            combined[column] = pd.NA
    return combined[ordered]


def discover_source_files(incoming_dir: Path) -> list[Path]:
    if not incoming_dir.is_dir():
        return []
    accepted = {".pdf", ".csv", ".xlsx", ".xlsm"}
    return sorted(
        path
        for path in incoming_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in accepted
        and not path.name.startswith("~$")
        and not path.name.startswith(".")
    )


def parse_source_files(incoming_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    sales_frames: list[pd.DataFrame] = []
    rental_frames: list[pd.DataFrame] = []
    warnings: list[str] = []

    for path in discover_source_files(incoming_dir):
        try:
            if path.suffix.lower() == ".pdf":
                kind = identify_pdf_kind(path)
                if kind == "sales":
                    sales_frames.append(parse_sales_pdf(path))
                elif kind == "rentals":
                    rental_frames.append(parse_rentals_pdf(path))
                else:
                    warnings.append(f"Skipped {path.name}: report type was not recognised.")
            else:
                parsed_any = False
                for kind, frame in read_tabular_sources(path):
                    parsed_any = True
                    (sales_frames if kind == "sales" else rental_frames).append(frame)
                if not parsed_any:
                    warnings.append(f"Skipped {path.name}: columns did not identify sales or rentals.")
        except Exception as exc:  # one bad cluster file should not break the whole site
            warnings.append(f"Skipped {path.name}: {exc}")

    sales = merge_history(empty_frame("sales"), pd.concat(sales_frames, ignore_index=True, sort=False) if sales_frames else empty_frame("sales"), "sales")
    rentals = merge_history(empty_frame("rentals"), pd.concat(rental_frames, ignore_index=True, sort=False) if rental_frames else empty_frame("rentals"), "rentals")
    return sales, rentals, warnings


def read_processed(path: Path, kind: DataKind) -> pd.DataFrame:
    if not path.is_file():
        return empty_frame(kind)
    return restore_types(pd.read_csv(path), kind)


def load_dashboard_data(
    incoming_dir: Path, processed_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    current_sales, current_rentals, warnings = parse_source_files(incoming_dir)
    saved_sales = read_processed(processed_dir / "sales.csv", "sales")
    saved_rentals = read_processed(processed_dir / "rentals.csv", "rentals")
    return (
        merge_history(saved_sales, current_sales, "sales"),
        merge_history(saved_rentals, current_rentals, "rentals"),
        warnings,
    )


def write_processed(
    incoming_dir: Path, processed_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    processed_dir.mkdir(parents=True, exist_ok=True)
    sales, rentals, warnings = load_dashboard_data(incoming_dir, processed_dir)
    for name, frame in (("sales.csv", sales), ("rentals.csv", rentals)):
        target = processed_dir / name
        temporary = target.with_suffix(target.suffix + ".tmp")
        frame.to_csv(temporary, index=False, date_format="%Y-%m-%d")
        temporary.replace(target)
    return sales, rentals, warnings


def source_fingerprint(incoming_dir: Path, processed_dir: Path) -> str:
    files = discover_source_files(incoming_dir)
    files += [path for path in (processed_dir / "sales.csv", processed_dir / "rentals.csv") if path.is_file()]
    parts = []
    for path in sorted(files):
        stat = path.stat()
        parts.append(f"{path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}")
    return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()
