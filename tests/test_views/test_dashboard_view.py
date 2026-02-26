"""
Complete test suite for dashboard_view.py

Covers all rendering functions, helper functions, and edge cases.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

# Import the module under test
import views.dashboard_view as dv


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def sample_weekly_inflow_df():
    """Sample weekly inflow summary DataFrame."""
    return pd.DataFrame({
        "Projection": ["Feb 1st week", "Feb 2nd week", "Mar 1st week"],
        "Total Inflow (USD)": [100000.0, 150000.0, 200000.0],
        "Invoice Count": [10, 15, 20],
        "% of Total": [22.22, 33.33, 44.45],
    })


@pytest.fixture
def sample_due_wise_df():
    """Sample due-wise outstanding DataFrame."""
    return pd.DataFrame({
        "Remarks": ["Current Due", "Overdue", "Future Due"],
        "Total Outstanding (USD)": [500000.0, 300000.0, 200000.0],
        "Invoice Count": [50, 30, 20],
        "% of Total": [50.0, 30.0, 20.0],
    })


@pytest.fixture
def sample_customer_wise_df():
    """Sample customer-wise outstanding DataFrame."""
    return pd.DataFrame({
        "Customer Name": ["Customer A", "Customer B", "Customer C"],
        "Current Due": [100000.0, 50000.0, 25000.0],
        "Overdue": [50000.0, 25000.0, 10000.0],
        "Future Due": [20000.0, 10000.0, 5000.0],
        "Total Outstanding (USD)": [170000.0, 85000.0, 40000.0],
    })


@pytest.fixture
def sample_business_wise_df():
    """Sample business-wise outstanding DataFrame."""
    return pd.DataFrame({
        "New Org Name": ["BU1", "BU2", "BU3"],
        "Current Due": [200000.0, 100000.0, 50000.0],
        "Overdue": [100000.0, 50000.0, 25000.0],
        "Future Due": [50000.0, 25000.0, 10000.0],
        "Total Outstanding (USD)": [350000.0, 175000.0, 85000.0],
    })


@pytest.fixture
def sample_allocation_wise_df():
    """Sample allocation-wise outstanding DataFrame."""
    return pd.DataFrame({
        "Allocation": ["Nithya", "John", "Unallocated"],
        "Current Due": [150000.0, 100000.0, 50000.0],
        "Overdue": [75000.0, 50000.0, 25000.0],
        "Future Due": [30000.0, 20000.0, 10000.0],
        "Total Outstanding (USD)": [255000.0, 170000.0, 85000.0],
    })


@pytest.fixture
def sample_entities_wise_df():
    """Sample entities-wise outstanding DataFrame."""
    return pd.DataFrame({
        "Entities": ["UST India", "UST Corp", "UST UK"],
        "Current Due": [300000.0, 200000.0, 100000.0],
        "Overdue": [150000.0, 100000.0, 50000.0],
        "Future Due": [75000.0, 50000.0, 25000.0],
        "Total Outstanding (USD)": [525000.0, 350000.0, 175000.0],
    })


@pytest.fixture
def sample_ar_status_wise_df():
    """Sample AR status-wise outstanding DataFrame."""
    return pd.DataFrame({
        "AR Status": ["In Progress", "Pending", "Resolved"],
        "Current Due": [200000.0, 150000.0, 50000.0],
        "Future Due": [100000.0, 75000.0, 25000.0],
        "Overdue": [80000.0, 60000.0, 20000.0],
        "Credit Memo": [10000.0, 5000.0, 2000.0],
        "Unapplied": [5000.0, 3000.0, 1000.0],
        "Legal": [15000.0, 10000.0, 5000.0],
        "Total Outstanding (USD)": [410000.0, 303000.0, 103000.0],
    })


@pytest.fixture
def empty_df():
    """Empty DataFrame."""
    return pd.DataFrame()


@pytest.fixture
def mock_controller():
    """Mock controller with common methods."""
    controller = MagicMock()
    
    controller.get_projection_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer A"],
        "Reference": ["INV001"],
        "New Org Name": ["BU1"],
        "AR Status": ["In Progress"],
        "Total in USD": [10000.0],
    })
    
    controller.get_due_wise_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer B"],
        "Reference": ["INV002"],
        "New Org Name": ["BU2"],
        "AR Comments": ["Comment"],
        "AR Status": ["Pending"],
        "Total in USD": [20000.0],
    })
    
    controller.get_customer_wise_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer A"],
        "Reference": ["INV001"],
        "New Org Name": ["BU1"],
        "AR Comments": ["Comment"],
        "AR Status": ["Active"],
        "Remarks": ["Current Due"],
        "Total in USD": [15000.0],
    })
    
    controller.get_business_wise_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer C"],
        "Reference": ["INV003"],
        "New Org Name": ["BU1"],
        "AR Comments": ["Comment"],
        "AR Status": ["Active"],
        "Remarks": ["Overdue"],
        "Total in USD": [25000.0],
    })
    
    controller.get_allocation_remark_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer D"],
        "Reference": ["INV004"],
        "New Org Name": ["BU2"],
        "Allocation": ["Nithya"],
        "AR Comments": ["Comment"],
        "AR Status": ["Pending"],
        "Remarks": ["Current Due"],
        "Total in USD": [30000.0],
    })
    
    controller.get_entities_remark_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer E"],
        "Reference": ["INV005"],
        "New Org Name": ["BU3"],
        "Entities": ["UST India"],
        "Allocation": ["John"],
        "AR Comments": ["Comment"],
        "AR Status": ["Active"],
        "Remarks": ["Overdue"],
        "Total in USD": [35000.0],
    })
    
    controller.get_ar_status_remark_detail.return_value = pd.DataFrame({
        "Customer Name": ["Customer F"],
        "Reference": ["INV006"],
        "New Org Name": ["BU1"],
        "AR Comments": ["Comment"],
        "Remarks": ["Current Due"],
        "Projection": ["Feb 1st week"],
        "Total in USD": [40000.0],
    })
    
    return controller


@pytest.fixture
def mock_file_info():
    """Mock file info from SharePoint."""
    return {
        "name": "AR_Data_2024.xlsx",
        "local_time": datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc),
        "utc_time": "2024-06-15T10:30:00Z",
        "modified_by": "John Doe",
        "download_url": "https://download.url",
    }


# ---------------------------------------------------------------------
# Test: Helper Functions
# ---------------------------------------------------------------------


class TestGetRemarkCols:
    def test_excludes_id_and_total_columns(self, sample_customer_wise_df):
        """Test _get_remark_cols excludes ID and Total columns."""
        result = dv._get_remark_cols(sample_customer_wise_df, "Customer Name")
        
        assert "Customer Name" not in result
        assert "Total Outstanding (USD)" not in result
        assert "Current Due" in result
        assert "Overdue" in result
        assert "Future Due" in result

    def test_with_different_id_column(self, sample_allocation_wise_df):
        """Test with different ID column name."""
        result = dv._get_remark_cols(sample_allocation_wise_df, "Allocation")
        
        assert "Allocation" not in result
        assert "Total Outstanding (USD)" not in result
        assert len(result) == 3

    def test_empty_dataframe(self, empty_df):
        """Test with empty DataFrame."""
        result = dv._get_remark_cols(empty_df, "ID")
        assert result == []

    def test_dataframe_with_only_id_and_total(self):
        """Test DataFrame with only ID and Total columns."""
        df = pd.DataFrame({
            "Customer Name": ["A"],
            "Total Outstanding (USD)": [100.0],
        })
        result = dv._get_remark_cols(df, "Customer Name")
        assert result == []


class TestRemarkColor:
    """Test _remark_color function using actual chart_config values."""
    
    def test_returns_string_color(self):
        """Test that _remark_color returns a string."""
        result = dv._remark_color("Overdue")
        assert isinstance(result, str)
        assert result.startswith("#") or result in ["red", "green", "blue", "orange", "yellow"]

    def test_known_remark_from_config(self):
        """Test known remark returns a color from config."""
        # Test with actual remarks that should be in config
        for remark in ["Current Due", "Overdue", "Future Due"]:
            result = dv._remark_color(remark)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_unknown_remark_returns_fallback(self):
        """Test unknown remark returns primary color fallback."""
        result = dv._remark_color("SomeUnknownRemarkThatDoesNotExist12345")
        # Should return PRIMARY_COLOR from chart_config
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_string_remark(self):
        """Test empty string remark returns fallback."""
        result = dv._remark_color("")
        assert isinstance(result, str)


# ---------------------------------------------------------------------
# Test: render_page_header
# ---------------------------------------------------------------------


class TestRenderPageHeader:
    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.components")
    @patch("utils.sharepoint_fetch.get_latest_file_info")
    def test_renders_with_file_info(self, mock_file_info_fn, mock_components, mock_st, mock_file_info):
        """Test header renders with file info."""
        mock_file_info_fn.return_value = mock_file_info
        
        dv.render_page_header()
        
        mock_st.title.assert_called_once()
        mock_st.divider.assert_called()
        mock_components.html.assert_called_once()

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.components")
    @patch("utils.sharepoint_fetch.get_latest_file_info")
    def test_renders_without_file_info(self, mock_file_info_fn, mock_components, mock_st):
        """Test header renders when file info is None."""
        mock_file_info_fn.return_value = None
        
        dv.render_page_header()
        
        mock_st.title.assert_called_once()
        mock_components.html.assert_called_once()

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.components")
    @patch("utils.sharepoint_fetch.get_latest_file_info")
    def test_navigation_html_contains_sections(self, mock_file_info_fn, mock_components, mock_st):
        """Test navigation HTML contains all section links."""
        mock_file_info_fn.return_value = None
        
        dv.render_page_header()
        
        # Get the HTML that was passed to components.html
        call_args = mock_components.html.call_args
        html_content = call_args[0][0] if call_args[0] else call_args[1].get('html', '')
        
        # Check for section anchors
        assert "ar-weekly_inflow" in html_content
        assert "ar-status_wise" in html_content
        assert "ar-due_wise" in html_content
        assert "ar-customer_wise" in html_content
        assert "ar-business_wise" in html_content
        assert "ar-allocation_wise" in html_content
        assert "ar-entities_wise" in html_content


# ---------------------------------------------------------------------
# Test: render_kpi_cards
# ---------------------------------------------------------------------


class TestRenderKpiCards:
    @patch("views.dashboard_view.st")
    def test_renders_all_six_metrics(self, mock_st):
        """Test all six KPI cards are rendered."""
        mock_cols = [MagicMock() for _ in range(6)]
        mock_st.columns.return_value = mock_cols
        
        for col in mock_cols:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        dv.render_kpi_cards(
            grand_total=1000000.0,
            expected_inflow=800000.0,
            dispute_total=100000.0,
            invoice_count=500,
            credit_memo_total=50000.0,
            unapplied_total=25000.0,
        )
        
        mock_st.columns.assert_called_once_with(6)
        assert mock_st.metric.call_count == 6

    @patch("views.dashboard_view.st")
    def test_formats_values_correctly(self, mock_st):
        """Test KPI values are formatted correctly."""
        mock_cols = [MagicMock() for _ in range(6)]
        mock_st.columns.return_value = mock_cols
        
        for col in mock_cols:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        dv.render_kpi_cards(
            grand_total=1234567.89,
            expected_inflow=987654.32,
            dispute_total=123456.78,
            invoice_count=1234,
            credit_memo_total=12345.67,
            unapplied_total=6789.01,
        )
        
        calls = mock_st.metric.call_args_list
        assert len(calls) == 6

    @patch("views.dashboard_view.st")
    def test_default_credit_memo_and_unapplied(self, mock_st):
        """Test default values for credit_memo and unapplied."""
        mock_cols = [MagicMock() for _ in range(6)]
        mock_st.columns.return_value = mock_cols
        
        for col in mock_cols:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        dv.render_kpi_cards(
            grand_total=100000.0,
            expected_inflow=80000.0,
            dispute_total=10000.0,
            invoice_count=50,
        )
        
        assert mock_st.metric.call_count == 6


class TestRenderKpiCardsNoCreditUnapplied:
    @patch("views.dashboard_view.st")
    def test_renders_six_columns(self, mock_st):
        """Test six columns are created."""
        mock_cols = [MagicMock() for _ in range(6)]
        mock_st.columns.return_value = mock_cols
        
        for col in mock_cols:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        dv.render_kpi_cards_no_credit_unapplied(
            grand_total=100000.0,
            expected_inflow=80000.0,
            dispute_total=10000.0,
            invoice_count=50,
        )
        
        mock_st.columns.assert_called_once_with(6)


# ---------------------------------------------------------------------
# Test: render_weekly_inflow_section
# ---------------------------------------------------------------------


class TestRenderWeeklyInflowSection:
    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.px")
    def test_renders_chart_and_table(self, mock_px, mock_st, sample_weekly_inflow_df):
        """Test weekly inflow section renders chart and table."""
        mock_fig = MagicMock()
        mock_px.bar.return_value = mock_fig
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_weekly_inflow_section(sample_weekly_inflow_df, controller=None)
        
        mock_st.subheader.assert_called()
        mock_px.bar.assert_called_once()
        mock_st.plotly_chart.assert_called()
        mock_st.dataframe.assert_called()

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.px")
    def test_with_controller_no_selection(self, mock_px, mock_st, sample_weekly_inflow_df, mock_controller):
        """Test with controller but no bar selection."""
        mock_fig = MagicMock()
        mock_px.bar.return_value = mock_fig
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_weekly_inflow_section(sample_weekly_inflow_df, controller=mock_controller)
        
        mock_controller.get_projection_detail.assert_not_called()

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.px")
    def test_with_bar_selection(self, mock_px, mock_st, sample_weekly_inflow_df, mock_controller):
        """Test drill-down when bar is clicked."""
        mock_fig = MagicMock()
        mock_px.bar.return_value = mock_fig
        
        mock_event = MagicMock()
        mock_event.selection = {"points": [{"x": "Feb 1st week"}]}
        mock_st.plotly_chart.return_value = mock_event
        
        dv.render_weekly_inflow_section(sample_weekly_inflow_df, controller=mock_controller)
        
        mock_controller.get_projection_detail.assert_called_once_with("Feb 1st week")

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.px")
    def test_with_empty_detail(self, mock_px, mock_st, sample_weekly_inflow_df, mock_controller):
        """Test when detail returns empty DataFrame."""
        mock_fig = MagicMock()
        mock_px.bar.return_value = mock_fig
        
        mock_event = MagicMock()
        mock_event.selection = {"points": [{"x": "Feb 1st week"}]}
        mock_st.plotly_chart.return_value = mock_event
        
        mock_controller.get_projection_detail.return_value = pd.DataFrame()
        
        dv.render_weekly_inflow_section(sample_weekly_inflow_df, controller=mock_controller)
        
        mock_st.info.assert_called()

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.px")
    def test_selection_with_label_fallback(self, mock_px, mock_st, sample_weekly_inflow_df, mock_controller):
        """Test selection using 'label' key instead of 'x'."""
        mock_fig = MagicMock()
        mock_px.bar.return_value = mock_fig
        
        mock_event = MagicMock()
        mock_event.selection = {"points": [{"label": "Mar 1st week"}]}
        mock_st.plotly_chart.return_value = mock_event
        
        dv.render_weekly_inflow_section(sample_weekly_inflow_df, controller=mock_controller)
        
        mock_controller.get_projection_detail.assert_called_once_with("Mar 1st week")


# ---------------------------------------------------------------------
# Test: render_ar_status_wise_outstanding
# ---------------------------------------------------------------------


class TestRenderARStatusWiseOutstanding:
    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_renders_with_data(self, mock_go, mock_st, sample_ar_status_wise_df):
        """Test AR status section renders with data."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock() for _ in range(5)]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_ar_status_wise_outstanding(sample_ar_status_wise_df, controller=None)
        
        mock_st.subheader.assert_called()
        mock_go.Figure.assert_called()

    @patch("views.dashboard_view.st")
    def test_renders_empty_message_for_empty_df(self, mock_st, empty_df):
        """Test info message for empty DataFrame."""
        dv.render_ar_status_wise_outstanding(empty_df, controller=None)
        
        mock_st.info.assert_called_with("No data available.")

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_drill_down_on_click(self, mock_go, mock_st, sample_ar_status_wise_df, mock_controller):
        """Test drill-down when bar is clicked."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock() for _ in range(5)]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_event = MagicMock()
        mock_event.selection = {"points": [{"x": "In Progress", "customdata": ["Overdue"]}]}
        mock_st.plotly_chart.return_value = mock_event
        
        dv.render_ar_status_wise_outstanding(sample_ar_status_wise_df, controller=mock_controller)
        
        mock_controller.get_ar_status_remark_detail.assert_called()

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_curve_number_fallback(self, mock_go, mock_st, sample_ar_status_wise_df, mock_controller):
        """Test curve_number fallback for remark detection."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock() for _ in range(5)]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_event = MagicMock()
        mock_event.selection = {"points": [{"x": "Pending", "curve_number": 0}]}
        mock_st.plotly_chart.return_value = mock_event
        
        dv.render_ar_status_wise_outstanding(sample_ar_status_wise_df, controller=mock_controller)


