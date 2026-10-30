"""
app.py
==============================================================================
Portfolio Project 004: Oncology Price Transparency & Economic Analysis
Interactive Executive Analytics Dashboard (Streamlit + Plotly + DuckDB)

Run locally:
    streamlit run app.py
==============================================================================
"""

import streamlit as st
import pandas as pd
import duckdb
from src.visualization.theme import COLORS
from src.visualization.interactive_plots import (
    plot_drug_markups_interactive,
    plot_ownership_disparities_interactive,
    plot_payer_power_interactive,
    plot_cash_paradox_interactive,
    plot_patient_coinsurance_interactive
)

# -----------------------------------------------------------------------------
# 1. Page Configuration & Theme
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Oncology Price Transparency Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for executive polish
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1B4965;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #6C757D;
        margin-bottom: 1.5rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1B4965;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. Data Loading with DuckDB In-Memory Caching
# -----------------------------------------------------------------------------
@st.cache_data
def load_data() -> pd.DataFrame:
    """Loads harmonized gold oncology markups data from local DuckDB instance."""
    con = duckdb.connect("data/processed/oncoprice.duckdb", read_only=True)
    query = """
    SELECT 
        brand_name,
        generic_name,
        hcpcs_code,
        hospital_name,
        ownership_type,
        payer_name,
        plan_name,
        standardized_payer_name,
        standardized_market_segment,
        standardized_market_segment AS payer_market_segment,
        service_line_scope,
        reimbursement_methodology,
        carve_out_type,
        network_status,
        is_in_network,
        include_in_commercial_benchmark,
        include_in_general_commercial_benchmark,
        include_in_transplant_carveout_benchmark,
        include_in_ma_benchmark,
        contract_cluster_id,
        data_quality_status,
        commercial_negotiated_rate,
        hospital_cash_rate AS cash_rate,
        hospital_gross_charge AS gross_charge,
        asp_benchmark_rate,
        commercial_markup_ratio,
        patient_coinsurance_20pct
    FROM gold_oncology_markups
    """
    df = con.sql(query).df()
    con.close()
    return df

df_raw = load_data()


# -----------------------------------------------------------------------------
# 3. Sidebar Filtering Engine
# -----------------------------------------------------------------------------
st.sidebar.title("Filter Console")
st.sidebar.markdown("Slice 5,068 commercial oncology contracts across hospitals, payers, and statutory segments.")

# Hospital Multi-Select Filter
all_hospitals = sorted(df_raw["hospital_name"].unique().tolist())
selected_hospitals = st.sidebar.multiselect(
    "Hospital Systems",
    options=all_hospitals,
    default=[],
    placeholder="All Hospitals (Default)",
    help="Select one or more hospital systems to evaluate. Leave empty to evaluate all 3 health systems."
)

# Drug Multi-Select Filter
all_drugs = sorted(df_raw["brand_name"].unique().tolist())
selected_drugs = st.sidebar.multiselect(
    "Oncology Biologics",
    options=all_drugs,
    default=[],
    placeholder="All 14 Biologics (Default)",
    help="Select one or more oncology biologics to evaluate. Leave empty to evaluate all 14 drugs."
)

# Benchmark Scope & Segment Filtering Mode
scope_mode = st.sidebar.selectbox(
    "Benchmark Scope & Presets",
    [
        "General Commercial Benchmark (Figures 1–5 Baseline, n=3,121)",
        "Custom Segment Explorer (Multi-Select)",
        "Full Universe (All 5,068 Contracts)"
    ],
    index=0,
    help=(
        "• 'General Commercial Benchmark': Restricts to the 3,121 clean, in-network commercial contracts "
        "matching publication Figures 1–5.\n"
        "• 'Custom Segment Explorer': Unlocks full multi-select control across all 7 statutory market segments, "
        "allowing you to isolate individual segments (e.g. Medicare Advantage, Medicaid) or combine them freely.\n"
        "• 'Full Universe': Evaluates all 5,068 contracts across all statutory segments."
    )
)

all_segments = [
    "Commercial Employer",
    "Medicare Advantage",
    "ACA Individual Exchange",
    "Medicaid Managed Care",
    "Correctional Healthcare",
    "Veterans Affairs (VA CCN)",
    "Military / TRICARE"
]

if scope_mode == "Custom Segment Explorer (Multi-Select)":
    selected_segments = st.sidebar.multiselect(
        "Select Market Segments",
        options=all_segments,
        default=[],
        placeholder="All 7 Segments (or pick individual)",
        help=(
            "Pick and choose individual statutory market segments to evaluate together. "
            "Leave empty to evaluate all 7 segments."
        )
    )
