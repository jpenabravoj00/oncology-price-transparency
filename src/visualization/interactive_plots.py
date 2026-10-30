"""
src/visualization/interactive_plots.py
==============================================================================
Portfolio Project 004: Oncology Price Transparency & Economic Analysis
Interactive Plotly Visualizations for Streamlit Dashboard

Mirrors Figures 1-5 with interactive tooltips, responsive sizing, and
consistent WCAG AA color tokens.
==============================================================================
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.visualization.theme import COLORS


def plot_drug_markups_interactive(df: pd.DataFrame) -> go.Figure:
    """Tab 1: Interactive horizontal bar chart of drug-level markups over ASP."""
    if df.empty or "commercial_markup_ratio" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="No contract data available for current filter selection.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=COLORS["Text_Muted"])
        )
        fig.update_layout(template="plotly_white", height=340)
        return fig

    summary = df.groupby(["brand_name", "generic_name"]).agg(
        median_markup=("commercial_markup_ratio", "median"),
        avg_markup=("commercial_markup_ratio", "mean"),
        contract_count=("commercial_markup_ratio", "count")
    ).reset_index().sort_values("median_markup", ascending=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=summary["brand_name"],
        x=summary["median_markup"],
        orientation="h",
        marker=dict(
            color=COLORS["Non-Profit Community"],
            line=dict(color=COLORS["Text_Primary"], width=1)
        ),
        customdata=summary[["generic_name", "contract_count", "avg_markup"]],
        hovertemplate=(
            "<b>%{y}</b> (%{customdata[0]})<br>"
            "Median Markup: <b>%{x:.2f}x ASP</b><br>"
            "Mean Markup: %{customdata[2]:.2f}x ASP<br>"
            "Negotiated Contracts: %{customdata[1]:,}<extra></extra>"
        )
    ))

    # Benchmark Line
    fig.add_vline(
        x=1.0,
        line_dash="dash",
        line_color=COLORS["Benchmark_ASP"],
        line_width=2,
        annotation_text="Medicare Part B Baseline (1.0x ASP)",
        annotation_position="top right"
    )

    # Dynamic height based on number of drugs displayed
    dynamic_height = max(340, len(summary) * 34 + 110)

    fig.update_layout(
        title="<b>Commercial Markup Over Medicare Part B ASP Baseline</b>",
        xaxis_title="Median Commercial Markup Ratio (Multiples of ASP)",
        yaxis_title="Biologic Brand Name",
        template="plotly_white",
        height=dynamic_height,
        xaxis=dict(autorange=True, rangemode="tozero"),
        margin=dict(l=110, r=40, t=60, b=40)
    )
    return fig


def plot_ownership_disparities_interactive(df: pd.DataFrame) -> go.Figure:
    """Tab 2: Interactive box & jitter plot by hospital ownership type with auto-adjusting Y-axis."""
    if df.empty or "ownership_type" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="No contract data available for current filter selection.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=COLORS["Text_Muted"])
        )
        fig.update_layout(template="plotly_white", height=340)
        return fig

    fig = px.box(
        df,
        x="ownership_type",
        y="commercial_markup_ratio",
        color="ownership_type",
        color_discrete_map={
            "For-Profit": COLORS["For-Profit"],
            "Non-Profit Community": COLORS["Non-Profit Community"],
            "Non-Profit Comprehensive Cancer Center": COLORS["Comprehensive Cancer Center"]
        },
        points="outliers",
        hover_data=["brand_name", "hospital_name", "payer_name", "commercial_negotiated_rate"]
    )

    fig.add_hline(
        y=1.0,
        line_dash="dash",
        line_color=COLORS["Benchmark_ASP"],
        line_width=2,
        annotation_text="Medicare Baseline (1.0x ASP)",
        annotation_position="bottom right"
    )

    # Auto-adjusting Y-axis with tozero mode: never clips high-markup outliers
    fig.update_layout(
        title="<b>Hospital Markup Distribution by Institutional Ownership</b>",
        xaxis_title="Hospital Ownership Model",
        yaxis_title="Commercial Markup Ratio (Multiples of ASP)",
        yaxis=dict(autorange=True, rangemode="tozero"),
        xaxis=dict(autorange=True),
        template="plotly_white",
        height=540,
        showlegend=False,
        margin=dict(l=60, r=40, t=60, b=40)
    )
    return fig


def plot_payer_power_interactive(df: pd.DataFrame) -> go.Figure:
    """Tab 3: Payer leverage comparison across market segments with auto-adjusting axes and wide margins."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No contract data available for current filter selection.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=COLORS["Text_Muted"])
        )
        fig.update_layout(template="plotly_white", height=340)
        return fig

    plot_df = df.copy()
    payer_col = "standardized_payer_name" if "standardized_payer_name" in plot_df.columns else "payer_name"
    segment_col = "standardized_market_segment" if "standardized_market_segment" in plot_df.columns else (
        "payer_market_segment" if "payer_market_segment" in plot_df.columns else "payer_name"
    )

    # Canonical display mapping for major Florida health plans
    payer_display_map = {
        "FLORIDA BLUE (GUIDEWELL)": "Florida Blue",
        "AETNA": "Aetna",
        "CIGNA": "Cigna",
        "UNITEDHEALTHCARE": "UnitedHealthcare",
        "HUMANA": "Humana",
        "AVMED": "AvMed",
        "OSCAR HEALTH": "Oscar Health",
        "MOLINA HEALTHCARE": "Molina",
        "SIMPLY HEALTHCARE": "Simply Healthcare",
        "SUNSHINE HEALTH (CENTENE)": "Sunshine Health",
        "AMBETTER (CENTENE)": "Ambetter",
        "DEVOTED HEALTH": "Devoted Health",
        "CAREPLUS HEALTH PLANS": "CarePlus",
        "CAPITAL HEALTH PLAN": "Capital Health Plan",
        "AMERICAN HEALTH PLAN": "American Health Plan"
    }
    plot_df["display_payer"] = plot_df[payer_col].map(
        lambda x: payer_display_map.get(str(x).upper(), str(x).title())
    )

    summary = plot_df.groupby(["display_payer", segment_col]).agg(
        median_markup=("commercial_markup_ratio", "median"),
        p25=("commercial_markup_ratio", lambda x: x.quantile(0.25)),
        p75=("commercial_markup_ratio", lambda x: x.quantile(0.75)),
        contracts=("commercial_markup_ratio", "count")
    ).reset_index().sort_values("median_markup", ascending=True)

    # Filter out low-sample noise if broadly unsegmented
    if len(summary) > 20:
        summary = summary[summary["contracts"] >= 10].sort_values("median_markup", ascending=True)

    # Clean row labels: only append segment name if multiple segments are present
    n_distinct_segments = summary[segment_col].nunique()
    if n_distinct_segments > 1:
        summary["row_label"] = summary["display_payer"] + " (" + summary[segment_col] + ")"
    else:
        summary["row_label"] = summary["display_payer"]

    segment_colors = {
        "Medicare Advantage": COLORS.get("Medicare Advantage", "#2A9D8F"),
        "ACA Individual Exchange": COLORS.get("ACA Individual Exchange", "#E76F51"),
        "Commercial Employer": COLORS.get("Commercial Employer", "#1B4965"),
        "Medicaid Managed Care": COLORS.get("Medicaid Managed Care", "#8338EC"),
        "Military / TRICARE": COLORS.get("Military / TRICARE", "#457B9D"),
        "Veterans Affairs (VA CCN)": COLORS.get("Veterans Affairs (VA CCN)", "#588157"),
        "Correctional Healthcare": COLORS.get("Correctional Healthcare", "#6C757D"),
        "Transplant COE Carve-Outs": COLORS.get("Transplant COE Carve-Outs", "#E07A5F")
    }

    fig = go.Figure()

    for segment in summary[segment_col].unique():
        color = segment_colors.get(segment, COLORS.get("Text_Primary", "#212529"))
        seg_data = summary[summary[segment_col] == segment]
        if seg_data.empty:
            continue
            
        err_plus = seg_data["p75"] - seg_data["median_markup"]
        err_minus = seg_data["median_markup"] - seg_data["p25"]

        fig.add_trace(go.Scatter(
            x=seg_data["median_markup"],
            y=seg_data["row_label"],
            mode="markers",
            name=segment,
            marker=dict(size=12, color=color, line=dict(color="#212529", width=1.2)),
            error_x=dict(
                type="data",
                symmetric=False,
                array=err_plus,
                arrayminus=err_minus,
                color=color,
                thickness=3.5,
                width=0  # Sleek horizontal range bar without vertical end-caps
            ),
            customdata=seg_data[["contracts", "p25", "p75"]],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Median Markup: <b>%{x:.2f}x ASP</b><br>"
                "IQR Spread: [%{customdata[1]:.2f}x – %{customdata[2]:.2f}x]<br>"
                "Contracts: %{customdata[0]:,}<extra></extra>"
            )
        ))

    fig.add_vline(
        x=1.0, line_dash="dash", line_color=COLORS["Benchmark_ASP"],
        line_width=2,
        annotation_text="Medicare ASP Baseline (1.0x)", annotation_position="top right"
    )

    # Dynamic height: scales smoothly from 340px up to 750px depending on row count
    dynamic_height = max(340, len(summary) * 40 + 130)

    # Left margin sized to comfortably avoid label truncation
    fig.update_layout(
        title="<b>Commercial Payer Leverage & Contracting Spread Across Segments</b>",
        xaxis_title="Median Commercial Markup Ratio (Multiples of ASP)",
        yaxis_title="",
        template="plotly_white",
        height=dynamic_height,
        xaxis=dict(autorange=True, rangemode="tozero"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=220, r=40, t=80, b=40)
    )
    return fig