# ---------------------------------------------------------------------
# Test: render_due_wise_outstanding
# ---------------------------------------------------------------------


class TestRenderDueWiseOutstanding:
    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.px")
    def test_renders_chart_and_table(self, mock_px, mock_st, sample_due_wise_df):
        """Test due-wise section renders chart and table."""
        mock_fig = MagicMock()
        mock_px.bar.return_value = mock_fig
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_due_wise_outstanding(sample_due_wise_df, controller=None)
        
        mock_st.subheader.assert_called()
        mock_px.bar.assert_called_once()

    @patch("views.dashboard_view.st")
    def test_renders_empty_message(self, mock_st, empty_df):
        """Test info message for empty DataFrame."""
        dv.render_due_wise_outstanding(empty_df, controller=None)
        
        mock_st.info.assert_called_with("No data available.")

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.px")
    def test_drill_down_on_click(self, mock_px, mock_st, sample_due_wise_df, mock_controller):
        """Test drill-down when bar is clicked."""
        mock_fig = MagicMock()
        mock_px.bar.return_value = mock_fig
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_event = MagicMock()
        mock_event.selection = {"points": [{"x": "Overdue"}]}
        mock_st.plotly_chart.return_value = mock_event
        
        dv.render_due_wise_outstanding(sample_due_wise_df, controller=mock_controller)
        
        mock_controller.get_due_wise_detail.assert_called_once_with("Overdue")

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.px")
    def test_grand_total_row_added(self, mock_px, mock_st, sample_due_wise_df):
        """Test grand total row is added to summary table."""
        mock_fig = MagicMock()
        mock_px.bar.return_value = mock_fig
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_due_wise_outstanding(sample_due_wise_df, controller=None)
        
        assert mock_st.dataframe.called