else:
    selected_segments = []

st.sidebar.markdown("**Governance & Outlier Controls**")

# Non-Contracted / Out-of-Network Toggle
include_non_contracted = st.sidebar.checkbox(
    "Include Out-of-Network Rates (n=140)",
    value=False,
    help=(
        "Per the HEOR governance plan, out-of-network rates (e.g., Oscar Health at Baptist, "
        "BlueSelect Non-Par and PHS at HCA) are excluded by default to avoid biasing in-network "
        "commercial discounts. Check this box to inspect non-contracted rates."
    )
)

# Exclude Medicaid Phantom Rates Toggle
exclude_phantom_medicaid = st.sidebar.checkbox(
    "Exclude Medicaid Phantom Rates (n=550)",
    value=True,
    help=(
        "Excludes Baptist unadjudicated RCM percent-of-charge rates (~$2,800 / 50x ASP) that result "
        "from hospital IT extraction scripts ignoring the statutory lesser-of Medicaid fee ceiling."
    )
)

# Case-Rate Outlier Filter
exclude_ahp_outlier = st.sidebar.checkbox(
    "Exclude $15k Case-Rate Outlier (n=15)",
    value=True,
    help=(
        "HCA Florida Memorial Hospital reports a flat $15,000.00 episode/case rate across 15 "
        "generic chemotherapy contracts for AMERICAN HEALTH PLAN (producing a 3,614x–5,263x ASP distortion). "
        "Uncheck to view raw unfiltered distortion across all charts."
    )
)

# Apply Filters
filtered_df = df_raw.copy()

# Multi-select Hospital Filter
if selected_hospitals:
    filtered_df = filtered_df[filtered_df["hospital_name"].isin(selected_hospitals)]

# Multi-select Drug Filter
if selected_drugs:
    filtered_df = filtered_df[filtered_df["brand_name"].isin(selected_drugs)]

# Apply Scope / Cohort Logic
if scope_mode == "General Commercial Benchmark (Figures 1–5 Baseline, n=3,121)":
    filtered_df = filtered_df[filtered_df["include_in_general_commercial_benchmark"] == True]
elif scope_mode == "Custom Segment Explorer (Multi-Select)":
    if selected_segments:
        filtered_df = filtered_df[filtered_df["standardized_market_segment"].isin(selected_segments)]
    
    # Out-of-Network Governance Filter in custom mode
    if not include_non_contracted:
        filtered_df = filtered_df[filtered_df["network_status"] != "NON_CONTRACTED"]

    # Medicaid Phantom Rate Governance Filter in custom mode
    if exclude_phantom_medicaid:
        filtered_df = filtered_df[filtered_df["data_quality_status"] != "EXCLUDE_PHANTOM_CDM_RATE"]

    # Case-Rate Outlier Filter in custom mode
    if exclude_ahp_outlier:
        filtered_df = filtered_df[filtered_df["payer_name"] != "AMERICAN HEALTH PLAN"]

elif scope_mode == "Full Universe (All 5,068 Contracts)":
    # Out-of-Network Governance Filter
    if not include_non_contracted:
        filtered_df = filtered_df[filtered_df["network_status"] != "NON_CONTRACTED"]

    # Medicaid Phantom Rate Governance Filter
    if exclude_phantom_medicaid:
        filtered_df = filtered_df[filtered_df["data_quality_status"] != "EXCLUDE_PHANTOM_CDM_RATE"]

    # Case-Rate Outlier Filter
    if exclude_ahp_outlier:
        filtered_df = filtered_df[filtered_df["payer_name"] != "AMERICAN HEALTH PLAN"]

total_contracts = len(filtered_df)

st.sidebar.divider()
st.sidebar.metric(
    "Total Contracts Evaluated",
    f"{total_contracts:,}",
    help="Number of negotiated payer-hospital drug contracts matching your current filters."
)
st.sidebar.divider()
st.sidebar.caption(
    "**Methodological Baseline:** Federal CMS Part B Average Sales Price (ASP + 6%). "
    "Data extracted from hospital MRFs under CMS Transparency Mandates."
)


# -----------------------------------------------------------------------------
# 4. Header & Executive KPI Cards
# -----------------------------------------------------------------------------
st.markdown('<div class="main-title">Oncology Price Transparency & Economic Analysis</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">'
    'Benchmarking hospital commercial markups, payer leverage, and out-of-pocket patient exposure '
    'against the Medicare Part B statutory baseline.</div>',
    unsafe_allow_html=True
)

