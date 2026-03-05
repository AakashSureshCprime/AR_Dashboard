"""
Complete test suite for controllers/projection_controller.py

Key corrections vs. the old test file:
- get_expected_inflow_total() filters to the *current calendar month* only,
  so tests mock `datetime.date.today` rather than asserting a hard-coded total.
- get_grand_total() and get_dispute_total() are tested against the fixture
  data values that the source actually produces.
- New methods added in the source (get_current_due_total, get_future_due_total,
  get_overdue_total, get_legal_total, get_next_month_inflow_total,
  get_next_month_name) are all covered.
- _sort_key week ordering is corrected: 'current'=1 maps to sort rank 1 which
  is *less than* '1st'=2, so "Current week" < "1st week".
"""

from datetime import date
from unittest.mock import MagicMock, PropertyMock, patch

import pandas as pd
import pytest

from controllers.projection_controller import ProjectionController

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_controller(df: pd.DataFrame) -> ProjectionController:
    """Wrap a DataFrame in a minimal DummyModel and return a controller."""

    # Add normalized columns that the production code expects
    # These are normally added by ARDataModel._clean()
    df = df.copy()
    if "Remarks" in df.columns:
        df["_remarks_norm"] = df["Remarks"].str.strip().str.lower()
    if "AR Status" in df.columns:
        df["_ar_status_norm"] = df["AR Status"].str.strip().str.lower()
    if "Allocation" in df.columns:
        df["_allocation_norm"] = df["Allocation"].str.strip().str.lower()
    if "Entities" in df.columns:
        df["_entities_norm"] = df["Entities"].str.strip().str.lower()
    if "Customer Name" in df.columns:
        df["_customer_name_norm"] = df["Customer Name"].str.strip().str.lower()
    if "New Org Name" in df.columns:
        df["_new_org_name_norm"] = df["New Org Name"].str.strip().str.lower()
    if "Projection" in df.columns:
        df["_projection_norm"] = df["Projection"].str.strip().str.lower()

    class _DummyModel:
        @property
        def dataframe(self):
            return df

    return ProjectionController(_DummyModel())


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_df():
    """Ten-column standard fixture used by most tests."""
    return pd.DataFrame(
        {
            "Projection": [
                "Feb 3rd week",
                "Feb 3rd week",
                "Dispute - Legal",
                "Mar 1st week",
                "Current week",
                "Feb Last week",
            ],
            "Total in USD": [1000.0, 2000.0, 500.0, 1500.0, 800.0, 700.0],
            "Reference": ["INV1", "INV2", "INV3", "INV4", "INV5", "INV6"],
            "Remarks": [
                "Current Due",
                "Overdue",
                "Credit Memo",
                "Future Due",
                "Unapplied",
                "Legal",
            ],
            "Customer Name": [
                "Customer A",
                "Customer A",
                "Customer B",
                "Customer C",
                "Customer D",
                "Customer E",
            ],
            "New Org Name": ["BU1", "BU1", "BU2", "Internal", "BU3", "BU4"],
            "Allocation": [
                "Nithya",
                "Unallocated",
                "Nithya",
                "Allocated",
                "Nithya",
                "John",
            ],
            "Entities": [
                "UST India",
                "UST India",
                "UST Corp",
                "UST India",
                "UST Corp",
                "UST India",
            ],
            "AR Status": [
                "In Progress",
                "Pending",
                "In Progress",
                "Resolved",
                "",
                "In Progress",
            ],
            "AR Comments": [
                "Comment 1",
                "Comment 2",
                "Comment 3",
                "Comment 4",
                "Comment 5",
                "Comment 6",
            ],
        }
    )


@pytest.fixture()
def controller(sample_df):
    return _make_controller(sample_df)


@pytest.fixture()
def empty_df():
    return pd.DataFrame(
        columns=[
            "Projection",
            "Total in USD",
            "Reference",
            "Remarks",
            "Customer Name",
            "New Org Name",
            "Allocation",
            "Entities",
            "AR Status",
            "AR Comments",
        ]
    )


@pytest.fixture()
def controller_empty(empty_df):
    return _make_controller(empty_df)


@pytest.fixture()
def df_with_internal_remarks():
    return pd.DataFrame(
        {
            "Projection": ["Feb 1st week", "Feb 2nd week", "Mar 1st week"],
            "Total in USD": [1000.0, 2000.0, 500.0],
            "Reference": ["INV1", "INV2", "INV3"],
            "Remarks": ["Internal", "Current Due", "Overdue"],
            "Customer Name": ["Customer A", "Customer B", "Customer C"],
            "New Org Name": ["BU1", "BU2", "BU3"],
            "Allocation": ["Nithya", "John", "Nithya"],
            "Entities": ["Entity1", "Entity2", "Entity3"],
            "AR Status": ["In Progress", "Pending", "Resolved"],
            "AR Comments": ["Comment 1", "Comment 2", "Comment 3"],
        }
    )


@pytest.fixture()
def controller_internal_remarks(df_with_internal_remarks):
    return _make_controller(df_with_internal_remarks)


# ─────────────────────────────────────────────────────────────────────────────
# Test: __init__ and df property
# ─────────────────────────────────────────────────────────────────────────────


