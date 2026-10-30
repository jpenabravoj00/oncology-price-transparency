# Data Dictionary & Schema Governance Guide
## Portfolio Project 004: Oncology Price Transparency & Economic Analysis

**Author:** Analytics Architecture & Engineering Team  
**Database Engine:** In-Process Columnar DuckDB (`data/processed/oncoprice.duckdb`)  
**Status:** Production Validated  
**Version:** 1.0  

---

## 1. Overview & Data Mart Architecture

This project employs a three-tier **Medallion Architecture (Bronze $\rightarrow$ Silver $\rightarrow$ Gold)** to transform raw, heterogeneous hospital machine-readable files (MRFs) into an enterprise-grade analytical mart benchmarked against federal statutory payment limits.

```
+--------------------------------------------------------------------------------------------------+
|                                      BRONZE RAW LAYER                                            |
|  - bronze_cms_asp: Official CMS Medicare Part B Average Sales Price (.xls/.csv)                  |
|  - bronze_baptist_mrf: Raw tall machine-readable file (3,741 oncology contracts)                |
|  - bronze_moffitt_mrf: Raw wide 559-column matrix (Unpivoted via src/harmonize_moffitt.py)       |
|  - bronze_hca_mrf: Raw tall machine-readable file (857 oncology contracts)                       |
+--------------------------------------------------------------------------------------------------+
                                                 │
                                                 ▼
+--------------------------------------------------------------------------------------------------+
|                                     SILVER HARMONIZED LAYER                                      |
|  - silver_cms_asp: Cleaned HCPCS J-codes, standard dosage units, and statutory payment limits    |
|  - silver_hospital_rates: Unified tall schema (5,068 rows across 3 Florida hospital systems)     |
+--------------------------------------------------------------------------------------------------+
                                                 │
                                                 ▼
+--------------------------------------------------------------------------------------------------+
|                                    GOLD ANALYTICAL MART                                          |
|  - gold_oncology_markups: 5,068 enriched commercial contracts joined to CMS ASP baselines        |
|  - Grain: One record per Hospital x Drug (HCPCS) x Payer x Plan contract filing                  |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. Master Table: `gold_oncology_markups`

* **Table Name**: `gold_oncology_markups`
* **Storage Format**: Columnar DuckDB Table
* **Record Count**: **5,068 rows** (3,121 general commercial baseline)
* **Primary Key / Grain**: Composite Key (`hospital_name`, `hcpcs_code`, `payer_name`, `plan_name`)

| # | Column Name | Data Type | Nullable | Source Lineage | Allowed Values / Domain | Business Definition & Analytical Purpose |
| :-: | :--- | :--- | :-: | :--- | :--- | :--- |
| **1** | `hospital_name` | `VARCHAR` | No | `silver_hospital_rates` | `Baptist Health South Florida`, `Moffitt Cancer Center`, `HCA Florida Memorial Hospital` | Legal operating name of the reporting health system. |
| **2** | `ownership_type` | `VARCHAR` | No | `silver_hospital_rates` | `Non-Profit Community`, `Comprehensive Cancer Center`, `For-Profit` | Institutional tax status and operating model classification. |
| **3** | `hcpcs_code` | `VARCHAR` | No | `silver_hospital_rates` | 5-character HCPCS J-codes (e.g., `J9271`, `J9299`, `J9355`) | Universal Healthcare Common Procedure Coding System identifier for the biologic. |
| **4** | `brand_name` | `VARCHAR` | No | `silver_cms_asp` | Proprietary drug names (e.g., `Keytruda`, `Opdivo`, `Herceptin`) | Commercial trade name of the physician-administered oncology therapeutic. |
| **5** | `generic_name` | `VARCHAR` | No | `silver_cms_asp` | Non-proprietary clinical names (e.g., `pembrolizumab`, `nivolumab`) | Active pharmaceutical chemical substance name. |
| **6** | `billing_unit` | `VARCHAR` | No | `silver_cms_asp` | `1 mg`, `10 mg`, `100 mg` | Official CMS statutory pricing measurement unit for HCPCS code. |
| **7** | `dosage_mg` | `DOUBLE` | No | `silver_cms_asp` | Numeric milligrams (e.g., `1.0`, `10.0`, `100.0`) | Milligram equivalence per statutory billing unit. |
| **8** | `payer_name` | `VARCHAR` | No | Bronze MRF | Raw text strings | Unstandardized insurance company name as published by the reporting hospital. |
| **9** | `plan_name` | `VARCHAR` | No | Bronze MRF | Raw text strings | Unstandardized benefit plan or contract schedule string as published by hospital. |
| **10** | `standardized_payer_name` | `VARCHAR` | No | Deterministic Crosswalk | `Aetna`, `AvMed`, `Cigna`, `Florida Blue`, `Humana`, `UnitedHealthcare`, etc. | Cleaned parent insurance organization name normalized across all reporting systems. |
| **11** | `standardized_market_segment` | `VARCHAR` | No | Deterministic Crosswalk | `Commercial Employer`, `Medicare Advantage`, `ACA Individual Exchange`, `Medicaid Managed Care`, `Military / TRICARE`, `Veterans Affairs (VA CCN)`, `Correctional Healthcare` | Statutory line of business under which underwriting risk and fee structures are held. |
| **12** | `service_line_scope` | `VARCHAR` | No | Deterministic Crosswalk | `Outpatient Facility`, `Pharmacy / Buy-and-Bill`, `Transplant COE` | Operational delivery site within hospital revenue cycle. |
| **13** | `reimbursement_methodology` | `VARCHAR` | No | Deterministic Crosswalk | `Fee Schedule`, `Percent of Billed Charges`, `Case Rate / Bundled` | Contract payment mechanism governing reimbursement calculation. |
| **14** | `carve_out_type` | `VARCHAR` | No | Deterministic Crosswalk | `Standard Oncology`, `Transplant Carve-Out`, `Specialty Pharmacy` | Contractual classification identifying specialized exclusion terms. |
| **15** | `network_status` | `VARCHAR` | No | Deterministic Crosswalk | `IN_NETWORK`, `NON_CONTRACTED` | Network participation flag decoupling entity identity from in-network participation. |
| **16** | `is_in_network` | `BOOLEAN` | No | Derived | `TRUE`, `FALSE` | Boolean convenience flag identifying contracted in-network rates. |
| **17** | `include_in_commercial_benchmark` | `BOOLEAN` | No | Derived | `TRUE`, `FALSE` | Flag isolating all in-network commercial lines (Employer + ACA + Transplant). |
| **18** | `include_in_general_commercial_benchmark` | `BOOLEAN` | No | Derived | `TRUE`, `FALSE` | Flag isolating standard in-network commercial contracts (Figures 1–5 baseline, n=3,121). |
| **19** | `include_in_transplant_carveout_benchmark` | `BOOLEAN` | No | Derived | `TRUE`, `FALSE` | Flag isolating specialized bone-marrow and cellular immunotherapy contracts. |
| **20** | `include_in_ma_benchmark` | `BOOLEAN` | No | Derived | `TRUE`, `FALSE` | Flag isolating federally anchored Medicare Advantage contracts (n=1,139). |
| **21** | `contract_cluster_id` | `VARCHAR` | No | Deterministic Crosswalk | Standardized alphanumeric contract IDs | Identifier clustering shared fee schedules across duplicate hospital plan filings. |
| **22** | `data_quality_status` | `VARCHAR` | No | Governance Audit | `VERIFIED_CONTRACT`, `SUSPECT_UNIT_MISMATCH`, `EXCLUDE_PHANTOM_CDM_RATE` | Data quality status tag tracking RCM anomalies and unit mismatches. |
| **23** | `asp_benchmark_rate` | `DOUBLE` | No | `silver_cms_asp` | Real positive dollar values (USD) | Statutory Medicare Part B payment limit ($\text{ASP} \times 1.06$) per billing unit. |
| **24** | `hospital_gross_charge` | `DOUBLE` | Yes | Bronze MRF / CDM | Real positive dollar values (USD) | Hospital undiscounted chargemaster list sticker price per billing unit. |
| **25** | `hospital_cash_rate` | `DOUBLE` | Yes | Bronze MRF / CDM | Real positive dollar values (USD) | Hospital published upfront self-pay discounted cash price per billing unit. |
| **26** | `commercial_negotiated_rate` | `DOUBLE` | No | Bronze MRF | Real positive dollar values (USD) | Legally binding in-network negotiated contract price per billing unit. |
| **27** | `commercial_markup_ratio` | `DOUBLE` | No | Derived (`CTE 4`) | Positive decimal ratio ($\ge 0.1\text{x}$) | Primary econometric multiplier: $\text{Negotiated Rate} / \text{ASP Benchmark Rate}$. |
| **28** | `chargemaster_markup_ratio` | `DOUBLE` | Yes | Derived (`CTE 4`) | Positive decimal ratio ($\ge 0.1\text{x}$) | Chargemaster inflation index: $\text{Gross Charge} / \text{ASP Benchmark Rate}$. |
| **29** | `cash_discount_advantage` | `DOUBLE` | Yes | Derived (`CTE 4`) | Dollar spread (USD, positive or negative) | Dollar spread: $\text{Negotiated Rate} - \text{Cash Rate}$. Positive indicates Cash is cheaper! |
| **30** | `patient_coinsurance_20pct` | `DOUBLE` | No | Derived (`CTE 4`) | Real dollar value (USD) | Standard 20% patient out-of-pocket coinsurance liability: $\text{Negotiated Rate} \times 0.20$. |

---

## 3. Reference Table: `silver_cms_asp`

* **Source**: Official CMS Medicare Part B Average Sales Price Payment Limits (CY2024/CY2026 Payment Files)
* **Storage Format**: Columnar DuckDB Table
* **Record Count**: **25 rows** (representing targeted oncology biologics)

| Column Name | Data Type | Nullable | Description & Statutory Context |
| :--- | :--- | :-: | :--- |
| `hcpcs_code` | `VARCHAR` | No | Universal 5-character HCPCS J-code (Primary Key). |
| `brand_name` | `VARCHAR` | No | Commercial trade name of therapeutic agent. |
| `generic_name` | `VARCHAR` | No | Official international non-proprietary drug name. |
| `billing_unit` | `VARCHAR` | No | CMS statutory dosage unit definition (e.g., `1 mg`, `10 mg`). |
| `dosage_mg` | `DOUBLE` | No | Milligram weight per billing unit. |
| `asp_payment_limit` | `DOUBLE` | No | Statutory reimbursement ceiling ($\text{ASP} \times 1.06$) established under SSA § 1847A. |

---

## 4. Reference Table: `silver_hospital_rates`

* **Source**: Harmonized Union of Baptist Health, Moffitt Cancer Center, and HCA Florida Memorial MRFs
* **Storage Format**: Columnar DuckDB Table
* **Record Count**: **5,068 rows**

| Column Group | Description |
| :--- | :--- |
| **Identifiers** | `hospital_name`, `ownership_type`, `hcpcs_code`, `code_type` (`HCPCS` / `CDM`). |
| **Pricing Fields** | `gross_charge`, `cash_discount_rate`, `negotiated_rate`, `min_rate`, `max_rate`. |
| **Payer & Plan** | `payer_name`, `plan_name`, `standardized_payer_name`, `standardized_market_segment`. |
| **Governance Flags** | `is_in_network`, `network_status`, `data_quality_status`, `contract_cluster_id`. |

---

## 5. Core Metric Mathematical Formulations

### 1. Medicare Part B ASP Statutory Ceiling ($\text{ASP}_{\text{limit}}$)
$$\text{ASP}_{\text{limit}} = \text{ASP} \times 1.06$$
* Statutory ceiling for outpatient physician-administered biologics under Social Security Act § 1847A.

### 2. Commercial Markup Ratio ($\text{Markup}_{\text{ASP}}$)
$$\text{Markup}_{\text{ASP}} = \frac{\text{commercial\_negotiated\_rate}}{\text{asp\_benchmark\_rate}}$$
* Quantifies the commercial price premium above federal cost recovery baselines.

### 3. Cash Discount Dollar Spread ($\text{Spread}_{\text{cash}}$)
$$\text{Spread}_{\text{cash}} = \text{commercial\_negotiated\_rate} - \text{hospital\_cash\_rate}$$
* A positive dollar value demonstrates the **Cash Paradox**: uninsured patients pay less than insured patients.

### 4. Patient 20% Coinsurance Exposure ($\text{Exposure}_{20\text{pct}}$)
$$\text{Exposure}_{20\text{pct}} = \text{commercial\_negotiated\_rate} \times 0.20$$
* Patient cost-share liability per statutory billing unit prior to reaching annual deductible and ACA Out-of-Pocket Maximum.
