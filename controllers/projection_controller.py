"""
Controller layer – business logic for weekly inflow projections.

Sits between the Model (data) and the View (UI).  All aggregation,
filtering, and derived metric calculations live here.
"""

import logging
import re
from typing import List, Optional, Tuple

import pandas as pd

from config.settings import projection_config
from models.ar_model import ARDataModel

logger = logging.getLogger(__name__)


class ProjectionController:
    """
    Computes weekly inflow projections and supporting analytics
    from the cleaned AR data.
    """

    def __init__(self, model: ARDataModel) -> None:
        self._model = model
        self._df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            self._df = self._model.dataframe
        return self._df

    def refresh(self) -> None:
        """Force re-read from model (e.g. after file change)."""
        self._df = self._model.load().dataframe

    # ------------------------------------------------------------------
    # Dynamic projection categorisation
    # ------------------------------------------------------------------

    def _get_all_projections(self) -> List[str]:
        """Return all unique, non-empty Projection values from the data."""
        return (
            self.df["Projection"]
            .dropna()
            .loc[lambda s: s.str.strip() != ""]
            .unique()
            .tolist()
        )

    def _split_inflow_dispute(self) -> Tuple[List[str], List[str]]:
        """
        Dynamically partition projection values into *inflow* and
        *non-inflow (dispute)* buckets using the configured keyword.
        """
        keyword = projection_config.DISPUTE_KEYWORD.lower()
        inflow, dispute = [], []
        for proj in self._get_all_projections():
            if keyword in proj.lower():
                dispute.append(proj)
            else:
                inflow.append(proj)
        return inflow, dispute

    @staticmethod
    def _sort_key(projection: str) -> Tuple:
        """
        Build a sort key that orders projection labels chronologically:

        1. Month rank  (Feb=2, Mar=3, …  fallback 99 for generic labels)
        2. Week rank   ('current'=1, '1st'=1, '2nd'=2, '3rd'=3,
                        '4th'=4, 'Last'=5,  fallback 99)
        3. Original string (alphabetical tiebreak)
        """
        MONTH_MAP = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        WEEK_MAP = {
            "current": 1, "1st": 2, "2nd": 3, "3rd": 4, "4th": 5, "last": 6,
        }

        lower = projection.lower()

        # --- month rank ---
        month_rank = 99
        for abbr, rank in MONTH_MAP.items():
            if abbr in lower:
                month_rank = rank
                break

        # "Next Month" → one month after any explicit month found so far
        if "next month" in lower:
            month_rank = 98        # always after explicit months

        # --- week rank ---
        week_rank = 99
        for token, rank in WEEK_MAP.items():
            if token in lower:
                week_rank = rank
                break

        return (month_rank, week_rank, lower)

    # ------------------------------------------------------------------
    # Weekly inflow projections
    # ------------------------------------------------------------------

    def get_weekly_inflow_summary(self) -> pd.DataFrame:
        """
        Aggregate *Total in USD* by Projection week.

        Returns a DataFrame with columns:
            Projection  |  Total Inflow (USD)  |  Invoice Count  |  % of Total
        ordered by the configured WEEK_ORDER.
        """
        grouped = (
            self.df
            .groupby("Projection", as_index=False)
            .agg(
                **{
                    "Total Inflow (USD)": ("Total in USD", "sum"),
                    "Invoice Count": ("Invoice", "count"),
                }
            )
        )

        # Apply dynamic sort order (inflow first, then dispute, both sorted)
        inflow_cats, dispute_cats = self._split_inflow_dispute()
        ordered = sorted(inflow_cats, key=self._sort_key) + sorted(dispute_cats)
        order_map = {v: i for i, v in enumerate(ordered)}
        grouped["_sort"] = grouped["Projection"].map(order_map).fillna(len(ordered))
        grouped = grouped.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)

        # Percentage of grand total
        grand_total = grouped["Total Inflow (USD)"].sum()
        grouped["% of Total"] = (
            (grouped["Total Inflow (USD)"] / grand_total * 100).round(2)
            if grand_total > 0
            else 0.0
        )

        return grouped

    def get_expected_inflow_total(self) -> float:
        """Sum of inflow categories only (excludes dispute projections)."""
        inflow_cats, _ = self._split_inflow_dispute()
        mask = self.df["Projection"].isin(inflow_cats)
        return float(self.df.loc[mask, "Total in USD"].sum())

    def get_dispute_total(self) -> float:
        """Sum of invoices whose Projection contains the dispute keyword."""
        _, dispute_cats = self._split_inflow_dispute()
        mask = self.df["Projection"].isin(dispute_cats)
        return float(self.df.loc[mask, "Total in USD"].sum())

    def get_grand_total(self) -> float:
        """Grand total across all projections."""
        return float(self.df["Total in USD"].sum())

    # ------------------------------------------------------------------
    # Due wise outstanding
    # ------------------------------------------------------------------

    def get_due_wise_outstanding(self) -> pd.DataFrame:
        """
        Aggregate *Total in USD* by Remarks (Current Due / Overdue).

        Returns a DataFrame with columns:
            Remarks  |  Total Outstanding (USD)  |  Invoice Count  |  % of Total
        """
        grouped = (
            self.df
            .groupby("Remarks", as_index=False)
            .agg(
                **{
                    "Total Outstanding (USD)": ("Total in USD", "sum"),
                    "Invoice Count": ("Invoice", "count"),
                }
            )
            .sort_values("Total Outstanding (USD)", ascending=False)
            .reset_index(drop=True)
        )

        grand_total = grouped["Total Outstanding (USD)"].sum()
        grouped["% of Total"] = (
            (grouped["Total Outstanding (USD)"] / grand_total * 100).round(2)
            if grand_total > 0
            else 0.0
        )

        return grouped

    # ------------------------------------------------------------------
    # Customer wise outstanding
    # ------------------------------------------------------------------

    def get_customer_wise_outstanding(self) -> pd.DataFrame:
        """
        Aggregate *Total in USD* by Customer Name and Remarks
        (Current Due / Overdue), with a total per customer.

        Returns a DataFrame with columns:
            Customer Name | Current Due | Overdue | Total Outstanding (USD)
        sorted by Total descending.
        """
        pivot = (
            self.df
            .groupby(["Customer Name", "Remarks"], as_index=False)
            .agg(**{"Amount": ("Total in USD", "sum")})
            .pivot_table(
                index="Customer Name",
                columns="Remarks",
                values="Amount",
                aggfunc="sum",
                fill_value=0.0,
            )
        )

        # Ensure both columns exist even if data has only one type
        for col in ("Current Due", "Overdue"):
            if col not in pivot.columns:
                pivot[col] = 0.0

        pivot["Total Outstanding (USD)"] = pivot["Current Due"] + pivot["Overdue"]
        pivot = (
            pivot
            .reset_index()
            .sort_values("Total Outstanding (USD)", ascending=False)
            .reset_index(drop=True)
        )

        return pivot[["Customer Name", "Current Due", "Overdue", "Total Outstanding (USD)"]]

    # ------------------------------------------------------------------
    # Business unit wise outstanding
    # ------------------------------------------------------------------

    def get_business_wise_outstanding(self) -> pd.DataFrame:
        """
        Aggregate *Total in USD* by Bus Unit Name and Remarks
        (Current Due / Overdue), with a total per business unit.

        Returns a DataFrame with columns:
            Bus Unit Name | Current Due | Overdue | Total Outstanding (USD)
        sorted by Total descending.
        """
        pivot = (
            self.df
            .groupby(["Bus Unit Name", "Remarks"], as_index=False)
            .agg(**{"Amount": ("Total in USD", "sum")})
            .pivot_table(
                index="Bus Unit Name",
                columns="Remarks",
                values="Amount",
                aggfunc="sum",
                fill_value=0.0,
            )
        )

        for col in ("Current Due", "Overdue"):
            if col not in pivot.columns:
                pivot[col] = 0.0

        pivot["Total Outstanding (USD)"] = pivot["Current Due"] + pivot["Overdue"]
        pivot = (
            pivot
            .reset_index()
            .sort_values("Total Outstanding (USD)", ascending=False)
            .reset_index(drop=True)
        )

        return pivot[["Bus Unit Name", "Current Due", "Overdue", "Total Outstanding (USD)"]]
