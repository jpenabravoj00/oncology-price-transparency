# Engineering Decision Log & Technical Architecture Post-Mortem
## Portfolio Project 004: Oncology Price Transparency & Economic Analysis

**Author:** Data & Analytics Engineering  
**Core Technologies:** DuckDB (In-Process OLAP), Python 3.11+, Streamlit, Plotly, SQL (Medallion Architecture)  
**Analytical Scope:** 5,068 commercial oncology contracts across 14 high-cost biologics  
**Status:** Production Hardened  

---

## 1. Project Motivation & Analytical Framework

### 1.1 The Problem
Under CMS federal price transparency regulations (45 CFR § 180.50), hospitals must publicly disclose standard charges and negotiated rates in Machine-Readable Files (MRFs). While the policy goal is price transparency, raw hospital files are notoriously heterogeneous and unstructured:
- File formats diverge widely (tall CSVs, 500+ column matrices, multi-hundred-megabyte JSON trees).
- Insurer names are inconsistent (`"BCBS FL"`, `"Florida Blue"`, `"Blue Options"`).
- Pricing structures mix fee schedules, percentage-of-charge discounts, and bundled package rates.

My goal in this project was to build a reproducible, end-to-end data pipeline to ingest, clean, and standardize commercial pricing from three Florida health systems (Baptist Health South Florida, Moffitt Cancer Center, and HCA Florida Memorial Hospital) and benchmark them against the federal statutory baseline: **CMS Medicare Part B Average Sales Price (ASP + 6%)**.

```
RAW HOSPITAL MRFs                          DATA ENGINEERING & HARMONIZATION                 ANALYTICS & APPLICATION
┌─────────────────────────────┐            ┌────────────────────────────────────────┐       ┌────────────────────────────┐
│ • Baptist Health (Tall CSV) │            │ 1. Dynamic Python Unpivoting           │       │ • DuckDB Columnar Mart     │
│ • Moffitt (559-Col Matrix)  │ ─────────► │    (Moffitt wide-to-tall ETL)          │ ────► │   (5,068 contracts)        │
│ • HCA Florida (Streamed JSON│            │ 2. Deterministic Regulatory Crosswalk  │       │ • Streamlit Web Dashboard  │
│   & Case-Rate Bundles)      │            │    (118 plans -> 7 statutory segments) │       │ • 300-DPI Publication Figs │
└─────────────────────────────┘            └────────────────────────────────────────┘       └────────────────────────────┘
```

### 1.2 Core Metrics Defined
To evaluate hospital commercial pricing, I anchored every contract to the official Medicare Part B payment limit:

1. **Medicare Part B Baseline ($\text{ASP}_{\text{limit}}$):**
   $$\text{ASP}_{\text{limit}} = \text{ASP} \times 1.06$$
   The statutory federal reimbursement limit under Social Security Act § 1847A.