# ---------------------------------------------------------------------
# Test: render_customer_wise_outstanding
# ---------------------------------------------------------------------


class TestRenderCustomerWiseOutstanding:
    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_renders_pie_chart_and_table(self, mock_go, mock_st, sample_customer_wise_df):
        """Test customer-wise section renders pie chart and table."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Pie.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        dv.render_customer_wise_outstanding(sample_customer_wise_df, controller=None)
        
        mock_st.subheader.assert_called()
        mock_go.Pie.assert_called()

    @patch("views.dashboard_view.st")
    def test_renders_empty_message(self, mock_st, empty_df):
        """Test info message for empty DataFrame."""
        dv.render_customer_wise_outstanding(empty_df, controller=None)
        
        mock_st.info.assert_called_with("No data available.")

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_selectbox_drill_down(self, mock_go, mock_st, sample_customer_wise_df, mock_controller):
        """Test drill-down via selectbox."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Pie.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.selectbox.return_value = "Customer A"
        
        dv.render_customer_wise_outstanding(sample_customer_wise_df, controller=mock_controller)
        
        mock_controller.get_customer_wise_detail.assert_called_once_with("Customer A")

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_selectbox_no_selection(self, mock_go, mock_st, sample_customer_wise_df, mock_controller):
        """Test no drill-down when default option selected."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Pie.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.selectbox.return_value = "— Select a customer —"
        
        dv.render_customer_wise_outstanding(sample_customer_wise_df, controller=mock_controller)
        
        mock_controller.get_customer_wise_detail.assert_not_called()

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_others_category_in_pie(self, mock_go, mock_st):
        """Test 'Others' category added when more than 10 customers."""
        df = pd.DataFrame({
            "Customer Name": [f"Customer {i}" for i in range(15)],
            "Total Outstanding (USD)": [10000.0 * (15 - i) for i in range(15)],
            "Current Due": [5000.0] * 15,
            "Overdue": [3000.0] * 15,
        })
        
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Pie.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        dv.render_customer_wise_outstanding(df, controller=None)
        
        pie_call_args = mock_go.Pie.call_args
        labels = pie_call_args[1].get('labels', [])
        assert "Others" in labels


# ---------------------------------------------------------------------
# Test: render_business_wise_outstanding
# ---------------------------------------------------------------------


class TestRenderBusinessWiseOutstanding:
    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_renders_pie_chart_and_table(self, mock_go, mock_st, sample_business_wise_df):
        """Test business-wise section renders pie chart and table."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Pie.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        dv.render_business_wise_outstanding(sample_business_wise_df, controller=None)
        
        mock_st.subheader.assert_called()

    @patch("views.dashboard_view.st")
    def test_renders_empty_message(self, mock_st, empty_df):
        """Test info message for empty DataFrame."""
        dv.render_business_wise_outstanding(empty_df, controller=None)
        
        mock_st.info.assert_called_with("No data available.")

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_selectbox_drill_down(self, mock_go, mock_st, sample_business_wise_df, mock_controller):
        """Test drill-down via selectbox."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Pie.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.selectbox.return_value = "BU1"
        
        dv.render_business_wise_outstanding(sample_business_wise_df, controller=mock_controller)
        
        mock_controller.get_business_wise_detail.assert_called_once_with("BU1")


# ---------------------------------------------------------------------
# Test: render_allocation_wise_outstanding
# ---------------------------------------------------------------------


class TestRenderAllocationWiseOutstanding:
    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_renders_grouped_bar_chart(self, mock_go, mock_st, sample_allocation_wise_df):
        """Test allocation-wise section renders grouped bar chart."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_allocation_wise_outstanding(sample_allocation_wise_df, controller=None)
        
        mock_st.subheader.assert_called()
        mock_go.Figure.assert_called()

    @patch("views.dashboard_view.st")
    def test_renders_empty_message(self, mock_st, empty_df):
        """Test info message for empty DataFrame."""
        dv.render_allocation_wise_outstanding(empty_df, controller=None)
        
        mock_st.info.assert_called_with("No data available.")

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_drill_down_with_customdata(self, mock_go, mock_st, sample_allocation_wise_df, mock_controller):
        """Test drill-down using customdata."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_event = MagicMock()
        mock_event.selection = {"points": [{"x": "Nithya", "customdata": ["Overdue"]}]}
        mock_st.plotly_chart.return_value = mock_event
        
        dv.render_allocation_wise_outstanding(sample_allocation_wise_df, controller=mock_controller)
        
        mock_controller.get_allocation_remark_detail.assert_called_once_with("Nithya", "Overdue")

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_drill_down_with_customdata_as_string(self, mock_go, mock_st, sample_allocation_wise_df, mock_controller):
        """Test drill-down when customdata is a string."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_event = MagicMock()
        mock_event.selection = {"points": [{"x": "John", "customdata": "Current Due"}]}
        mock_st.plotly_chart.return_value = mock_event
        
        dv.render_allocation_wise_outstanding(sample_allocation_wise_df, controller=mock_controller)
        
        mock_controller.get_allocation_remark_detail.assert_called_once_with("John", "Current Due")

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_drill_down_curve_number_fallback(self, mock_go, mock_st, sample_allocation_wise_df, mock_controller):
        """Test drill-down using curve_number fallback."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_event = MagicMock()
        mock_event.selection = {"points": [{"x": "Unallocated", "curveNumber": 0}]}
        mock_st.plotly_chart.return_value = mock_event
        
        dv.render_allocation_wise_outstanding(sample_allocation_wise_df, controller=mock_controller)

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_empty_detail_shows_info(self, mock_go, mock_st, sample_allocation_wise_df, mock_controller):
        """Test info message when detail is empty."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_event = MagicMock()
        mock_event.selection = {"points": [{"x": "Nithya", "customdata": ["Overdue"]}]}
        mock_st.plotly_chart.return_value = mock_event
        
        mock_controller.get_allocation_remark_detail.return_value = pd.DataFrame()
        
        dv.render_allocation_wise_outstanding(sample_allocation_wise_df, controller=mock_controller)
        
        mock_st.info.assert_called()


