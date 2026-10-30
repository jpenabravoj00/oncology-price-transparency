"""
src/visualization/theme.py
==============================================================================
Portfolio Project 004: Oncology Price Transparency & Economic Analysis
Unified Styling, Typography, Color Palettes & Export Specifications

Purpose:
Decouple visual styling and formatting rules from analytical plotting logic.
Supports both Matplotlib/Seaborn (static 300 DPI exports) and Plotly (Streamlit).
==============================================================================
"""

import os
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib_cache"
import matplotlib.pyplot as plt
import duckdb

# -----------------------------------------------------------------------------
# 1. Database Connection Helper
# -----------------------------------------------------------------------------
DB_PATH = "data/processed/oncoprice.duckdb"

def get_db_connection(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """
    Returns a connection to the DuckDB analytics database.
    Defaults to read_only=True to prevent file locks between the Streamlit app
    and concurrent analytical scripts.
    """
    return duckdb.connect(DB_PATH, read_only=read_only)


# -----------------------------------------------------------------------------
# 2. Healthcare & Economic Color Palette (WCAG AA Compliant)
# -----------------------------------------------------------------------------
COLORS = {
    # Institutional Ownership Types
    "For-Profit": "#D9381E",             # Urgent Crimson (Aggressive pricing)
    "Non-Profit Community": "#1B4965",   # Deep Slate Blue (Traditional system)
    "Comprehensive Cancer Center": "#2B9348", # Clinical Green (Academic/NCI)

    # Market Segments / Payers
    "Medicare Advantage": "#2A9D8F",      # Regulated Teal (Low markup)
    "ACA Individual Exchange": "#E76F51", # Exchange Coral (Moderate markup)
    "Commercial Employer": "#1B4965",     # Deep Slate Blue (Matches Figures 1 & 2)
    "Medicaid Managed Care": "#8338EC",   # Purple (State Medicaid MCO)
    "Military / TRICARE": "#457B9D",      # Air Force Blue (Federal Statutory Floor)
    "Veterans Affairs (VA CCN)": "#588157",# Sage Green (Community Care Network)
    "Correctional Healthcare": "#6C757D", # Slate Gray (Prison System Care)
    "Transplant COE Carve-Outs": "#E07A5F",# Terracotta (Specialty Facility)

    # Economic Benchmarks & Spreads
    "Benchmark_ASP": "#C1121F",          # Bold Red Benchmark Line (1.0x ASP)
    "Cash_Advantage_Positive": "#38B000",# Emerald (Cash is cheaper than insured)
    "Cash_Advantage_Negative": "#9D0208",# Deep Red (Insured is cheaper than cash)
    
    # Neutral Tones
    "Background": "#FFFFFF",
    "Card_Background": "#F8F9FA",
    "Text_Primary": "#212529",
    "Text_Muted": "#6C757D",
    "Gridlines": "#E9ECEF"
}


# -----------------------------------------------------------------------------
# 3. Matplotlib / Seaborn Publication Theme
# -----------------------------------------------------------------------------
def set_publication_style():
    """Configures global matplotlib styling for crisp 300 DPI publication charts."""
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Helvetica Neue", "Arial"],
        "text.color": COLORS["Text_Primary"],
        "axes.labelcolor": COLORS["Text_Primary"],
        "xtick.color": COLORS["Text_Primary"],
        "ytick.color": COLORS["Text_Primary"],
        "axes.edgecolor": COLORS["Text_Muted"],
        "grid.color": COLORS["Gridlines"],
        "grid.linestyle": "--",
        "grid.alpha": 0.7,
        "figure.facecolor": COLORS["Background"],
        "axes.facecolor": COLORS["Background"],
        "figure.titlesize": 16,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "savefig.dpi": 300,
        "savefig.bbox": "tight"
    })