kpi1, kpi2, kpi3 = st.columns(3)

median_markup = filtered_df["commercial_markup_ratio"].median() if total_contracts > 0 else 0
valid_cash_df = filtered_df[filtered_df["cash_rate"].notnull() & (filtered_df["cash_rate"] > 0)]
cash_cheaper_pct = (
    (valid_cash_df["cash_rate"] < valid_cash_df["commercial_negotiated_rate"]).mean() * 100
    if len(valid_cash_df) > 0 else 0
)
max_coinsurance = filtered_df["patient_coinsurance_20pct"].max() if total_contracts > 0 else 0

with kpi1:
    st.metric(
        "Median Markup Over ASP",
        f"{median_markup:.2f}x",
        help="Typical commercial insurance rate expressed as a multiple of the Medicare Part B Average Sales Price (ASP + 6%) federal benchmark."
    )
with kpi2:
    st.metric(
        "Cash Price Advantage",
        f"{cash_cheaper_pct:.1f}%",
        help="Percentage of contracts with a published cash rate (> $0) where paying uninsured self-pay cash is cheaper than the negotiated commercial insurance rate."
    )
with kpi3:
    st.metric(
        "Max Patient Exposure (20%)",
        f"${max_coinsurance:,.0f}",
        help="Highest single 20% patient coinsurance rate for a 1-unit dose"
    )

st.divider()


# -----------------------------------------------------------------------------
# 5. Option A: Tabbed Analytical Layout
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Drug-Level Markups",
    "Institutional Ownership",
    "Payer Negotiation Power",
    "The Cash Price Paradox",
    "Patient Coinsurance Toxicity"
])

# --- TAB 1: DRUG-LEVEL MARKUPS ---
with tab1:
    st.subheader("Commercial Markup by Cancer Biologic")
    st.caption("How commercial insurers reimburse hospitals relative to the statutory Medicare Part B ASP limit.")
    fig1 = plot_drug_markups_interactive(filtered_df)
    st.plotly_chart(fig1, use_container_width=True)

    with st.expander("View Tabular Data (Drug Markups)"):
        st.dataframe(
            filtered_df.groupby(["brand_name", "generic_name"]).agg(
                contract_count=("commercial_markup_ratio", "count"),
                median_markup=("commercial_markup_ratio", "median"),
                min_markup=("commercial_markup_ratio", "min"),
                max_markup=("commercial_markup_ratio", "max")
            ).reset_index(),
            use_container_width=True
        )

# --- TAB 2: OWNERSHIP DISPARITIES ---
with tab2:
    st.subheader("Hospital Pricing by Ownership Model")
    st.caption("Empirical test of whether Non-Profit community hospitals price closer to cost than For-Profit chains.")
    fig2 = plot_ownership_disparities_interactive(filtered_df)
    st.plotly_chart(fig2, use_container_width=True)

# --- TAB 3: PAYER NEGOTIATION POWER ---
with tab3:
    st.subheader("Payer Leverage Across Market Segments")
    st.caption("Comparing negotiated reimbursement multiples between Medicare Advantage, ACA Exchanges, and Commercial Employers.")
    fig3 = plot_payer_power_interactive(filtered_df)
    st.plotly_chart(fig3, use_container_width=True)

