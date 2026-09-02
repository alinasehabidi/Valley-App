"""Visual styling for the Inside The Valley public dashboard."""

from __future__ import annotations

import html
import os

BRAND = {
    "ink": "#182019",
    "forest": "#263128",
    "forest_dark": "#121A14",
    "sage": "#7D8A78",
    "sand": "#C7B99E",
    "sand_light": "#E7DFD0",
    "cream": "#F5F1E8",
    "paper": "#FFFCF7",
    "muted": "#6F756F",
}

DEFAULT_LOGO_URL = "https://insidethevalley.ae/wp-content/uploads/2026/08/logo.png"
DEFAULT_CONTACT_URL = "https://insidethevalley.ae"


def apply_theme(st) -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Libre+Caslon+Display&display=swap');

        :root {{
            --itv-ink: {BRAND['ink']};
            --itv-forest: {BRAND['forest']};
            --itv-forest-dark: {BRAND['forest_dark']};
            --itv-sage: {BRAND['sage']};
            --itv-sand: {BRAND['sand']};
            --itv-sand-light: {BRAND['sand_light']};
            --itv-cream: {BRAND['cream']};
            --itv-paper: {BRAND['paper']};
            --itv-muted: {BRAND['muted']};
        }}

        html, body, [class*="css"], .stApp {{
            font-family: "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: var(--itv-ink);
        }}

        .stApp {{
            background:
                radial-gradient(circle at 4% 2%, rgba(199,185,158,.20), transparent 26rem),
                var(--itv-cream);
        }}

        [data-testid="stHeader"] {{ height: 0; background: transparent; }}
        #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
        [data-testid="stStatusWidget"], .stDeployButton {{ display: none !important; }}

        .block-container {{
            max-width: 1180px;
            padding-top: 1.1rem;
            padding-bottom: 3.5rem;
        }}

        .itv-hero {{
            position: relative;
            overflow: hidden;
            padding: clamp(1.45rem, 4vw, 3rem);
            margin-bottom: 1.1rem;
            border-radius: 26px;
            color: #fff;
            background:
                radial-gradient(circle at 87% 17%, rgba(199,185,158,.23), transparent 18rem),
                linear-gradient(135deg, var(--itv-forest) 0%, #19231C 62%, var(--itv-forest-dark) 100%);
            box-shadow: 0 24px 58px rgba(24,32,25,.15);
        }}

        .itv-hero::after {{
            content: "";
            position: absolute;
            width: 540px;
            height: 235px;
            right: -85px;
            bottom: -120px;
            border: 1px solid rgba(231,223,208,.22);
            border-radius: 50%;
            box-shadow:
                0 -24px 0 -23px rgba(231,223,208,.18),
                0 -48px 0 -47px rgba(231,223,208,.13),
                0 -72px 0 -71px rgba(231,223,208,.09);
            transform: rotate(-7deg);
        }}

        .itv-hero-grid {{
            position: relative;
            z-index: 2;
            display: grid;
            grid-template-columns: minmax(0,1fr) minmax(160px,290px);
            gap: 2rem;
            align-items: center;
        }}

        .itv-eyebrow {{
            margin-bottom: .7rem;
            color: var(--itv-sand-light);
            font-size: .73rem;
            font-weight: 700;
            letter-spacing: .18em;
            text-transform: uppercase;
        }}

        .itv-hero h1 {{
            max-width: 720px;
            margin: 0;
            color: #fff;
            font-family: "Libre Caslon Display", Georgia, serif;
            font-size: clamp(2rem, 5vw, 4.1rem);
            font-weight: 400;
            line-height: 1.02;
            letter-spacing: -.035em;
        }}

        .itv-hero-copy {{
            max-width: 720px;
            margin: 1rem 0 0;
            color: rgba(255,255,255,.78);
            font-size: clamp(.96rem, 1.8vw, 1.1rem);
            line-height: 1.7;
        }}

        .itv-logo {{
            width: 100%;
            max-height: 145px;
            object-fit: contain;
            filter: drop-shadow(0 10px 18px rgba(0,0,0,.18));
        }}

        .itv-meta {{
            position: relative;
            z-index: 2;
            display: flex;
            flex-wrap: wrap;
            gap: .55rem;
            margin-top: 1.35rem;
        }}

        .itv-pill {{
            display: inline-flex;
            align-items: center;
            min-height: 34px;
            padding: .43rem .72rem;
            border: 1px solid rgba(255,255,255,.14);
            border-radius: 999px;
            color: rgba(255,255,255,.82);
            background: rgba(255,255,255,.07);
            backdrop-filter: blur(8px);
            font-size: .77rem;
        }}

        .itv-section {{ margin: 1.75rem 0 .72rem; }}
        .itv-section .eyebrow {{
            color: var(--itv-sage);
            font-size: .71rem;
            font-weight: 700;
            letter-spacing: .14em;
            text-transform: uppercase;
        }}
        .itv-section h2 {{
            margin: .28rem 0 0;
            color: var(--itv-ink);
            font-family: "Libre Caslon Display", Georgia, serif;
            font-size: clamp(1.55rem, 3vw, 2.35rem);
            font-weight: 400;
            letter-spacing: -.025em;
        }}
        .itv-section p {{
            max-width: 800px;
            margin: .42rem 0 0;
            color: var(--itv-muted);
            line-height: 1.65;
        }}

        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: rgba(125,138,120,.22) !important;
            border-radius: 20px !important;
            background: rgba(255,252,247,.86);
            box-shadow: 0 10px 28px rgba(24,32,25,.05);
        }}

        div[data-testid="stMetric"] {{
            min-height: 124px;
            padding: 1.02rem 1.12rem;
            border: 1px solid rgba(125,138,120,.20);
            border-radius: 18px;
            background: var(--itv-paper);
            box-shadow: 0 8px 22px rgba(24,32,25,.045);
        }}
        div[data-testid="stMetricLabel"] p {{
            color: var(--itv-muted);
            font-size: .74rem;
            font-weight: 700;
            letter-spacing: .045em;
            text-transform: uppercase;
        }}
        div[data-testid="stMetricValue"] {{
            color: var(--itv-ink);
            font-family: "Libre Caslon Display", Georgia, serif;
            font-size: clamp(1.5rem, 3vw, 2.28rem);
            letter-spacing: -.025em;
        }}
        div[data-testid="stMetricDelta"] {{ color: var(--itv-sage); font-size: .78rem; }}

        div[role="radiogroup"] {{ gap: .45rem; flex-wrap: wrap; }}
        div[role="radiogroup"] label {{
            margin: 0 !important;
            padding: .55rem .82rem !important;
            border: 1px solid rgba(125,138,120,.25);
            border-radius: 999px;
            background: #fff;
            transition: all .15s ease;
        }}
        div[role="radiogroup"] label:has(input:checked) {{
            border-color: var(--itv-forest);
            color: #fff !important;
            background: var(--itv-forest);
            box-shadow: 0 7px 18px rgba(38,49,40,.16);
        }}
        div[role="radiogroup"] label:has(input:checked) p {{ color: #fff !important; }}

        [data-baseweb="select"] > div {{
            min-height: 48px;
            border-color: rgba(125,138,120,.28) !important;
            border-radius: 12px !important;
            background: #fff !important;
        }}
        [data-testid="stWidgetLabel"] p {{
            color: var(--itv-ink);
            font-size: .81rem;
            font-weight: 600;
        }}

        [data-testid="stDataFrame"] {{
            overflow: hidden;
            border: 1px solid rgba(125,138,120,.20);
            border-radius: 16px;
            background: #fff;
        }}

        .itv-records {{
            display: grid;
            gap: .62rem;
        }}
        .itv-record {{
            display: grid;
            grid-template-columns: minmax(230px,1.35fr) minmax(150px,.75fr) minmax(150px,.75fr);
            gap: 1rem;
            align-items: center;
            padding: .95rem 1.05rem;
            border: 1px solid rgba(125,138,120,.18);
            border-radius: 16px;
            background: rgba(255,252,247,.94);
            box-shadow: 0 7px 20px rgba(24,32,25,.035);
        }}
        .itv-record-main {{ min-width: 0; }}
        .itv-record-date {{
            margin-bottom: .2rem;
            color: var(--itv-muted);
            font-size: .7rem;
            font-weight: 700;
            letter-spacing: .055em;
            text-transform: uppercase;
        }}
        .itv-record-home {{
            overflow: hidden;
            color: var(--itv-ink);
            font-family: "Libre Caslon Display", Georgia, serif;
            font-size: 1.17rem;
            line-height: 1.2;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .itv-record-sub {{
            margin-top: .2rem;
            color: var(--itv-muted);
            font-size: .78rem;
        }}
        .itv-record-tag {{
            display: inline-flex;
            margin-top: .48rem;
            padding: .26rem .53rem;
            border-radius: 999px;
            font-size: .69rem;
            font-weight: 700;
        }}
        .itv-record-tag.ready, .itv-record-tag.new {{
            color: #2F7354;
            background: #E7F5ED;
        }}
        .itv-record-tag.offplan {{
            color: #946A22;
            background: #FFF0D8;
        }}
        .itv-record-tag.renewed {{
            color: #735B2F;
            background: #F7ECD8;
        }}
        .itv-record-stat {{
            min-width: 0;
            padding-left: .95rem;
            border-left: 1px solid rgba(125,138,120,.18);
        }}
        .itv-record-stat span {{
            display: block;
            margin-bottom: .18rem;
            color: var(--itv-muted);
            font-size: .69rem;
            font-weight: 700;
            letter-spacing: .045em;
            text-transform: uppercase;
        }}
        .itv-record-stat strong {{
            display: block;
            overflow: hidden;
            color: var(--itv-ink);
            font-size: .95rem;
            font-weight: 700;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .itv-insight {{
            margin: .65rem 0 1rem;
            padding: 1.18rem 1.28rem;
            border-left: 4px solid var(--itv-sand);
            border-radius: 0 16px 16px 0;
            background: rgba(255,252,247,.94);
            box-shadow: 0 8px 22px rgba(24,32,25,.04);
        }}
        .itv-insight h3 {{
            margin: 0 0 .38rem;
            color: var(--itv-ink);
            font-family: "Libre Caslon Display", Georgia, serif;
            font-size: 1.34rem;
            font-weight: 400;
        }}
        .itv-insight p {{ margin: 0; color: var(--itv-muted); line-height: 1.65; }}

        .itv-cta-card {{
            display: grid;
            grid-template-columns: minmax(0,1fr) auto;
            align-items: center;
            gap: 1.2rem;
            margin-top: 1.2rem;
            padding: 1.32rem 1.48rem;
            border-radius: 20px;
            color: #fff;
            background: linear-gradient(135deg, var(--itv-forest), var(--itv-forest-dark));
        }}
        .itv-cta-card h3 {{
            margin: 0;
            color: #fff;
            font-family: "Libre Caslon Display", Georgia, serif;
            font-size: 1.5rem;
            font-weight: 400;
        }}
        .itv-cta-card p {{ margin: .34rem 0 0; color: rgba(255,255,255,.72); line-height: 1.55; }}
        .itv-cta {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 46px;
            padding: .65rem 1rem;
            border-radius: 999px;
            color: var(--itv-ink) !important;
            background: var(--itv-sand-light);
            font-size: .84rem;
            font-weight: 700;
            text-decoration: none !important;
            white-space: nowrap;
        }}

        .itv-footnote {{
            margin-top: 1.6rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(125,138,120,.20);
            color: var(--itv-muted);
            font-size: .74rem;
            line-height: 1.6;
        }}

        .stAlert {{ border-radius: 14px; }}

        @media (max-width: 720px) {{
            .block-container {{ padding: .7rem .8rem 2.5rem; }}
            .itv-hero {{ border-radius: 20px; padding: 1.3rem; }}
            .itv-hero-grid {{ grid-template-columns: 1fr; }}
            .itv-logo {{ max-width: 230px; max-height: 90px; object-position: left center; }}
            .itv-record {{ grid-template-columns: 1fr; gap: .72rem; }}
            .itv-record-home {{ white-space: normal; }}
            .itv-record-stat {{ padding: .68rem 0 0; border-left: 0; border-top: 1px solid rgba(125,138,120,.18); }}
            .itv-cta-card {{ grid-template-columns: 1fr; }}
            .itv-cta {{ width: 100%; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(st, updated_through: str, history: str) -> None:
    logo = html.escape(os.getenv("ITV_LOGO_URL", DEFAULT_LOGO_URL), quote=True)
    st.markdown(
        f"""
        <section class="itv-hero">
            <div class="itv-hero-grid">
                <div>
                    <div class="itv-eyebrow">The Valley by Emaar</div>
                    <h1>Market insights, made clear.</h1>
                    <p class="itv-hero-copy">
                        Explore actual sales and rental activity by neighbourhood, in a focused view
                        designed for buyers, sellers, tenants and landlords.
                    </p>
                </div>
                <img class="itv-logo" src="{logo}" alt="Inside The Valley">
            </div>
            <div class="itv-meta">
                <span class="itv-pill">Updated through {html.escape(updated_through)}</span>
                <span class="itv-pill">Available history: {html.escape(history)}</span>
                <span class="itv-pill">Updated bi-weekly</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def section(st, eyebrow: str, title: str, body: str = "") -> None:
    body_html = f"<p>{html.escape(body)}</p>" if body else ""
    st.markdown(
        f"""
        <div class="itv-section">
            <div class="eyebrow">{html.escape(eyebrow)}</div>
            <h2>{html.escape(title)}</h2>
            {body_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight(st, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="itv-insight">
            <h3>{html.escape(title)}</h3>
            <p>{html.escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def cta(st, title: str, body: str, button: str) -> None:
    url = html.escape(os.getenv("ITV_CONTACT_URL", DEFAULT_CONTACT_URL), quote=True)
    st.markdown(
        f"""
        <div class="itv-cta-card">
            <div>
                <h3>{html.escape(title)}</h3>
                <p>{html.escape(body)}</p>
            </div>
            <a class="itv-cta" href="{url}" target="_blank" rel="noopener noreferrer">
                {html.escape(button)}
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footnote(st, updated_through: str) -> None:
    st.markdown(
        f"""
        <div class="itv-footnote">
            Source: Dubai real-estate transaction and tenancy records supplied through the current
            DXBinteract or Dubai Land Department exports in this repository. Updated through
            {html.escape(updated_through)}. These are descriptive market benchmarks, not a formal
            valuation or financial advice. The latest month may be incomplete.
        </div>
        """,
        unsafe_allow_html=True,
    )
