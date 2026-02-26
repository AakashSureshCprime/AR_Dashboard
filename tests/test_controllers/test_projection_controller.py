from unittest.mock import MagicMock, PropertyMock

import pandas as pd
import pytest

from controllers.projection_controller import ProjectionController


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def sample_df():
    """Standard sample DataFrame for testing."""
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


@pytest.fixture
def controller(sample_df):
    """Controller with standard sample data."""

    class DummyModel:
        @property
        def dataframe(self):
            return sample_df

    return ProjectionController(DummyModel())


@pytest.fixture
def empty_df():
    """Empty DataFrame with expected columns."""
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


@pytest.fixture
def controller_empty(empty_df):
    """Controller with empty DataFrame."""

    class DummyModel:
        @property
        def dataframe(self):
            return empty_df

    return ProjectionController(DummyModel())


@pytest.fixture
def df_missing_columns():
    """DataFrame with minimal columns."""
    return pd.DataFrame(
        {
            "Projection": ["Feb 1st week"],
            "Total in USD": [1000.0],
            "Customer Name": ["Customer A"],
        }
    )


@pytest.fixture
def controller_missing_cols(df_missing_columns):
    """Controller with minimal columns."""

    class DummyModel:
        @property
        def dataframe(self):
            return df_missing_columns

    return ProjectionController(DummyModel())


@pytest.fixture
def df_with_internal_remarks():
    """DataFrame with Internal remarks to test filtering."""
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


@pytest.fixture
def controller_internal_remarks(df_with_internal_remarks):
    """Controller with internal remarks data."""

    class DummyModel:
        @property
        def dataframe(self):
            return df_with_internal_remarks

    return ProjectionController(DummyModel())


# ---------------------------------------------------------------------
# Test: __init__ and df property
# ---------------------------------------------------------------------


class TestInitialization:
    def test_init_creates_controller(self, sample_df):
        mock_model = MagicMock()
        type(mock_model).dataframe = PropertyMock(return_value=sample_df)

        controller = ProjectionController(mock_model)

        assert controller._model == mock_model
        assert controller._df is None

    def test_df_property_lazy_loads(self, sample_df):
        mock_model = MagicMock()
        type(mock_model).dataframe = PropertyMock(return_value=sample_df)

        controller = ProjectionController(mock_model)

        # First access should load
        df = controller.df
        assert df is not None
        assert len(df) == len(sample_df)

        # Second access should use cached value
        df2 = controller.df
        assert df is df2

    def test_refresh_reloads_data(self, sample_df):
        mock_model = MagicMock()
        mock_model.load.return_value.dataframe = sample_df

        controller = ProjectionController(mock_model)
        controller._df = pd.DataFrame()  # Set cached value

        controller.refresh()

        mock_model.load.assert_called_once()
        assert controller._df.equals(sample_df)


# ---------------------------------------------------------------------
# Test: _get_all_projections
# ---------------------------------------------------------------------


