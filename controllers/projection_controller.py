"""
Controller layer – business logic for weekly inflow projections.

Sits between the Model (data) and the View (UI).  All aggregation,
filtering, and derived metric calculations live here.
"""

import calendar
import logging
from datetime import date

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
        self._df: pd.DataFrame | None = None

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

    def _get_all_projections(self) -> list[str]:
        """Return all unique, non-empty Projection values from the data."""
        return (
            self.df["Projection"]
            .dropna()
            .loc[lambda s: s.str.strip() != ""]
            .unique()
            .tolist()
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _select_available(df: pd.DataFrame, cols: list[str]) -> list[str]:
        """Return only columns that exist in df, preserving the requested order."""
        return [c for c in cols if c in df.columns]

    # =====================================================================
    # PATCH FILE — apply these two changes to your existing codebase
    # =====================================================================

    def get_projection_detail(self, projection_value: str) -> "pd.DataFrame":
        """
        Return invoice-level detail rows for a given Projection value.

        Columns returned:
            Customer Name | Reference | New Org Name | AR Status | Total in USD
        """
        mask = self.df["Projection"] == projection_value
        wanted = [
            "Customer Name",
            "Reference",
            "New Org Name",
            "AR Comments",
            "AR Status",
            "Total in USD",
        ]
        cols = self._select_available(self.df, wanted)
        detail = self.df.loc[mask, cols].copy()
        if "Reference" in detail.columns:
            detail["Reference"] = detail["Reference"].astype(str)
        detail = detail.sort_values("Total in USD", ascending=False).reset_index(
            drop=True
        )
        return detail

    # ------------------------------------------------------------------
    # Due wise drill-down detail
    # ------------------------------------------------------------------

    def get_due_wise_detail(self, remarks_value: str) -> pd.DataFrame:
        """
        Return invoice-level detail rows for a given Remarks value.

        Columns returned:
            Customer Name | Reference | New Org Name | AR Comments | AR Status | Total in USD
        """
        mask = self.df["_remarks_norm"] == remarks_value.strip().lower()
        wanted = [
            "Customer Name",
            "Reference",
            "New Org Name",
            "AR Comments",
            "AR Status",
            "Total in USD",
        ]
        cols = self._select_available(self.df, wanted)
        detail = self.df.loc[mask, cols].copy()
        if "Reference" in detail.columns:
            detail["Reference"] = detail["Reference"].astype(str)

        detail = detail.sort_values("Total in USD", ascending=False).reset_index(
            drop=True
        )
        return detail

    # ------------------------------------------------------------------
    # Customer wise drill-down detail
    # ------------------------------------------------------------------

    def get_customer_wise_detail(self, customer_name: str) -> pd.DataFrame:
        """
        Return invoice-level detail rows for a given Customer Name.

        Columns returned:
            Customer Name | Reference | New Org Name | AR Comments |
            AR Status | Remarks | Total in USD
        """
        mask = self.df["_customer_name_norm"] == customer_name.strip().lower()
        wanted = [
            "Customer Name",
            "Reference",
            "New Org Name",
            "AR Comments",
            "AR Status",
            "Remarks",
            "Total in USD",
        ]
        cols = self._select_available(self.df, wanted)
        detail = self.df.loc[mask, cols].copy()
        if "Reference" in detail.columns:
            detail["Reference"] = detail["Reference"].astype(str)

        detail = detail.sort_values("Total in USD", ascending=False).reset_index(
            drop=True
        )
        return detail

        # ------------------------------------------------------------------

    # Business wise drill-down detail
    # ------------------------------------------------------------------

    def get_business_wise_detail(self, org_name: str) -> pd.DataFrame:
        """
        Return invoice-level detail rows for a given New Org Name.

        Columns returned:
            Customer Name | Reference | New Org Name | AR Comments |
            AR Status | Remarks | Total in USD
        """
        mask = self.df["_new_org_name_norm"] == org_name.strip().lower()
        wanted = [
            "Customer Name",
            "Reference",
            "New Org Name",
            "AR Comments",
            "AR Status",
            "Remarks",
            "Total in USD",
        ]
        cols = self._select_available(self.df, wanted)
        detail = self.df.loc[mask, cols].copy()
        if "Reference" in detail.columns:
            detail["Reference"] = detail["Reference"].astype(str)

        detail = detail.sort_values("Total in USD", ascending=False).reset_index(
            drop=True
        )
        return detail

    # ------------------------------------------------------------------
    # Allocation wise drill-down detail (by allocation + remark)
    # ------------------------------------------------------------------

    def get_allocation_remark_detail(
        self, allocation_value: str, remarks_value: str
    ) -> pd.DataFrame:
        """
        Return invoice-level detail rows for a given Allocation AND Remarks.

        E.g., clicking the "Overdue" bar for "Nithya" returns only
        Nithya's overdue invoices.
        """
        mask = (self.df["_allocation_norm"] == allocation_value.strip().lower()) & (
            self.df["_remarks_norm"] == remarks_value.strip().lower()
        )
        wanted = [
            "Customer Name",
            "Reference",
            "New Org Name",
            "Allocation",
            "AR Comments",
            "AR Status",
            "Remarks",
            "Total in USD",
        ]
        cols = self._select_available(self.df, wanted)
        detail = self.df.loc[mask, cols].copy()
        if "Reference" in detail.columns:
            detail["Reference"] = detail["Reference"].astype(str)
        detail = detail.sort_values("Total in USD", ascending=False).reset_index(
            drop=True
        )
        return detail

    # ------------------------------------------------------------------
    # Entities wise drill-down detail (by entity + remark)
    # ------------------------------------------------------------------

    def get_entities_remark_detail(
        self, entity_value: str, remarks_value: str
    ) -> pd.DataFrame:
        """
        Return invoice-level detail rows for a given Entity AND Remarks.

        E.g., clicking the "Overdue" bar for "UST India" returns only
        UST India's overdue invoices.
        """
        mask = (self.df["_entities_norm"] == entity_value.strip().lower()) & (
            self.df["_remarks_norm"] == remarks_value.strip().lower()
        )
        wanted = [
            "Customer Name",
            "Reference",
            "New Org Name",
            "Entities",
            "Allocation",
            "AR Comments",
            "AR Status",
            "Remarks",
            "Total in USD",
        ]
        cols = self._select_available(self.df, wanted)
        detail = self.df.loc[mask, cols].copy()
        if "Reference" in detail.columns:
            detail["Reference"] = detail["Reference"].astype(str)
        detail = detail.sort_values("Total in USD", ascending=False).reset_index(
            drop=True
        )
        return detail

    # ------------------------------------------------------------------
    # AR Status wise outstanding
    # ------------------------------------------------------------------

    def get_ar_status_wise_outstanding(self) -> pd.DataFrame:
        """
        Aggregate *Total in USD* by AR Status and Remarks,
        with a total per AR Status.

        Returns a DataFrame with columns:
            AR Status | Current Due | Future Due | Overdue | Total Outstanding (USD)
        sorted by Total descending.
        """
        # Filter to only valid remarks using pre-normalized column
        valid_remarks = [
            "current due",
            "future due",
            "overdue",
            "credit memo",
            "unapplied",
            "legal",
        ]
        mask = self.df["_remarks_norm"].isin(valid_remarks)

        # Exclude empty/null AR Status
        mask &= self.df["AR Status"].notna() & (self.df["AR Status"].str.strip() != "")

        filtered_df = self.df.loc[mask].copy()

        pivot = (
            filtered_df.groupby(["AR Status", "Remarks"], as_index=False)
            .agg(**{"Amount": ("Total in USD", "sum")})
            .pivot_table(
                index="AR Status",
                columns="Remarks",
                values="Amount",
                aggfunc="sum",
                fill_value=0.0,
            )
        )

        # Ensure canonical columns exist
        for col in ("Current Due", "Future Due", "Overdue"):
            if col not in pivot.columns:
                pivot[col] = 0.0

        remark_cols = [c for c in pivot.columns if c != "Total Outstanding (USD)"]
        pivot["Total Outstanding (USD)"] = pivot[remark_cols].sum(axis=1)
        pivot = (
            pivot.reset_index()
            .sort_values("Total Outstanding (USD)", ascending=False)
            .reset_index(drop=True)
        )

        return pivot[["AR Status"] + remark_cols + ["Total Outstanding (USD)"]]

    def get_ar_status_remark_detail(
        self, ar_status: str, remarks_value: str
    ) -> pd.DataFrame:
        """
        Return invoice-level detail rows for a given AR Status AND Remarks.

        E.g., clicking the "Overdue" bar for "In Progress" returns only
        In Progress overdue invoices.
        """
        mask = (self.df["_ar_status_norm"] == ar_status.strip().lower()) & (
            self.df["_remarks_norm"] == remarks_value.strip().lower()
        )
        wanted = [
            "Customer Name",
            "Reference",
            "New Org Name",
            "AR Comments",
            "Remarks",
            "Projection",
            "Total in USD",
        ]
        cols = self._select_available(self.df, wanted)
        detail = self.df.loc[mask, cols].copy()
        if "Reference" in detail.columns:
            detail["Reference"] = detail["Reference"].astype(str)
        detail = detail.sort_values("Total in USD", ascending=False).reset_index(
            drop=True
        )
        return detail

    def _split_inflow_dispute(self) -> tuple[list[str], list[str]]:
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
    def _sort_key(projection: str) -> tuple:
        """
        Build a sort key that orders projection labels chronologically:

        1. Month rank  (Feb=2, Mar=3, …  fallback 99 for generic labels)
        2. Week rank   ('current'=1, '1st'=1, '2nd'=2, '3rd'=3,
                        '4th'=4, 'Last'=5,  fallback 99)
        3. Original string (alphabetical tiebreak)
        """
        MONTH_MAP = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        WEEK_MAP = {
            "current": 1,
            "1st": 2,
            "2nd": 3,
            "3rd": 4,
            "4th": 5,
            "last": 6,
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
            month_rank = 98  # always after explicit months

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
        grouped = self.df.groupby("Projection", as_index=False).agg(
            **{
                "Total Inflow (USD)": ("Total in USD", "sum"),
                # Use group size for robustness when 'Reference' column is missing
                "Invoice Count": ("Projection", "size"),
            }
        )

        # Apply dynamic sort order (inflow first, then dispute, both sorted)
        inflow_cats, dispute_cats = self._split_inflow_dispute()
        ordered = sorted(inflow_cats, key=self._sort_key) + sorted(dispute_cats)
        order_map = {v: i for i, v in enumerate(ordered)}
        grouped["_sort"] = grouped["Projection"].map(order_map).fillna(len(ordered))
        grouped = (
            grouped.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)
        )

        # Percentage of grand total
        grand_total = grouped["Total Inflow (USD)"].sum()
        grouped["% of Total"] = (
            (grouped["Total Inflow (USD)"] / grand_total * 100).round(2)
            if grand_total > 0
            else 0.0
        )

        return grouped

    def get_expected_inflow_total(self) -> float:
        """Sum of inflow categories for the CURRENT calendar month only."""

        inflow_cats, _ = self._split_inflow_dispute()

        current_month_abbr = date.today().strftime("%b").lower()

        current_month_inflow = [
            proj for proj in inflow_cats if current_month_abbr in proj.lower()
        ]

        if not current_month_inflow:
            return 0.0

        mask = self.df["Projection"].isin(current_month_inflow)
        return float(self.df.loc[mask, "Total in USD"].sum())

    def get_next_month_inflow_total(self) -> float:

        inflow_cats, _ = self._split_inflow_dispute()

        today = date.today()
        next_month_num = today.month % 12 + 1
        next_month_abbr = calendar.month_abbr[next_month_num].lower()
        next_month_first_week = [
            proj
            for proj in inflow_cats
            if next_month_abbr in proj.lower()
            and "1st" in proj.lower()
            and "next month" not in proj.lower()  # exclude any "Next Month" labels
        ]

        if not next_month_first_week:
            return 0.0

        mask = self.df["Projection"].isin(next_month_first_week)
        return float(self.df.loc[mask, "Total in USD"].sum())

    def get_next_month_name(self) -> str:
        """Return the name of the next month."""
        today = date.today()
        next_month_num = today.month % 12 + 1
        return calendar.month_name[next_month_num]

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
        # Filter using pre-normalized column
        valid_remarks = [
            "future due",
            "current due",
            "overdue",
            "credit memo",
            "unapplied",
        ]
        mask = self.df["_remarks_norm"].isin(valid_remarks) & (
            self.df["_remarks_norm"] != "internal"
        )
        filtered_df = self.df.loc[mask]

        grouped = (
            filtered_df.groupby("Remarks", as_index=False)
            .agg(
                **{
                    "Total Outstanding (USD)": ("Total in USD", "sum"),
                    "Invoice Count": ("Remarks", "size"),
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

    def get_credit_memo_total(self) -> float:
        """Sum of invoices where Remarks is 'Credit Memo' (case-insensitive)."""
        mask = self.df["_remarks_norm"] == "credit memo"
        return float(self.df.loc[mask, "Total in USD"].sum())

    def get_unapplied_total(self) -> float:
        """Sum of invoices where Remarks is 'Unapplied' (case-insensitive)."""
        mask = self.df["_remarks_norm"] == "unapplied"
        return float(self.df.loc[mask, "Total in USD"].sum())

    def get_current_due_total(self) -> float:
        """Sum of invoices where Remarks is 'Current Due' (case-insensitive)."""
        mask = self.df["_remarks_norm"] == "current due"
        return float(self.df.loc[mask, "Total in USD"].sum())

    def get_future_due_total(self) -> float:
        """Sum of invoices where Remarks is 'Future Due' (case-insensitive)."""
        mask = self.df["_remarks_norm"] == "future due"
        return float(self.df.loc[mask, "Total in USD"].sum())

    def get_overdue_total(self) -> float:
        """Sum of invoices where Remarks is 'Overdue' (case-insensitive)."""
        mask = self.df["_remarks_norm"] == "overdue"
        return float(self.df.loc[mask, "Total in USD"].sum())

    def get_legal_total(self) -> float:
        """Sum of invoices where Remarks is 'Legal' (case-insensitive)."""
        mask = self.df["_remarks_norm"] == "legal"
        return float(self.df.loc[mask, "Total in USD"].sum())

    def get_all_kpi_metrics(self) -> dict:
        """
        Compute all KPI metrics in a single DataFrame pass for better performance.

        Returns a dict with keys:
            grand_total, expected_inflow, next_month_1st_week, dispute_total,
            invoice_count, credit_memo_total, current_due, future_due,
            unapplied_total, overdue_total, legal_total, next_month_name
        """
        df = self.df
        remarks_norm = df["_remarks_norm"]
        total_usd = df["Total in USD"]

        # Build all masks at once using pre-normalized column
        results = {
            "grand_total": float(total_usd.sum()),
            "invoice_count": len(df),
            "credit_memo_total": float(total_usd[remarks_norm == "credit memo"].sum()),
            "unapplied_total": float(total_usd[remarks_norm == "unapplied"].sum()),
            "current_due": float(total_usd[remarks_norm == "current due"].sum()),
            "future_due": float(total_usd[remarks_norm == "future due"].sum()),
            "overdue_total": float(total_usd[remarks_norm == "overdue"].sum()),
            "legal_total": float(total_usd[remarks_norm == "legal"].sum()),
            "next_month_name": self.get_next_month_name(),
        }

        # Compute projection-based metrics
        inflow_cats, dispute_cats = self._split_inflow_dispute()

        # Expected inflow (current month)
        current_month_abbr = date.today().strftime("%b").lower()
        current_month_inflow = [
            proj for proj in inflow_cats if current_month_abbr in proj.lower()
        ]
        if current_month_inflow:
            mask = df["Projection"].isin(current_month_inflow)
            results["expected_inflow"] = float(total_usd[mask].sum())
        else:
            results["expected_inflow"] = 0.0

        # Next month 1st week
        next_month_num = date.today().month % 12 + 1
        next_month_abbr = calendar.month_abbr[next_month_num].lower()
        next_month_first_week = [
            proj
            for proj in inflow_cats
            if next_month_abbr in proj.lower()
            and "1st" in proj.lower()
            and "next month" not in proj.lower()
        ]
        if next_month_first_week:
            mask = df["Projection"].isin(next_month_first_week)
            results["next_month_1st_week"] = float(total_usd[mask].sum())
        else:
            results["next_month_1st_week"] = 0.0

        # Dispute total
        if dispute_cats:
            mask = df["Projection"].isin(dispute_cats)
            results["dispute_total"] = float(total_usd[mask].sum())
        else:
            results["dispute_total"] = 0.0

        return results

    # ------------------------------------------------------------------
    # Customer wise outstanding
    # ------------------------------------------------------------------

    def get_customer_wise_outstanding(self) -> pd.DataFrame:
        """
        Aggregate *Total in USD* by Customer Name and Remarks,
        with a total per customer.

        Returns a DataFrame with columns:
            Customer Name | <Remark1> | <Remark2> | … | Total Outstanding (USD)
        sorted by Total descending.
        """
        # Filter out internal using pre-normalized column
        filtered_df = self.df[self.df["_remarks_norm"] != "internal"]
        pivot = (
            filtered_df.groupby(["Customer Name", "Remarks"], as_index=False)
            .agg(**{"Amount": ("Total in USD", "sum")})
            .pivot_table(
                index="Customer Name",
                columns="Remarks",
                values="Amount",
                aggfunc="sum",
                fill_value=0.0,
            )
        )

        # Ensure canonical columns exist
        for col in ("Current Due", "Overdue"):
            if col not in pivot.columns:
                pivot[col] = 0.0

        remark_cols = [c for c in pivot.columns if c != "Total Outstanding (USD)"]
        pivot["Total Outstanding (USD)"] = pivot[remark_cols].sum(axis=1)
        pivot = (
            pivot.reset_index()
            .sort_values("Total Outstanding (USD)", ascending=False)
            .reset_index(drop=True)
        )

        return pivot[["Customer Name"] + remark_cols + ["Total Outstanding (USD)"]]

    # ------------------------------------------------------------------
    # Business unit wise outstanding
    # ------------------------------------------------------------------

    def get_business_wise_outstanding(self) -> pd.DataFrame:
        """
        Aggregate *Total in USD* by New Org Name and Remarks,
        with a total per business unit. Excludes 'Internal' business unit.

        Returns a DataFrame with columns:
            New Org Name | <Remark1> | … | Total Outstanding (USD)
        sorted by Total descending.
        """
        # Filter out "Internal" business unit using pre-normalized column
        filtered_df = self.df[self.df["_new_org_name_norm"] != "internal"]

        pivot = (
            filtered_df.groupby(["New Org Name", "Remarks"], as_index=False)
            .agg(**{"Amount": ("Total in USD", "sum")})
            .pivot_table(
                index="New Org Name",
                columns="Remarks",
                values="Amount",
                aggfunc="sum",
                fill_value=0.0,
            )
        )

        for col in ("Current Due", "Overdue"):
            if col not in pivot.columns:
                pivot[col] = 0.0

        remark_cols = [c for c in pivot.columns if c != "Total Outstanding (USD)"]
        pivot["Total Outstanding (USD)"] = pivot[remark_cols].sum(axis=1)
        pivot = (
            pivot.reset_index()
            .sort_values("Total Outstanding (USD)", ascending=False)
            .reset_index(drop=True)
        )

        return pivot[["New Org Name"] + remark_cols + ["Total Outstanding (USD)"]]

    # ------------------------------------------------------------------
    # Allocation wise outstanding
    # ------------------------------------------------------------------

    def get_allocation_wise_outstanding(self) -> pd.DataFrame:
        """
        Aggregate *Total in USD* by Allocation and Remarks,
        with a total per allocation.

        Returns a DataFrame with columns:
            Allocation | <Remark1> | … | Total Outstanding (USD)
        sorted by Total descending.
        """
        # Filter out internal using pre-normalized column
        filtered_df = self.df[self.df["_remarks_norm"] != "internal"]
        pivot = (
            filtered_df.groupby(["Allocation", "Remarks"], as_index=False)
            .agg(**{"Amount": ("Total in USD", "sum")})
            .pivot_table(
                index="Allocation",
                columns="Remarks",
                values="Amount",
                aggfunc="sum",
                fill_value=0.0,
            )
        )

        for col in ("Current Due", "Overdue"):
            if col not in pivot.columns:
                pivot[col] = 0.0

        remark_cols = [c for c in pivot.columns if c != "Total Outstanding (USD)"]
        pivot["Total Outstanding (USD)"] = pivot[remark_cols].sum(axis=1)
        pivot = (
            pivot.reset_index()
            .sort_values("Total Outstanding (USD)", ascending=False)
            .reset_index(drop=True)
        )

        return pivot[["Allocation"] + remark_cols + ["Total Outstanding (USD)"]]

    # ------------------------------------------------------------------
    # Entities wise outstanding
    # ------------------------------------------------------------------

    def get_entities_wise_outstanding(self) -> pd.DataFrame:
        """
        Aggregate *Total in USD* by Entities and Remarks,
        with a total per entity.

        Returns a DataFrame with columns:
            Entities | <Remark1> | … | Total Outstanding (USD)
        sorted by Total descending.
        """
        pivot = (
            self.df.groupby(["Entities", "Remarks"], as_index=False)
            .agg(**{"Amount": ("Total in USD", "sum")})
            .pivot_table(
                index="Entities",
                columns="Remarks",
                values="Amount",
                aggfunc="sum",
                fill_value=0.0,
            )
        )

        for col in ("Current Due", "Overdue"):
            if col not in pivot.columns:
                pivot[col] = 0.0

        remark_cols = [c for c in pivot.columns if c != "Total Outstanding (USD)"]
        pivot["Total Outstanding (USD)"] = pivot[remark_cols].sum(axis=1)
        pivot = (
            pivot.reset_index()
            .sort_values("Total Outstanding (USD)", ascending=False)
            .reset_index(drop=True)
        )

        return pivot[["Entities"] + remark_cols + ["Total Outstanding (USD)"]]
