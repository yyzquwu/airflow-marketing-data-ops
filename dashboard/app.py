from __future__ import annotations

import sys
from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CSV_PATH = PROJECT_ROOT / "output" / "unified_campaign_daily.csv"
METRIC_COLUMNS = ["impressions", "clicks", "spend", "conversions"]
REQUIRED_COLUMNS = [
    "date",
    "source",
    "account_id",
    "campaign_id",
    "campaign_name",
    "impressions",
    "clicks",
    "spend",
    "conversions",
    "ctr",
    "cpc",
    "cpa",
]
SOURCE_LABELS = {
    "google_ads": "Google Ads",
    "meta_ads": "Meta Ads",
    "tiktok_ads": "TikTok Ads",
}
PLATFORM_COLORS = {
    "Google Ads": "#2563eb",
    "Meta Ads": "#0f766e",
    "TikTok Ads": "#db2777",
}


def safe_divide(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def prepare_campaign_data(df: pd.DataFrame) -> pd.DataFrame:
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing_columns:
        joined = ", ".join(missing_columns)
        raise ValueError(f"Uploaded CSV is missing required columns: {joined}")

    prepared = df.copy()
    prepared["date"] = pd.to_datetime(prepared["date"], errors="coerce", format="mixed").dt.normalize()
    if prepared["date"].isna().any():
        raise ValueError("CSV contains rows with invalid dates.")

    for column in METRIC_COLUMNS + ["ctr", "cpc", "cpa"]:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce").fillna(0)

    prepared["source_label"] = prepared["source"].map(SOURCE_LABELS).fillna(prepared["source"])
    return prepared.sort_values(["date", "source_label", "campaign_name"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_default_campaign_data() -> tuple[pd.DataFrame, bool, str]:
    generated = False
    if not DEFAULT_CSV_PATH.exists():
        from marketing_data_ops.pipeline import run_pipeline

        run_pipeline(PROJECT_ROOT)
        generated = True

    df = pd.read_csv(DEFAULT_CSV_PATH)
    source_path = DEFAULT_CSV_PATH.relative_to(PROJECT_ROOT).as_posix()
    return prepare_campaign_data(df), generated, source_path


def filter_campaign_data(
    df: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    sources: list[str],
    campaigns: list[str],
) -> pd.DataFrame:
    filtered = df[
        (df["date"] >= start_date)
        & (df["date"] <= end_date)
        & (df["source"].isin(sources))
        & (df["campaign_name"].isin(campaigns))
    ]
    return filtered.copy()


def summarize_performance(df: pd.DataFrame) -> dict[str, float]:
    spend = float(df["spend"].sum())
    impressions = float(df["impressions"].sum())
    clicks = float(df["clicks"].sum())
    conversions = float(df["conversions"].sum())
    return {
        "spend": spend,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "ctr": safe_divide(clicks, impressions),
        "cpc": safe_divide(spend, clicks),
        "cpa": safe_divide(spend, conversions),
    }


def platform_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("source_label", as_index=False)[METRIC_COLUMNS]
        .sum()
        .sort_values("spend", ascending=False)
    )
    summary["ctr"] = summary.apply(lambda row: safe_divide(row["clicks"], row["impressions"]), axis=1)
    summary["cpc"] = summary.apply(lambda row: safe_divide(row["spend"], row["clicks"]), axis=1)
    summary["cpa"] = summary.apply(lambda row: safe_divide(row["spend"], row["conversions"]), axis=1)
    return summary


def campaign_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(["campaign_name", "source_label"], as_index=False)[METRIC_COLUMNS]
        .sum()
        .sort_values(["conversions", "spend"], ascending=[False, False])
    )
    summary["ctr"] = summary.apply(lambda row: safe_divide(row["clicks"], row["impressions"]), axis=1)
    summary["cpc"] = summary.apply(lambda row: safe_divide(row["spend"], row["clicks"]), axis=1)
    summary["cpa"] = summary.apply(lambda row: safe_divide(row["spend"], row["conversions"]), axis=1)
    return summary


def time_series(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("date", as_index=False)[METRIC_COLUMNS]
        .sum()
        .sort_values("date")
    )


def money(value: float) -> str:
    return f"${value:,.0f}" if abs(value) >= 100 else f"${value:,.2f}"


def number(value: float) -> str:
    return f"{value:,.0f}"


def percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --page-bg: #eef3f8;
            --ink: #0f172a;
            --muted: #475569;
            --line: #d8e1ec;
            --panel: #ffffff;
            --navy: #071623;
        }
        [data-testid="stAppViewContainer"] {
            background: var(--page-bg);
        }
        [data-testid="stHeader"] {
            background: transparent;
        }
        [data-testid="stToolbar"] {
            display: none;
        }
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stMarkdown p {
            color: #334155;
            font-size: 0.88rem;
            font-weight: 650;
        }
        [data-testid="stSidebar"] h1 {
            color: var(--ink);
            font-size: 1.2rem;
            line-height: 1.15;
            margin-bottom: 0.15rem;
        }
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: #64748b;
            font-size: 0.82rem;
            line-height: 1.4;
        }
        [data-testid="stFileUploaderDropzone"] {
            background: #f8fafc;
            border: 1px dashed #94a3b8;
            border-radius: 8px;
        }
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] span {
            color: #334155;
        }
        .stDownloadButton button {
            background: #0f766e;
            border: 1px solid #0f766e;
            border-radius: 8px;
            color: #ffffff;
            font-weight: 700;
        }
        .stDownloadButton button:hover {
            background: #115e59;
            border-color: #115e59;
            color: #ffffff;
        }
        [data-baseweb="tag"] {
            background: #2563eb !important;
            border-radius: 6px !important;
            color: #ffffff !important;
        }
        [data-baseweb="tag"] span {
            color: #ffffff !important;
        }
        .main .block-container {
            max-width: 1360px;
            padding-top: 1.25rem;
            padding-bottom: 2.5rem;
        }
        h1, h2, h3, p, div, span {
            letter-spacing: 0;
        }
        .masthead {
            background: linear-gradient(135deg, #071623 0%, #0b2440 58%, #12325a 100%);
            border: 1px solid #17345a;
            border-radius: 8px;
            box-shadow: 0 18px 42px rgba(7, 22, 35, 0.18);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 28px;
            margin-bottom: 20px;
            min-height: 148px;
            padding: 22px 24px;
            position: relative;
            overflow: hidden;
        }
        .masthead:after {
            background: #22d3ee;
            bottom: 0;
            content: "";
            height: 4px;
            left: 0;
            position: absolute;
            width: 35%;
        }
        .masthead-title {
            color: #ffffff !important;
            font-size: 2rem;
            font-weight: 760;
            line-height: 1.12;
            margin: 0;
        }
        .masthead-copy {
            color: #cbd5e1 !important;
            font-size: 0.98rem;
            line-height: 1.55;
            margin: 10px 0 0;
            max-width: 760px;
        }
        .lineage-chip {
            background: rgba(255, 255, 255, 0.09);
            border: 1px solid rgba(226, 232, 240, 0.22);
            border-radius: 8px;
            color: #e2e8f0;
            font-size: 0.78rem;
            line-height: 1.45;
            max-width: 360px;
            padding: 12px 14px;
        }
        .metric-card {
            background: #ffffff;
            border: 1px solid var(--line);
            border-left: 5px solid var(--accent);
            border-radius: 8px;
            box-shadow: 0 16px 34px rgba(15, 23, 42, 0.07);
            min-height: 122px;
            padding: 16px 17px 14px;
        }
        .metric-head {
            align-items: center;
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
        }
        .metric-swatch {
            background: var(--accent);
            border-radius: 999px;
            display: inline-block;
            height: 9px;
            width: 9px;
        }
        .metric-label {
            color: #475569;
            font-size: 0.76rem;
            font-weight: 720;
            text-transform: uppercase;
        }
        .metric-value {
            color: var(--ink);
            font-size: 1.62rem;
            font-weight: 780;
            line-height: 1.1;
            margin-bottom: 8px;
        }
        .metric-note {
            color: #64748b;
            font-size: 0.82rem;
            line-height: 1.35;
        }
        .section-title {
            color: var(--ink);
            font-size: 1.02rem;
            font-weight: 760;
            margin: 16px 0 10px;
        }
        .insight-card {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: 0 12px 26px rgba(15, 23, 42, 0.05);
            min-height: 132px;
            padding: 15px 16px;
        }
        .insight-kicker {
            color: #0f766e;
            font-size: 0.75rem;
            font-weight: 720;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        .insight-main {
            color: var(--ink);
            font-size: 1.05rem;
            font-weight: 740;
            line-height: 1.3;
            margin-bottom: 8px;
        }
        .insight-detail {
            color: var(--muted);
            font-size: 0.86rem;
            line-height: 1.45;
        }
        .stPlotlyChart {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: 0 14px 30px rgba(15, 23, 42, 0.055);
            padding: 8px 8px 4px;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: 0 14px 30px rgba(15, 23, 42, 0.045);
            overflow: hidden;
        }
        @media (max-width: 900px) {
            .masthead {
                display: block;
                min-height: auto;
            }
            .lineage-chip {
                margin-top: 16px;
                max-width: none;
            }
            .masthead-title {
                font-size: 1.65rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, note: str, accent: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card" style="--accent: {accent};">
            <div class="metric-head">
                <span class="metric-swatch"></span>
                <div class="metric-label">{escape(label)}</div>
            </div>
            <div class="metric-value">{escape(value)}</div>
            <div class="metric-note">{escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_insight(kicker: str, main: str, detail: str) -> None:
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-kicker">{escape(kicker)}</div>
            <div class="insight-main">{escape(main)}</div>
            <div class="insight-detail">{escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_figure(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=24, r=24, t=44, b=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(family="Arial, sans-serif", color="#334155", size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        title_font=dict(color="#0f172a", size=17),
    )
    fig.update_xaxes(showgrid=False, linecolor="#d8e1ec", tickfont=dict(color="#475569"))
    fig.update_yaxes(gridcolor="#edf2f7", zerolinecolor="#edf2f7", tickfont=dict(color="#475569"))
    return fig


def render_trend_chart(df: pd.DataFrame) -> None:
    trend = time_series(df)
    trend["date_label"] = trend["date"].dt.strftime("%b %d")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=trend["date_label"],
            y=trend["spend"],
            name="Spend",
            mode="lines+markers",
            line=dict(color="#2563eb", width=3),
            marker=dict(size=8),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=trend["date_label"],
            y=trend["conversions"],
            name="Conversions",
            marker_color="#0f766e",
            opacity=0.78,
        ),
        secondary_y=True,
    )
    fig.update_layout(title="Spend and conversions by day")
    fig.update_xaxes(type="category")
    fig.update_yaxes(title_text="Spend", secondary_y=False)
    fig.update_yaxes(title_text="Conversions", secondary_y=True)
    st.plotly_chart(style_figure(fig, 390), width="stretch")


def render_platform_chart(df: pd.DataFrame) -> None:
    summary = platform_summary(df)
    fig = px.bar(
        summary,
        x="source_label",
        y="spend",
        color="source_label",
        color_discrete_map=PLATFORM_COLORS,
        text=summary["spend"].map(money),
        title="Spend by platform",
        labels={"source_label": "", "spend": "Spend"},
    )
    fig.update_traces(textposition="outside", marker_line_width=0)
    st.plotly_chart(style_figure(fig, 345), width="stretch")


def render_efficiency_chart(df: pd.DataFrame) -> None:
    summary = campaign_summary(df).sort_values("cpa", ascending=True)
    fig = px.bar(
        summary,
        x="cpa",
        y="campaign_name",
        color="source_label",
        color_discrete_map=PLATFORM_COLORS,
        orientation="h",
        title="Cost per acquisition by campaign",
        labels={"campaign_name": "", "cpa": "CPA", "source_label": "Platform"},
    )
    fig.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(style_figure(fig, 345), width="stretch")


def render_takeaways(df: pd.DataFrame) -> None:
    platform = platform_summary(df)
    campaigns = campaign_summary(df)
    top_spend = platform.iloc[0]
    top_conversions = campaigns.sort_values("conversions", ascending=False).iloc[0]
    efficient = campaigns[campaigns["conversions"] > 0].sort_values("cpa", ascending=True).iloc[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        render_insight(
            "Budget concentration",
            f"{top_spend['source_label']} carries {money(top_spend['spend'])} in spend",
            f"{percent(top_spend['spend'] / platform['spend'].sum())} of filtered media spend.",
        )
    with col2:
        render_insight(
            "Conversion leader",
            str(top_conversions["campaign_name"]),
            f"{number(top_conversions['conversions'])} conversions at {money(top_conversions['cpa'])} CPA.",
        )
    with col3:
        render_insight(
            "Efficiency watch",
            str(efficient["campaign_name"]),
            f"Lowest CPA in the filtered view: {money(efficient['cpa'])}.",
        )


def render_campaign_table(df: pd.DataFrame) -> None:
    leaderboard = campaign_summary(df).copy()
    leaderboard["ctr"] = leaderboard["ctr"].map(percent)
    leaderboard["spend"] = leaderboard["spend"].map(money)
    leaderboard["cpc"] = leaderboard["cpc"].map(money)
    leaderboard["cpa"] = leaderboard["cpa"].map(money)
    leaderboard["impressions"] = leaderboard["impressions"].map(number)
    leaderboard["clicks"] = leaderboard["clicks"].map(number)
    leaderboard["conversions"] = leaderboard["conversions"].map(number)
    leaderboard = leaderboard[
        [
            "campaign_name",
            "source_label",
            "spend",
            "impressions",
            "clicks",
            "conversions",
            "ctr",
            "cpc",
            "cpa",
        ]
    ]
    leaderboard.columns = [
        "Campaign",
        "Platform",
        "Spend",
        "Impressions",
        "Clicks",
        "Conversions",
        "CTR",
        "CPC",
        "CPA",
    ]
    st.dataframe(leaderboard, width="stretch", hide_index=True, height=260)


def main() -> None:
    st.set_page_config(
        page_title="Marketing Data Ops Dashboard",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()

    default_df, generated_default, source_path = load_default_campaign_data()

    with st.sidebar:
        st.title("Campaign Console")
        st.caption("Default CSV is generated from the raw platform extracts in this repo.")
        uploaded = st.file_uploader("Upload unified campaign CSV", type=["csv"])

    if uploaded is not None:
        try:
            df = prepare_campaign_data(pd.read_csv(uploaded))
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
        source_note = f"Uploaded file: {uploaded.name}"
    else:
        df = default_df
        source_note = f"Default file: {source_path}"
        if generated_default:
            source_note += " (generated on load)"

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    label_to_source = dict(zip(df["source_label"], df["source"]))
    platform_labels = sorted(label_to_source)
    campaign_names = sorted(df["campaign_name"].unique())

    with st.sidebar:
        selected_dates = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        selected_platforms = st.multiselect(
            "Platforms",
            options=platform_labels,
            default=platform_labels,
        )
        selected_campaigns = st.multiselect(
            "Campaigns",
            options=campaign_names,
            default=campaign_names,
        )

    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date = end_date = selected_dates

    selected_sources = [label_to_source[label] for label in selected_platforms]
    filtered = filter_campaign_data(
        df=df,
        start_date=pd.Timestamp(start_date),
        end_date=pd.Timestamp(end_date),
        sources=selected_sources,
        campaigns=selected_campaigns,
    )

    with st.sidebar:
        st.download_button(
            "Download filtered CSV",
            data=filtered.drop(columns=["source_label"]).to_csv(index=False),
            file_name="filtered_campaign_daily.csv",
            mime="text/csv",
            disabled=filtered.empty,
        )

    st.markdown(
        f"""
        <div class="masthead">
            <div>
                <h1 class="masthead-title">Marketing Data Ops Dashboard</h1>
                <p class="masthead-copy">
                    A recruiter-friendly view of the Airflow pipeline output: unified campaign
                    performance, quality-ready CSV lineage, and analyst takeaways across paid media sources.
                </p>
            </div>
            <div class="lineage-chip">{escape(source_note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if filtered.empty:
        st.warning("No rows match the selected filters.")
        st.stop()

    totals = summarize_performance(filtered)
    date_count = filtered["date"].nunique()
    campaign_count = filtered["campaign_name"].nunique()

    metric_cols = st.columns(5)
    with metric_cols[0]:
        render_metric_card("Spend", money(totals["spend"]), f"{date_count} reporting days", "#2563eb")
    with metric_cols[1]:
        render_metric_card("Conversions", number(totals["conversions"]), f"{campaign_count} active campaigns", "#0f766e")
    with metric_cols[2]:
        render_metric_card("CPA", money(totals["cpa"]), "Spend divided by conversions", "#db2777")
    with metric_cols[3]:
        render_metric_card("CTR", percent(totals["ctr"]), f"{number(totals['clicks'])} total clicks", "#f59e0b")
    with metric_cols[4]:
        render_metric_card("CPC", money(totals["cpc"]), f"{number(totals['impressions'])} impressions", "#7c3aed")

    st.markdown('<div class="section-title">Performance Trend</div>', unsafe_allow_html=True)
    render_trend_chart(filtered)

    chart_cols = st.columns(2)
    with chart_cols[0]:
        render_platform_chart(filtered)
    with chart_cols[1]:
        render_efficiency_chart(filtered)

    st.markdown('<div class="section-title">Analyst Takeaways</div>', unsafe_allow_html=True)
    render_takeaways(filtered)

    st.markdown('<div class="section-title">Campaign Leaderboard</div>', unsafe_allow_html=True)
    render_campaign_table(filtered)

    st.caption(
        "Lineage: data/raw platform extracts -> pipeline validation and normalization -> "
        "output/unified_campaign_daily.csv -> Streamlit dashboard."
    )


if __name__ == "__main__":
    main()
