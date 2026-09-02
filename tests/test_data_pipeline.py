from pathlib import Path

import pandas as pd

from src.analytics import filter_market
from src.data_pipeline import (
    canonicalise_sales_table,
    identify_pdf_kind,
    merge_history,
    parse_rentals_pdf,
    parse_sales_pdf,
)

ROOT = Path(__file__).resolve().parents[1]
SALES_PDF = ROOT / "data" / "incoming" / "The Valley (All Phases), Al Yufrah 1-3.pdf"
RENTALS_PDF = ROOT / "data" / "incoming" / "The Valley (All Phases), Al Yufrah 1-4.pdf"


def test_identifies_dxbinteract_reports():
    assert identify_pdf_kind(SALES_PDF) == "sales"
    assert identify_pdf_kind(RENTALS_PDF) == "rentals"


def test_current_pdf_parsers_extract_records():
    sales = parse_sales_pdf(SALES_PDF)
    rentals = parse_rentals_pdf(RENTALS_PDF)
    assert len(sales) == 300
    assert len(rentals) == 300
    assert sales["cluster"].nunique() >= 10
    assert rentals["cluster"].nunique() >= 4


def test_history_merge_does_not_duplicate_same_batch():
    sales = parse_sales_pdf(SALES_PDF)
    once = merge_history(pd.DataFrame(), sales, "sales")
    twice = merge_history(once, sales, "sales")
    assert len(twice) == len(once)
    assert twice["record_uid"].is_unique


def test_tabular_sales_aliases_and_single_cluster_view(tmp_path):
    path = tmp_path / "Nara Sales.csv"
    raw = pd.DataFrame(
        {
            "Location": ["Nara, The Valley, Al Yufrah 1"],
            "Status": ["Ready Villa"],
            "Sale Price": ["AED 2,900,000"],
            "Price / sqft": ["1,450"],
            "Specs": ["3 Beds 1,873 sqft"],
            "Transaction Date": ["31 Aug 2026"],
            "Sold By": ["Individual"],
        }
    )
    parsed = canonicalise_sales_table(raw, path)
    assert parsed.iloc[0]["cluster"] == "Nara"
    assert parsed.iloc[0]["bedrooms"] == 3
    assert parsed.iloc[0]["price"] == 2_900_000

    view = filter_market(parsed, "sales", "Nara", 6, bedrooms=3)
    assert len(view.filtered) == 1
    assert set(view.filtered["cluster"]) == {"Nara"}


def test_dld_transaction_csv_columns_are_supported(tmp_path):
    from src.data_pipeline import canonicalise_rentals_table

    sales_path = tmp_path / "The Valley DLD Transactions.csv"
    sales_raw = pd.DataFrame(
        {
            "Project": ["Nara"],
            "Transaction Date": ["31-08-2026"],
            "Amount": ["2900000"],
            "Transaction Size (sq.m)": ["174.0"],
            "Room(s)": ["3 B/R"],
            "Registration type": ["Existing Properties"],
            "Property Type": ["Villa"],
            "Transaction Type": ["Sales"],
        }
    )
    sales = canonicalise_sales_table(sales_raw, sales_path)
    assert len(sales) == 1
    assert sales.iloc[0]["cluster"] == "Nara"
    assert sales.iloc[0]["status"] == "Ready"
    assert 1_870 < sales.iloc[0]["area_sqft"] < 1_875
    assert sales.iloc[0]["price_per_sqft"] > 1_500

    rentals_path = tmp_path / "The Valley DLD Rents.csv"
    rentals_raw = pd.DataFrame(
        {
            "Project": ["Nara"],
            "Start Date": ["01-09-2026"],
            "End Date": ["31-08-2027"],
            "Contract Amount": ["135000"],
            "Annual Amount": ["135000"],
            "Property Size (sq.m)": ["174.0"],
            "Number of Rooms": ["3 B/R"],
            "Version": ["Renewed"],
            "Property Type": ["Villa"],
        }
    )
    rentals = canonicalise_rentals_table(rentals_raw, rentals_path)
    assert len(rentals) == 1
    assert rentals.iloc[0]["cluster"] == "Nara"
    assert rentals.iloc[0]["contract_type"] == "Renewed"
    assert rentals.iloc[0]["annualised_rent"] == 135_000
    assert rentals.iloc[0]["duration_months"] == 12
    assert 1_870 < rentals.iloc[0]["area_sqft"] < 1_875


def test_12_month_view_uses_market_wide_latest_date_and_full_calendar():
    frame = pd.DataFrame(
        {
            "cluster": ["Quiet Cluster", "Active Cluster"],
            "date": pd.to_datetime(["2024-07-10", "2024-12-15"]),
            "price_per_sqft": [1_200.0, 1_350.0],
            "bedrooms": pd.array([3, 3], dtype="Int64"),
            "status": ["Ready", "Ready"],
            "possible_partial_or_nonstandard_sale": [False, False],
        }
    )

    view = filter_market(frame, "sales", "Quiet Cluster", 12)

    assert view.end == pd.Timestamp("2024-12-15")
    assert view.start == pd.Timestamp("2024-01-01")
    assert len(view.monthly_value) == 12
    assert view.monthly_value["month"].min() == pd.Timestamp("2024-01-01")
    assert view.monthly_value["month"].max() == pd.Timestamp("2024-12-01")
    assert len(view.filtered) == 1


def test_public_period_options_are_only_6_and_12_months():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "[6, 12]," in app_source
    assert "[6, 12, 24]" not in app_source