class TestGetAllProjections:
    def test_returns_unique_projections(self, controller):
        projections = controller._get_all_projections()

        assert isinstance(projections, list)
        assert "Feb 3rd week" in projections
        assert "Dispute - Legal" in projections
        assert "Mar 1st week" in projections

    def test_excludes_empty_and_null_projections(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week1", "", None, "  ", "Week2"],
                "Total in USD": [100, 200, 300, 400, 500],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        projections = controller._get_all_projections()

        assert "Week1" in projections
        assert "Week2" in projections
        assert "" not in projections
        assert None not in projections

    def test_empty_dataframe_returns_empty_list(self, controller_empty):
        projections = controller_empty._get_all_projections()
        assert projections == []


# ---------------------------------------------------------------------
# Test: _select_available
# ---------------------------------------------------------------------


class TestSelectAvailable:
    def test_returns_existing_columns_in_order(self, sample_df):
        cols = ProjectionController._select_available(
            sample_df, ["Customer Name", "Reference", "NonExistent", "Total in USD"]
        )
        assert cols == ["Customer Name", "Reference", "Total in USD"]

    def test_returns_empty_for_no_matches(self, sample_df):
        cols = ProjectionController._select_available(
            sample_df, ["NonExistent1", "NonExistent2"]
        )
        assert cols == []

    def test_empty_requested_list(self, sample_df):
        cols = ProjectionController._select_available(sample_df, [])
        assert cols == []


# ---------------------------------------------------------------------
# Test: _split_inflow_dispute
# ---------------------------------------------------------------------


class TestSplitInflowDispute:
    def test_splits_correctly(self, controller):
        inflow, dispute = controller._split_inflow_dispute()

        assert "Dispute - Legal" in dispute
        assert "Feb 3rd week" in inflow
        assert "Mar 1st week" in inflow

    def test_no_disputes(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week1", "Week2"],
                "Total in USD": [100, 200],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        inflow, dispute = controller._split_inflow_dispute()

        assert len(dispute) == 0
        assert "Week1" in inflow
        assert "Week2" in inflow

    def test_all_disputes(self):
        df = pd.DataFrame(
            {
                "Projection": ["Dispute - A", "Dispute - B"],
                "Total in USD": [100, 200],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        inflow, dispute = controller._split_inflow_dispute()

        assert len(inflow) == 0
        assert "Dispute - A" in dispute
        assert "Dispute - B" in dispute


# ---------------------------------------------------------------------
# Test: _sort_key
# ---------------------------------------------------------------------


class TestSortKey:
    def test_month_ordering(self):
        jan_key = ProjectionController._sort_key("Jan 1st week")
        feb_key = ProjectionController._sort_key("Feb 1st week")
        mar_key = ProjectionController._sort_key("Mar 1st week")

        assert jan_key < feb_key < mar_key

    def test_week_ordering_within_month(self):
        current = ProjectionController._sort_key("Feb Current week")
        first = ProjectionController._sort_key("Feb 1st week")
        second = ProjectionController._sort_key("Feb 2nd week")
        third = ProjectionController._sort_key("Feb 3rd week")
        fourth = ProjectionController._sort_key("Feb 4th week")
        last = ProjectionController._sort_key("Feb Last week")

        assert current < first < second < third < fourth < last

    def test_next_month_ordering(self):
        feb_key = ProjectionController._sort_key("Feb 1st week")
        next_month_key = ProjectionController._sort_key("Next Month")

        assert feb_key < next_month_key
        assert next_month_key[0] == 98

    def test_unknown_month_gets_high_rank(self):
        unknown = ProjectionController._sort_key("Unknown Projection")
        feb = ProjectionController._sort_key("Feb 1st week")

        assert unknown > feb
        assert unknown[0] == 99

    def test_unknown_week_gets_high_rank(self):
        unknown = ProjectionController._sort_key("Feb Unknown")
        known = ProjectionController._sort_key("Feb 1st week")

        assert unknown > known
        assert unknown[1] == 99

    def test_all_months_covered(self):
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
        for i, month in enumerate(months):
            key = ProjectionController._sort_key(f"{month} 1st week")
            assert key[0] == i + 1

    def test_case_insensitive(self):
        lower = ProjectionController._sort_key("feb 1st week")
        upper = ProjectionController._sort_key("FEB 1ST WEEK")
        mixed = ProjectionController._sort_key("Feb 1st Week")

        assert lower[0] == upper[0] == mixed[0]
        assert lower[1] == upper[1] == mixed[1]


# ---------------------------------------------------------------------
# Test: get_weekly_inflow_summary
# ---------------------------------------------------------------------


class TestGetWeeklyInflowSummary:
    def test_returns_correct_columns(self, controller):
        summary = controller.get_weekly_inflow_summary()

        assert "Projection" in summary.columns
        assert "Total Inflow (USD)" in summary.columns
        assert "Invoice Count" in summary.columns
        assert "% of Total" in summary.columns

    def test_total_inflow_matches(self, controller):
        summary = controller.get_weekly_inflow_summary()
        assert summary["Total Inflow (USD)"].sum() == 6500.0

    def test_invoice_count_matches(self, controller):
        summary = controller.get_weekly_inflow_summary()
        assert summary["Invoice Count"].sum() == 6

    def test_percentage_sums_to_100(self, controller):
        summary = controller.get_weekly_inflow_summary()
        assert abs(summary["% of Total"].sum() - 100.0) < 0.1

    def test_sorted_by_week_order(self, controller):
        summary = controller.get_weekly_inflow_summary()
        projections = summary["Projection"].tolist()

        # Dispute should be at the end
        assert projections[-1] == "Dispute - Legal"

    def test_empty_data_returns_empty_summary(self, controller_empty):
        summary = controller_empty.get_weekly_inflow_summary()
        assert len(summary) == 0

    def test_zero_total_percentage(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week1"],
                "Total in USD": [0.0],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        summary = controller.get_weekly_inflow_summary()

        assert summary["% of Total"].iloc[0] == 0.0


# ---------------------------------------------------------------------
# Test: get_expected_inflow_total
# ---------------------------------------------------------------------


class TestGetExpectedInflowTotal:
    def test_excludes_dispute(self, controller):
        total = controller.get_expected_inflow_total()
        # Total minus dispute (500)
        assert total == 6000.0

    def test_empty_returns_zero(self, controller_empty):
        assert controller_empty.get_expected_inflow_total() == 0.0


# ---------------------------------------------------------------------
# Test: get_dispute_total
# ---------------------------------------------------------------------


class TestGetDisputeTotal:
    def test_returns_dispute_only(self, controller):
        total = controller.get_dispute_total()
        assert total == 500.0

    def test_no_disputes_returns_zero(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week1", "Week2"],
                "Total in USD": [100, 200],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        assert controller.get_dispute_total() == 0.0


# ---------------------------------------------------------------------
# Test: get_grand_total
# ---------------------------------------------------------------------


class TestGetGrandTotal:
    def test_returns_correct_total(self, controller):
        assert controller.get_grand_total() == 6500.0

    def test_empty_returns_zero(self, controller_empty):
        assert controller_empty.get_grand_total() == 0.0


# ---------------------------------------------------------------------
# Test: get_projection_detail
# ---------------------------------------------------------------------


class TestGetProjectionDetail:
    def test_returns_correct_rows(self, controller):
        detail = controller.get_projection_detail("Feb 3rd week")

        assert len(detail) == 2
        assert "Customer Name" in detail.columns
        assert "Total in USD" in detail.columns

    def test_sorted_by_amount_descending(self, controller):
        detail = controller.get_projection_detail("Feb 3rd week")
        amounts = detail["Total in USD"].tolist()

        assert amounts == sorted(amounts, reverse=True)

    def test_reference_converted_to_string(self, controller):
        detail = controller.get_projection_detail("Feb 3rd week")
        assert detail["Reference"].dtype == object

    def test_no_matching_projection_returns_empty(self, controller):
        detail = controller.get_projection_detail("NonExistent")
        assert len(detail) == 0

    def test_missing_columns_handled(self, controller_missing_cols):
        detail = controller_missing_cols.get_projection_detail("Feb 1st week")
        assert "Customer Name" in detail.columns
        assert "Reference" not in detail.columns


# ---------------------------------------------------------------------
# Test: get_due_wise_outstanding
# ---------------------------------------------------------------------


class TestGetDueWiseOutstanding:
    def test_returns_correct_columns(self, controller):
        df = controller.get_due_wise_outstanding()

        assert "Remarks" in df.columns
        assert "Total Outstanding (USD)" in df.columns
        assert "Invoice Count" in df.columns
        assert "% of Total" in df.columns

    def test_excludes_internal_remarks(self, controller_internal_remarks):
        df = controller_internal_remarks.get_due_wise_outstanding()
        remarks = df["Remarks"].str.lower().tolist()
        assert "internal" not in remarks

    def test_sorted_by_amount_descending(self, controller):
        df = controller.get_due_wise_outstanding()
        amounts = df["Total Outstanding (USD)"].tolist()
        assert amounts == sorted(amounts, reverse=True)

    def test_percentage_calculation(self, controller):
        df = controller.get_due_wise_outstanding()
        # Total should match filtered data
        assert df["% of Total"].sum() <= 100.1  # Allow small rounding

    def test_only_valid_remarks_included(self, controller):
        df = controller.get_due_wise_outstanding()
        valid = ["future due", "current due", "overdue", "credit memo", "unapplied"]
        for remark in df["Remarks"]:
            assert remark.lower() in valid


# ---------------------------------------------------------------------
# Test: get_due_wise_detail
# ---------------------------------------------------------------------


class TestGetDueWiseDetail:
    def test_returns_matching_rows(self, controller):
        detail = controller.get_due_wise_detail("Current Due")
        assert len(detail) == 1
        assert detail.iloc[0]["Customer Name"] == "Customer A"

    def test_case_insensitive_matching(self, controller):
        detail_lower = controller.get_due_wise_detail("current due")
        detail_upper = controller.get_due_wise_detail("CURRENT DUE")
        assert len(detail_lower) == len(detail_upper)

    def test_sorted_by_amount_descending(self, controller):
        detail = controller.get_due_wise_detail("Overdue")
        if len(detail) > 1:
            amounts = detail["Total in USD"].tolist()
            assert amounts == sorted(amounts, reverse=True)

    def test_no_matches_returns_empty(self, controller):
        detail = controller.get_due_wise_detail("NonExistent")
        assert len(detail) == 0


# ---------------------------------------------------------------------
# Test: get_credit_memo_total
# ---------------------------------------------------------------------


class TestGetCreditMemoTotal:
    def test_returns_correct_total(self, controller):
        assert controller.get_credit_memo_total() == 500.0

    def test_case_insensitive(self):
        df = pd.DataFrame(
            {
                "Remarks": ["CREDIT MEMO", "credit memo"],
                "Total in USD": [100.0, 200.0],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        assert controller.get_credit_memo_total() == 300.0


# ---------------------------------------------------------------------
# Test: get_unapplied_total
# ---------------------------------------------------------------------


class TestGetUnappliedTotal:
    def test_returns_correct_total(self, controller):
        assert controller.get_unapplied_total() == 800.0

    def test_no_unapplied_returns_zero(self):
        df = pd.DataFrame(
            {
                "Remarks": ["Current Due", "Overdue"],
                "Total in USD": [100.0, 200.0],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        assert controller.get_unapplied_total() == 0.0


# ---------------------------------------------------------------------
# Test: get_customer_wise_outstanding
# ---------------------------------------------------------------------


class TestGetCustomerWiseOutstanding:
    def test_returns_correct_columns(self, controller):
        df = controller.get_customer_wise_outstanding()

        assert "Customer Name" in df.columns
        assert "Total Outstanding (USD)" in df.columns

    def test_excludes_internal_remarks(self, controller_internal_remarks):
        df = controller_internal_remarks.get_customer_wise_outstanding()
        # Should have filtered out internal
        total = df["Total Outstanding (USD)"].sum()
        assert total == 2500.0  # 2000 + 500, excluding 1000 internal

    def test_adds_missing_due_columns(self):
        df = pd.DataFrame(
            {
                "Customer Name": ["A", "B"],
                "Remarks": ["Other", "Other"],
                "Total in USD": [100.0, 200.0],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        result = controller.get_customer_wise_outstanding()

        assert "Current Due" in result.columns
        assert "Overdue" in result.columns

    def test_sorted_by_total_descending(self, controller):
        df = controller.get_customer_wise_outstanding()
        amounts = df["Total Outstanding (USD)"].tolist()
        assert amounts == sorted(amounts, reverse=True)


# ---------------------------------------------------------------------
# Test: get_customer_wise_detail
# ---------------------------------------------------------------------


class TestGetCustomerWiseDetail:
    def test_returns_matching_rows(self, controller):
        detail = controller.get_customer_wise_detail("Customer A")
        assert len(detail) == 2  # Two invoices for Customer A

    def test_case_insensitive(self, controller):
        detail = controller.get_customer_wise_detail("customer a")
        assert len(detail) == 2

    def test_includes_remarks_column(self, controller):
        detail = controller.get_customer_wise_detail("Customer A")
        assert "Remarks" in detail.columns

    def test_no_matches_returns_empty(self, controller):
        detail = controller.get_customer_wise_detail("NonExistent")
        assert len(detail) == 0


# ---------------------------------------------------------------------
# Test: get_business_wise_outstanding
# ---------------------------------------------------------------------


class TestGetBusinessWiseOutstanding:
    def test_excludes_internal_org(self, controller):
        df = controller.get_business_wise_outstanding()
        org_names = df["New Org Name"].str.lower().tolist()
        assert "internal" not in org_names

    def test_returns_correct_columns(self, controller):
        df = controller.get_business_wise_outstanding()
        assert "New Org Name" in df.columns
        assert "Total Outstanding (USD)" in df.columns

    def test_adds_missing_due_columns(self):
        df = pd.DataFrame(
            {
                "New Org Name": ["BU1", "BU2"],
                "Remarks": ["Other", "Other"],
                "Total in USD": [100.0, 200.0],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        result = controller.get_business_wise_outstanding()

        assert "Current Due" in result.columns
        assert "Overdue" in result.columns

    def test_sorted_by_total_descending(self, controller):
        df = controller.get_business_wise_outstanding()
        amounts = df["Total Outstanding (USD)"].tolist()
        assert amounts == sorted(amounts, reverse=True)


# ---------------------------------------------------------------------
# Test: get_business_wise_detail
# ---------------------------------------------------------------------


class TestGetBusinessWiseDetail:
    def test_returns_matching_rows(self, controller):
        detail = controller.get_business_wise_detail("BU1")
        assert len(detail) == 2

    def test_case_insensitive(self, controller):
        detail = controller.get_business_wise_detail("bu1")
        assert len(detail) == 2

    def test_includes_remarks_column(self, controller):
        detail = controller.get_business_wise_detail("BU1")
        assert "Remarks" in detail.columns


# ---------------------------------------------------------------------
# Test: get_allocation_wise_outstanding
# ---------------------------------------------------------------------


class TestGetAllocationWiseOutstanding:
    def test_returns_correct_columns(self, controller):
        df = controller.get_allocation_wise_outstanding()

        assert "Allocation" in df.columns
        assert "Total Outstanding (USD)" in df.columns

    def test_excludes_internal_remarks(self, controller_internal_remarks):
        df = controller_internal_remarks.get_allocation_wise_outstanding()
        total = df["Total Outstanding (USD)"].sum()
        assert total == 2500.0

    def test_adds_missing_due_columns(self):
        df = pd.DataFrame(
            {
                "Allocation": ["A", "B"],
                "Remarks": ["Other", "Other"],
                "Total in USD": [100.0, 200.0],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        result = controller.get_allocation_wise_outstanding()

        assert "Current Due" in result.columns
        assert "Overdue" in result.columns


# ---------------------------------------------------------------------
# Test: get_allocation_remark_detail
# ---------------------------------------------------------------------


class TestGetAllocationRemarkDetail:
    def test_returns_matching_rows(self, controller):
        detail = controller.get_allocation_remark_detail("Nithya", "Current Due")
        assert len(detail) == 1

    def test_case_insensitive(self, controller):
        detail = controller.get_allocation_remark_detail("nithya", "current due")
        assert len(detail) == 1

    def test_includes_allocation_column(self, controller):
        detail = controller.get_allocation_remark_detail("Nithya", "Current Due")
        assert "Allocation" in detail.columns

    def test_no_matches_returns_empty(self, controller):
        detail = controller.get_allocation_remark_detail("NonExistent", "NonExistent")
        assert len(detail) == 0


# ---------------------------------------------------------------------
# Test: get_entities_wise_outstanding
# ---------------------------------------------------------------------


class TestGetEntitiesWiseOutstanding:
    def test_returns_correct_columns(self, controller):
        df = controller.get_entities_wise_outstanding()

        assert "Entities" in df.columns
        assert "Total Outstanding (USD)" in df.columns

    def test_adds_missing_due_columns(self):
        df = pd.DataFrame(
            {
                "Entities": ["E1", "E2"],
                "Remarks": ["Other", "Other"],
                "Total in USD": [100.0, 200.0],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        result = controller.get_entities_wise_outstanding()

        assert "Current Due" in result.columns
        assert "Overdue" in result.columns

    def test_sorted_by_total_descending(self, controller):
        df = controller.get_entities_wise_outstanding()
        amounts = df["Total Outstanding (USD)"].tolist()
        assert amounts == sorted(amounts, reverse=True)


# ---------------------------------------------------------------------
# Test: get_entities_remark_detail
# ---------------------------------------------------------------------


class TestGetEntitiesRemarkDetail:
    def test_returns_matching_rows(self, controller):
        detail = controller.get_entities_remark_detail("UST India", "Current Due")
        assert len(detail) == 1

    def test_case_insensitive(self, controller):
        detail = controller.get_entities_remark_detail("ust india", "current due")
        assert len(detail) == 1

    def test_includes_entities_column(self, controller):
        detail = controller.get_entities_remark_detail("UST India", "Current Due")
        assert "Entities" in detail.columns

    def test_no_matches_returns_empty(self, controller):
        detail = controller.get_entities_remark_detail("NonExistent", "NonExistent")
        assert len(detail) == 0


# ---------------------------------------------------------------------
# Test: get_ar_status_wise_outstanding
# ---------------------------------------------------------------------


class TestGetARStatusWiseOutstanding:
    def test_returns_correct_columns(self, controller):
        df = controller.get_ar_status_wise_outstanding()

        assert "AR Status" in df.columns
        assert "Total Outstanding (USD)" in df.columns

    def test_excludes_empty_ar_status(self, controller):
        df = controller.get_ar_status_wise_outstanding()
        ar_statuses = df["AR Status"].tolist()
        assert "" not in ar_statuses
        assert None not in ar_statuses

    def test_only_valid_remarks_included(self, controller):
        df = controller.get_ar_status_wise_outstanding()
        # Should only include valid remarks
        assert len(df) > 0

    def test_adds_missing_columns(self):
        df = pd.DataFrame(
            {
                "AR Status": ["Status1"],
                "Remarks": ["Other"],
                "Total in USD": [100.0],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        result = controller.get_ar_status_wise_outstanding()

        assert "Current Due" in result.columns
        assert "Future Due" in result.columns
        assert "Overdue" in result.columns

    def test_sorted_by_total_descending(self, controller):
        df = controller.get_ar_status_wise_outstanding()
        if len(df) > 1:
            amounts = df["Total Outstanding (USD)"].tolist()
            assert amounts == sorted(amounts, reverse=True)


# ---------------------------------------------------------------------
# Test: get_ar_status_remark_detail
# ---------------------------------------------------------------------


class TestGetARStatusRemarkDetail:
    def test_returns_matching_rows(self, controller):
        detail = controller.get_ar_status_remark_detail("In Progress", "Current Due")
        assert len(detail) == 1

    def test_case_insensitive(self, controller):
        detail = controller.get_ar_status_remark_detail("in progress", "current due")
        assert len(detail) == 1

    def test_includes_projection_column(self, controller):
        detail = controller.get_ar_status_remark_detail("In Progress", "Current Due")
        assert "Projection" in detail.columns

    def test_no_matches_returns_empty(self, controller):
        detail = controller.get_ar_status_remark_detail("NonExistent", "NonExistent")
        assert len(detail) == 0

    def test_sorted_by_amount_descending(self, controller):
        detail = controller.get_ar_status_remark_detail("In Progress", "Legal")
        if len(detail) > 1:
            amounts = detail["Total in USD"].tolist()
            assert amounts == sorted(amounts, reverse=True)


# ---------------------------------------------------------------------
# Edge Cases and Integration Tests
# ---------------------------------------------------------------------


class TestEdgeCases:
    def test_whitespace_handling_in_remarks(self):
        df = pd.DataFrame(
            {
                "Remarks": ["  Current Due  ", "Overdue ", " Credit Memo"],
                "Total in USD": [100.0, 200.0, 300.0],
                "Customer Name": ["A", "B", "C"],
                "New Org Name": ["BU1", "BU2", "BU3"],
                "Allocation": ["X", "Y", "Z"],
                "Entities": ["E1", "E2", "E3"],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        result = controller.get_due_wise_outstanding()

        # Should handle whitespace correctly
        assert len(result) == 3

    def test_special_characters_in_projection(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week-1", "Week/2", "Week@3"],
                "Total in USD": [100.0, 200.0, 300.0],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        summary = controller.get_weekly_inflow_summary()

        assert len(summary) == 3

    def test_numeric_reference_conversion(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week1"],
                "Total in USD": [100.0],
                "Reference": [12345],  # Numeric reference
                "Customer Name": ["A"],
                "New Org Name": ["BU1"],
                "AR Status": ["Active"],
                "AR Comments": ["Comment"],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        detail = controller.get_projection_detail("Week1")

        assert detail["Reference"].dtype == object
        assert detail["Reference"].iloc[0] == "12345"

    def test_large_dataset_performance(self):
        # Create a larger dataset
        import numpy as np

        n = 10000
        df = pd.DataFrame(
            {
                "Projection": np.random.choice(["Week1", "Week2", "Week3"], n),
                "Total in USD": np.random.uniform(100, 10000, n),
                "Remarks": np.random.choice(
                    ["Current Due", "Overdue", "Future Due"], n
                ),
                "Customer Name": [f"Customer {i % 100}" for i in range(n)],
                "New Org Name": np.random.choice(["BU1", "BU2", "BU3"], n),
                "Allocation": np.random.choice(["A", "B", "C"], n),
                "Entities": np.random.choice(["E1", "E2", "E3"], n),
                "AR Status": np.random.choice(["Active", "Pending", "Resolved"], n),
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())

        # Should complete without error
        summary = controller.get_weekly_inflow_summary()
        assert len(summary) > 0

        customer_df = controller.get_customer_wise_outstanding()
        assert len(customer_df) > 0


class TestZeroAndNegativeValues:
    def test_zero_totals(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week1", "Week2"],
                "Total in USD": [0.0, 0.0],
                "Remarks": ["Current Due", "Overdue"],
                "Customer Name": ["A", "B"],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())

        assert controller.get_grand_total() == 0.0
        summary = controller.get_weekly_inflow_summary()
        assert summary["% of Total"].eq(0.0).all()

    def test_negative_values(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week1", "Week2"],
                "Total in USD": [-100.0, 200.0],
                "Remarks": ["Credit Memo", "Current Due"],
                "Customer Name": ["A", "B"],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())

        assert controller.get_grand_total() == 100.0
        assert controller.get_credit_memo_total() == -100.0


# ---------------------------------------------------------------------
# Test: Missing column scenarios
# ---------------------------------------------------------------------


class TestMissingColumns:
    def test_detail_with_missing_reference(self):
        df = pd.DataFrame(
            {
                "Projection": ["Week1"],
                "Total in USD": [100.0],
                "Customer Name": ["A"],
                # No Reference column
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        detail = controller.get_projection_detail("Week1")

        assert "Reference" not in detail.columns
        assert len(detail) == 1

    def test_due_detail_with_missing_columns(self):
        df = pd.DataFrame(
            {
                "Remarks": ["Current Due"],
                "Total in USD": [100.0],
                "Customer Name": ["A"],
            }
        )

        class DummyModel:
            @property
            def dataframe(self):
                return df

        controller = ProjectionController(DummyModel())
        detail = controller.get_due_wise_detail("Current Due")

        assert "Customer Name" in detail.columns
        assert "AR Comments" not in detail.columns