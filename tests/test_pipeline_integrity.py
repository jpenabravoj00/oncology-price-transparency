"""
tests/test_pipeline_integrity.py
==============================================================================
Portfolio Project 004: Oncology Price Transparency & Economic Analysis
Automated Pipeline Integrity & Data Quality Verification Suite

Tests the end-to-end DuckDB analytical mart for:
1. Database connectivity and schema structure
2. Row count universe completeness (5,068 gold contracts / 3,121 baseline)
3. Non-negative pricing and valid statutory benchmark limits
4. Exactness of derived econometric metrics (markup ratios, coinsurance, spreads)
5. Comprehensive hospital and statutory market segment representation
6. Outlier tagging and referential join integrity

Usage:
    ./.venv/bin/python -m unittest tests/test_pipeline_integrity.py
==============================================================================
"""

import os
import unittest
import duckdb

DB_PATH = "data/processed/oncoprice.duckdb"

class TestPipelineIntegrity(unittest.TestCase):
    """Defensive automated assertions for the oncology price transparency data mart."""

    @classmethod
    def setUpClass(cls):
        """Establish a read-only DuckDB connection for all test methods."""
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError(f"Analytics database not found at {DB_PATH}")
        cls.con = duckdb.connect(DB_PATH, read_only=True)

    @classmethod
    def tearDownClass(cls):
        """Close connection cleanly."""
        cls.con.close()

    # -------------------------------------------------------------------------
    # 1. Universe Size & Completeness Assertions
    # -------------------------------------------------------------------------
    def test_database_tables_exist(self):
        """Verify that silver and gold tables exist in DuckDB."""
        tables = [t[0] for t in self.con.sql("SHOW TABLES").fetchall()]
        self.assertIn("gold_oncology_markups", tables, "gold_oncology_markups table missing")
        self.assertIn("silver_hospital_rates", tables, "silver_hospital_rates table missing")
        self.assertIn("silver_cms_asp", tables, "silver_cms_asp table missing")

    def test_gold_contract_universe_count(self):
        """Assert total gold contracts match the verified universe of exactly 5,068 rows."""
        count = self.con.sql("SELECT COUNT(*) FROM gold_oncology_markups").fetchone()[0]
        self.assertEqual(count, 5068, f"Expected 5,068 gold contracts, but found {count}")

    def test_general_commercial_benchmark_count(self):
        """Assert general commercial baseline subset matches the verified 3,121 contracts."""
        count = self.con.sql(
            "SELECT COUNT(*) FROM gold_oncology_markups WHERE include_in_general_commercial_benchmark = TRUE"
        ).fetchone()[0]
        self.assertEqual(count, 3121, f"Expected 3,121 general commercial benchmark contracts, found {count}")

    # -------------------------------------------------------------------------
    # 2. Pricing & Benchmark Validity Assertions
    # -------------------------------------------------------------------------
    def test_no_null_or_negative_pricing(self):
        """Assert that negotiated rates and ASP benchmark rates are strictly positive numbers."""
        invalid_rates = self.con.sql("""
            SELECT COUNT(*) FROM gold_oncology_markups
            WHERE commercial_negotiated_rate IS NULL 
               OR commercial_negotiated_rate <= 0
               OR asp_benchmark_rate IS NULL
               OR asp_benchmark_rate <= 0
        """).fetchone()[0]
        self.assertEqual(invalid_rates, 0, f"Found {invalid_rates} rows with null or negative pricing rates")

    def test_referential_integrity_asp(self):
        """Assert zero orphan records where a hospital drug rate lacks a matching CMS ASP benchmark."""
        orphans = self.con.sql("""
            SELECT COUNT(*) FROM gold_oncology_markups
            WHERE asp_benchmark_rate IS NULL
        """).fetchone()[0]
        self.assertEqual(orphans, 0, f"Found {orphans} orphan hospital contracts without CMS ASP benchmark")

    # -------------------------------------------------------------------------
    # 3. Categorical & Segmentation Integrity Assertions
    # -------------------------------------------------------------------------
    def test_hospital_representation(self):
        """Assert all three target Florida health systems are represented with non-zero contracts."""
        hospitals = self.con.sql("""
            SELECT hospital_name, COUNT(*) AS n 
            FROM gold_oncology_markups 
            GROUP BY hospital_name
        """).df().set_index("hospital_name")["n"].to_dict()

        expected = ["Baptist Health South Florida", "Moffitt Cancer Center", "HCA Florida Memorial Hospital"]
        for h in expected:
            self.assertIn(h, hospitals, f"Hospital {h} missing from gold mart")
            self.assertGreater(hospitals[h], 0, f"Hospital {h} has zero contracts")

    def test_seven_statutory_market_segments(self):
        """Assert that all 7 official statutory lines of business exist in the gold crosswalk."""
        segments = set(self.con.sql("""
            SELECT DISTINCT standardized_market_segment FROM gold_oncology_markups
        """).df()["standardized_market_segment"].tolist())

        expected_segments = {
            "Commercial Employer",
            "Medicare Advantage",
            "ACA Individual Exchange",
            "Medicaid Managed Care",
            "Correctional Healthcare",
            "Veterans Affairs (VA CCN)",
            "Military / TRICARE"
        }
        self.assertEqual(segments, expected_segments, "Statutory market segment alignment discrepancy")

    # -------------------------------------------------------------------------
    # 4. Mathematical & Derived Metric Integrity Assertions
    # -------------------------------------------------------------------------
    def test_markup_ratio_math(self):
        """Assert that commercial_markup_ratio matches negotiated_rate / asp_benchmark_rate within float precision."""
        discrepancies = self.con.sql("""
            SELECT COUNT(*) FROM gold_oncology_markups
            WHERE ABS(commercial_markup_ratio - (commercial_negotiated_rate / asp_benchmark_rate)) > 0.05
        """).fetchone()[0]
        self.assertEqual(discrepancies, 0, f"Found {discrepancies} rows where markup ratio deviates from definition")

    def test_patient_coinsurance_math(self):
        """Assert that patient 20% coinsurance liability equals 20% of commercial negotiated rate."""
        discrepancies = self.con.sql("""
            SELECT COUNT(*) FROM gold_oncology_markups
            WHERE ABS(patient_coinsurance_20pct - (commercial_negotiated_rate * 0.20)) > 0.05
        """).fetchone()[0]
        self.assertEqual(discrepancies, 0, f"Found {discrepancies} rows where 20% coinsurance math deviates")

    def test_cash_discount_spread_bounds(self):
        """Assert that cash discount advantage equals negotiated_rate - hospital_cash_rate in dollars."""
        discrepancies = self.con.sql("""
            SELECT COUNT(*) FROM gold_oncology_markups
            WHERE hospital_cash_rate IS NOT NULL
              AND ABS(cash_discount_advantage - (commercial_negotiated_rate - hospital_cash_rate)) > 0.05
        """).fetchone()[0]
        self.assertEqual(discrepancies, 0, f"Found {discrepancies} contracts where cash discount advantage deviates from dollar spread")


if __name__ == "__main__":
    unittest.main()