# --- TAB 4: CASH PRICE PARADOX ---
with tab4:
    st.subheader("The Cash Price Paradox")
    st.caption("Quantifying the prevalence where uninsured self-pay cash prices beat negotiated commercial rates.")

    # Calculate coverage stats for dynamic user transparency message
    missing_cash_contracts = total_contracts - len(valid_cash_df)
    missing_note = (
        f" (**{missing_cash_contracts:,}** of {total_contracts:,} total contracts lacked a published hospital cash rate and were excluded.)"
        if missing_cash_contracts > 0 else ""
    )

    total_cash_drugs = valid_cash_df["brand_name"].nunique()
    cheaper_mask = valid_cash_df["cash_rate"] < valid_cash_df["commercial_negotiated_rate"]
    qualifying_drugs = valid_cash_df[cheaper_mask]["brand_name"].nunique()
    omitted_drugs = total_cash_drugs - qualifying_drugs

    shown_contracts = len(valid_cash_df[valid_cash_df["brand_name"].isin(valid_cash_df[cheaper_mask]["brand_name"])])
    omitted_contracts = len(valid_cash_df) - shown_contracts

    qual_label = "drug" if qualifying_drugs == 1 else "drugs"
    total_label = "drug" if total_cash_drugs == 1 else "drugs"
    omit_label = "drug" if omitted_drugs == 1 else "drugs"

    if len(valid_cash_df) == 0:
        st.info(
            f"**0 of {total_contracts:,} total contracts** in this filter selection have a published self-pay cash rate."
        )
    elif qualifying_drugs == 0:
        st.info(
            f"**0 of {total_cash_drugs} {total_label}** (**{len(valid_cash_df):,} published cash contracts**) "
            f"in this selection have a self-pay cash price lower than the commercial insurance rate.{missing_note}"
        )
    elif omitted_drugs > 0:
        st.info(
            f"Showing **{qualifying_drugs} of {total_cash_drugs} {total_label}** with published cash rates "
            f"(**{shown_contracts:,} contracts** represented below). The remaining **{omitted_drugs} {omit_label} "
            f"({omitted_contracts:,} published cash contracts)** had **0 contracts** where cash beat commercial insurance "
            f"and are omitted from the chart.{missing_note}"
        )
    else:
        st.info(
            f"Showing **{'all ' if qualifying_drugs > 1 else ''}{qualifying_drugs} {qual_label}** with published cash rates "
            f"(**{shown_contracts:,} published cash contracts**)—every drug in this selection has at least one contract "
            f"where self-pay cash beats commercial insurance.{missing_note}"
        )

    fig4 = plot_cash_paradox_interactive(filtered_df)
    st.plotly_chart(fig4, use_container_width=True)

# --- TAB 5: PATIENT COINSURANCE TOXICITY ---
with tab5:
    has_keytruda = (filtered_df["brand_name"] == "Keytruda").any() if total_contracts > 0 else False
    target_drug_name = "Keytruda" if has_keytruda else ("Selected Biologics" if total_contracts > 0 else "No Data")
    st.subheader("Patient Financial Toxicity & Out-of-Pocket Exposure")
    st.caption(f"Standard 20% commercial coinsurance exposure for {target_drug_name} across hospital systems.")

    if has_keytruda:
        dosage_selection = st.radio(
            "Clinical Dosing Scenario:",
            options=["Standard 200 mg Clinical Infusion", "Statutory 1 mg Billing Unit"],
            horizontal=True,
            help="Toggle between the statutory HCPCS J9271 1 mg unit price and a complete 200 mg IV infusion encounter dose administered every 3 weeks."
        )
        dosage_mode = "infusion_dose" if "200 mg" in dosage_selection else "billing_unit"
        
        if dosage_mode == "infusion_dose":
            st.info(
                "💡 **Clinical Context & The ACA Out-of-Pocket Maximum**: "
                "Under FDA oncology guidelines, Keytruda is administered as a **200 mg intravenous infusion every 3 weeks** "
                r"(\$2,172 statutory ASP baseline). Under standard 20% coinsurance, a patient's liability on a single cycle can reach "
                r"**\$3,181 to \$9,582**. Under the statutory **Affordable Care Act (ACA) Out-of-Pocket Maximum (\$9,200 individual)**, "
                "patients satisfy their annual deductible in **Cycles 1–2**, after which the self-insured employer plan sponsor absorbs 100% of the remaining 4.41x markup tail."
            )
    else:
        dosage_mode = "billing_unit"

    fig5 = plot_patient_coinsurance_interactive(filtered_df, dosage_mode=dosage_mode)
    st.plotly_chart(fig5, use_container_width=True)

    with st.expander("Inspect Patient Coinsurance Contract Details"):
        coinsurance_df = (
            filtered_df[filtered_df["brand_name"] == "Keytruda"].copy()
            if has_keytruda
            else filtered_df.copy()
        )
        
        if has_keytruda and dosage_mode == "infusion_dose":
            coinsurance_df["infusion_coinsurance_200mg"] = coinsurance_df["patient_coinsurance_20pct"] * 200.0
            cols_to_show = ["hospital_name", "ownership_type", "payer_name", "commercial_negotiated_rate", "patient_coinsurance_20pct", "infusion_coinsurance_200mg"]
            sort_col = "infusion_coinsurance_200mg"
        else:
            cols_to_show = ["hospital_name", "ownership_type", "payer_name", "commercial_negotiated_rate", "patient_coinsurance_20pct"]
            sort_col = "patient_coinsurance_20pct"

        if not has_keytruda and "brand_name" in coinsurance_df.columns:
            cols_to_show = ["brand_name"] + cols_to_show
            
        st.dataframe(
            coinsurance_df[cols_to_show].sort_values(sort_col, ascending=False),
            use_container_width=True
        )
