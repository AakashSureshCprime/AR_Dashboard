"""
Data model layer – responsible for loading, cleaning, and serving AR data.
"""

import io
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from utils.sharepoint_fetch import download_latest_file

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
    # Local-currency aging buckets
    _LOCAL_AGING_COLS = [
        "-0",
        "1-30",
        "31-60",
        "61-90",
        "91-180",
        "181-365",
        ">1year",
    ]
    # USD aging buckets (pandas renames duplicate headers with .1 suffix)
    _USD_AGING_COLS = [
        "-0 .1",
        "1-30 .1",
        "31-60 .1",
        "61-90 .1",
        "91-180 .1",
        "181-365 .1",
        ">1year .1",
    ]
    _MONETARY_COLS = _LOCAL_AGING_COLS + ["Total"] + _USD_AGING_COLS + ["Total in USD"]

    def __init__(self, file_path: Optional[Path] = None) -> None:
        self._file_path = file_path
        self._df: Optional[pd.DataFrame] = None
        self._last_modified: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> "ARDataModel":
        """Load and clean data from SharePoint. Returns *self* for chaining."""
        try:
            file_content, info = download_latest_file()
        except Exception as e:
            logger.exception("Failed to download SharePoint file")
            raise RuntimeError("AR data download failed") from e
        self._last_modified = info["utc_time"]
        # Try CSV first, fallback to Excel
        try:
            raw = pd.read_csv(
                io.BytesIO(file_content), dtype=str, keep_default_na=False
            )
        except Exception:
            raw = pd.read_excel(io.BytesIO(file_content))
        self._df = self._clean(raw)
        logger.info(
            "Loaded %d invoice rows from SharePoint file %s",
            len(self._df),
            info["name"],
        )
        return self

    @property
    def last_modified(self) -> Optional[str]:
        """Return last modified timestamp of the loaded SharePoint file."""
        return self._last_modified

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

        # 0. Strip whitespace from column names
        df.columns = df.columns.str.strip()

        # 1. Forward-fill Customer ID and Customer Name (grouped invoices)
        for col in ("Customer ID", "Customer Name"):
            if col in df.columns:
                df[col] = df[col].replace("", pd.NA).ffill()

        # 2. Strip whitespace from key text columns
        text_cols = [
            "Projection",
            "Review",
            "Remarks",
            "Description",
            "Entities",
            "New Org Name",
            "Engagement Practice Name",
            "Engagement Manager",
            "Mode of Submission",
            "AR Comments",
            "Allocation",
            "Region",
            "CUR",
            "PMT Method",
            "Actions",
            "Comments",
        ]
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        # 3. Parse monetary columns
        for col in self._MONETARY_COLS:
            if col in df.columns:
                df[col] = self._parse_monetary(df[col])

        # 4. Parse numeric columns
        for col in ("ROE", "AGE", "PMT Terms"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 5. Parse date columns
        for col in ("GL posting date", "Invoice date", "Due date"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce")

        return df

    @staticmethod
    def _parse_monetary(series: pd.Series) -> pd.Series:
        cleaned = series.astype(str).str.strip()

        # Detect parentheses negative
        is_negative_paren = cleaned.str.startswith("(") & cleaned.str.endswith(")")
        cleaned = cleaned.str.replace("(", "", regex=False).str.replace(
            ")", "", regex=False
        )

        # Remove commas only
        cleaned = cleaned.str.replace(",", "", regex=False)

        # Replace pure dashes or blanks with zero
        cleaned = cleaned.replace({"-": "0", "": "0"})

        result = pd.to_numeric(cleaned, errors="coerce").fillna(0.0)

        # Apply parentheses negativity
        result = result.where(~is_negative_paren, -result)

        return result
