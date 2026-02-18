"""
Data model layer – responsible for loading, cleaning, and serving AR data.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from config.settings import app_config

logger = logging.getLogger(__name__)


class ARDataModel:
    """
    Encapsulates all data-access logic for the .
Accounts Receivable dataset
    Responsibilities:
        - Load raw CSV with correct dtypes.
        - Clean / normalise monetary columns.
        - Forward-fill Customer Name for grouped invoice rows.
        - Expose a clean DataFrame for downstream consumers.
    """

    # Columns that hold monetary values with thousand-separator commas
    _MONETARY_COLS = [
        "Total", "Total in USD",
        "0", "30-Jan", "31-60", "61-90", "91-180", "181-365", ">1year",
    ]

    # USD-specific aging bucket columns
    _USD_AGING_COLS = [
        "0", "30-Jan", "31-60", "61-90", "91-180", "181-365", ">1year",
    ]

    def __init__(self, file_path: Optional[Path] = None) -> None:
        self._file_path = file_path or app_config.DATA_FILE
        self._df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> "ARDataModel":
        """Load and clean data from disk. Returns *self* for chaining."""
        raw = self._read_csv()
        self._df = self._clean(raw)
        logger.info("Loaded %d invoice rows from %s", len(self._df), self._file_path)
        return self

    @property
    def dataframe(self) -> pd.DataFrame:
        """Return cleaned DataFrame (read-only copy)."""
        if self._df is None:
            self.load()
        return self._df.copy()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_csv(self) -> pd.DataFrame:
        """Read the CSV, treating all aging-bucket columns as strings initially."""
        return pd.read_csv(
            self._file_path,
            dtype=str,
            keep_default_na=False,
        )

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all cleaning / transformation steps."""
        df = df.copy()

        # 1. Forward-fill Customer ID and Customer Name (grouped invoices)
        for col in ("Customer ID", "Customer Name"):
            df[col] = df[col].replace("", pd.NA).ffill()

        # 2. Strip whitespace from key text columns
        text_cols = [
            "Projection", "Review", "Remarks", "Description",
            "Entities", "Bus Unit Name", "Engagement Practice Name",
            "Engagement Manager", "Mode of Submission", "AR Comments",
        ]
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].str.strip()

        # 3. Parse monetary columns
        for col in self._MONETARY_COLS:
            if col in df.columns:
                df[col] = self._parse_monetary(df[col])

        # 4. Parse numeric columns
        for col in ("ROE", "AGE", "TERMS"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 5. Parse date columns
        for col in ("GL posting date", "Invoice date", "Due date"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce")

        return df

    @staticmethod
    def _parse_monetary(series: pd.Series) -> pd.Series:
        """
        Convert monetary string values like '9,452' or ' -   ' to float.

        Returns 0.0 for dashes / blanks.
        """
        cleaned = (
            series
            .str.replace(",", "", regex=False)
            .str.replace("-", "", regex=False)
            .str.strip()
            .replace("", "0")
        )
        return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)
