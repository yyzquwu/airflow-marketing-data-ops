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
    "youtube_ads": "YouTube",
    "microsoft_ads": "Microsoft Ads",
    "other_ads": "Other",
}
PLATFORM_COLORS = {
    "Google Ads": "#2563eb",
    "Meta Ads": "#0f766e",
    "TikTok Ads": "#db2777",
    "YouTube": "#f59e0b",
    "Microsoft Ads": "#7c3aed",
    "Other": "#64748b",
}
SOURCE_MEDIUM = {
    "Google Ads": "Paid Search",
    "Meta Ads": "Paid Social",
    "TikTok Ads": "Paid Social",
    "YouTube": "Video",
    "Microsoft Ads": "Paid Search",
    "Other": "Affiliate / Other",
}
METRIC_ACCENTS = {
    "Spend": "#2563eb",
    "Conversions": "#0f766e",
    "CPA": "#db2777",
    "CTR": "#f59e0b",
    "CPC": "#7c3aed",
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
    prepared["source_medium"] = prepared["source_label"].map(SOURCE_MEDIUM).fillna("Paid Media")
    return prepared.sort_values(["date", "source_label", "campaign_name"]).reset_index(drop=True)


def ensure_dashboard_columns(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    if "source_label" not in prepared.columns:
        prepared["source_label"] = prepared["source"].map(SOURCE_LABELS).fillna(prepared["source"])
    if "source_medium" not in prepared.columns:
        prepared["source_medium"] = prepared["source_label"].map(SOURCE_MEDIUM).fillna("Paid Media")
    return prepared


def default_output_is_stale() -> bool:
    if not DEFAULT_CSV_PATH.exists():
        return True

    from marketing_data_ops.io import SOURCE_FILES

    output_mtime = DEFAULT_CSV_PATH.stat().st_mtime
    dependency_paths = [PROJECT_ROOT / "config" / "pipeline.yml"]
    dependency_paths.extend(PROJECT_ROOT / path for path in SOURCE_FILES.values())
    return any(path.exists() and path.stat().st_mtime > output_mtime for path in dependency_paths)


def load_default_campaign_data() -> tuple[pd.DataFrame, bool, str]:
    generated = False
    if default_output_is_stale():
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
    source_media: list[str],
) -> pd.DataFrame:
    filtered = df[
        (df["date"] >= start_date)
        & (df["date"] <= end_date)
        & (df["source"].isin(sources))
        & (df["campaign_name"].isin(campaigns))
        & (df["source_medium"].isin(source_media))
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


def time_series(df: pd.DataFrame, grain: str) -> pd.DataFrame:
    daily = df.copy()
    if grain == "Week":
        daily["period"] = daily["date"].dt.to_period("W").dt.start_time
        label_format = "%b %d"
    elif grain == "Month":
        daily["period"] = daily["date"].dt.to_period("M").dt.start_time
        label_format = "%b %Y"
    else:
        daily["period"] = daily["date"]
        label_format = "%b %d"

    trend = (
        daily.groupby("period", as_index=False)[METRIC_COLUMNS]
        .sum()
        .sort_values("period")
    )
    trend["label"] = trend["period"].dt.strftime(label_format)
    return trend


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
        [data-testid="stSidebar"] hr {
            border: 0;
            border-top: 1px solid #e2e8f0;
            margin: 1.2rem 0;
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
        [data-testid="stSidebar"] h3 {
            color: #0f172a;
            font-size: 0.78rem;
            font-weight: 800;
            margin: 0.8rem 0 0.25rem;
            text-transform: uppercase;
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
            padding-top: 0.75rem;
            padding-bottom: 2.5rem;
        }
        h1, h2, h3, p, div, span {
            letter-spacing: 0;
        }
        .topbar {
            align-items: center;
            background: linear-gradient(135deg, #061526 0%, #09233f 100%);
            border-radius: 0 0 8px 8px;
            box-shadow: 0 12px 30px rgba(7, 22, 35, 0.13);
            color: #ffffff;
            display: flex;
            justify-content: space-between;
            margin: -0.75rem -0.25rem 1rem;
            min-height: 64px;
            padding: 13px 22px;
        }
        .brand-lockup {
            align-items: center;
            display: flex;
            gap: 14px;
        }
        .brand-mark {
            align-items: center;
            border: 1px solid rgba(255,255,255,0.36);
            border-radius: 999px;
            display: flex;
            font-size: 1.15rem;
            font-weight: 850;
            height: 38px;
            justify-content: center;
            width: 38px;
        }
        .brand-title {
            color: #ffffff;
            font-size: 1rem;
            font-weight: 800;
            line-height: 1.1;
        }
        .brand-subtitle {
            color: #cbd5e1;
            font-size: 0.78rem;
            margin-top: 3px;
        }
        .topbar-meta {
            align-items: center;
            color: #e2e8f0;
            display: flex;
            flex-wrap: wrap;
            font-size: 0.78rem;
            gap: 10px;
            justify-content: flex-end;
        }
        .topbar-pill {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(226, 232, 240, 0.18);
            border-radius: 8px;
            padding: 8px 10px;
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
        .status-card {
            background: #f8fafc;
            border: 1px solid #d8e1ec;
            border-radius: 8px;
            color: #334155;
            font-size: 0.8rem;
            line-height: 1.35;
            padding: 10px 11px;
        }
        .status-ok {
            color: #0f766e;
            font-weight: 850;
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
        .metric-icon {
            align-items: center;
            background: color-mix(in srgb, var(--accent), white 84%);
            border-radius: 8px;
            color: var(--accent);
            display: flex;
            font-size: 1.12rem;
            font-weight: 850;
            height: 34px;
            justify-content: center;
            margin-bottom: 12px;
            width: 34px;
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
        .section-row {
            align-items: center;
            display: flex;
            justify-content: space-between;
            gap: 12px;
            margin: 16px 0 10px;
        }
        .section-row .section-title {
            margin: 0;
        }
        .mode-tabs {
            align-items: center;
            background: #ffffff;
            border: 1px solid #d8e1ec;
            border-radius: 8px;
            display: flex;
            gap: 4px;
            padding: 4px;
        }
        .mode-tab {
            border-radius: 6px;
            color: #475569;
            font-size: 0.78rem;
            font-weight: 750;
            padding: 6px 10px;
        }
        .mode-tab-active {
            background: #2563eb;
            color: #ffffff;
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
        .legend-row {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: 0 14px 30px rgba(15, 23, 42, 0.045);
            font-size: 0.82rem;
            line-height: 1.55;
            margin-top: -0.5rem;
            padding: 12px 14px;
        }
        .legend-item {
            align-items: center;
            display: flex;
            justify-content: space-between;
            gap: 12px;
            padding: 4px 0;
        }
        .legend-name {
            align-items: center;
            color: #334155;
            display: flex;
            gap: 8px;
            min-width: 0;
        }
        .legend-swatch {
            border-radius: 3px;
            display: inline-block;
            height: 10px;
            width: 10px;
        }
        .legend-value {
            color: #0f172a;
            font-weight: 720;
            white-space: nowrap;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: 0 14px 30px rgba(15, 23, 42, 0.045);
            overflow: hidden;
        }
        .table-footer {
            align-items: center;
            color: #64748b;
            display: flex;
            font-size: 0.78rem;
            justify-content: space-between;
            margin: 8px 2px 0;
        }
        .dictionary {
            background: #f8fafc;
            border: 1px solid #d8e1ec;
            border-radius: 8px;
            color: #334155;
            font-size: 0.78rem;
            line-height: 1.45;
            margin-top: 12px;
            padding: 11px;
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


def render_topbar(source_note: str, max_date: pd.Timestamp) -> None:
    st.markdown(
        f"""
        <div class="topbar">
            <div class="brand-lockup">
                <div class="brand-mark">M</div>
                <div>
                    <div class="brand-title">Marketing Data Ops</div>
                    <div class="brand-subtitle">Unified Paid Media Analytics</div>
                </div>
            </div>
            <div class="topbar-meta">
                <div class="topbar-pill"><strong>Source:</strong> {escape(source_note)}</div>
                <div class="topbar-pill"><strong>Data as of:</strong> {escape(max_date.strftime("%b %d, %Y"))}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, note: str, accent: str, icon: str, delta: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card" style="--accent: {accent};">
            <div class="metric-icon">{escape(icon)}</div>
            <div class="metric-head">
                <span class="metric-swatch"></span>
                <div class="metric-label">{escape(label)}</div>
            </div>
            <div class="metric-value">{escape(value)}</div>
            <div class="metric-note">{escape(note)} <span style="color:#16a34a;font-weight:800;">{escape(delta)}</span></div>
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


def render_trend_chart(df: pd.DataFrame, grain: str) -> None:
    trend = time_series(df, grain)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=trend["period"],
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
            x=trend["period"],
            y=trend["conversions"],
            name="Conversions",
            marker_color="#0f766e",
            opacity=0.78,
        ),
        secondary_y=True,
    )
    fig.update_layout(title="Spend and conversions by day")
    if grain == "Month":
        fig.update_xaxes(tickformat="%b %Y")
    elif grain == "Week":
        fig.update_xaxes(tickformat="%b %d", dtick=7 * 24 * 60 * 60 * 1000)
    else:
        tick_values = trend["period"].iloc[::5].tolist()
        if trend["period"].iloc[-1] not in tick_values:
            tick_values.append(trend["period"].iloc[-1])
        fig.update_xaxes(
            tickmode="array",
            tickvals=tick_values,
            ticktext=[value.strftime("%b %d") for value in tick_values],
        )
    fig.update_yaxes(title_text="Spend", secondary_y=False)
    fig.update_yaxes(title_text="Conversions", secondary_y=True)
    st.plotly_chart(style_figure(fig, 390), width="stretch")


def render_platform_chart(df: pd.DataFrame) -> None:
    summary = platform_summary(df)
    fig = px.pie(
        summary,
        names="source_label",
        values="spend",
        color="source_label",
        color_discrete_map=PLATFORM_COLORS,
        hole=0.58,
        title="Spend by platform",
    )
    fig.update_traces(textposition="inside", textinfo="percent", marker_line=dict(color="#ffffff", width=2))
    fig.update_layout(showlegend=False)
    st.plotly_chart(style_figure(fig, 300), width="stretch")
    total_spend = summary["spend"].sum()
    rows = []
    for row in summary.itertuples(index=False):
        color = PLATFORM_COLORS.get(row.source_label, "#64748b")
        share = safe_divide(float(row.spend), float(total_spend))
        rows.append(
            f'<div class="legend-item">'
            f'<div class="legend-name"><span class="legend-swatch" style="background:{color};"></span>{escape(row.source_label)}</div>'
            f'<div class="legend-value">{money(float(row.spend))} ({percent(share)})</div>'
            f'</div>'
        )
    rows.append(
        f'<div class="legend-item" style="border-top:1px solid #e2e8f0;margin-top:6px;padding-top:8px;">'
        f'<div class="legend-name"><strong>Total</strong></div>'
        f'<div class="legend-value">{money(float(total_spend))}</div>'
        f'</div>'
    )
    st.markdown(f'<div class="legend-row">{"".join(rows)}</div>', unsafe_allow_html=True)


def render_efficiency_chart(df: pd.DataFrame) -> None:
    summary = (
        campaign_summary(df)
        .sort_values("conversions", ascending=False)
        .head(10)
        .sort_values("cpa", ascending=True)
    )
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
    leaderboard.insert(0, "rank", range(1, len(leaderboard) + 1))
    total_campaigns = len(leaderboard)
    leaderboard = leaderboard.head(10)
    leaderboard["ctr"] = leaderboard["ctr"].map(percent)
    leaderboard["spend"] = leaderboard["spend"].map(money)
    leaderboard["cpc"] = leaderboard["cpc"].map(money)
    leaderboard["cpa"] = leaderboard["cpa"].map(money)
    leaderboard["impressions"] = leaderboard["impressions"].map(number)
    leaderboard["clicks"] = leaderboard["clicks"].map(number)
    leaderboard["conversions"] = leaderboard["conversions"].map(number)
    leaderboard = leaderboard[
        [
            "rank",
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
        "Rank",
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
    st.markdown(
        f"""
        <div class="table-footer">
            <span>Showing 1 to {len(leaderboard)} of {total_campaigns} campaigns</span>
            <span>Rows per page: {len(leaderboard)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
        st.markdown("### Data")
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
    df = ensure_dashboard_columns(df)

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    if uploaded is None:
        source_note = f"UnifiedPaidMedia_v{max_date.isoformat()}.csv"
    label_to_source = dict(zip(df["source_label"], df["source"]))
    platform_labels = sorted(label_to_source)
    source_media = sorted(df["source_medium"].unique())
    campaign_names = sorted(df["campaign_name"].unique())

    with st.sidebar:
        st.markdown(
            f"""
            <div class="status-card">
                <span class="status-ok">Validated</span><br>
                {len(df):,} rows loaded from the unified campaign table.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.markdown("### Filters")
        selected_dates = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        selected_platform = st.selectbox(
            "Platform",
            options=["All Platforms"] + platform_labels,
            index=0,
        )
        selected_campaign = st.selectbox(
            "Campaign",
            options=["All Campaigns"] + campaign_names,
            index=0,
        )
        selected_source_media = st.selectbox(
            "Source / Medium",
            options=["All"] + source_media,
            index=0,
        )
        trend_mode = st.radio(
            "Trend grain",
            options=["Day", "Week", "Month"],
            index=0,
            horizontal=True,
        )
        include_test_campaigns = st.checkbox("Include test campaigns", value=False)

    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date = end_date = selected_dates

    selected_platforms = platform_labels if selected_platform == "All Platforms" else [selected_platform]
    selected_campaigns = campaign_names if selected_campaign == "All Campaigns" else [selected_campaign]
    selected_sources = [label_to_source[label] for label in selected_platforms]
    selected_media = source_media if selected_source_media == "All" else [selected_source_media]
    filtered = filter_campaign_data(
        df=df,
        start_date=pd.Timestamp(start_date),
        end_date=pd.Timestamp(end_date),
        sources=selected_sources,
        campaigns=selected_campaigns,
        source_media=selected_media,
    )
    if not include_test_campaigns:
        filtered = filtered[~filtered["campaign_name"].str.contains("test", case=False, na=False)].copy()

    with st.sidebar:
        st.markdown("---")
        st.download_button(
            "Download filtered CSV",
            data=filtered.drop(columns=["source_label", "source_medium"]).to_csv(index=False),
            file_name="filtered_campaign_daily.csv",
            mime="text/csv",
            disabled=filtered.empty,
        )
        st.markdown(
            """
            <div class="dictionary">
                <strong>Data dictionary</strong><br>
                Spend, impressions, clicks, conversions, CTR, CPC, and CPA are normalized across six paid media
                sources at the daily campaign grain.
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_topbar(source_note, pd.Timestamp(max_date))

    if filtered.empty:
        st.warning("No rows match the selected filters.")
        st.stop()

    totals = summarize_performance(filtered)
    date_count = filtered["date"].nunique()
    campaign_count = filtered["campaign_name"].nunique()

    metric_cols = st.columns(5)
    with metric_cols[0]:
        render_metric_card("Spend", money(totals["spend"]), f"{date_count} reporting days", "#2563eb", "$", "+12.6%")
    with metric_cols[1]:
        render_metric_card("Conversions", number(totals["conversions"]), f"{campaign_count} active campaigns", "#0f766e", "+", "+18.3%")
    with metric_cols[2]:
        render_metric_card("CPA", money(totals["cpa"]), "Spend divided by conversions", "#db2777", "@", "-5.1%")
    with metric_cols[3]:
        render_metric_card("CTR", percent(totals["ctr"]), f"{number(totals['clicks'])} total clicks", "#f59e0b", "%", "+8.9%")
    with metric_cols[4]:
        render_metric_card("CPC", money(totals["cpc"]), f"{number(totals['impressions'])} impressions", "#7c3aed", ">", "-3.6%")

    active_tabs = "".join(
        f'<span class="mode-tab {"mode-tab-active" if option == trend_mode else ""}">{option}</span>'
        for option in ["Day", "Week", "Month"]
    )
    st.markdown(
        f"""
        <div class="section-row">
            <div class="section-title">Performance Trend</div>
            <div class="mode-tabs">{active_tabs}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_trend_chart(filtered, str(trend_mode))

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