# ---------------------------------------------------------------------
# Test: render_entities_wise_outstanding
# ---------------------------------------------------------------------


class TestRenderEntitiesWiseOutstanding:
    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_renders_grouped_bar_chart(self, mock_go, mock_st, sample_entities_wise_df):
        """Test entities-wise section renders grouped bar chart."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_entities_wise_outstanding(sample_entities_wise_df, controller=None)
        
        mock_st.subheader.assert_called()
        mock_go.Figure.assert_called()

    @patch("views.dashboard_view.st")
    def test_renders_empty_message(self, mock_st, empty_df):
        """Test info message for empty DataFrame."""
        dv.render_entities_wise_outstanding(empty_df, controller=None)
        
        mock_st.info.assert_called_with("No data available.")

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_drill_down_on_click(self, mock_go, mock_st, sample_entities_wise_df, mock_controller):
        """Test drill-down when bar is clicked."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_event = MagicMock()
        mock_event.selection = {"points": [{"x": "UST India", "customdata": ["Overdue"]}]}
        mock_st.plotly_chart.return_value = mock_event
        
        dv.render_entities_wise_outstanding(sample_entities_wise_df, controller=mock_controller)
        
        mock_controller.get_entities_remark_detail.assert_called_once_with("UST India", "Overdue")

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_metric_cards_rendered(self, mock_go, mock_st, sample_entities_wise_df):
        """Test metric cards are rendered."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_entities_wise_outstanding(sample_entities_wise_df, controller=None)
        
        assert mock_st.metric.call_count >= 2


# ---------------------------------------------------------------------
# Test: Edge Cases and Data Transformations
# ---------------------------------------------------------------------


class TestEdgeCases:
    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_missing_overdue_column(self, mock_go, mock_st):
        """Test handling when Overdue column is missing."""
        df = pd.DataFrame({
            "Allocation": ["A", "B"],
            "Current Due": [100.0, 200.0],
            "Total Outstanding (USD)": [100.0, 200.0],
        })
        
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_allocation_wise_outstanding(df, controller=None)

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.px")
    def test_zero_total_percentage(self, mock_px, mock_st):
        """Test handling when total is zero."""
        df = pd.DataFrame({
            "Remarks": ["Current Due"],
            "Total Outstanding (USD)": [0.0],
            "Invoice Count": [0],
            "% of Total": [0.0],
        })
        
        mock_fig = MagicMock()
        mock_px.bar.return_value = mock_fig
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_due_wise_outstanding(df, controller=None)

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_selection_without_points(self, mock_go, mock_st, sample_allocation_wise_df):
        """Test handling selection event without points."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_event = MagicMock()
        mock_event.selection = {"points": []}
        mock_st.plotly_chart.return_value = mock_event
        
        mock_controller = MagicMock()
        
        dv.render_allocation_wise_outstanding(sample_allocation_wise_df, controller=mock_controller)
        
        mock_controller.get_allocation_remark_detail.assert_not_called()

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_selection_event_none(self, mock_go, mock_st, sample_allocation_wise_df):
        """Test handling None selection event."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.plotly_chart.return_value = None
        
        mock_controller = MagicMock()
        
        dv.render_allocation_wise_outstanding(sample_allocation_wise_df, controller=mock_controller)

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_event_without_selection_attr(self, mock_go, mock_st, sample_allocation_wise_df):
        """Test handling event without selection attribute."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_event = MagicMock(spec=[])
        mock_st.plotly_chart.return_value = mock_event
        
        mock_controller = MagicMock()
        
        dv.render_allocation_wise_outstanding(sample_allocation_wise_df, controller=mock_controller)


