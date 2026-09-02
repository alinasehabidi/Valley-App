"""Inside The Valley public market-insights application.

Cloud entry point:
    streamlit run app.py

The public app reads every supported file in ``data/incoming`` and combines it
with the persistent history in ``data/processed``.  Visitors can inspect one
market, one neighbourhood and one filter choice at a time.
"""

from __future__ import annotations

import html
import os
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Literal

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analytics import (
    aed,
    aed_psf,
    change_text,
    compact_aed,
    filter_market,
    latest_nonfuture,
    middle_range,
    percent,
    trend_change,
)
from src.data_pipeline import load_dashboard_data, source_fingerprint
from src.theme import BRAND, apply_theme, cta, footnote, insight, render_hero, section

APP_DIR = Path(__file__).resolve().parent
INCOMING_DIR = Path(os.getenv("ITV_INCOMING_DIR", APP_DIR / "data" / "incoming"))
PROCESSED_DIR = Path(os.getenv("ITV_PROCESSED_DIR", APP_DIR / "data" / "processed"))

MarketKind = Literal["sales", "rentals"]
Aggregation = Literal["median", "count"]


@dataclass(frozen=True)
class ChartMetric:
    label: str
    column: str | None
    aggregation: Aggregation
    kind: Literal["aed", "aed_psf", "count", "percent"]
    chart_title: str


CHART_METRICS: dict[MarketKind, tuple[ChartMetric, ...]] = {
    "sales": (
        ChartMetric(
            "Price per sq ft",
            "price_per_sqft",
            "median",
            "aed_psf",
            "Median registered price per sq ft",
        ),
        ChartMetric(
            "Sale price",
            "price",
            "median",
            "aed",
            "Median registered sale price",
        ),
        ChartMetric(
            "Number of sales",
            None,
            "count",
            "count",
            "Registered sales by month",
        ),
    ),
    "rentals": (
        ChartMetric(
            "Annual rent",
            "annualised_rent",
            "median",
            "aed",
            "Median annual rent",
        ),
        ChartMetric(
            "Rent per sq ft",
            "annualised_rent_per_sqft",
            "median",
            "aed_psf",
            "Median annual rent per sq ft",
        ),
        ChartMetric(
            "Number of contracts",
            None,
            "count",
            "count",
            "Rental contracts by month",
        ),
        ChartMetric(
            "Rental yield",
            "rental_yield_pct",
            "median",
            "percent",
            "Median reported rental yield",
        ),
    ),
}


