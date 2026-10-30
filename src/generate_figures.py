"""
src/generate_figures.py
==============================================================================
Portfolio Project 004: Oncology Price Transparency & Economic Analysis
Automated Publication Figure Generation Pipeline

Generates 300 DPI high-resolution figures saved to reports/figures/
==============================================================================
"""

import os
import sys
sys.path.insert(0, ".")

import matplotlib.pyplot as plt
import seaborn as sns
from src.visualization.theme import (
    get_db_connection,
    set_publication_style,
    COLORS
)

OUTPUT_DIR = "reports/figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_figure_1():
    """
    Figure 1: Median Commercial Markup Over Medicare Part B ASP Baseline
    Source: sql/04_analytics_queries/01_highest_markup_drugs.sql
    """
    print("-> Generating Figure 1: Drug-Level Markups over ASP...")
    set_publication_style()
    con = get_db_connection()
    
    query = """
    SELECT 
        brand_name,
        generic_name,
        COUNT(*) AS contract_count,
        ROUND(MEDIAN(commercial_markup_ratio), 2) AS median_markup,
        ROUND(AVG(commercial_markup_ratio), 2) AS avg_markup
    FROM gold_oncology_markups
    WHERE include_in_general_commercial_benchmark = TRUE
    GROUP BY brand_name, generic_name
    ORDER BY median_markup DESC;
    """
    df = con.sql(query).df()
    total_contracts = df["contract_count"].sum()
    
    fig, ax = plt.subplots(figsize=(11, 7))
    
    bars = ax.barh(
        df["brand_name"],
        df["median_markup"],
        color=COLORS["Non-Profit Community"],
        edgecolor=COLORS["Text_Primary"],
        linewidth=0.8,
        height=0.62,
        alpha=0.9
    )
    
    ax.invert_yaxis()
    
    ax.axvline(
        x=1.0,
        color=COLORS["Benchmark_ASP"],
        linestyle="--",
        linewidth=2.0,
        label="CMS Medicare Part B Statutory Baseline (1.0x ASP)"
    )
    
    for bar, val, count in zip(bars, df["median_markup"], df["contract_count"]):
        width = bar.get_width()
        ax.text(
            width + 0.12,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.2f}x  ({count:,} contracts)",
            va="center",
            ha="left",
            fontsize=9.5,
            fontweight="bold",
            color=COLORS["Text_Primary"]
        )
        
    fig.suptitle(
        "Figure 1: Commercial Markups for Top Oncology Biologics Over Medicare Part B ASP",
        fontsize=14,
        fontweight="bold",
        x=0.08,
        y=0.98,
        ha="left"
    )
    ax.set_title(
        f"Comparing median commercial negotiated rates across 14 oncology medications ({total_contracts:,} in-network contracts, Florida health systems)",
        fontsize=10,
        color=COLORS["Text_Muted"],
        pad=16,
        loc="left"
    )
    
    ax.set_xlabel("Commercial Negotiated Rate as Multiple of ASP (1.0x = Medicare Baseline)", fontsize=11, labelpad=10)
    ax.set_ylabel("")
    ax.set_xlim(0, df["median_markup"].max() * 1.35)
    
    ax.legend(loc="lower right", frameon=True, facecolor=COLORS["Card_Background"], fontsize=10)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    output_path = os.path.join(OUTPUT_DIR, "figure_1.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"✓ Successfully exported Figure 1 to {output_path}")


def generate_figure_2():
    """
    Figure 2: Commercial Markup Comparison Across Hospital Ownership Models
    Source: sql/04_analytics_queries/02_markups_by_ownership_type.sql
    """
    print("-> Generating Figure 2: Institutional Ownership Markup Comparison...")
    set_publication_style()
    con = get_db_connection()
    
    query = """
    SELECT 
        hospital_name,
        ownership_type,
        COUNT(*) AS total_contracts,
        ROUND(MEDIAN(commercial_markup_ratio), 2) AS median_markup,
        ROUND(QUANTILE_CONT(commercial_markup_ratio, 0.25), 2) AS q25_markup,
        ROUND(QUANTILE_CONT(commercial_markup_ratio, 0.75), 2) AS q75_markup
    FROM gold_oncology_markups
    WHERE include_in_general_commercial_benchmark = TRUE
      AND commercial_markup_ratio BETWEEN 1.0 AND 20.0
    GROUP BY hospital_name, ownership_type
    ORDER BY median_markup DESC;
    """
    df = con.sql(query).df()
    
    err_lower = df["median_markup"] - df["q25_markup"]
    err_upper = df["q75_markup"] - df["median_markup"]
    asymmetric_error = [err_lower, err_upper]
    
    bar_colors = []
    for o in df["ownership_type"]:
        if "For-Profit" in o:
            bar_colors.append(COLORS["For-Profit"])
        elif "Comprehensive Cancer Center" in o:
            bar_colors.append(COLORS["Comprehensive Cancer Center"])
        else:
            bar_colors.append(COLORS["Non-Profit Community"])
    
    display_labels = [
        f"{hosp}\n({own})"
        for hosp, own in zip(df["hospital_name"], df["ownership_type"])
    ]
    
    fig, ax = plt.subplots(figsize=(10, 6.5))
    
    bars = ax.bar(
        display_labels,
        df["median_markup"],
        yerr=asymmetric_error,
        capsize=8,
        color=bar_colors,
        edgecolor=COLORS["Text_Primary"],
        linewidth=0.8,
        width=0.52,
        alpha=0.9,
        error_kw=dict(lw=1.5, capthick=1.5, ecolor=COLORS["Text_Primary"])
    )
    
    ax.axhline(
        y=1.0,
        color=COLORS["Benchmark_ASP"],
        linestyle="--",
        linewidth=2.0,
        label="CMS Medicare Part B Statutory Baseline (1.0x ASP)"
    )
    
    for bar, med, q25, q75, count in zip(bars, df["median_markup"], df["q25_markup"], df["q75_markup"], df["total_contracts"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            q75 + 0.35,
            f"Median: {med:.2f}x\nIQR: [{q25:.2f}x – {q75:.2f}x]\n({count:,} contracts)",
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="bold",
            color=COLORS["Text_Primary"]
        )
        
    fig.suptitle(
        "Figure 2: Oncology Drug Markups Across Hospital Ownership Structures",
        fontsize=14,
        fontweight="bold",
        x=0.08,
        y=0.98,
        ha="left"
    )
    ax.set_title(
        "Debunking the Non-Profit Myth: Commercial Markups (Median & IQR) vs. Medicare Part B ASP",
        fontsize=10,
        color=COLORS["Text_Muted"],
        pad=16,
        loc="left"
    )
    
    ax.set_ylabel("Commercial Negotiated Rate as Multiple of ASP (1.0x = Baseline)", fontsize=11, labelpad=10)
    ax.set_ylim(0, df["q75_markup"].max() * 1.55)
    
    ax.legend(loc="upper right", frameon=True, facecolor=COLORS["Card_Background"], fontsize=10)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    output_path = os.path.join(OUTPUT_DIR, "figure_2.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"✓ Successfully exported Figure 2 to {output_path}")


def generate_figure_3():
    """
    Figure 3: Payer Negotiation Leverage & Contracting Range
    Source: sql/04_analytics_queries/03_payer_negotiation_power.sql
    """
    print("-> Generating Figure 3: Commercial Payer Negotiation Power (Dumbbell Plot)...")
    set_publication_style()
    con = get_db_connection()
    
    query = """
    SELECT 
        CASE 
            WHEN standardized_payer_name = 'FLORIDA BLUE (GUIDEWELL)' THEN 'Florida Blue'
            WHEN standardized_payer_name = 'AETNA' THEN 'Aetna'
            WHEN standardized_payer_name = 'CIGNA' THEN 'Cigna'
            WHEN standardized_payer_name = 'UNITEDHEALTHCARE' THEN 'UnitedHealthcare'
            WHEN standardized_payer_name = 'HUMANA' THEN 'Humana'
            WHEN standardized_payer_name = 'AVMED' THEN 'AvMed'
            ELSE standardized_payer_name
        END AS payer_name,
        standardized_market_segment,
        ROUND(MEDIAN(commercial_markup_ratio), 2) AS median_markup,
        COUNT(*) as contracts
    FROM gold_oncology_markups
    WHERE standardized_payer_name IN (
        'FLORIDA BLUE (GUIDEWELL)', 'AETNA', 'CIGNA', 
        'UNITEDHEALTHCARE', 'HUMANA', 'AVMED'
    )
      AND standardized_market_segment IN ('Medicare Advantage', 'ACA Individual Exchange', 'Commercial Employer')
      AND is_in_network = TRUE
      AND data_quality_status = 'VALID_NEGOTIATED_RATE'
      AND commercial_markup_ratio BETWEEN 0.5 AND 20.0
    GROUP BY 1, 2;
    """
    df = con.sql(query).df()
    
    # 6 major Florida commercial payers ordered by commercial markup ascending
    payers = ['AvMed', 'Humana', 'Aetna', 'Cigna', 'Florida Blue', 'UnitedHealthcare']
    
    fig, ax = plt.subplots(figsize=(11.0, 6.5))
    
    segment_colors = {
        'Medicare Advantage': COLORS['Medicare Advantage'],
        'ACA Individual Exchange': COLORS['ACA Individual Exchange'],
        'Commercial Employer': COLORS['Commercial Employer']
    }
    
    ax.axvline(
        x=1.0,
        color=COLORS["Benchmark_ASP"],
        linestyle="--",
        linewidth=1.8,
        label="Medicare Part B Baseline (1.0x ASP)"
    )
    
    for y, payer in enumerate(payers):
        sub = df[df['payer_name'] == payer].sort_values('median_markup')
        if sub.empty: 
            continue
        
        min_x = sub['median_markup'].min()
        max_x = sub['median_markup'].max()
        
        # Horizontal connector barbell line
        ax.plot([min_x, max_x], [y, y], color='#CED4DA', linewidth=3.5, zorder=2, solid_capstyle='round')
        
        # Segment markers and staggered data labels
        for _, row in sub.iterrows():
            seg = row['standardized_market_segment']
            val = row['median_markup']
            col = segment_colors.get(seg, COLORS['Text_Primary'])
            
            ax.scatter(val, y, color=col, s=130, edgecolor=COLORS['Text_Primary'], linewidth=1.2, zorder=4)
            
            # Label placement to avoid collisions
            if seg == 'Medicare Advantage':
                ax.text(val + 0.08, y - 0.28, f"{val:.2f}x", ha='left', va='center', fontsize=9.0, fontweight='bold', color=col)
            elif seg == 'ACA Individual Exchange':
                ax.text(val, y + 0.28, f"{val:.2f}x", ha='center', va='center', fontsize=9.0, fontweight='bold', color=col)
            else: # Commercial Employer
                if payer == 'AvMed':
                    ax.text(val + 0.08, y - 0.28, f"{val:.2f}x", ha='left', va='center', fontsize=9.0, fontweight='bold', color=col)
                elif payer == 'UnitedHealthcare':
                    ax.text(val, y - 0.28, f"{val:.2f}x", ha='center', va='center', fontsize=9.0, fontweight='bold', color=col)
                else:
                    ax.text(val, y - 0.28, f"{val:.2f}x", ha='center', va='center', fontsize=9.0, fontweight='bold', color=col)
            
    ax.set_yticks(range(len(payers)))
    ax.set_yticklabels(payers, fontsize=11, fontweight='bold')
    ax.set_ylim(-0.7, 5.7)
    
    fig.suptitle(
        "Figure 3: Commercial Payer Leverage & Contracting Spread Across Market Segments",
        fontsize=13.5,
        fontweight="bold",
        x=0.08,
        y=0.98,
        ha="left"
    )
    total_contracts = df['contracts'].sum()
    ax.set_title(
        f"Dumbbell plot showing median negotiated markup spreads across major Florida health plans ({total_contracts:,} contracts)",
        fontsize=10,
        color=COLORS["Text_Muted"],
        pad=16,
        loc="left"
    )
    
    ax.set_xlabel("Median Negotiated Rate as Multiple of ASP (1.0x = Medicare Baseline)", fontsize=11, labelpad=10)
    ax.set_ylabel("")
    ax.set_xlim(0, 8.2)
    
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color=COLORS["Benchmark_ASP"], linestyle="--", lw=2, label="Medicare Statutory Baseline (1.0x)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["Medicare Advantage"], markersize=10, label="Medicare Advantage (Part C)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["ACA Individual Exchange"], markersize=10, label="ACA Individual Exchange"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["Commercial Employer"], markersize=10, label="Commercial Employer Group")
    ]
    ax.legend(handles=legend_elements, loc="lower right", frameon=True, facecolor=COLORS["Card_Background"], fontsize=9.5)
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    output_path = os.path.join(OUTPUT_DIR, "figure_3.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"✓ Successfully exported Figure 3 to {output_path}")


def generate_figure_4():
    """
    Figure 4: The Cash Price Paradox (Top 5 Drugs by Out-of-Pocket Savings)
    Source: sql/04_analytics_queries/04_cash_price_paradox.sql
    Visual: Single-panel horizontal bar chart highlighting median unit dollar savings
    with embedded prevalence percentages and generous header spacing.
    """
    print("-> Generating Figure 4: The Cash Price Paradox (Top 5 Drugs Single-Panel)...")
    set_publication_style()
    con = get_db_connection()
    
    query = """
    WITH top_drugs AS (
        SELECT 
            brand_name,
            COUNT(*) AS total_contracts,
            ROUND(COUNT(CASE WHEN cash_discount_advantage > 0 THEN 1 END) * 100.0 / COUNT(*), 1) AS pct_cash_cheaper,
            ROUND(MEDIAN(CASE WHEN cash_discount_advantage > 0 THEN cash_discount_advantage END), 2) AS median_savings
        FROM gold_oncology_markups
        WHERE hospital_cash_rate IS NOT NULL
          AND include_in_general_commercial_benchmark = TRUE
        GROUP BY brand_name
        HAVING COUNT(CASE WHEN cash_discount_advantage > 0 THEN 1 END) > 0
        ORDER BY median_savings DESC
        LIMIT 5
    )
    SELECT * FROM top_drugs ORDER BY median_savings ASC;
    """
    df = con.sql(query).df()
    
    # 1. Canvas dimensions: 11.5 inches wide x 6.5 inches high
    fig, ax = plt.subplots(figsize=(11.5, 6.5))
    
    # 2. Draw horizontal bars with our consistent Slate Blue
    bars = ax.barh(
        df["brand_name"],
        df["median_savings"],
        color=COLORS["Commercial Employer"], # Deep Slate Blue (#1B4965)
        edgecolor=COLORS["Text_Primary"],
        linewidth=0.8,
        height=0.52,
        alpha=0.9
    )
    
    # 3. Add clean, decoupled data labels:
    # - Contract prevalence INSIDE the bar in white text near the origin
    # - Dollar savings OUTSIDE the bar at the tip (aligned with the x-axis scale)
    for bar, savings, pct, total in zip(bars, df["median_savings"], df["pct_cash_cheaper"], df["total_contracts"]):
        width = bar.get_width()
        
        # Inside the bar (left-aligned near origin)
        ax.text(
            8.0,
            bar.get_y() + bar.get_height() / 2,
            f"{pct:.1f}% cheaper  (n={total:,})",
            va="center",
            ha="left",
            fontsize=10.0,
            fontweight="bold",
            color="#FFFFFF"
        )
        
        # Outside the bar (at the tip)
        ax.text(
            width + 5.0,
            bar.get_y() + bar.get_height() / 2,
            f"+${savings:,.2f} / unit",
            va="center",
            ha="left",
            fontsize=10.5,
            fontweight="bold",
            color=COLORS["Text_Primary"]
        )
    
    # 4. Axis formatting and limits
    ax.set_xlabel("Median Cash Advantage ($ / Billing Unit Saved When Paying Self-Pay Cash)", fontsize=11, labelpad=10)
    ax.set_xlim(0, df["median_savings"].max() * 1.30) # Room for dollar label badges
    
    # Format x-axis with dollar ticks
    import matplotlib.ticker as ticker
    ax.xaxis.set_major_formatter(ticker.StrMethodFormatter("${x:,.0f}"))
    
    # Explanatory Legend aligned with new positions
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elements = [
        Patch(facecolor=COLORS["Commercial Employer"], edgecolor=COLORS["Text_Primary"], label="Bar / Tip Label: Median Cash Savings / Billing Unit ($)"),
        Line2D([0], [0], marker="", color="none", label="Inner Bar Text: % of Contracts Cheaper in Cash (Sample Size)")
    ]
    ax.legend(handles=legend_elements, loc="lower right", frameon=True, facecolor=COLORS["Card_Background"], fontsize=9.0)
    
    # 5. Header Layout: Title + Subtitle with comfortable spacing
    fig.suptitle(
        "Figure 4: The Cash Price Paradox — When Hospital Self-Pay Beats Commercial Rates",
        fontsize=13.5,
        fontweight="bold",
        x=0.08,
        y=0.96,
        ha="left"
    )
    min_sav = df["median_savings"].min()
    max_sav = df["median_savings"].max()
    min_pct = df["pct_cash_cheaper"].min()
    max_pct = df["pct_cash_cheaper"].max()
    plt.figtext(
        0.08, 0.88,
        f"In {min_pct:.0f}% to {max_pct:.0f}% of in-network commercial contracts, hospital self-pay cash prices beat negotiated rates.\nFor top oncology biologics, self-pay patients save \\${min_sav:,.0f} to \\${max_sav:,.0f} per billing unit over commercial insurance.",
        fontsize=9.8,
        color=COLORS["Text_Muted"],
        ha="left"
    )
    
    # Reserve top 16% of canvas for headers
    plt.tight_layout(rect=[0, 0, 1, 0.85])
    
    output_path = os.path.join(OUTPUT_DIR, "figure_4.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"✓ Successfully exported Figure 4 to {output_path}")


def generate_figure_5():
    """
    Figure 5: Patient Coinsurance Toxicity — Out-of-Pocket Exposure for Keytruda
    Source: sql/04_analytics_queries/05_patient_coinsurance_toxicity.sql
    """
    print("-> Generating Figure 5: Patient Coinsurance Toxicity (Keytruda Case Study)...")
    set_publication_style()
    con = get_db_connection()
    
    query = """
    SELECT 
        hospital_name,
        ownership_type,
        COUNT(*) AS plan_count,
        ROUND(MIN(patient_coinsurance_20pct), 2) AS min_coinsurance,
        ROUND(MEDIAN(patient_coinsurance_20pct), 2) AS median_coinsurance,
        ROUND(MAX(patient_coinsurance_20pct), 2) AS max_coinsurance,
        ROUND(AVG(asp_benchmark_rate * 0.20), 2) AS statutory_asp_coinsurance
    FROM gold_oncology_markups
    WHERE brand_name = 'Keytruda'
      AND include_in_general_commercial_benchmark = TRUE
    GROUP BY hospital_name, ownership_type
    ORDER BY median_coinsurance ASC;
    """
    df = con.sql(query).df()
    
    color_map = {
        "For-Profit": COLORS["For-Profit"],
        "Non-Profit Community": COLORS["Non-Profit Community"],
        "Non-Profit Comprehensive Cancer Center": COLORS["Comprehensive Cancer Center"]
    }
    
    fig, ax = plt.subplots(figsize=(12, 7.5))
    
    y_positions = range(len(df))
    statutory_asp = df["statutory_asp_coinsurance"].iloc[0] # $10.86
    
    # 1. Main Plot: Draw Ranges and Medians
    for idx, row in df.iterrows():
        y = idx
        c = color_map.get(row["ownership_type"], COLORS["Text_Primary"])
        
        # Horizontal Range Span (Min to Max)
        ax.hlines(
            y=y,
            xmin=row["min_coinsurance"],
            xmax=row["max_coinsurance"],
            color=c,
            linewidth=6.5,
            alpha=0.35,
            zorder=3
        )
        
        # Min & Max endpoint caps
        ax.scatter([row["min_coinsurance"], row["max_coinsurance"]], [y, y], color=c, s=40, zorder=4)
        
        # Median Point Marker
        ax.scatter(row["median_coinsurance"], y, color=c, s=180, edgecolors=COLORS["Text_Primary"], linewidth=1.5, zorder=5)
        
        # Text Callouts on Main Canvas
        if row["ownership_type"] == "For-Profit":
            # HCA Callouts: Median & Ceiling
            ax.text(
                row["median_coinsurance"], y + 0.18,
                f"Median: ${row['median_coinsurance']:,.2f} ({row['median_coinsurance']/statutory_asp:.1f}x ASP)",
                ha="center", va="bottom", fontsize=10, fontweight="bold", color=c
            )
            ax.text(
                row["max_coinsurance"] + 30, y,
                f"Max: ${row['max_coinsurance']:,.2f}",
                ha="left", va="center", fontsize=9.5, fontweight="bold", color=COLORS["Text_Primary"]
            )
        elif row["ownership_type"] == "Non-Profit Community":
            # Baptist Max Callout
            ax.text(
                row["max_coinsurance"] + 30, y,
                f"Max: ${row['max_coinsurance']:,.2f}",
                ha="left", va="center", fontsize=9.5, fontweight="bold", color=COLORS["Text_Primary"]
            )
            ax.text(
                row["median_coinsurance"] + 25, y + 0.18,
                f"Median: ${row['median_coinsurance']:,.2f}",
                ha="left", va="bottom", fontsize=9.5, fontweight="bold", color=c
            )
        else:
            # Moffitt
            ax.text(
                row["median_coinsurance"] + 35, y,
                f"Median: ${row['median_coinsurance']:,.2f}",
                ha="left", va="center", fontsize=9.5, fontweight="bold", color=c
            )

    # Statutory ASP Vertical Line
    ax.axvline(x=statutory_asp, color=COLORS["Benchmark_ASP"], linestyle="--", linewidth=1.8, alpha=0.85, zorder=2)
    ax.text(
        statutory_asp + 25, 2.42,
        f"Medicare Part B Statutory Baseline (${statutory_asp:,.2f})",
        color=COLORS["Benchmark_ASP"], fontsize=9, fontweight="bold", ha="left", va="center"
    )

    # -------------------------------------------------------------------------
    # Alternative A: Concise, Color-Coded Y-Axis Labels (Two-Line Format)
    # -------------------------------------------------------------------------
    short_hospital_names = {
        "HCA Florida Memorial Hospital": "HCA Florida Memorial",
        "Baptist Health South Florida": "Baptist Health S. Florida",
        "Moffitt Cancer Center": "Moffitt Cancer Center"
    }
    
    clean_labels = [
        f"{short_hospital_names.get(row['hospital_name'], row['hospital_name'])}\n(n={row['plan_count']:,})"
        for _, row in df.iterrows()
    ]
    ax.set_yticks(y_positions)
    ax.set_yticklabels(clean_labels, fontsize=10.5, fontweight="bold")
    
    # Apply matching colors directly to each Y-axis tick label
    for tick_label, (_, row) in zip(ax.get_yticklabels(), df.iterrows()):
        c = color_map.get(row["ownership_type"], COLORS["Text_Primary"])
        tick_label.set_color(c)
        
    ax.set_xlabel("Patient 20% Coinsurance Exposure ($ / 1 mg Billing Unit)", fontsize=11, labelpad=8)
    ax.set_xlim(-50, 3600)
    
    import matplotlib.ticker as ticker
    ax.xaxis.set_major_formatter(ticker.StrMethodFormatter("${x:,.0f}"))
    ax.grid(axis="x", linestyle="--", alpha=0.5)

    # -------------------------------------------------------------------------
    # Legend Placement (Positioned in Open Center Canvas away from HCA Ceiling)
    # -------------------------------------------------------------------------
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS["For-Profit"], markersize=8, label="For-Profit"),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS["Non-Profit Community"], markersize=8, label="Non-Profit Community"),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=COLORS["Comprehensive Cancer Center"], markersize=8, label="Academic NCI Cancer Center"),
    ]
    ax.legend(
        handles=legend_elements,
        loc="upper center",
        bbox_to_anchor=(0.50, 0.90),
        frameon=True,
        facecolor=COLORS["Card_Background"],
        edgecolor=COLORS["Gridlines"],
        fontsize=9.0
    )

    # -------------------------------------------------------------------------
    # 2. Inset Zoom Plot: $0 to $100 Regulatory / Baseline Zone
    # -------------------------------------------------------------------------
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    ax_inset = inset_axes(
        ax,
        width="44%",
        height="38%",
        loc="lower right",
        bbox_to_anchor=(0.0, 0.08, 0.98, 0.95),
        bbox_transform=ax.transAxes,
        borderpad=1.5
    )
    
    # Render data on Inset Axis (Strictly within $0 - $100)
    for idx, row in df.iterrows():
        y = idx
        c = color_map.get(row["ownership_type"], COLORS["Text_Primary"])
        
        # Horizontal span within inset window
        clipped_max = min(row["max_coinsurance"], 100)
        ax_inset.hlines(y=y, xmin=row["min_coinsurance"], xmax=clipped_max, color=c, linewidth=5, alpha=0.35)
        ax_inset.scatter([row["min_coinsurance"]], [y], color=c, s=30)
        
        # Only render and label median point IF it falls inside the $0 - $100 zoom window
        if row["median_coinsurance"] <= 100:
            ax_inset.scatter(row["median_coinsurance"], y, color=c, s=120, edgecolors=COLORS["Text_Primary"], linewidth=1.2, zorder=5)
            ax_inset.text(
                row["median_coinsurance"] + 2.5, y,
                f"${row['median_coinsurance']:.2f}",
                va="center", ha="left", fontsize=8.5, fontweight="bold", color=c,
                clip_on=True
            )
        else:
            # For HCA, label Min to the right of its dot to avoid overlapping ASP on the left
            ax_inset.text(
                row["min_coinsurance"] + 3.0, y + 0.22,
                f"Min: ${row['min_coinsurance']:.2f}",
                va="bottom", ha="left", fontsize=8.0, fontweight="bold", color=c,
                clip_on=True
            )
            ax_inset.annotate(
                "",
                xy=(100, y), xytext=(82, y),
                arrowprops=dict(arrowstyle="->", color=c, lw=1.5)
            )
    
    # Baseline on Inset: placed to the LEFT of the dashed line to prevent overlap with HCA Min ($12.25)
    ax_inset.axvline(x=statutory_asp, color=COLORS["Benchmark_ASP"], linestyle="--", linewidth=1.5, alpha=0.85)
    ax_inset.text(
        statutory_asp - 1.5, 2.38, f"ASP: ${statutory_asp:.2f}",
        color=COLORS["Benchmark_ASP"], fontsize=8.0, fontweight="bold", va="bottom", ha="right",
        clip_on=True
    )
    
    ax_inset.set_xlim(-16, 105)
    ax_inset.set_ylim(-0.5, 2.7)
    ax_inset.set_yticks([]) # Shared context, no redundant Y labels
    ax_inset.xaxis.set_major_formatter(ticker.StrMethodFormatter("${x:,.0f}"))
    
    # Escaped LaTeX dollar signs to render literally as $0 – $100
    ax_inset.set_title("ZOOM IN: \\$0 – \\$100 Zone (Baseline Dynamics)", fontsize=9.2, fontweight="bold", pad=6)
    ax_inset.grid(axis="x", linestyle=":", alpha=0.6)
    ax_inset.set_facecolor(COLORS["Card_Background"])
    
    # -------------------------------------------------------------------------
    # 3. Titles and Annotations
    # -------------------------------------------------------------------------
    fig.suptitle(
        "Figure 5: Patient Coinsurance Toxicity — Out-of-Pocket Exposure for Keytruda",
        fontsize=13.5,
        fontweight="bold",
        x=0.08,
        y=0.96,
        ha="left"
    )
    plt.figtext(
        0.08, 0.88,
        "Commercial 20% coinsurance creates dual exposure risks: an institutional lottery across hospitals (up to 78.5x ASP)\nand an intra-hospital plan lottery where coverage disparities expose patients to up to \\$3,181 / unit.",
        fontsize=9.8,
        color=COLORS["Text_Muted"],
        ha="left"
    )
    
    plt.tight_layout(rect=[0, 0, 1, 0.85])
    
    output_path = os.path.join(OUTPUT_DIR, "figure_5.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"✓ Successfully exported Figure 5 to {output_path}")


if __name__ == "__main__":
    generate_figure_1()
    generate_figure_2()
    generate_figure_3()
    generate_figure_4()
    generate_figure_5()