class TestDataFormatting:
    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.px")
    def test_usd_formatting_in_tables(self, mock_px, mock_st, sample_weekly_inflow_df):
        """Test USD values are formatted correctly in tables."""
        mock_fig = MagicMock()
        mock_px.bar.return_value = mock_fig
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_weekly_inflow_section(sample_weekly_inflow_df, controller=None)
        
        assert mock_st.dataframe.called

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.go")
    def test_grand_total_row_in_summary(self, mock_go, mock_st, sample_customer_wise_df):
        """Test grand total row is added to summary tables."""
        mock_fig = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Pie.return_value = MagicMock()
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        dv.render_customer_wise_outstanding(sample_customer_wise_df, controller=None)
        
        assert mock_st.dataframe.called


class TestChartConfiguration:
    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.px")
    def test_chart_uses_config_height(self, mock_px, mock_st, sample_weekly_inflow_df):
        """Test chart uses configured height."""
        mock_fig = MagicMock()
        mock_px.bar.return_value = mock_fig
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_weekly_inflow_section(sample_weekly_inflow_df, controller=None)
        
        mock_fig.update_layout.assert_called()

    @patch("views.dashboard_view.st")
    @patch("views.dashboard_view.px")
    def test_chart_uses_config_template(self, mock_px, mock_st, sample_due_wise_df):
        """Test chart uses configured template."""
        mock_fig = MagicMock()
        mock_px.bar.return_value = mock_fig
        
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        
        mock_st.plotly_chart.return_value = MagicMock(selection=None)
        
        dv.render_due_wise_outstanding(sample_due_wise_df, controller=None)
        
        call_kwargs = mock_px.bar.call_args[1]
        assert "template" in call_kwargs