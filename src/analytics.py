"""Small, transparent analytics helpers used by the client-facing app."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

DataKind = Literal["sales", "rentals"]


@dataclass(frozen=True)
class MarketView:
    filtered: pd.DataFrame
    monthly_value: pd.DataFrame
    monthly_activity: pd.DataFrame
    start: pd.Timestamp
    end: pd.Timestamp
    date_column: str
    value_column: str


def latest_nonfuture(series: pd.Series) -> pd.Timestamp:
    dates = pd.to_datetime(series, errors="coerce").dropna()
    if dates.empty:
        return pd.Timestamp.today().normalize()
    today = pd.Timestamp.today().normalize()
    past = dates[dates <= today]
    return (past.max() if not past.empty else dates.max()).normalize()


def filter_market(
    frame: pd.DataFrame,
    kind: DataKind,
    cluster: str,
    months: int,
    bedrooms: int | None = None,
    category: str | None = None,
    hide_nonstandard_sales: bool = True,
) -> MarketView:
    date_column = "date" if kind == "sales" else "start_date"
    value_column = "price_per_sqft" if kind == "sales" else "annualised_rent"
    category_column = "status" if kind == "sales" else "contract_type"

    # Keep every neighbourhood on the same current market window.  Previously the
    # end date was taken from the selected neighbourhood after filtering, which
    # could make a 12-month choice silently end several months early when that
    # neighbourhood had no recent transaction.
    market_dates = pd.to_datetime(frame[date_column], errors="coerce")
    end = latest_nonfuture(market_dates)
    start = end.to_period("M").to_timestamp() - pd.DateOffset(months=months - 1)

    work = frame[frame["cluster"].eq(cluster)].copy()
    if bedrooms is not None:
        work = work[work["bedrooms"].eq(bedrooms)]
    if category:
        work = work[work[category_column].eq(category)]
    if kind == "sales" and hide_nonstandard_sales and "possible_partial_or_nonstandard_sale" in work:
        work = work[~work["possible_partial_or_nonstandard_sale"]]

    work[date_column] = pd.to_datetime(work[date_column], errors="coerce")
    work = work[work[date_column].between(start, end, inclusive="both")].copy()
    work["month"] = work[date_column].dt.to_period("M").dt.to_timestamp()

    month_index = pd.date_range(start, end.to_period("M").to_timestamp(), freq="MS")
    monthly_value = (
        work.groupby("month")[value_column].median().reindex(month_index).rename("value").reset_index()
    )
    monthly_value.columns = ["month", "value"]
    monthly_activity = (
        work.groupby("month").size().reindex(month_index, fill_value=0).rename("transactions").reset_index()
    )
    monthly_activity.columns = ["month", "transactions"]

    return MarketView(
        filtered=work,
        monthly_value=monthly_value,
        monthly_activity=monthly_activity,
        start=start,
        end=end,
        date_column=date_column,
        value_column=value_column,
    )


def percentage_change(old: float | None, new: float | None) -> float | None:
    if old is None or new is None or pd.isna(old) or pd.isna(new) or old == 0:
        return None
    return (float(new) - float(old)) / abs(float(old)) * 100


def trend_change(monthly: pd.DataFrame) -> tuple[float | None, str]:
    valid = monthly.dropna(subset=["value"]).sort_values("month")
    current_month = pd.Timestamp.today().to_period("M").to_timestamp()
    complete = valid[valid["month"] < current_month]
    if not complete.empty:
        valid = complete
    if len(valid) >= 6:
        previous = float(valid.iloc[-6:-3]["value"].median())
        recent = float(valid.iloc[-3:]["value"].median())
        return percentage_change(previous, recent), "recent 3 months vs prior 3 months"
    if len(valid) >= 2:
        return percentage_change(float(valid.iloc[0]["value"]), float(valid.iloc[-1]["value"])), "first vs latest available month"
    return None, "not enough monthly history"


def middle_range(series: pd.Series) -> tuple[float | None, float | None]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None, None
    return float(values.quantile(0.25)), float(values.quantile(0.75))


def compact_aed(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    absolute = abs(float(value))
    if absolute >= 1_000_000_000:
        return f"AED {value / 1_000_000_000:.2f}B"
    if absolute >= 1_000_000:
        return f"AED {value / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"AED {value / 1_000:.0f}K"
    return f"AED {value:,.0f}"


def aed(value: float | None) -> str:
    return "Not available" if value is None or pd.isna(value) else f"AED {value:,.0f}"


def aed_psf(value: float | None) -> str:
    return "Not available" if value is None or pd.isna(value) else f"AED {value:,.0f}/sq ft"


def percent(value: float | None) -> str:
    return "Not available" if value is None or pd.isna(value) else f"{value:,.1f}%"


def change_text(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "Not enough history"
    return f"{value:+.1f}%"
