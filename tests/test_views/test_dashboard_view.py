"""
Complete test suite for views/dashboard_view.py

Key corrections vs. the old test file:
- render_kpi_cards() now takes 12 parameters and creates 9 columns / 9 metrics.
- render_kpi_cards_no_credit_unapplied() creates 6 columns, 6 metric calls.
- render_due_wise_outstanding uses st.columns([2, 1]).
- Navigation anchor IDs verified against the actual source sections list.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import views.dashboard_view as dv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_col():
    col = MagicMock()
    col.__enter__ = MagicMock(return_value=col)
    col.__exit__ = MagicMock(return_value=False)
    return col


def _cols(n):
    return [_mock_col() for _ in range(n)]


def _no_selection():
    ev = MagicMock()
    ev.selection = None
    return ev


def _selection(points):
    ev = MagicMock()
    ev.selection = {"points": points}
    return ev


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def weekly_df():
    return pd.DataFrame({
        "Projection": ["Feb 1st week", "Feb 2nd week", "Mar 1st week"],
        "Total Inflow (USD)": [100_000.0, 150_000.0, 200_000.0],
        "Invoice Count": [10, 15, 20],
        "% of Total": [22.22, 33.33, 44.45],
    })


@pytest.fixture()
def due_df():
    return pd.DataFrame({
        "Remarks": ["Current Due", "Overdue", "Future Due"],
        "Total Outstanding (USD)": [500_000.0, 300_000.0, 200_000.0],
        "Invoice Count": [50, 30, 20],
        "% of Total": [50.0, 30.0, 20.0],
    })


@pytest.fixture()
def customer_df():
    return pd.DataFrame({
        "Customer Name": ["Customer A", "Customer B", "Customer C"],
        "Current Due": [100_000.0, 50_000.0, 25_000.0],
        "Overdue": [50_000.0, 25_000.0, 10_000.0],
        "Future Due": [20_000.0, 10_000.0, 5_000.0],
        "Total Outstanding (USD)": [170_000.0, 85_000.0, 40_000.0],
    })


@pytest.fixture()
def business_df():
    return pd.DataFrame({
        "New Org Name": ["BU1", "BU2", "BU3"],
        "Current Due": [200_000.0, 100_000.0, 50_000.0],
        "Overdue": [100_000.0, 50_000.0, 25_000.0],
        "Future Due": [50_000.0, 25_000.0, 10_000.0],
        "Total Outstanding (USD)": [350_000.0, 175_000.0, 85_000.0],
    })


@pytest.fixture()
def allocation_df():
    return pd.DataFrame({
        "Allocation": ["Nithya", "John", "Unallocated"],
        "Current Due": [150_000.0, 100_000.0, 50_000.0],
        "Overdue": [75_000.0, 50_000.0, 25_000.0],
        "Future Due": [30_000.0, 20_000.0, 10_000.0],
        "Total Outstanding (USD)": [255_000.0, 170_000.0, 85_000.0],
    })


@pytest.fixture()
def entities_df():
    return pd.DataFrame({
        "Entities": ["UST India", "UST Corp", "UST UK"],
        "Current Due": [300_000.0, 200_000.0, 100_000.0],
        "Overdue": [150_000.0, 100_000.0, 50_000.0],
        "Future Due": [75_000.0, 50_000.0, 25_000.0],
        "Total Outstanding (USD)": [525_000.0, 350_000.0, 175_000.0],
    })


@pytest.fixture()
def ar_status_df():
    return pd.DataFrame({
        "AR Status": ["In Progress", "Pending", "Resolved"],
        "Current Due": [200_000.0, 150_000.0, 50_000.0],
        "Future Due": [100_000.0, 75_000.0, 25_000.0],
        "Overdue": [80_000.0, 60_000.0, 20_000.0],
        "Credit Memo": [10_000.0, 5_000.0, 2_000.0],
        "Unapplied": [5_000.0, 3_000.0, 1_000.0],
        "Legal": [15_000.0, 10_000.0, 5_000.0],
        "Total Outstanding (USD)": [410_000.0, 303_000.0, 103_000.0],
    })


@pytest.fixture()
def empty_df():
    return pd.DataFrame()


@pytest.fixture()
def mock_controller():
    ctrl = MagicMock()
    ctrl.get_projection_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer A"], "Reference": ["INV001"],
        "New Org Name": ["BU1"], "AR Status": ["In Progress"],
        "Total in USD": [10_000.0],
    })
    ctrl.get_due_wise_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer B"], "Reference": ["INV002"],
        "Total in USD": [20_000.0],
    })
    ctrl.get_customer_wise_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer A"], "Reference": ["INV001"],
        "Total in USD": [15_000.0],
    })
    ctrl.get_business_wise_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer C"], "Reference": ["INV003"],
        "Total in USD": [25_000.0],
    })
    ctrl.get_allocation_remark_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer D"], "Reference": ["INV004"],
        "Total in USD": [30_000.0],
    })
    ctrl.get_entities_remark_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer E"], "Reference": ["INV005"],
        "Total in USD": [35_000.0],
    })
    ctrl.get_ar_status_remark_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer F"], "Reference": ["INV006"],
        "Total in USD": [40_000.0],
    })
    return ctrl


# ===========================================================================
# Test: Helper functions
# ===========================================================================

class TestGetRemarkCols:
    def test_excludes_id_and_total(self, customer_df):
        result = dv._get_remark_cols(customer_df, "Customer Name")
        assert "Customer Name" not in result
        assert "Total Outstanding (USD)" not in result

    def test_includes_remark_columns(self, customer_df):
        result = dv._get_remark_cols(customer_df, "Customer Name")
        assert set(result) == {"Current Due", "Overdue", "Future Due"}

    def test_preserves_column_order(self, customer_df):
        assert dv._get_remark_cols(customer_df, "Customer Name") == [
            "Current Due", "Overdue", "Future Due"
        ]

    def test_different_id_column(self, allocation_df):
        result = dv._get_remark_cols(allocation_df, "Allocation")
        assert "Allocation" not in result
        assert len(result) == 3

    def test_empty_df_returns_empty_list(self, empty_df):
        assert dv._get_remark_cols(empty_df, "ID") == []

    def test_only_id_and_total_returns_empty(self):
        df = pd.DataFrame({"X": [1], "Total Outstanding (USD)": [1.0]})
        assert dv._get_remark_cols(df, "X") == []


class TestRemarkColor:
    def test_returns_string(self):
        assert isinstance(dv._remark_color("Overdue"), str)

    def test_non_empty(self):
        assert len(dv._remark_color("Current Due")) > 0

    def test_unknown_returns_fallback_string(self):
        result = dv._remark_color("ZZZUnknown999")
        assert isinstance(result, str) and len(result) > 0

    def test_empty_string_returns_fallback(self):
        assert isinstance(dv._remark_color(""), str)

    def test_same_remark_same_color(self):
        assert dv._remark_color("Overdue") == dv._remark_color("Overdue")


# ===========================================================================
# Test: render_page_header
# ===========================================================================

class TestRenderPageHeader:
    @patch("views.dashboard_view.components")
    @patch("views.dashboard_view.st")
    @patch("utils.sharepoint_fetch.get_latest_file_info")
    def test_calls_st_title(self, mock_fi, mock_st, mock_comp):
        mock_fi.return_value = None
        dv.render_page_header()
        mock_st.title.assert_called_once()

    @patch("views.dashboard_view.components")
    @patch("views.dashboard_view.st")
    @patch("utils.sharepoint_fetch.get_latest_file_info")
    def test_calls_st_divider(self, mock_fi, mock_st, mock_comp):
        mock_fi.return_value = None
        dv.render_page_header()
        mock_st.divider.assert_called()

    @patch("views.dashboard_view.components")
    @patch("views.dashboard_view.st")
    @patch("utils.sharepoint_fetch.get_latest_file_info")
    def test_calls_components_html_once(self, mock_fi, mock_st, mock_comp):
        mock_fi.return_value = None
        dv.render_page_header()
        mock_comp.html.assert_called_once()

    @patch("views.dashboard_view.components")
    @patch("views.dashboard_view.st")
    @patch("utils.sharepoint_fetch.get_latest_file_info")
    def test_nav_html_contains_all_anchors(self, mock_fi, mock_st, mock_comp):
        mock_fi.return_value = None
        dv.render_page_header()
        html = mock_comp.html.call_args[0][0]
        for anchor in (
            "ar-weekly_inflow", "ar-status_wise", "ar-due_wise",
            "ar-customer_wise", "ar-business_wise",
            "ar-allocation_wise", "ar-entities_wise",
        ):
            assert anchor in html

    @patch("views.dashboard_view.components")
    @patch("views.dashboard_view.st")
    @patch("utils.sharepoint_fetch.get_latest_file_info")
    def test_renders_markdown_when_file_info_present(self, mock_fi, mock_st, mock_comp):
        mock_fi.return_value = {
            "name": "AR.xlsx",
            "local_time": datetime(2024, 6, 15, 10, 30, tzinfo=timezone.utc),
        }
        dv.render_page_header()
        mock_st.markdown.assert_called()

    @patch("views.dashboard_view.components")
    @patch("views.dashboard_view.st")
    @patch("utils.sharepoint_fetch.get_latest_file_info")
    def test_no_file_info_markdown_block_skipped(self, mock_fi, mock_st, mock_comp):
        mock_fi.return_value = None
        dv.render_page_header()
        file_info_calls = [
            c for c in mock_st.markdown.call_args_list
            if "Latest Sheet Update" in str(c)
        ]
        assert len(file_info_calls) == 0


# ===========================================================================
# Test: render_kpi_cards  (9 columns, 9 metrics)
# ===========================================================================

class TestRenderKpiCards:
    def _call(self, mock_st, **overrides):
        mock_st.columns.return_value = _cols(9)
        params = dict(
            grand_total=1_000_000.0, expected_inflow=800_000.0,
            next_month_1st_week=200_000.0, dispute_total=100_000.0,
            invoice_count=500, credit_memo_total=50_000.0,
            current_due=300_000.0, future_due=200_000.0,
            overdue_total=150_000.0, unapplied_total=25_000.0,
            legal_total=10_000.0, next_month_name="March",
        )
        params.update(overrides)
        dv.render_kpi_cards(**params)

    @patch("views.dashboard_view.st")
    def test_creates_nine_columns(self, mock_st):
        self._call(mock_st)
        mock_st.columns.assert_called_once_with(9)

    @patch("views.dashboard_view.st")
    def test_renders_nine_metrics(self, mock_st):
        self._call(mock_st)
        assert mock_st.metric.call_count == 9

    @patch("views.dashboard_view.st")
    def test_calls_divider(self, mock_st):
        self._call(mock_st)
        mock_st.divider.assert_called()

    @patch("views.dashboard_view.st")
    def test_next_month_name_in_a_label(self, mock_st):
        self._call(mock_st, next_month_name="April")
        all_label_args = " ".join(
            str(c) for c in mock_st.metric.call_args_list
        )
        assert "April" in all_label_args

    @patch("views.dashboard_view.st")
    def test_zero_values_do_not_raise(self, mock_st):
        self._call(mock_st, grand_total=0.0, expected_inflow=0.0,
                   next_month_1st_week=0.0, dispute_total=0.0, invoice_count=0)


# ===========================================================================
# Test: render_kpi_cards_no_credit_unapplied  (6 columns, 6 metrics)
# ===========================================================================

class TestRenderKpiCardsNoCreditUnapplied:
    def _call(self, mock_st, **overrides):
        mock_st.columns.return_value = _cols(6)
        params = dict(
            grand_total=100_000.0, expected_inflow=80_000.0,
            dispute_total=10_000.0, invoice_count=50,
        )
        params.update(overrides)
        dv.render_kpi_cards_no_credit_unapplied(**params)

    @patch("views.dashboard_view.st")
    def test_creates_six_columns(self, mock_st):
        self._call(mock_st)
        mock_st.columns.assert_called_once_with(6)

    @patch("views.dashboard_view.st")
    def test_renders_six_metrics(self, mock_st):
        self._call(mock_st)
        assert mock_st.metric.call_count == 6

    @patch("views.dashboard_view.st")
    def test_calls_divider(self, mock_st):
        self._call(mock_st)
        mock_st.divider.assert_called()

    @patch("views.dashboard_view.st")
    def test_zero_values_do_not_raise(self, mock_st):
        self._call(mock_st, grand_total=0.0, invoice_count=0)


# ===========================================================================
# Test: render_weekly_inflow_section
# ===========================================================================

class TestRenderWeeklyInflowSection:
    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_calls_subheader(self, mock_st, mock_px, weekly_df):
        mock_px.bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _no_selection()
        dv.render_weekly_inflow_section(weekly_df, controller=None)
        mock_st.subheader.assert_called()

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_calls_px_bar(self, mock_st, mock_px, weekly_df):
        mock_px.bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _no_selection()
        dv.render_weekly_inflow_section(weekly_df, controller=None)
        mock_px.bar.assert_called_once()

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_template_kwarg_present(self, mock_st, mock_px, weekly_df):
        mock_px.bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _no_selection()
        dv.render_weekly_inflow_section(weekly_df, controller=None)
        assert "template" in mock_px.bar.call_args[1]

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_summary_dataframe_rendered(self, mock_st, mock_px, weekly_df):
        mock_px.bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _no_selection()
        dv.render_weekly_inflow_section(weekly_df, controller=None)
        mock_st.dataframe.assert_called()

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_no_drill_down_without_selection(self, mock_st, mock_px, weekly_df, mock_controller):
        mock_px.bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _no_selection()
        dv.render_weekly_inflow_section(weekly_df, controller=mock_controller)
        mock_controller.get_projection_detail.assert_not_called()

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_drill_down_x_key(self, mock_st, mock_px, weekly_df, mock_controller):
        mock_px.bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _selection([{"x": "Feb 1st week"}])
        dv.render_weekly_inflow_section(weekly_df, controller=mock_controller)
        mock_controller.get_projection_detail.assert_called_once_with("Feb 1st week")

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_drill_down_label_fallback(self, mock_st, mock_px, weekly_df, mock_controller):
        mock_px.bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _selection([{"label": "Mar 1st week"}])
        dv.render_weekly_inflow_section(weekly_df, controller=mock_controller)
        mock_controller.get_projection_detail.assert_called_once_with("Mar 1st week")

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_empty_detail_shows_info(self, mock_st, mock_px, weekly_df, mock_controller):
        mock_px.bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _selection([{"x": "Feb 1st week"}])
        mock_controller.get_projection_detail.return_value = pd.DataFrame()
        dv.render_weekly_inflow_section(weekly_df, controller=mock_controller)
        mock_st.info.assert_called()

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_empty_points_no_drill_down(self, mock_st, mock_px, weekly_df, mock_controller):
        mock_px.bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _selection([])
        dv.render_weekly_inflow_section(weekly_df, controller=mock_controller)
        mock_controller.get_projection_detail.assert_not_called()

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_point_with_no_x_or_label_no_drill_down(self, mock_st, mock_px, weekly_df, mock_controller):
        mock_px.bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _selection([{"curve_number": 0}])
        dv.render_weekly_inflow_section(weekly_df, controller=mock_controller)
        mock_controller.get_projection_detail.assert_not_called()


# ===========================================================================
# Test: render_ar_status_wise_outstanding
# ===========================================================================

class TestRenderARStatusWiseOutstanding:
    def _setup(self, mock_st, mock_go):
        mock_st.columns.return_value = _cols(5)
        mock_go.Figure.return_value = MagicMock()
        mock_go.Bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _no_selection()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_calls_subheader(self, mock_st, mock_go, ar_status_df):
        self._setup(mock_st, mock_go)
        dv.render_ar_status_wise_outstanding(ar_status_df, controller=None)
        mock_st.subheader.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_empty_df_shows_info(self, mock_st, mock_go, empty_df):
        dv.render_ar_status_wise_outstanding(empty_df, controller=None)
        mock_st.info.assert_called_with("No data available.")

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_creates_go_figure(self, mock_st, mock_go, ar_status_df):
        self._setup(mock_st, mock_go)
        dv.render_ar_status_wise_outstanding(ar_status_df, controller=None)
        mock_go.Figure.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_five_metric_cards(self, mock_st, mock_go, ar_status_df):
        self._setup(mock_st, mock_go)
        dv.render_ar_status_wise_outstanding(ar_status_df, controller=None)
        assert mock_st.metric.call_count == 5

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_drill_down_customdata(self, mock_st, mock_go, ar_status_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = _selection(
            [{"x": "In Progress", "customdata": ["Overdue"]}]
        )
        dv.render_ar_status_wise_outstanding(ar_status_df, controller=mock_controller)
        mock_controller.get_ar_status_remark_detail.assert_called_once_with(
            "In Progress", "Overdue"
        )

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_drill_down_curve_number_fallback(self, mock_st, mock_go, ar_status_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = _selection(
            [{"x": "Pending", "curve_number": 0}]
        )
        dv.render_ar_status_wise_outstanding(ar_status_df, controller=mock_controller)
        mock_controller.get_ar_status_remark_detail.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_no_drill_down_no_selection(self, mock_st, mock_go, ar_status_df, mock_controller):
        self._setup(mock_st, mock_go)
        dv.render_ar_status_wise_outstanding(ar_status_df, controller=mock_controller)
        mock_controller.get_ar_status_remark_detail.assert_not_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_empty_detail_shows_info(self, mock_st, mock_go, ar_status_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = _selection(
            [{"x": "In Progress", "customdata": ["Overdue"]}]
        )
        mock_controller.get_ar_status_remark_detail.return_value = pd.DataFrame()
        dv.render_ar_status_wise_outstanding(ar_status_df, controller=mock_controller)
        mock_st.info.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_summary_dataframe_rendered(self, mock_st, mock_go, ar_status_df):
        self._setup(mock_st, mock_go)
        dv.render_ar_status_wise_outstanding(ar_status_df, controller=None)
        mock_st.dataframe.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_empty_points_no_drill_down(self, mock_st, mock_go, ar_status_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = _selection([])
        dv.render_ar_status_wise_outstanding(ar_status_df, controller=mock_controller)
        mock_controller.get_ar_status_remark_detail.assert_not_called()


# ===========================================================================
# Test: render_due_wise_outstanding
# ===========================================================================

class TestRenderDueWiseOutstanding:
    def _setup(self, mock_st, mock_px):
        mock_st.columns.return_value = _cols(2)
        mock_px.bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _no_selection()

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_calls_subheader(self, mock_st, mock_px, due_df):
        self._setup(mock_st, mock_px)
        dv.render_due_wise_outstanding(due_df, controller=None)
        mock_st.subheader.assert_called()

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_empty_df_shows_info(self, mock_st, mock_px, empty_df):
        dv.render_due_wise_outstanding(empty_df, controller=None)
        mock_st.info.assert_called_with("No data available.")

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_columns_called_with_2_1(self, mock_st, mock_px, due_df):
        self._setup(mock_st, mock_px)
        dv.render_due_wise_outstanding(due_df, controller=None)
        mock_st.columns.assert_called_with([2, 1])

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_bar_chart_rendered(self, mock_st, mock_px, due_df):
        self._setup(mock_st, mock_px)
        dv.render_due_wise_outstanding(due_df, controller=None)
        mock_px.bar.assert_called_once()

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_template_kwarg_in_bar(self, mock_st, mock_px, due_df):
        self._setup(mock_st, mock_px)
        dv.render_due_wise_outstanding(due_df, controller=None)
        assert "template" in mock_px.bar.call_args[1]

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_dataframe_rendered(self, mock_st, mock_px, due_df):
        self._setup(mock_st, mock_px)
        dv.render_due_wise_outstanding(due_df, controller=None)
        mock_st.dataframe.assert_called()

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_drill_down_on_click(self, mock_st, mock_px, due_df, mock_controller):
        self._setup(mock_st, mock_px)
        mock_st.plotly_chart.return_value = _selection([{"x": "Overdue"}])
        dv.render_due_wise_outstanding(due_df, controller=mock_controller)
        mock_controller.get_due_wise_detail.assert_called_once_with("Overdue")

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_no_drill_down_no_selection(self, mock_st, mock_px, due_df, mock_controller):
        self._setup(mock_st, mock_px)
        dv.render_due_wise_outstanding(due_df, controller=mock_controller)
        mock_controller.get_due_wise_detail.assert_not_called()

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_empty_detail_shows_info(self, mock_st, mock_px, due_df, mock_controller):
        self._setup(mock_st, mock_px)
        mock_st.plotly_chart.return_value = _selection([{"x": "Current Due"}])
        mock_controller.get_due_wise_detail.return_value = pd.DataFrame()
        dv.render_due_wise_outstanding(due_df, controller=mock_controller)
        mock_st.info.assert_called()

    @patch("views.dashboard_view.px")
    @patch("views.dashboard_view.st")
    def test_zero_total_does_not_raise(self, mock_st, mock_px):
        self._setup(mock_st, mock_px)
        df = pd.DataFrame({
            "Remarks": ["Current Due"], "Total Outstanding (USD)": [0.0],
            "Invoice Count": [0], "% of Total": [0.0],
        })
        dv.render_due_wise_outstanding(df, controller=None)


# ===========================================================================
# Test: render_customer_wise_outstanding
# ===========================================================================

class TestRenderCustomerWiseOutstanding:
    def _setup(self, mock_st, mock_go):
        mock_st.columns.return_value = _cols(2)
        mock_go.Figure.return_value = MagicMock()
        mock_go.Pie.return_value = MagicMock()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_calls_subheader(self, mock_st, mock_go, customer_df):
        self._setup(mock_st, mock_go)
        dv.render_customer_wise_outstanding(customer_df, controller=None)
        mock_st.subheader.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_empty_df_shows_info(self, mock_st, mock_go, empty_df):
        dv.render_customer_wise_outstanding(empty_df, controller=None)
        mock_st.info.assert_called_with("No data available.")

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_pie_chart_created(self, mock_st, mock_go, customer_df):
        self._setup(mock_st, mock_go)
        dv.render_customer_wise_outstanding(customer_df, controller=None)
        mock_go.Pie.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_summary_dataframe_rendered(self, mock_st, mock_go, customer_df):
        self._setup(mock_st, mock_go)
        dv.render_customer_wise_outstanding(customer_df, controller=None)
        mock_st.dataframe.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_selectbox_drill_down(self, mock_st, mock_go, customer_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.selectbox.return_value = "Customer A"
        dv.render_customer_wise_outstanding(customer_df, controller=mock_controller)
        mock_controller.get_customer_wise_detail.assert_called_once_with("Customer A")

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_default_selectbox_no_drill_down(self, mock_st, mock_go, customer_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.selectbox.return_value = "— Select a customer —"
        dv.render_customer_wise_outstanding(customer_df, controller=mock_controller)
        mock_controller.get_customer_wise_detail.assert_not_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_others_bucket_for_more_than_10_customers(self, mock_st, mock_go):
        self._setup(mock_st, mock_go)
        df = pd.DataFrame({
            "Customer Name": [f"C{i}" for i in range(15)],
            "Total Outstanding (USD)": [float(10_000 * (15 - i)) for i in range(15)],
            "Current Due": [5_000.0] * 15,
            "Overdue": [3_000.0] * 15,
        })
        dv.render_customer_wise_outstanding(df, controller=None)
        assert "Others" in mock_go.Pie.call_args[1].get("labels", [])

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_no_others_for_ten_or_fewer(self, mock_st, mock_go, customer_df):
        self._setup(mock_st, mock_go)
        dv.render_customer_wise_outstanding(customer_df, controller=None)
        assert "Others" not in mock_go.Pie.call_args[1].get("labels", [])

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_empty_detail_shows_info(self, mock_st, mock_go, customer_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.selectbox.return_value = "Customer A"
        mock_controller.get_customer_wise_detail.return_value = pd.DataFrame()
        dv.render_customer_wise_outstanding(customer_df, controller=mock_controller)
        mock_st.info.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_two_metric_cards(self, mock_st, mock_go, customer_df):
        self._setup(mock_st, mock_go)
        dv.render_customer_wise_outstanding(customer_df, controller=None)
        assert mock_st.metric.call_count >= 2


# ===========================================================================
# Test: render_business_wise_outstanding
# ===========================================================================

class TestRenderBusinessWiseOutstanding:
    def _setup(self, mock_st, mock_go):
        mock_st.columns.return_value = _cols(2)
        mock_go.Figure.return_value = MagicMock()
        mock_go.Pie.return_value = MagicMock()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_calls_subheader(self, mock_st, mock_go, business_df):
        self._setup(mock_st, mock_go)
        dv.render_business_wise_outstanding(business_df, controller=None)
        mock_st.subheader.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_empty_df_shows_info(self, mock_st, mock_go, empty_df):
        dv.render_business_wise_outstanding(empty_df, controller=None)
        mock_st.info.assert_called_with("No data available.")

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_pie_chart_created(self, mock_st, mock_go, business_df):
        self._setup(mock_st, mock_go)
        dv.render_business_wise_outstanding(business_df, controller=None)
        mock_go.Pie.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_selectbox_drill_down(self, mock_st, mock_go, business_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.selectbox.return_value = "BU1"
        dv.render_business_wise_outstanding(business_df, controller=mock_controller)
        mock_controller.get_business_wise_detail.assert_called_once_with("BU1")

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_default_selectbox_no_drill_down(self, mock_st, mock_go, business_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.selectbox.return_value = "— Select a business unit —"
        dv.render_business_wise_outstanding(business_df, controller=mock_controller)
        mock_controller.get_business_wise_detail.assert_not_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_summary_dataframe_rendered(self, mock_st, mock_go, business_df):
        self._setup(mock_st, mock_go)
        dv.render_business_wise_outstanding(business_df, controller=None)
        mock_st.dataframe.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_empty_detail_shows_info(self, mock_st, mock_go, business_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.selectbox.return_value = "BU1"
        mock_controller.get_business_wise_detail.return_value = pd.DataFrame()
        dv.render_business_wise_outstanding(business_df, controller=mock_controller)
        mock_st.info.assert_called()


# ===========================================================================
# Test: render_allocation_wise_outstanding
# ===========================================================================

class TestRenderAllocationWiseOutstanding:
    def _setup(self, mock_st, mock_go):
        mock_st.columns.return_value = _cols(2)
        mock_go.Figure.return_value = MagicMock()
        mock_go.Bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _no_selection()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_calls_subheader(self, mock_st, mock_go, allocation_df):
        self._setup(mock_st, mock_go)
        dv.render_allocation_wise_outstanding(allocation_df, controller=None)
        mock_st.subheader.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_empty_df_shows_info(self, mock_st, mock_go, empty_df):
        dv.render_allocation_wise_outstanding(empty_df, controller=None)
        mock_st.info.assert_called_with("No data available.")

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_grouped_bar_chart_created(self, mock_st, mock_go, allocation_df):
        self._setup(mock_st, mock_go)
        dv.render_allocation_wise_outstanding(allocation_df, controller=None)
        mock_go.Figure.assert_called()
        mock_go.Bar.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_drill_down_customdata_list(self, mock_st, mock_go, allocation_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = _selection(
            [{"x": "Nithya", "customdata": ["Overdue"]}]
        )
        dv.render_allocation_wise_outstanding(allocation_df, controller=mock_controller)
        mock_controller.get_allocation_remark_detail.assert_called_once_with("Nithya", "Overdue")

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_drill_down_customdata_string(self, mock_st, mock_go, allocation_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = _selection(
            [{"x": "John", "customdata": "Current Due"}]
        )
        dv.render_allocation_wise_outstanding(allocation_df, controller=mock_controller)
        mock_controller.get_allocation_remark_detail.assert_called_once_with("John", "Current Due")

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_drill_down_curve_number_fallback(self, mock_st, mock_go, allocation_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = _selection([{"x": "Unallocated", "curveNumber": 0}])
        dv.render_allocation_wise_outstanding(allocation_df, controller=mock_controller)
        mock_controller.get_allocation_remark_detail.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_empty_points_no_drill_down(self, mock_st, mock_go, allocation_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = _selection([])
        dv.render_allocation_wise_outstanding(allocation_df, controller=mock_controller)
        mock_controller.get_allocation_remark_detail.assert_not_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_none_event_no_drill_down(self, mock_st, mock_go, allocation_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = None
        dv.render_allocation_wise_outstanding(allocation_df, controller=mock_controller)
        mock_controller.get_allocation_remark_detail.assert_not_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_event_without_selection_attr_no_drill_down(self, mock_st, mock_go, allocation_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = MagicMock(spec=[])
        dv.render_allocation_wise_outstanding(allocation_df, controller=mock_controller)
        mock_controller.get_allocation_remark_detail.assert_not_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_empty_detail_shows_info(self, mock_st, mock_go, allocation_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = _selection(
            [{"x": "Nithya", "customdata": ["Overdue"]}]
        )
        mock_controller.get_allocation_remark_detail.return_value = pd.DataFrame()
        dv.render_allocation_wise_outstanding(allocation_df, controller=mock_controller)
        mock_st.info.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_missing_overdue_column_does_not_raise(self, mock_st, mock_go):
        self._setup(mock_st, mock_go)
        df = pd.DataFrame({
            "Allocation": ["A", "B"],
            "Current Due": [100.0, 200.0],
            "Total Outstanding (USD)": [100.0, 200.0],
        })
        dv.render_allocation_wise_outstanding(df, controller=None)

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_summary_dataframe_rendered(self, mock_st, mock_go, allocation_df):
        self._setup(mock_st, mock_go)
        dv.render_allocation_wise_outstanding(allocation_df, controller=None)
        mock_st.dataframe.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_two_metric_cards(self, mock_st, mock_go, allocation_df):
        self._setup(mock_st, mock_go)
        dv.render_allocation_wise_outstanding(allocation_df, controller=None)
        assert mock_st.metric.call_count >= 2


# ===========================================================================
# Test: render_entities_wise_outstanding
# ===========================================================================

class TestRenderEntitiesWiseOutstanding:
    def _setup(self, mock_st, mock_go):
        mock_st.columns.return_value = _cols(2)
        mock_go.Figure.return_value = MagicMock()
        mock_go.Bar.return_value = MagicMock()
        mock_st.plotly_chart.return_value = _no_selection()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_calls_subheader(self, mock_st, mock_go, entities_df):
        self._setup(mock_st, mock_go)
        dv.render_entities_wise_outstanding(entities_df, controller=None)
        mock_st.subheader.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_empty_df_shows_info(self, mock_st, mock_go, empty_df):
        dv.render_entities_wise_outstanding(empty_df, controller=None)
        mock_st.info.assert_called_with("No data available.")

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_grouped_bar_chart_created(self, mock_st, mock_go, entities_df):
        self._setup(mock_st, mock_go)
        dv.render_entities_wise_outstanding(entities_df, controller=None)
        mock_go.Figure.assert_called()
        mock_go.Bar.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_drill_down_customdata(self, mock_st, mock_go, entities_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = _selection(
            [{"x": "UST India", "customdata": ["Overdue"]}]
        )
        dv.render_entities_wise_outstanding(entities_df, controller=mock_controller)
        mock_controller.get_entities_remark_detail.assert_called_once_with("UST India", "Overdue")

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_drill_down_curve_number_fallback(self, mock_st, mock_go, entities_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = _selection([{"x": "UST Corp", "curveNumber": 1}])
        dv.render_entities_wise_outstanding(entities_df, controller=mock_controller)
        mock_controller.get_entities_remark_detail.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_no_drill_down_no_selection(self, mock_st, mock_go, entities_df, mock_controller):
        self._setup(mock_st, mock_go)
        dv.render_entities_wise_outstanding(entities_df, controller=mock_controller)
        mock_controller.get_entities_remark_detail.assert_not_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_empty_detail_shows_info(self, mock_st, mock_go, entities_df, mock_controller):
        self._setup(mock_st, mock_go)
        mock_st.plotly_chart.return_value = _selection(
            [{"x": "UST India", "customdata": ["Overdue"]}]
        )
        mock_controller.get_entities_remark_detail.return_value = pd.DataFrame()
        dv.render_entities_wise_outstanding(entities_df, controller=mock_controller)
        mock_st.info.assert_called()

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_two_metric_cards(self, mock_st, mock_go, entities_df):
        self._setup(mock_st, mock_go)
        dv.render_entities_wise_outstanding(entities_df, controller=None)
        assert mock_st.metric.call_count >= 2

    @patch("views.dashboard_view.go")
    @patch("views.dashboard_view.st")
    def test_summary_dataframe_rendered(self, mock_st, mock_go, entities_df):
        self._setup(mock_st, mock_go)
        dv.render_entities_wise_outstanding(entities_df, controller=None)
        mock_st.dataframe.assert_called()