class TestInitialization:
    def test_stores_model_reference(self, sample_df):
        mock_model = MagicMock()
        type(mock_model).dataframe = PropertyMock(return_value=sample_df)
        ctrl = ProjectionController(mock_model)
        assert ctrl._model is mock_model

    def test_df_is_none_before_first_access(self, sample_df):
        mock_model = MagicMock()
        type(mock_model).dataframe = PropertyMock(return_value=sample_df)
        ctrl = ProjectionController(mock_model)
        assert ctrl._df is None

    def test_df_property_lazy_loads_on_first_access(self, sample_df):
        mock_model = MagicMock()
        type(mock_model).dataframe = PropertyMock(return_value=sample_df)
        ctrl = ProjectionController(mock_model)
        df = ctrl.df
        assert df is not None
        assert len(df) == len(sample_df)

    def test_df_property_caches_result(self, sample_df):
        mock_model = MagicMock()
        type(mock_model).dataframe = PropertyMock(return_value=sample_df)
        ctrl = ProjectionController(mock_model)
        df1 = ctrl.df
        df2 = ctrl.df
        assert df1 is df2

    def test_refresh_clears_cache_and_reloads(self, sample_df):
        mock_model = MagicMock()
        mock_model.load.return_value.dataframe = sample_df
        ctrl = ProjectionController(mock_model)
        ctrl._df = pd.DataFrame()  # stale cache
        ctrl.refresh()
        mock_model.load.assert_called_once()
        assert ctrl._df.equals(sample_df)


# ─────────────────────────────────────────────────────────────────────────────
# Test: _get_all_projections
# ─────────────────────────────────────────────────────────────────────────────


class TestGetAllProjections:
    def test_returns_list(self, controller):
        assert isinstance(controller._get_all_projections(), list)

    def test_contains_expected_projections(self, controller):
        projections = controller._get_all_projections()
        assert "Feb 3rd week" in projections
        assert "Dispute - Legal" in projections
        assert "Mar 1st week" in projections

    def test_deduplicates_values(self, controller):
        projections = controller._get_all_projections()
        # "Feb 3rd week" appears twice in fixture but should appear once
        assert projections.count("Feb 3rd week") == 1

    def test_excludes_empty_strings(self):
        df = pd.DataFrame(
            {"Projection": ["Week1", "", "  ", "Week2"], "Total in USD": [1, 2, 3, 4]}
        )
        ctrl = _make_controller(df)
        projections = ctrl._get_all_projections()
        assert "" not in projections
        assert "  " not in projections

    def test_excludes_null_values(self):
        df = pd.DataFrame(
            {"Projection": ["Week1", None, "Week2"], "Total in USD": [1, 2, 3]}
        )
        ctrl = _make_controller(df)
        projections = ctrl._get_all_projections()
        assert None not in projections

    def test_empty_dataframe_returns_empty_list(self, controller_empty):
        assert controller_empty._get_all_projections() == []


# ─────────────────────────────────────────────────────────────────────────────
# Test: _select_available (static)
# ─────────────────────────────────────────────────────────────────────────────


class TestSelectAvailable:
    def test_returns_only_existing_columns(self, sample_df):
        result = ProjectionController._select_available(
            sample_df, ["Customer Name", "NonExistent", "Total in USD"]
        )
        assert result == ["Customer Name", "Total in USD"]

    def test_preserves_requested_order(self, sample_df):
        result = ProjectionController._select_available(
            sample_df, ["Total in USD", "Customer Name"]
        )
        assert result == ["Total in USD", "Customer Name"]

    def test_returns_empty_list_when_no_matches(self, sample_df):
        assert ProjectionController._select_available(sample_df, ["A", "B"]) == []

    def test_returns_empty_list_for_empty_request(self, sample_df):
        assert ProjectionController._select_available(sample_df, []) == []

    def test_handles_all_matching(self, sample_df):
        cols = ["Projection", "Total in USD"]
        assert ProjectionController._select_available(sample_df, cols) == cols


# ─────────────────────────────────────────────────────────────────────────────
# Test: _split_inflow_dispute
# ─────────────────────────────────────────────────────────────────────────────


class TestSplitInflowDispute:
    def test_dispute_keyword_routes_to_dispute_bucket(self, controller):
        inflow, dispute = controller._split_inflow_dispute()
        assert "Dispute - Legal" in dispute

    def test_non_dispute_routes_to_inflow_bucket(self, controller):
        inflow, dispute = controller._split_inflow_dispute()
        assert "Feb 3rd week" in inflow
        assert "Mar 1st week" in inflow

    def test_no_disputes_gives_empty_dispute_list(self):
        df = pd.DataFrame({"Projection": ["Week1", "Week2"], "Total in USD": [1, 2]})
        ctrl = _make_controller(df)
        inflow, dispute = ctrl._split_inflow_dispute()
        assert dispute == []
        assert set(inflow) == {"Week1", "Week2"}

    def test_all_disputes_gives_empty_inflow_list(self):
        df = pd.DataFrame(
            {"Projection": ["Dispute - A", "Dispute - B"], "Total in USD": [1, 2]}
        )
        ctrl = _make_controller(df)
        inflow, dispute = ctrl._split_inflow_dispute()
        assert inflow == []
        assert set(dispute) == {"Dispute - A", "Dispute - B"}

    def test_returns_tuple_of_two_lists(self, controller):
        result = controller._split_inflow_dispute()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert isinstance(result[1], list)