def plot_cash_paradox_interactive(df: pd.DataFrame) -> go.Figure:
    """Tab 4: Self-pay cash price advantage versus commercial rates with auto-adjusting axes."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No contract data available for current filter selection.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=COLORS["Text_Muted"])
        )
        fig.update_layout(template="plotly_white", height=340)
        return fig

    # Robust column detection for cash_rate and commercial_negotiated_rate
    cash_col = "cash_rate" if "cash_rate" in df.columns else "hospital_cash_rate"
    rate_col = "commercial_negotiated_rate" if "commercial_negotiated_rate" in df.columns else "negotiated_rate"

    if cash_col not in df.columns or rate_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Cash rate or commercial rate columns not found in dataset.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=COLORS["Text_Muted"])
        )
        fig.update_layout(template="plotly_white", height=340)
        return fig

    # Filter contracts with valid published cash price (> $0)
    cash_df = df[df[cash_col].notnull() & (df[cash_col] > 0)].copy()
    cash_df["cash_cheaper"] = cash_df[cash_col] < cash_df[rate_col]
    cash_df["cash_savings"] = cash_df[rate_col] - cash_df[cash_col]

    # Step 1: Count total valid cash contracts and cheaper-in-cash contracts per drug
    all_drugs_summary = cash_df.groupby("brand_name").agg(
        total_contracts=(rate_col, "count"),
        cheaper_contracts=("cash_cheaper", "sum")
    ).reset_index()

    # Step 2: Calculate median dollar savings ONLY across contracts where cash is cheaper (> $0)
    positive_savings = (
        cash_df[cash_df["cash_savings"] > 0]
        .groupby("brand_name")["cash_savings"]
        .median()
        .reset_index()
        .rename(columns={"cash_savings": "median_savings"})
    )

    # Step 3: Inner merge keeps ONLY drugs with at least 1 cheaper-in-cash contract
    summary = pd.merge(all_drugs_summary, positive_savings, on="brand_name")

    fig = go.Figure()

    if summary.empty:
        fig.add_annotation(
            text="No contracts in this filter selection have a cash price lower than commercial insurance.",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=15, color=COLORS["Text_Muted"])
        )
        fig.update_layout(
            title="<b>The Cash Price Paradox: Median Savings When Paying Self-Pay Cash</b>",
            template="plotly_white",
            height=340,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=40, r=40, t=60, b=40)
        )
        return fig

    summary["pct_cheaper"] = (summary["cheaper_contracts"] / summary["total_contracts"]) * 100
    summary = summary.sort_values("median_savings", ascending=True)

    fig.add_trace(go.Bar(
        y=summary["brand_name"],
        x=summary["median_savings"],
        orientation="h",
        marker=dict(color=COLORS["Commercial Employer"]),
        customdata=summary[["pct_cheaper", "total_contracts", "cheaper_contracts"]],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Median Cash Savings: <b>$%{x:,.2f} / unit</b><br>"
            "Contracts Cheaper in Cash: %{customdata[0]:.1f}% (%{customdata[2]:,} of %{customdata[1]:,})<extra></extra>"
        )
    ))

    dynamic_height = max(320, len(summary) * 36 + 110)

    fig.update_layout(
        title="<b>The Cash Price Paradox: Median Savings When Paying Self-Pay Cash</b>",
        xaxis_title="Median Cash Advantage ($ Saved / Billing Unit)",
        yaxis_title="Biologic Brand Name",
        template="plotly_white",
        height=dynamic_height,
        xaxis=dict(autorange=True, rangemode="tozero"),
        margin=dict(l=110, r=40, t=60, b=40)
    )
    return fig


def plot_patient_coinsurance_interactive(df: pd.DataFrame, dosage_mode: str = "billing_unit") -> go.Figure:
    """Tab 5: Patient 20% coinsurance exposure across institutions (Keytruda focus) with dosage scenario toggle."""
    if df.empty or "patient_coinsurance_20pct" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="No contract data available for current filter selection.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=COLORS["Text_Muted"])
        )
        fig.update_layout(template="plotly_white", height=340)
        return fig

    keytruda = df[df["brand_name"] == "Keytruda"].copy()
    has_keytruda = not keytruda.empty
    if not has_keytruda:
        keytruda = df.copy()

    # Determine dosage multiplier: 200x for clinical infusion encounter dose (Keytruda 200 mg)
    is_infusion = (dosage_mode == "infusion_dose" and has_keytruda)
    multiplier = 200.0 if is_infusion else 1.0

    summary = keytruda.groupby(["hospital_name", "ownership_type"]).agg(
        min_coinsurance=("patient_coinsurance_20pct", "min"),
        median_coinsurance=("patient_coinsurance_20pct", "median"),
        max_coinsurance=("patient_coinsurance_20pct", "max"),
        contracts=("patient_coinsurance_20pct", "count")
    ).reset_index().sort_values("median_coinsurance", ascending=True)

    summary["min_coinsurance"] = summary["min_coinsurance"] * multiplier
    summary["median_coinsurance"] = summary["median_coinsurance"] * multiplier
    summary["max_coinsurance"] = summary["max_coinsurance"] * multiplier

    fig = go.Figure()

    color_map = {
        "For-Profit": COLORS["For-Profit"],
        "Non-Profit Community": COLORS["Non-Profit Community"],
        "Non-Profit Comprehensive Cancer Center": COLORS["Comprehensive Cancer Center"]
    }

    unit_label = "200 mg Infusion" if is_infusion else "1 mg Billing Unit"

    for _, row in summary.iterrows():
        c = color_map.get(row["ownership_type"], COLORS["Text_Primary"])
        
        # Range bar (Whisker)
        fig.add_trace(go.Scatter(
            x=[row["min_coinsurance"], row["max_coinsurance"]],
            y=[row["hospital_name"], row["hospital_name"]],
            mode="lines",
            line=dict(color=c, width=8),
            showlegend=False,
            hoverinfo="skip"
        ))

        # Median marker
        fig.add_trace(go.Scatter(
            x=[row["median_coinsurance"]],
            y=[row["hospital_name"]],
            mode="markers",
            marker=dict(size=14, color=c, line=dict(color="#212529", width=1.5)),
            name=row["ownership_type"],
            customdata=[[row["min_coinsurance"], row["max_coinsurance"], row["contracts"]]],
            hovertemplate=(
                f"<b>%{{y}}</b><br>"
                f"Median 20% Coinsurance: <b>$%{{x:,.2f}} / {unit_label}</b><br>"
                f"Range: [$%{{customdata[0]:,.2f}} - $%{{customdata[1]:,.2f}}]<br>"
                f"Plans: %{{customdata[2]:,}}<extra></extra>"
            )
        ))

    # ASP Statutory Baseline line
    baseline_val = 10.86 * multiplier
    baseline_text = f"Medicare Baseline (${baseline_val:,.2f})"
    fig.add_vline(
        x=baseline_val, line_dash="dash", line_color=COLORS["Benchmark_ASP"],
        annotation_text=baseline_text, annotation_position="top right"
    )

    dynamic_height = max(320, len(summary) * 75 + 120)

    title_suffix = " (200 mg Infusion Dose)" if is_infusion else ""
    fig.update_layout(
        title=f"<b>Patient 20% Coinsurance Toxicity: Out-of-Pocket Exposure for Keytruda{title_suffix}</b>",
        xaxis_title=f"Patient 20% Out-of-Pocket Coinsurance ($ / {unit_label})",
        yaxis_title="Hospital System",
        template="plotly_white",
        height=dynamic_height,
        xaxis=dict(autorange=True, rangemode="tozero"),
        showlegend=False,
        margin=dict(l=220, r=50, t=60, b=40)
    )
    return fig