2. **Commercial Markup Ratio ($\text{Markup}_{\text{ASP}}$):**
   $$\text{Markup}_{\text{ASP}} = \frac{\text{Negotiated Rate}}{\text{ASP}_{\text{limit}}}$$
   Measures the commercial price multiplier over federal cost limits (e.g., $1.0\times$ = cost parity; $4.41\times$ = our project's median commercial markup).

3. **Cash Discount Advantage ($\text{Advantage}_{\text{cash}}$):**
   $$\text{Advantage}_{\text{cash}} = \text{Negotiated Insured Rate} - \text{Discounted Cash Price}$$
   A positive value flags the "Cash Paradox," where paying cash out-of-pocket is cheaper than using in-network insurance.

4. **Patient Coinsurance Exposure (20%):**
   $$\text{Coinsurance}_{20\%} = \text{Negotiated Rate} \times 0.20$$
   Standard commercial cost-sharing on outpatient specialty infusions.

---

## 2. Challenge 1: Moffitt Dynamic Wide-to-Tall Unpivot & CDM Matching

### The Challenge
Moffitt Cancer Center is an NCI-Designated Comprehensive Cancer Center. Including Moffitt was essential for comparing academic specialty centers against community non-profits and for-profit chains. 

However, Moffitt did not publish a standard relational table. Instead, they published a wide matrix with **559 columns**:
- Every insurance plan was placed in its own column header (e.g., `Aetna Commercial [negotiated_rate]`).
- Rows were identified by internal Charge Description Master (CDM) SKU numbers rather than universal HCPCS codes.
- The matrix formed a "staircase of NaNs," where cancer drugs appeared on separate rows for facility fee schedules vs. pharmacy gross charges.

```
MOFFITT'S RAW 559-COLUMN STRUCTURE:
┌──────────────┬──────────────┬──────────────┬────────────┬───────────┬───────────┐
│ code|1 (CDM) │ code|2 (HCPCS)│ Gross Charge │ Cash Price │ Aetna PPO │ Cigna HMO │
├──────────────┼──────────────┼──────────────┼────────────┼───────────┼───────────┤
│ 1004521      │ J9271        │ NaN          │ NaN        │ $9,800.00 │ NaN       │
│ 1004522      │ J9271        │ $324.00      │ $162.00    │ NaN       │ NaN       │
└──────────────┴──────────────┴──────────────┴────────────┴───────────┴───────────┘
```

### The Solution (`src/harmonize_moffitt.py`)
I evaluated two approaches:
1. *Rejected Alternative:* Writing a large SQL query with 34 hardcoded `CASE WHEN` statements and column names. This would be fragile and would break whenever Moffitt modified plan headers in future releases.
2. *Selected Implementation:* I wrote a dynamic Python ETL pipeline using regular expressions and `pd.melt()`:
   - Programmatically searched for outpatient facility columns ending in `|negotiated_dollar`.
   - Filtered out `(MMG)` (Moffitt Medical Group) doctor professional fees to keep facility comparisons clean.
   - Unpivoted the wide plan columns into tall relational rows.
   - Attached Moffitt's true pharmacy gross charge (`$324.00`) and 50% cash discount rate (`$162.00`) by matching HCPCS codes.

This generated 470 clean, tall contract records across all 14 cancer biologics without fragile hardcoding.

---

## 3. Challenge 2: Deterministic Payer-Plan Crosswalk & Regulatory Grounding

### The Challenge
Hospital files contained **118 distinct, unstandardized payer and plan strings** (`"BCBS FL"`, `"Florida Blue HMO"`, `"Blue Options"`, `"Oscar Health Non-Par"`). To evaluate insurer negotiating leverage, I needed to know the exact statutory line of business (e.g., Commercial Employer vs. Medicare Advantage vs. ACA Exchange).

### The Solution (`src/build_payer_plan_crosswalk.py`)
I avoided fuzzy string matching or LLM-based categorization, which can introduce hallucinations. Instead, I built a deterministic 118-row crosswalk mapped directly against official public government registries:
1. **CMS Medicare Advantage Landscape File (CY2026):** Verified contract IDs, parent organizations, and approved marketing names.
2. **CMS Qualified Health Plan (QHP) Public Use File (PUF):** Verified ACA Exchange product identifiers in Florida.
3. **Data.Medicaid.gov Enrollment Reports:** Verified contracted Medicaid Managed Care Organizations (SMMC).

```
THE 7 STATUTORY MARKET SEGMENTS:
1. Commercial Employer        - Employer-sponsored group plans (Highest markups)
2. Medicare Advantage         - Privately managed Part C plans (Anchored to Medicare ASP)
3. ACA Individual Exchange    - ACA Marketplace plans with individual deductible exposure
4. Medicaid Managed Care      - State-contracted managed Medicaid plans
5. Military / TRICARE         - Defense health programs subject to statutory payment floors
6. Veterans Affairs (VA CCN)  - VA Community Care Network claims
7. Correctional Healthcare    - State prison healthcare contracts
```

#### Decoupling Network Participation (`network_status: NON_CONTRACTED`)
When a hospital published rates for non-participating insurers (e.g., Oscar Health at Baptist labeled `NON CONTRACTED`), I decoupled the insurer's identity from its network status:
- Standardized Payer: `OSCAR HEALTH`
- Market Segment: `ACA Individual Exchange`
- Network Status: `NON_CONTRACTED` (`is_in_network = FALSE`)

This preserved the raw data for out-of-network charge analysis while allowing me to filter out non-contracted rates from our in-network commercial benchmark cohort (yielding our clean 3,121-contract baseline).

---

## 4. Challenge 3: Revenue Cycle Mechanics & Outlier Investigation

### The Challenge
Preliminary data audits revealed three major data anomalies:
1. **Baptist Medicaid Paradox ($2,800 vs. $70):** Baptist Health listed Medicaid managed care rates for Keytruda at over $2,800 (more than 50x ASP), even though Florida Medicaid caps reimbursement around $70.
2. **HCA $15,000 Case-Rate Outliers:** HCA Florida Memorial reported 15 contracts with an identical rate of exactly `$15,000.00`.
3. **HCA $8.56 Rate:** A Medicare Advantage contract published at `$8.56`—a 10x dosage unit division artifact.

### The Solution & Revenue Cycle Analysis
Rather than simply running an automated outlier removal script, I investigated the underlying hospital billing mechanics:

1. **The "Coupon vs. Price Cap" Finding (Baptist Medicaid):**
   - Hospital IT departments often run automated contract-modeling scripts that apply a nominal percentage discount (e.g., 20% off chargemaster) across all contracts without programming statutory fee ceilings.
   - Under state law, Medicaid MCOs pay the lesser of billed charges or the state Medicaid fee schedule ceiling ($70). The $2,800 figure was an unadjudicated modeling artifact ("phantom rate"). I quarantined these rows under `data_quality_status = 'EXCLUDE_PHANTOM_CDM_RATE'`.
2. **The `NC` Suffix:** Baptist plans frequently included an `NC` tag (e.g., `Molina Medicaid NC`). In hospital billing, `NC` stands for **Non-Capitated**, meaning high-cost chemotherapy biologics are carved out of monthly doctor capitation fees and billed as fee-for-service items.
3. **HCA $15,000 Bundled Episode Rates:**
   - HCA negotiated flat case-rates where $15,000 covered the entire infusion encounter (facility stay, nursing, and drug combined).
   - Silently deleting these rows would hide how for-profit systems structure contracts, but keeping them unadjusted would distort drug-only markups.
   - I built an interactive **Global Outlier Isolation Toggle** in `app.py`. This gives users full visibility into both pure drug pricing and bundled hospital contracting models.

---

## 5. Challenge 4: Database Architecture Trade-Offs (Why DuckDB?)

### The Evaluation
I needed an analytical database that could execute multi-CTE SQL transformations across 5,068 contracts, power responsive Streamlit visualizations, and allow anyone to clone the repository and run the app in seconds without setup friction.

| Consideration | Pandas (In-Memory) | PostgreSQL (Client-Server) | DuckDB (In-Process OLAP) — **SELECTED** |
| :--- | :--- | :--- | :--- |
| **Execution Engine** | Row-oriented Python interpreter | Disk/Server daemon | **Vectorized columnar C++ engine** |
| **Setup Friction** | Low | High (requires local database setup) | **Zero (single portable `.duckdb` file)** |
| **SQL Capability** | None (verbose method chaining) | Full ANSI SQL | **Full ANSI SQL with native Window/CTE support** |
| **Memory Footprint** | High (object types cause 3x–5x bloat)| Heavy server overhead | **Compact columnar storage** |
| **Reproducibility** | Moderate | Poor (breaks if server isn't running)| **Maximum (`git clone` $\rightarrow$ run immediately)** |

### Implementation
I selected **DuckDB** (`data/processed/oncoprice.duckdb`). 
- Multi-CTE SQL scripts (`sql/03_gold/01_create_gold_markups.sql`) run cleanly inside DuckDB.
- Setting `read_only=True` in database connection handlers prevents file-lock conflicts between Streamlit and analytical scripts.

---

## 6. Technical Limitations & Telemetry Boundaries

Responsible health data analysis requires acknowledging telemetry limits:

1. **Absence of Claims Volume Weights:** MRFs disclose contracted rate schedules, but not patient claims volumes. A contract covering 5 patients looks identical in the table to one covering 50,000. To prevent fringe contracts from distorting findings, I enforced **median-first reporting**, reported interquartile ranges (IQR), and used distribution box plots rather than relying on arithmetic averages.
2. **Pre-Service Rates vs. Post-Adjudication Remittance:** Published rates represent contracted agreements *on paper*, not post-adjudication claims paid after medical necessity denials or retrospective manufacturer rebates.
3. **340B Drug Acquisition Economics:** Covered safety-net entities purchase cancer biologics at 20% to 50% below ASP under federal 340B statute. Because our benchmark is ASP + 6%, a 4.41x commercial markup over ASP represents a gross hospital margin exceeding 600% on 340B inventory.
4. **Geographic Confounding (GPCI):** In Figure 2, non-profit Baptist Health (Miami) commands higher median markups (4.50x) than for-profit HCA (Jacksonville, 3.80x). While institutional ownership is a key factor, regional labor costs, the CMS Geographic Practice Cost Index (GPCI), and local hospital market concentration also influence regional pricing.