# ─────────────────────────────────────────────────────────────────────────────
# Test: _sort_key (static)
# ─────────────────────────────────────────────────────────────────────────────


class TestSortKey:
    def test_month_ordering_jan_before_feb(self):
        assert ProjectionController._sort_key(
            "Jan 1st week"
        ) < ProjectionController._sort_key("Feb 1st week")

    def test_month_ordering_feb_before_mar(self):
        assert ProjectionController._sort_key(
            "Feb 1st week"
        ) < ProjectionController._sort_key("Mar 1st week")

    def test_all_twelve_months_in_correct_rank_order(self):
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        for idx, month in enumerate(months):
            key = ProjectionController._sort_key(f"{month} 1st week")
            assert key[0] == idx + 1, f"{month} expected rank {idx + 1}, got {key[0]}"

    def test_week_rank_current_before_1st(self):
        assert ProjectionController._sort_key(
            "Feb Current week"
        ) < ProjectionController._sort_key("Feb 1st week")

    def test_week_rank_1st_before_2nd(self):
        assert ProjectionController._sort_key(
            "Feb 1st week"
        ) < ProjectionController._sort_key("Feb 2nd week")

    def test_week_rank_2nd_before_3rd(self):
        assert ProjectionController._sort_key(
            "Feb 2nd week"
        ) < ProjectionController._sort_key("Feb 3rd week")

    def test_week_rank_3rd_before_4th(self):
        assert ProjectionController._sort_key(
            "Feb 3rd week"
        ) < ProjectionController._sort_key("Feb 4th week")

    def test_week_rank_4th_before_last(self):
        assert ProjectionController._sort_key(
            "Feb 4th week"
        ) < ProjectionController._sort_key("Feb Last week")

    def test_next_month_gets_rank_98(self):
        key = ProjectionController._sort_key("Next Month")
        assert key[0] == 98

    def test_next_month_sorts_after_explicit_months(self):
        assert ProjectionController._sort_key(
            "Dec Last week"
        ) < ProjectionController._sort_key("Next Month")

    def test_unknown_month_gets_rank_99(self):
        assert ProjectionController._sort_key("Unknown Projection")[0] == 99

    def test_unknown_week_gets_rank_99(self):
        assert ProjectionController._sort_key("Feb Unknown")[1] == 99

    def test_unknown_sorts_after_known(self):
        assert ProjectionController._sort_key(
            "Feb 1st week"
        ) < ProjectionController._sort_key("Unknown Projection")

    def test_case_insensitive_month(self):
        lower = ProjectionController._sort_key("feb 1st week")
        upper = ProjectionController._sort_key("FEB 1ST WEEK")
        assert lower[0] == upper[0] == 2

    def test_case_insensitive_week(self):
        lower = ProjectionController._sort_key("feb 1st week")
        upper = ProjectionController._sort_key("FEB 1ST WEEK")
        assert lower[1] == upper[1]

    def test_returns_tuple(self):
        assert isinstance(ProjectionController._sort_key("Jan 1st week"), tuple)

    def test_tuple_has_three_elements(self):
        assert len(ProjectionController._sort_key("Jan 1st week")) == 3


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_weekly_inflow_summary
# ─────────────────────────────────────────────────────────────────────────────


