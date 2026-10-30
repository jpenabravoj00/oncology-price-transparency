"""
src/harmonize_moffitt.py
==============================================================================
Portfolio Project 004: Oncology Price Transparency & Economic Analysis
Moffitt Cancer Center Silver-Layer Data Harmonization (Python ETL)

Purpose:
    Dynamically transforms Moffitt Cancer Center's wide CMS v3.0.0 MRF table
    (bronze_moffitt_mrf) into a clean, tall relational staging table
    (silver_moffitt_clean) inside DuckDB:
      1. Extracts true hospital gross sticker and 50% cash discount rates
         from outpatient facility pharmacy rows (Pattern A: code|2).
      2. Dynamically discovers and melts fixed fee-schedule contracts
         (Pattern B: code|1) and percent-of-charges contracts (Pattern A: code|2),
         excluding physician group (MMG) doctor fees.
      3. Harmonizes schema with Baptist Health and HCA Florida Memorial.

Usage:
    ./.venv/bin/python src/harmonize_moffitt.py
==============================================================================
"""

import duckdb
import pandas as pd


def harmonize_moffitt(db_path: str = "data/processed/oncoprice.duckdb"):
    print(f"Connecting to DuckDB instance: {db_path}...")
    con = duckdb.connect(db_path)

    # 1. Load raw Moffitt Bronze table
    df_raw = con.sql("SELECT * FROM bronze_moffitt_mrf").df()
    print(f"Loaded bronze_moffitt_mrf ({len(df_raw)} rows, {len(df_raw.columns)} columns).")

    # -------------------------------------------------------------------------
    # Step 1: Hospital Price Reference Map (Pattern A: Pharmacy Inventory)
    # -------------------------------------------------------------------------
    # Pattern A holds the true chargemaster gross charge and 50% cash discount
    pat_a = df_raw[
        (df_raw["code|2"].astype(str).str.startswith("J")) &
        (df_raw["setting"] == "outpatient") &
        (df_raw["billing_class"] == "facility")
    ].copy()

    prices = pat_a.groupby("code|2").agg(
        gross_charge=("standard_charge|gross", "mean"),
        cash_discount_rate=("standard_charge|discounted_cash", "mean")
    ).reset_index().rename(columns={"code|2": "hcpcs_code"}).round(2)

    # -------------------------------------------------------------------------
    # Step 2: Dynamic Column Discovery
    # -------------------------------------------------------------------------
    pat_b = df_raw[
        (df_raw["code|1"].astype(str).str.startswith("J")) &
        (df_raw["setting"] == "outpatient") &
        (df_raw["billing_class"] == "facility")
    ].copy()

    # Identify all outpatient facility payer columns (excluding doctor MMG columns)
    payer_cols = [
        c for c in df_raw.columns 
        if c.endswith("|negotiated_dollar") and "(MMG)" not in c
    ]

    # Columns active in Pattern B (Fee Schedule) vs Pattern A only (Percent of charges)
    b_cols = [c for c in payer_cols if pat_b[c].notnull().sum() > 0]
    a_cols = [c for c in payer_cols if c not in b_cols and pat_a[c].notnull().sum() > 0]

    print(f"Discovered {len(b_cols)} Fee Schedule plans and {len(a_cols)} Percent-of-Charge facility plans.")

    # -------------------------------------------------------------------------
    # Step 3: Reshape Wide Columns to Tall Format (pd.melt)
    # -------------------------------------------------------------------------
    # Collapse Pattern B's 4-row staircase per drug
    b_collapsed = pat_b.groupby("code|1")[b_cols].max().reset_index().rename(columns={"code|1": "hcpcs_code"})
    b_tall = b_collapsed.melt(
        id_vars=["hcpcs_code"],
        value_vars=b_cols,
        var_name="raw_col",
        value_name="negotiated_rate"
    ).dropna(subset=["negotiated_rate"])

    # Collapse Pattern A's clinic department duplicates per drug
    a_collapsed = pat_a.groupby("code|2")[a_cols].max().reset_index().rename(columns={"code|2": "hcpcs_code"})
    a_tall = a_collapsed.melt(
        id_vars=["hcpcs_code"],
        value_vars=a_cols,
        var_name="raw_col",
        value_name="negotiated_rate"
    ).dropna(subset=["negotiated_rate"])

    # Combine both contract types
    combined = pd.concat([b_tall, a_tall], ignore_index=True)
    combined = combined[combined["negotiated_rate"] > 0].copy()

    # -------------------------------------------------------------------------
    # Step 4: Parse Payer/Plan Names & Harmonize Metadata
    # -------------------------------------------------------------------------
    combined["payer_name"] = combined["raw_col"].apply(lambda x: x.split("|")[1].strip().upper())
    combined["plan_name"] = combined["raw_col"].apply(lambda x: x.split("|")[2].strip())

    # Attach hospital gross and cash prices
    final_df = pd.merge(combined, prices, on="hcpcs_code", how="inner")
    final_df["hospital_name"] = "Moffitt Cancer Center"
    final_df["ownership_type"] = "Non-Profit Comprehensive Cancer Center"

    # Map drug description from bronze
    desc_map = (
        df_raw[df_raw["code|1"].astype(str).str.startswith("J")]
        .groupby("code|1")["description"]
        .first()
        .to_dict()
    )
    final_df["drug_description"] = final_df["hcpcs_code"].map(desc_map)

    # Reorder to match exact Silver table schema
    final_moffitt_df = final_df[[
        "hospital_name", "ownership_type", "hcpcs_code", "drug_description",
        "payer_name", "plan_name", "gross_charge", "cash_discount_rate", "negotiated_rate"
    ]].sort_values(["hcpcs_code", "payer_name", "plan_name"]).reset_index(drop=True)

    # -------------------------------------------------------------------------
    # Step 5: Save to DuckDB
    # -------------------------------------------------------------------------
    con.register("df_temp", final_moffitt_df)
    con.execute("CREATE OR REPLACE TABLE silver_moffitt_clean AS SELECT * FROM df_temp")
    con.close()

    print("\nSuccessfully built 'silver_moffitt_clean' in DuckDB!")
    print(f"  Total Contracts Extracted : {len(final_moffitt_df):,}")
    print(f"  Distinct Oncology Drugs   : {final_moffitt_df['hcpcs_code'].nunique()}")
    print(f"  Distinct Commercial Payers: {final_moffitt_df['payer_name'].nunique()}")
    print(f"  Distinct Insurance Plans  : {final_moffitt_df['plan_name'].nunique()}")
    print("\nSample Preview (First 5 Rows):")
    print(final_moffitt_df.head(5).to_string(index=False))


if __name__ == "__main__":
    harmonize_moffitt()