@st.cache_data(show_spinner=False)
def cached_dashboard_data(
    incoming_dir: str,
    processed_dir: str,
    fingerprint: str,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Load data only when an incoming or processed file has changed."""

    del fingerprint
    return load_dashboard_data(Path(incoming_dir), Path(processed_dir))


def query_value(name: str) -> str | None:
    """Read a single optional query-string value without failing on old Streamlit."""

    try:
        value = st.query_params.get(name)
    except Exception:
        return None
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value) if value else None


def option_index(options: list[str], requested: str | None, fallback: int = 0) -> int:
    if requested:
        requested_key = requested.strip().casefold()
        for index, option in enumerate(options):
            if option.casefold() == requested_key:
                return index
    return fallback


def available_history(sales: pd.DataFrame, rentals: pd.DataFrame) -> tuple[str, str]:
    """Return the latest non-future date and the combined available history label."""

    dated: list[pd.Series] = []
    for frame, column in ((sales, "date"), (rentals, "start_date")):
        if not frame.empty and column in frame:
            series = pd.to_datetime(frame[column], errors="coerce").dropna()
            if not series.empty:
                dated.append(series)

    if not dated:
        return "Not available", "Not available"

    all_dates = pd.concat(dated, ignore_index=True)
    latest = latest_nonfuture(all_dates)
    earliest = all_dates.min()
    return f"{latest:%d %b %Y}", f"{earliest:%b %Y} to {latest:%b %Y}"


def market_label(kind: MarketKind) -> str:
    return "Sales" if kind == "sales" else "Rentals"


def selected_bedroom(label: str) -> int | None:
    if label == "All bedrooms":
        return None
    try:
        return int(label.split()[0])
    except (TypeError, ValueError, IndexError):
        return None


def monthly_metric(
    filtered: pd.DataFrame,
    date_column: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    metric: ChartMetric,
) -> pd.DataFrame:
    """Build one continuous monthly line for the selected metric."""

    months = pd.date_range(start, end.to_period("M").to_timestamp(), freq="MS")
    work = filtered.copy()
    work["month"] = pd.to_datetime(work[date_column], errors="coerce").dt.to_period("M").dt.to_timestamp()

    if metric.aggregation == "count":
        values = work.groupby("month").size().reindex(months, fill_value=0)
    else:
        values = (
            work.groupby("month")[metric.column]
            .median()
            .reindex(months)
        )

    return pd.DataFrame({"month": months, "value": values.to_numpy()})


def format_chart_value(value: float | None, kind: str) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    if kind == "aed":
        return compact_aed(float(value))
    if kind == "aed_psf":
        return aed_psf(float(value))
    if kind == "percent":
        return percent(float(value))
    return f"{float(value):,.0f}"


def movement_word(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "has insufficient history for a reliable movement figure"
    if abs(float(value)) < 0.5:
        return "was broadly stable"
    return f"moved {'up' if value > 0 else 'down'} {abs(float(value)):.1f}%"


def axis_settings(metric: ChartMetric) -> dict[str, object]:
    if metric.kind == "percent":
        return {"ticksuffix": "%", "tickformat": ",.1f"}
    if metric.kind == "count":
        return {"tickformat": ",.0f"}
    if metric.kind == "aed_psf":
        return {"tickprefix": "AED ", "tickformat": ",.0f"}
    return {"tickprefix": "AED ", "tickformat": ",.0f"}


def hover_template(metric: ChartMetric) -> str:
    if metric.kind == "percent":
        value = "%{y:,.1f}%"
    elif metric.kind == "count":
        value = "%{y:,.0f}"
    elif metric.kind == "aed_psf":
        value = "AED %{y:,.0f} / sq ft"
    else:
        value = "AED %{y:,.0f}"
    return "%{x|%b %Y}<br><b>" + value + "</b><extra></extra>"


def render_chart(
    monthly: pd.DataFrame,
    metric: ChartMetric,
    cluster: str,
    months: int,
) -> None:
    plot = monthly.dropna(subset=["value"])
    if plot.empty:
        st.info("There is not enough information to draw this trend for the selected filters.")
        return

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=plot["month"],
            y=plot["value"],
            mode="lines+markers",
            line={"color": BRAND["forest"], "width": 3.2, "shape": "spline"},
            marker={
                "size": 8,
                "color": BRAND["sand"],
                "line": {"color": BRAND["forest"], "width": 1.5},
            },
            fill="tozeroy" if metric.aggregation == "count" else None,
            fillcolor="rgba(125,138,120,0.10)",
            connectgaps=False,
            hovertemplate=hover_template(metric),
        )
    )

    figure.update_layout(
        title={
            "text": f"{metric.chart_title}<br><sup>{html.escape(cluster)} · last {months} months</sup>",
            "x": 0.01,
            "xanchor": "left",
        },
        height=430,
        margin={"l": 12, "r": 16, "t": 78, "b": 12},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hovermode="x",
        font={"family": "DM Sans, Arial, sans-serif", "color": BRAND["ink"]},
        title_font={"family": "Libre Caslon Display, Georgia, serif", "size": 23},
    )
    period_start = pd.to_datetime(monthly["month"], errors="coerce").min()
    period_end = pd.to_datetime(monthly["month"], errors="coerce").max()
    if pd.notna(period_end):
        period_end = period_end + pd.offsets.MonthEnd(1)

    figure.update_xaxes(
        title=None,
        showgrid=False,
        tickformat="%b\n%Y",
        dtick="M1",
        range=[period_start, period_end]
        if pd.notna(period_start) and pd.notna(period_end)
        else None,
        linecolor="rgba(125,138,120,.25)",
        tickfont={"color": BRAND["muted"], "size": 11},
    )
    figure.update_yaxes(
        title=None,
        gridcolor="rgba(125,138,120,.16)",
        zeroline=False,
        tickfont={"color": BRAND["muted"], "size": 11},
        **axis_settings(metric),
    )

    st.plotly_chart(
        figure,
        use_container_width=True,
        config={"displayModeBar": False, "responsive": True},
    )


def safe_text(value: object, fallback: str = "—") -> str:
    if value is None or pd.isna(value):
        return fallback
    text = str(value).strip()
    return text if text else fallback


def record_tag(value: object) -> str:
    text = safe_text(value)
    css = "renewed" if text.casefold().startswith("renew") else "ready" if text.casefold() == "ready" else "offplan" if "off" in text.casefold() else "new"
    return f'<span class="itv-record-tag {css}">{html.escape(text)}</span>'


def render_recent_records(frame: pd.DataFrame, kind: MarketKind, limit: int = 8) -> None:
    if frame.empty:
        st.info("No matching registrations are available for this selection.")
        return

    date_column = "date" if kind == "sales" else "start_date"
    recent = frame.sort_values(date_column, ascending=False).head(limit)
    cards: list[str] = []

    for _, row in recent.iterrows():
        date_value = pd.to_datetime(row.get(date_column), errors="coerce")
        date_text = date_value.strftime("%d %b %Y") if not pd.isna(date_value) else "Date unavailable"
        bedrooms = row.get("bedrooms")
        home = f"{int(bedrooms)} bedroom {safe_text(row.get('property_type'), 'home').lower()}" if pd.notna(bedrooms) else safe_text(row.get("property_type"), "Home")
        area = row.get("area_sqft")
        area_text = f"{float(area):,.0f} sq ft" if pd.notna(area) else "Area unavailable"

        if kind == "sales":
            tag = record_tag(row.get("status"))
            primary_label = "Sale price"
            primary_value = aed(row.get("price"))
            secondary_label = "Price / sq ft"
            secondary_value = aed_psf(row.get("price_per_sqft"))
        else:
            tag = record_tag(row.get("contract_type"))
            primary_label = "Annual rent"
            primary_value = aed(row.get("annualised_rent"))
            secondary_label = "Reported yield"
            secondary_value = percent(row.get("rental_yield_pct"))

        cards.append(
            dedent(
                f"""
            <div class="itv-record">
                <div class="itv-record-main">
                    <div class="itv-record-date">{html.escape(date_text)}</div>
                    <div class="itv-record-home">{html.escape(home)}</div>
                    <div class="itv-record-sub">{html.escape(area_text)}</div>
                    {tag}
                </div>
                <div class="itv-record-stat">
                    <span>{html.escape(primary_label)}</span>
                    <strong>{html.escape(primary_value)}</strong>
                </div>
                <div class="itv-record-stat">
                    <span>{html.escape(secondary_label)}</span>
                    <strong>{html.escape(secondary_value)}</strong>
                </div>
            </div>
            """
            ).strip()
        )

    st.markdown('<div class="itv-records">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def insight_copy(
    frame: pd.DataFrame,
    kind: MarketKind,
    goal: str,
    cluster: str,
    metric: ChartMetric,
    movement: float | None,
    movement_basis: str,
) -> tuple[str, str]:
    count = len(frame)
    movement_sentence = (
        f"The {metric.label.lower()} trend {movement_word(movement)} ({movement_basis})."
    )

    if kind == "sales":
        median_price = frame["price"].median()
        median_psf = frame["price_per_sqft"].median()
        low, high = middle_range(frame["price"])
        range_text = (
            f"The middle half of matching sales fell between {compact_aed(low)} and {compact_aed(high)}."
            if low is not None and high is not None
            else "A reliable price range is not available for these filters."
        )
        if goal == "Buying":
            title = f"What this means for a buyer in {cluster}"
            body = (
                f"The selection contains {count:,} registered sale{'s' if count != 1 else ''}, "
                f"with a median price of {compact_aed(median_price)} and a median of {aed_psf(median_psf)}. "
                f"{range_text} {movement_sentence} Use this as a neighbourhood benchmark; the exact "
                "plot, orientation, condition and floor plan can materially affect an individual home's value."
            )
        else:
            title = f"What this means for a seller in {cluster}"
            body = (
                f"Matching registered sales show a median price of {compact_aed(median_price)} and "
                f"{aed_psf(median_psf)}. {range_text} {movement_sentence} For an asking-price decision, "
                "the closest recent comparable homes should carry more weight than the cluster median alone."
            )
    else:
        median_rent = frame["annualised_rent"].median()
        median_yield = frame["rental_yield_pct"].median()
        low, high = middle_range(frame["annualised_rent"])
        range_text = (
            f"The middle half of annualised rents fell between {aed(low)} and {aed(high)}."
            if low is not None and high is not None
            else "A reliable rental range is not available for these filters."
        )
        if goal == "Renting":
            title = f"What this means for a tenant in {cluster}"
            body = (
                f"The selection contains {count:,} rental contract{'s' if count != 1 else ''}, with a "
                f"median annualised rent of {aed(median_rent)}. {range_text} {movement_sentence} "
                "Furnishing, plot position, upgrades, payment terms and contract length can affect the final rent."
            )
        else:
            title = f"What this means for a landlord in {cluster}"
            body = (
                f"Matching contracts show a median annualised rent of {aed(median_rent)} and a median "
                f"reported yield of {percent(median_yield)}. {range_text} {movement_sentence} A specific "
                "letting recommendation should still be checked against the closest current and recently agreed homes."
            )

    return title, body


def cta_copy(kind: MarketKind, goal: str, cluster: str) -> tuple[str, str, str]:
    if kind == "sales" and goal == "Buying":
        return (
            f"Looking to buy in {cluster}?",
            "Get a focused view of available homes, plots and the closest comparable sales.",
            "Speak to Ameer",
        )
    if kind == "sales":
        return (
            f"Thinking of selling in {cluster}?",
            "Discuss the most relevant comparable evidence and a practical route to market.",
            "Request a market review",
        )
    if goal == "Renting":
        return (
            f"Looking to rent in {cluster}?",
            "Check suitable homes and current asking levels with a specialist who knows The Valley.",
            "Explore available homes",
        )
    return (
        f"Letting a home in {cluster}?",
        "Review recent agreed rents and position the property for the current market.",
        "Discuss rental positioning",
    )


def diagnostics(warnings: list[str], sales: pd.DataFrame, rentals: pd.DataFrame) -> None:
    enabled = os.getenv("ITV_SHOW_DATA_STATUS", "false").strip().lower() in {"1", "true", "yes"}
    if not enabled:
        return
    with st.expander("Data status", expanded=False):
        st.write(
            {
                "incoming_folder": str(INCOMING_DIR),
                "processed_folder": str(PROCESSED_DIR),
                "sales_records": len(sales),
                "rental_records": len(rentals),
            }
        )
        if warnings:
            st.warning("\n".join(warnings))
        else:
            st.success("All recognised source files loaded successfully.")


def main() -> None:
    st.set_page_config(
        page_title="Inside The Valley | Market Insights",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_theme(st)

    fingerprint = source_fingerprint(INCOMING_DIR, PROCESSED_DIR)
    try:
        with st.spinner("Preparing the latest market view…"):
            sales, rentals, warnings = cached_dashboard_data(
                str(INCOMING_DIR),
                str(PROCESSED_DIR),
                fingerprint,
            )
    except Exception as exc:
        st.error("The market data could not be loaded.")
        if os.getenv("ITV_SHOW_DATA_STATUS", "false").lower() in {"1", "true", "yes"}:
            st.exception(exc)
        st.stop()

    if sales.empty and rentals.empty:
        st.error("No recognised sales or rental files are available yet.")
        st.info("Add a DXBinteract PDF, CSV or Excel export to data/incoming and redeploy.")
        st.stop()

    updated_through, history = available_history(sales, rentals)
    render_hero(st, updated_through, history)

    available_markets: list[str] = []
    if not sales.empty:
        available_markets.append("Sales")
    if not rentals.empty:
        available_markets.append("Rentals")

    requested_market = query_value("market")
    market_name = st.radio(
        "Choose a market",
        available_markets,
        index=option_index(available_markets, requested_market),
        horizontal=True,
        key="market_choice",
    )
    kind: MarketKind = "sales" if market_name == "Sales" else "rentals"
    data = sales if kind == "sales" else rentals

    section(
        st,
        "Focused market view",
        f"Explore {market_name.lower()} one neighbourhood at a time.",
        "Choose the home type and time period that matter to you. Every selection shows one clear market line, not a multi-cluster comparison.",
    )

    goal_options = ["Buying", "Selling"] if kind == "sales" else ["Renting", "Letting"]
    requested_goal = query_value("goal")
    cluster_options = sorted(data["cluster"].dropna().astype(str).unique().tolist())
    requested_cluster = query_value("cluster") or os.getenv("ITV_DEFAULT_CLUSTER")

    bedroom_values = sorted(int(value) for value in data["bedrooms"].dropna().unique())
    bedroom_options = ["All bedrooms"] + [f"{value} bedrooms" for value in bedroom_values]

    category_column = "status" if kind == "sales" else "contract_type"
    category_title = "Sale status" if kind == "sales" else "Contract type"
    category_values = sorted(
        value
        for value in data[category_column].dropna().astype(str).unique().tolist()
        if value and value != "Unknown"
    )
    category_options = ["All sale statuses" if kind == "sales" else "All contract types"] + category_values
    metric_options = [metric.label for metric in CHART_METRICS[kind]]

    with st.container(border=True):
        first = st.columns([1.25, 2.0, 1.25])
        goal = first[0].radio(
            "I am",
            goal_options,
            index=option_index(goal_options, requested_goal),
            horizontal=True,
            key=f"{kind}_goal",
        )
        cluster = first[1].selectbox(
            "Neighbourhood",
            cluster_options,
            index=option_index(cluster_options, requested_cluster),
            key=f"{kind}_cluster",
            help="Only one neighbourhood can be selected at a time.",
        )
        months = int(
            first[2].radio(
                "Time period",
                [6, 12],
                index=1,
                horizontal=True,
                format_func=lambda value: f"{value}m",
                key=f"{kind}_months",
            )
        )

        second = st.columns([1.2, 1.35, 1.55])
        bedroom_label = second[0].selectbox(
            "Bedrooms",
            bedroom_options,
            key=f"{kind}_bedrooms",
        )
        category_label = second[1].selectbox(
            category_title,
            category_options,
            key=f"{kind}_category",
        )
        requested_metric = query_value("metric")
        metric_label = second[2].selectbox(
            "Trend to show",
            metric_options,
            index=option_index(metric_options, requested_metric),
            key=f"{kind}_metric",
        )

    bedrooms = selected_bedroom(bedroom_label)
    category = None if category_label.startswith("All ") else category_label
    view = filter_market(
        data,
        kind,
        cluster,
        months,
        bedrooms=bedrooms,
        category=category,
        hide_nonstandard_sales=True,
    )

    if view.filtered.empty:
        st.warning("No registrations match this exact selection. Try a different bedroom choice, status or time period.")
        diagnostics(warnings, sales, rentals)
        footnote(st, updated_through)
        st.stop()

    metric = next(item for item in CHART_METRICS[kind] if item.label == metric_label)
    monthly = monthly_metric(view.filtered, view.date_column, view.start, view.end, metric)
    movement, movement_basis = trend_change(monthly)
    latest_valid = monthly.dropna(subset=["value"]).sort_values("month")
    latest_value = float(latest_valid.iloc[-1]["value"]) if not latest_valid.empty else None

    section(
        st,
        "At a glance",
        f"{cluster} {market_name.lower()}",
        f"Based on {len(view.filtered):,} matching registered record{'s' if len(view.filtered) != 1 else ''} from {view.start:%b %Y} to {view.end:%b %Y}.",
    )

    if kind == "sales":
        metrics = st.columns(4)
        metrics[0].metric("Median sale price", compact_aed(view.filtered["price"].median()))
        metrics[1].metric("Median price / sq ft", aed_psf(view.filtered["price_per_sqft"].median()))
        metrics[2].metric("Registered sales", f"{len(view.filtered):,}")
        latest_metric = metrics[3]
    else:
        metrics = st.columns(5)
        metrics[0].metric("Median annual rent", aed(view.filtered["annualised_rent"].median()))
        metrics[1].metric(
            "Median annual rent / sq ft",
            aed_psf(view.filtered["annualised_rent_per_sqft"].median()),
        )
        metrics[2].metric("Median reported yield", percent(view.filtered["rental_yield_pct"].median()))
        metrics[3].metric("Rental contracts", f"{len(view.filtered):,}")
        latest_metric = metrics[4]
    latest_metric.metric(
        f"Latest monthly {metric.label.lower()}",
        format_chart_value(latest_value, metric.kind),
        delta=change_text(movement),
        help=f"Movement basis: {movement_basis}.",
    )

    with st.container(border=True):
        render_chart(monthly, metric, cluster, months)
        st.caption(
            f"Monthly median values are used for prices, rents and yields. Activity charts show record counts. "
            f"Movement is calculated using {movement_basis}. The latest month may be incomplete. "
            "Months without matching source records are left blank rather than estimated."
        )

    title, body = insight_copy(
        view.filtered,
        kind,
        goal,
        cluster,
        metric,
        movement,
        movement_basis,
    )
    insight(st, title, body)

    section(
        st,
        "Recent evidence",
        "Latest matching registrations",
        "A concise view of the newest records behind the selected market benchmark.",
    )
    render_recent_records(view.filtered, kind, limit=8)

    cta_title, cta_body, cta_button = cta_copy(kind, goal, cluster)
    cta(st, cta_title, cta_body, cta_button)

    diagnostics(warnings, sales, rentals)
    footnote(st, updated_through)


if __name__ == "__main__":
    main()