class TestGetWeeklyInflowSummary:
    def test_returns_dataframe(self, controller):
        assert isinstance(controller.get_weekly_inflow_summary(), pd.DataFrame)

    def test_has_required_columns(self, controller):
        summary = controller.get_weekly_inflow_summary()
        for col in ("Projection", "Total Inflow (USD)", "Invoice Count", "% of Total"):
            assert col in summary.columns

    def test_total_inflow_equals_grand_total(self, controller):
        summary = controller.get_weekly_inflow_summary()
        assert summary["Total Inflow (USD)"].sum() == 6500.0

    def test_invoice_count_equals_total_rows(self, controller):
        summary = controller.get_weekly_inflow_summary()
        assert summary["Invoice Count"].sum() == 6

    def test_percentage_sums_to_100(self, controller):
        summary = controller.get_weekly_inflow_summary()
        assert abs(summary["% of Total"].sum() - 100.0) < 0.01

    def test_dispute_projection_is_sorted_last(self, controller):
        summary = controller.get_weekly_inflow_summary()
        projections = summary["Projection"].tolist()
        assert projections[-1] == "Dispute - Legal"

    def test_feb_before_mar_in_output(self, controller):
        summary = controller.get_weekly_inflow_summary()
        projections = summary["Projection"].tolist()
        feb_indices = [i for i, p in enumerate(projections) if "Feb" in p]
        mar_indices = [i for i, p in enumerate(projections) if "Mar" in p]
        assert all(f < m for f in feb_indices for m in mar_indices)

    def test_empty_dataframe_returns_empty_summary(self, controller_empty):
        assert len(controller_empty.get_weekly_inflow_summary()) == 0

    def test_zero_total_percentage_is_zero(self):
        df = pd.DataFrame({"Projection": ["Week1"], "Total in USD": [0.0]})
        ctrl = _make_controller(df)
        summary = ctrl.get_weekly_inflow_summary()
        assert summary["% of Total"].iloc[0] == 0.0

    def test_each_projection_appears_exactly_once(self, controller):
        summary = controller.get_weekly_inflow_summary()
        assert summary["Projection"].nunique() == len(summary)


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_expected_inflow_total  (month-aware — must mock today's date)
# ─────────────────────────────────────────────────────────────────────────────


class TestGetExpectedInflowTotal:
    def test_returns_zero_when_no_current_month_match(self, controller):
        # Force today to a month that does not appear in the fixture
        with patch("controllers.projection_controller.date") as mock_date:
            mock_date.today.return_value = date(2024, 6, 1)  # June — not in fixture
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            total = controller.get_expected_inflow_total()
        assert total == 0.0

    def test_returns_feb_inflow_when_today_is_february(self, controller):
        # Fixture has Feb 3rd week (1000+2000=3000) and Feb Last week (700) = 3700
        with patch("controllers.projection_controller.date") as mock_date:
            mock_date.today.return_value = date(2024, 2, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            total = controller.get_expected_inflow_total()
        assert total == 3700.0

    def test_returns_mar_inflow_when_today_is_march(self, controller):
        # Fixture has Mar 1st week = 1500
        with patch("controllers.projection_controller.date") as mock_date:
            mock_date.today.return_value = date(2024, 3, 5)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            total = controller.get_expected_inflow_total()
        assert total == 1500.0

    def test_excludes_dispute_projections(self, controller):
        # Even if the month matches, dispute rows must not be included
        with patch("controllers.projection_controller.date") as mock_date:
            mock_date.today.return_value = date(2024, 2, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            total = controller.get_expected_inflow_total()
        assert total == 3700.0  # Dispute - Legal (500) not included

    def test_empty_dataframe_returns_zero(self, controller_empty):
        with patch("controllers.projection_controller.date") as mock_date:
            mock_date.today.return_value = date(2024, 2, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            assert controller_empty.get_expected_inflow_total() == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_next_month_inflow_total
# ─────────────────────────────────────────────────────────────────────────────


class TestGetNextMonthInflowTotal:
    def test_returns_next_month_1st_week_total(self, controller):
        # When today is in Feb, next month is Mar; Mar 1st week = 1500
        with patch("controllers.projection_controller.date") as mock_date:
            mock_date.today.return_value = date(2024, 2, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            total = controller.get_next_month_inflow_total()
        assert total == 1500.0

    def test_returns_zero_when_no_1st_week_for_next_month(self, controller):
        # When today is in Mar, next month is Apr; fixture has no Apr entries
        with patch("controllers.projection_controller.date") as mock_date:
            mock_date.today.return_value = date(2024, 3, 5)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            total = controller.get_next_month_inflow_total()
        assert total == 0.0

    def test_empty_dataframe_returns_zero(self, controller_empty):
        with patch("controllers.projection_controller.date") as mock_date:
            mock_date.today.return_value = date(2024, 2, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            assert controller_empty.get_next_month_inflow_total() == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_next_month_name
# ─────────────────────────────────────────────────────────────────────────────


class TestGetNextMonthName:
    def test_returns_correct_next_month_name(self, controller):
        with patch("controllers.projection_controller.date") as mock_date:
            mock_date.today.return_value = date(2024, 1, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            assert controller.get_next_month_name() == "February"

    def test_december_wraps_to_january(self, controller):
        with patch("controllers.projection_controller.date") as mock_date:
            mock_date.today.return_value = date(2024, 12, 1)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            assert controller.get_next_month_name() == "January"

    def test_returns_string(self, controller):
        assert isinstance(controller.get_next_month_name(), str)


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_dispute_total
# ─────────────────────────────────────────────────────────────────────────────


class TestGetDisputeTotal:
    def test_returns_dispute_rows_only(self, controller):
        assert controller.get_dispute_total() == 500.0

    def test_no_disputes_returns_zero(self):
        df = pd.DataFrame({"Projection": ["Week1"], "Total in USD": [100.0]})
        assert _make_controller(df).get_dispute_total() == 0.0

    def test_empty_dataframe_returns_zero(self, controller_empty):
        assert controller_empty.get_dispute_total() == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_grand_total
# ─────────────────────────────────────────────────────────────────────────────


class TestGetGrandTotal:
    def test_sums_all_rows(self, controller):
        assert controller.get_grand_total() == 6500.0

    def test_empty_returns_zero(self, controller_empty):
        assert controller_empty.get_grand_total() == 0.0

    def test_returns_float(self, controller):
        assert isinstance(controller.get_grand_total(), float)


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_credit_memo_total
# ─────────────────────────────────────────────────────────────────────────────


class TestGetCreditMemoTotal:
    def test_returns_correct_total(self, controller):
        assert controller.get_credit_memo_total() == 500.0

    def test_case_insensitive(self):
        df = pd.DataFrame(
            {
                "Remarks": ["CREDIT MEMO", "credit memo", "Credit Memo"],
                "Total in USD": [100.0, 200.0, 300.0],
            }
        )
        assert _make_controller(df).get_credit_memo_total() == 600.0

    def test_no_credit_memos_returns_zero(self):
        df = pd.DataFrame({"Remarks": ["Current Due"], "Total in USD": [100.0]})
        assert _make_controller(df).get_credit_memo_total() == 0.0

    def test_returns_float(self, controller):
        assert isinstance(controller.get_credit_memo_total(), float)


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_unapplied_total
# ─────────────────────────────────────────────────────────────────────────────


class TestGetUnappliedTotal:
    def test_returns_correct_total(self, controller):
        assert controller.get_unapplied_total() == 800.0

    def test_no_unapplied_returns_zero(self):
        df = pd.DataFrame({"Remarks": ["Current Due"], "Total in USD": [100.0]})
        assert _make_controller(df).get_unapplied_total() == 0.0

    def test_case_insensitive(self):
        df = pd.DataFrame(
            {
                "Remarks": ["UNAPPLIED", "Unapplied"],
                "Total in USD": [50.0, 50.0],
            }
        )
        assert _make_controller(df).get_unapplied_total() == 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_current_due_total
# ─────────────────────────────────────────────────────────────────────────────


class TestGetCurrentDueTotal:
    def test_returns_correct_total(self, controller):
        assert controller.get_current_due_total() == 1000.0

    def test_case_insensitive(self):
        df = pd.DataFrame(
            {
                "Remarks": ["CURRENT DUE", "current due"],
                "Total in USD": [100.0, 200.0],
            }
        )
        assert _make_controller(df).get_current_due_total() == 300.0

    def test_no_current_due_returns_zero(self):
        df = pd.DataFrame({"Remarks": ["Overdue"], "Total in USD": [100.0]})
        assert _make_controller(df).get_current_due_total() == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_future_due_total
# ─────────────────────────────────────────────────────────────────────────────


class TestGetFutureDueTotal:
    def test_returns_correct_total(self, controller):
        assert controller.get_future_due_total() == 1500.0

    def test_no_future_due_returns_zero(self):
        df = pd.DataFrame({"Remarks": ["Current Due"], "Total in USD": [100.0]})
        assert _make_controller(df).get_future_due_total() == 0.0

    def test_case_insensitive(self):
        df = pd.DataFrame(
            {
                "Remarks": ["FUTURE DUE", "future due"],
                "Total in USD": [100.0, 200.0],
            }
        )
        assert _make_controller(df).get_future_due_total() == 300.0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_overdue_total
# ─────────────────────────────────────────────────────────────────────────────


class TestGetOverdueTotal:
    def test_returns_correct_total(self, controller):
        assert controller.get_overdue_total() == 2000.0

    def test_no_overdue_returns_zero(self):
        df = pd.DataFrame({"Remarks": ["Current Due"], "Total in USD": [100.0]})
        assert _make_controller(df).get_overdue_total() == 0.0

    def test_case_insensitive(self):
        df = pd.DataFrame(
            {
                "Remarks": ["OVERDUE", "overdue"],
                "Total in USD": [100.0, 200.0],
            }
        )
        assert _make_controller(df).get_overdue_total() == 300.0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_legal_total
# ─────────────────────────────────────────────────────────────────────────────


class TestGetLegalTotal:
    def test_returns_correct_total(self, controller):
        assert controller.get_legal_total() == 700.0

    def test_no_legal_returns_zero(self):
        df = pd.DataFrame({"Remarks": ["Current Due"], "Total in USD": [100.0]})
        assert _make_controller(df).get_legal_total() == 0.0

    def test_case_insensitive(self):
        df = pd.DataFrame(
            {
                "Remarks": ["LEGAL", "legal"],
                "Total in USD": [100.0, 200.0],
            }
        )
        assert _make_controller(df).get_legal_total() == 300.0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_projection_detail
# ─────────────────────────────────────────────────────────────────────────────


class TestGetProjectionDetail:
    def test_returns_correct_number_of_rows(self, controller):
        assert len(controller.get_projection_detail("Feb 3rd week")) == 2

    def test_contains_expected_columns(self, controller):
        detail = controller.get_projection_detail("Feb 3rd week")
        assert "Customer Name" in detail.columns
        assert "Total in USD" in detail.columns

    def test_sorted_descending_by_amount(self, controller):
        detail = controller.get_projection_detail("Feb 3rd week")
        amounts = detail["Total in USD"].tolist()
        assert amounts == sorted(amounts, reverse=True)

    def test_reference_converted_to_string(self, controller):
        detail = controller.get_projection_detail("Feb 3rd week")
        assert detail["Reference"].dtype == object

    def test_no_match_returns_empty_dataframe(self, controller):
        assert len(controller.get_projection_detail("NonExistent")) == 0

    def test_missing_optional_columns_not_included(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week1"],
                "Total in USD": [100.0],
                "Customer Name": ["A"],
            }
        )
        detail = _make_controller(df).get_projection_detail("Week1")
        assert "Customer Name" in detail.columns
        assert "Reference" not in detail.columns


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_due_wise_outstanding
# ─────────────────────────────────────────────────────────────────────────────


class TestGetDueWiseOutstanding:
    def test_has_required_columns(self, controller):
        df = controller.get_due_wise_outstanding()
        for col in (
            "Remarks",
            "Total Outstanding (USD)",
            "Invoice Count",
            "% of Total",
        ):
            assert col in df.columns

    def test_excludes_internal_remarks(self, controller_internal_remarks):
        df = controller_internal_remarks.get_due_wise_outstanding()
        assert "internal" not in df["Remarks"].str.lower().tolist()

    def test_only_valid_remarks_included(self, controller):
        valid = {"future due", "current due", "overdue", "credit memo", "unapplied"}
        df = controller.get_due_wise_outstanding()
        for remark in df["Remarks"]:
            assert remark.lower() in valid

    def test_sorted_descending_by_total(self, controller):
        df = controller.get_due_wise_outstanding()
        amounts = df["Total Outstanding (USD)"].tolist()
        assert amounts == sorted(amounts, reverse=True)

    def test_percentage_sums_to_100(self, controller):
        df = controller.get_due_wise_outstanding()
        assert abs(df["% of Total"].sum() - 100.0) < 0.1

    def test_empty_dataframe_returns_empty(self, controller_empty):
        assert len(controller_empty.get_due_wise_outstanding()) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_due_wise_detail
# ─────────────────────────────────────────────────────────────────────────────


class TestGetDueWiseDetail:
    def test_returns_matching_rows(self, controller):
        detail = controller.get_due_wise_detail("Current Due")
        assert len(detail) == 1
        assert detail.iloc[0]["Customer Name"] == "Customer A"

    def test_case_insensitive_matching(self, controller):
        assert len(controller.get_due_wise_detail("current due")) == len(
            controller.get_due_wise_detail("CURRENT DUE")
        )

    def test_sorted_descending_by_amount(self, controller):
        detail = controller.get_due_wise_detail("Overdue")
        amounts = detail["Total in USD"].tolist()
        assert amounts == sorted(amounts, reverse=True)

    def test_no_match_returns_empty(self, controller):
        assert len(controller.get_due_wise_detail("NonExistent")) == 0

    def test_reference_converted_to_string(self, controller):
        detail = controller.get_due_wise_detail("Current Due")
        assert detail["Reference"].dtype == object


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_customer_wise_outstanding
# ─────────────────────────────────────────────────────────────────────────────


class TestGetCustomerWiseOutstanding:
    def test_has_required_columns(self, controller):
        df = controller.get_customer_wise_outstanding()
        assert "Customer Name" in df.columns
        assert "Total Outstanding (USD)" in df.columns

    def test_excludes_internal_remarks(self, controller_internal_remarks):
        df = controller_internal_remarks.get_customer_wise_outstanding()
        # Internal remark row (1000) excluded; Current Due (2000) + Overdue (500) = 2500
        assert df["Total Outstanding (USD)"].sum() == 2500.0

    def test_canonical_columns_added_when_missing(self):
        df = pd.DataFrame(
            {
                "Customer Name": ["A"],
                "Remarks": ["Other"],
                "Total in USD": [100.0],
            }
        )
        result = _make_controller(df).get_customer_wise_outstanding()
        assert "Current Due" in result.columns
        assert "Overdue" in result.columns

    def test_sorted_descending_by_total(self, controller):
        df = controller.get_customer_wise_outstanding()
        amounts = df["Total Outstanding (USD)"].tolist()
        assert amounts == sorted(amounts, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_customer_wise_detail
# ─────────────────────────────────────────────────────────────────────────────


class TestGetCustomerWiseDetail:
    def test_returns_all_rows_for_customer(self, controller):
        assert len(controller.get_customer_wise_detail("Customer A")) == 2

    def test_case_insensitive(self, controller):
        assert len(controller.get_customer_wise_detail("customer a")) == 2

    def test_includes_remarks_column(self, controller):
        assert "Remarks" in controller.get_customer_wise_detail("Customer A").columns

    def test_no_match_returns_empty(self, controller):
        assert len(controller.get_customer_wise_detail("NonExistent")) == 0

    def test_sorted_descending_by_amount(self, controller):
        detail = controller.get_customer_wise_detail("Customer A")
        amounts = detail["Total in USD"].tolist()
        assert amounts == sorted(amounts, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_business_wise_outstanding
# ─────────────────────────────────────────────────────────────────────────────


class TestGetBusinessWiseOutstanding:
    def test_has_required_columns(self, controller):
        df = controller.get_business_wise_outstanding()
        assert "New Org Name" in df.columns
        assert "Total Outstanding (USD)" in df.columns

    def test_excludes_internal_org_name(self, controller):
        df = controller.get_business_wise_outstanding()
        assert "internal" not in df["New Org Name"].str.lower().tolist()

    def test_canonical_columns_added_when_missing(self):
        df = pd.DataFrame(
            {
                "New Org Name": ["BU1"],
                "Remarks": ["Other"],
                "Total in USD": [100.0],
            }
        )
        result = _make_controller(df).get_business_wise_outstanding()
        assert "Current Due" in result.columns
        assert "Overdue" in result.columns

    def test_sorted_descending_by_total(self, controller):
        df = controller.get_business_wise_outstanding()
        amounts = df["Total Outstanding (USD)"].tolist()
        assert amounts == sorted(amounts, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_business_wise_detail
# ─────────────────────────────────────────────────────────────────────────────


class TestGetBusinessWiseDetail:
    def test_returns_matching_rows(self, controller):
        assert len(controller.get_business_wise_detail("BU1")) == 2

    def test_case_insensitive(self, controller):
        assert len(controller.get_business_wise_detail("bu1")) == 2

    def test_includes_remarks_column(self, controller):
        assert "Remarks" in controller.get_business_wise_detail("BU1").columns

    def test_no_match_returns_empty(self, controller):
        assert len(controller.get_business_wise_detail("NonExistent")) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_allocation_wise_outstanding
# ─────────────────────────────────────────────────────────────────────────────


class TestGetAllocationWiseOutstanding:
    def test_has_required_columns(self, controller):
        df = controller.get_allocation_wise_outstanding()
        assert "Allocation" in df.columns
        assert "Total Outstanding (USD)" in df.columns

    def test_excludes_internal_remarks(self, controller_internal_remarks):
        df = controller_internal_remarks.get_allocation_wise_outstanding()
        assert df["Total Outstanding (USD)"].sum() == 2500.0

    def test_canonical_columns_added_when_missing(self):
        df = pd.DataFrame(
            {
                "Allocation": ["X"],
                "Remarks": ["Other"],
                "Total in USD": [100.0],
            }
        )
        result = _make_controller(df).get_allocation_wise_outstanding()
        assert "Current Due" in result.columns
        assert "Overdue" in result.columns

    def test_sorted_descending_by_total(self, controller):
        df = controller.get_allocation_wise_outstanding()
        amounts = df["Total Outstanding (USD)"].tolist()
        assert amounts == sorted(amounts, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_allocation_remark_detail
# ─────────────────────────────────────────────────────────────────────────────


class TestGetAllocationRemarkDetail:
    def test_returns_matching_rows(self, controller):
        detail = controller.get_allocation_remark_detail("Nithya", "Current Due")
        assert len(detail) == 1

    def test_case_insensitive(self, controller):
        assert len(
            controller.get_allocation_remark_detail("nithya", "current due")
        ) == len(controller.get_allocation_remark_detail("Nithya", "Current Due"))

    def test_includes_allocation_column(self, controller):
        detail = controller.get_allocation_remark_detail("Nithya", "Current Due")
        assert "Allocation" in detail.columns

    def test_no_match_returns_empty(self, controller):
        assert len(controller.get_allocation_remark_detail("Ghost", "NonExistent")) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_entities_wise_outstanding
# ─────────────────────────────────────────────────────────────────────────────


class TestGetEntitiesWiseOutstanding:
    def test_has_required_columns(self, controller):
        df = controller.get_entities_wise_outstanding()
        assert "Entities" in df.columns
        assert "Total Outstanding (USD)" in df.columns

    def test_canonical_columns_added_when_missing(self):
        df = pd.DataFrame(
            {
                "Entities": ["E1"],
                "Remarks": ["Other"],
                "Total in USD": [100.0],
            }
        )
        result = _make_controller(df).get_entities_wise_outstanding()
        assert "Current Due" in result.columns
        assert "Overdue" in result.columns

    def test_sorted_descending_by_total(self, controller):
        df = controller.get_entities_wise_outstanding()
        amounts = df["Total Outstanding (USD)"].tolist()
        assert amounts == sorted(amounts, reverse=True)

    def test_total_matches_grand_total(self, controller):
        df = controller.get_entities_wise_outstanding()
        assert df["Total Outstanding (USD)"].sum() == pytest.approx(6500.0)


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_entities_remark_detail
# ─────────────────────────────────────────────────────────────────────────────


class TestGetEntitiesRemarkDetail:
    def test_returns_matching_rows(self, controller):
        detail = controller.get_entities_remark_detail("UST India", "Current Due")
        assert len(detail) == 1

    def test_case_insensitive(self, controller):
        assert len(
            controller.get_entities_remark_detail("ust india", "current due")
        ) == len(controller.get_entities_remark_detail("UST India", "Current Due"))

    def test_includes_entities_column(self, controller):
        detail = controller.get_entities_remark_detail("UST India", "Current Due")
        assert "Entities" in detail.columns

    def test_no_match_returns_empty(self, controller):
        assert len(controller.get_entities_remark_detail("Ghost", "NonExistent")) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_ar_status_wise_outstanding
# ─────────────────────────────────────────────────────────────────────────────


class TestGetARStatusWiseOutstanding:
    def test_has_required_columns(self, controller):
        df = controller.get_ar_status_wise_outstanding()
        assert "AR Status" in df.columns
        assert "Total Outstanding (USD)" in df.columns

    def test_excludes_empty_ar_status(self, controller):
        df = controller.get_ar_status_wise_outstanding()
        assert "" not in df["AR Status"].tolist()
        assert df["AR Status"].notna().all()

    def test_canonical_remark_columns_added(self, controller):
        df = controller.get_ar_status_wise_outstanding()
        for col in ("Current Due", "Future Due", "Overdue"):
            assert col in df.columns

    def test_sorted_descending_by_total(self, controller):
        df = controller.get_ar_status_wise_outstanding()
        amounts = df["Total Outstanding (USD)"].tolist()
        assert amounts == sorted(amounts, reverse=True)

    def test_returns_dataframe(self, controller):
        assert isinstance(controller.get_ar_status_wise_outstanding(), pd.DataFrame)

    def test_only_valid_remarks_aggregated(self):
        df = pd.DataFrame(
            {
                "AR Status": ["Active", "Active"],
                "Remarks": ["Current Due", "Invalid Remark"],
                "Total in USD": [100.0, 999.0],
            }
        )
        result = _make_controller(df).get_ar_status_wise_outstanding()
        # Invalid remark should not contribute
        assert result["Total Outstanding (USD)"].sum() == 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_ar_status_remark_detail
# ─────────────────────────────────────────────────────────────────────────────


class TestGetARStatusRemarkDetail:
    def test_returns_matching_rows(self, controller):
        detail = controller.get_ar_status_remark_detail("In Progress", "Current Due")
        assert len(detail) == 1

    def test_case_insensitive(self, controller):
        assert len(
            controller.get_ar_status_remark_detail("in progress", "current due")
        ) == len(controller.get_ar_status_remark_detail("In Progress", "Current Due"))

    def test_includes_projection_column(self, controller):
        detail = controller.get_ar_status_remark_detail("In Progress", "Current Due")
        assert "Projection" in detail.columns

    def test_no_match_returns_empty(self, controller):
        assert len(controller.get_ar_status_remark_detail("Ghost", "NonExistent")) == 0

    def test_sorted_descending_by_amount(self, controller):
        detail = controller.get_ar_status_remark_detail("In Progress", "Current Due")
        amounts = detail["Total in USD"].tolist()
        assert amounts == sorted(amounts, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Edge cases
# ─────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_numeric_reference_converted_to_string_in_projection_detail(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week1"],
                "Total in USD": [100.0],
                "Reference": [12345],
                "Customer Name": ["A"],
            }
        )
        detail = _make_controller(df).get_projection_detail("Week1")
        assert detail["Reference"].dtype == object
        assert detail["Reference"].iloc[0] == "12345"

    def test_whitespace_remarks_stripped_in_due_outstanding(self):
        df = pd.DataFrame(
            {
                "Remarks": ["  Current Due  ", " Overdue "],
                "Total in USD": [100.0, 200.0],
                "Customer Name": ["A", "B"],
                "New Org Name": ["BU1", "BU2"],
                "Allocation": ["X", "Y"],
                "Entities": ["E1", "E2"],
            }
        )
        result = _make_controller(df).get_due_wise_outstanding()
        assert len(result) == 2

    def test_zero_totals_produce_zero_percentage(self):
        df = pd.DataFrame({"Projection": ["Week1"], "Total in USD": [0.0]})
        summary = _make_controller(df).get_weekly_inflow_summary()
        assert summary["% of Total"].iloc[0] == 0.0

    def test_negative_totals_handled_by_grand_total(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week1", "Week2"],
                "Total in USD": [-100.0, 200.0],
            }
        )
        assert _make_controller(df).get_grand_total() == 100.0

    def test_negative_credit_memo_total(self):
        df = pd.DataFrame(
            {
                "Remarks": ["Credit Memo"],
                "Total in USD": [-500.0],
            }
        )
        assert _make_controller(df).get_credit_memo_total() == -500.0

    def test_large_dataset_weekly_summary_completes(self):
        import numpy as np

        rng = np.random.default_rng(42)
        n = 10_000
        df = pd.DataFrame(
            {
                "Projection": rng.choice(
                    ["Feb 1st week", "Feb 2nd week", "Dispute - A"], n
                ),
                "Total in USD": rng.uniform(100, 10_000, n),
                "Remarks": rng.choice(["Current Due", "Overdue", "Future Due"], n),
                "Customer Name": [f"Customer {i % 100}" for i in range(n)],
                "New Org Name": rng.choice(["BU1", "BU2", "BU3"], n),
                "Allocation": rng.choice(["A", "B"], n),
                "Entities": rng.choice(["E1", "E2"], n),
                "AR Status": rng.choice(["Active", "Pending"], n),
            }
        )
        ctrl = _make_controller(df)
        summary = ctrl.get_weekly_inflow_summary()
        assert len(summary) > 0
        assert ctrl.get_customer_wise_outstanding()["Total Outstanding (USD)"].sum() > 0

    def test_special_characters_in_projection_name(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week-1/A", "Week@2"],
                "Total in USD": [100.0, 200.0],
            }
        )
        summary = _make_controller(df).get_weekly_inflow_summary()
        assert len(summary) == 2

    def test_missing_ar_comments_column_does_not_crash_projection_detail(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week1"],
                "Total in USD": [100.0],
                "Customer Name": ["A"],
                "Reference": ["INV1"],
            }
        )
        detail = _make_controller(df).get_projection_detail("Week1")
        assert "AR Comments" not in detail.columns
        assert len(detail) == 1
