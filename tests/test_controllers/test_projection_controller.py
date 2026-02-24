import pytest
import pandas as pd
from unittest.mock import MagicMock

from controllers.projection_controller import ProjectionController


# ---------------------------------------------------------------------
# Sample Data Fixture
# ---------------------------------------------------------------------

@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "Projection": [
            "Feb 3rd week",
            "Feb 3rd week",
            "Dispute - Legal",
            "Mar 1st week"
        ],
        "Total in USD": [1000.0, 2000.0, 500.0, 1500.0],
        "Invoice": ["INV1", "INV2", "INV3", "INV4"],
        "Remarks": [
            "Current Due",
            "Overdue",
            "Credit Memo",
            "Future Due"
        ],
        "Customer Name": [
            "Customer A",
            "Customer A",
            "Customer B",
            "Customer C"
        ],
        "Bus Unit Name": [
            "BU1",
            "BU1",
            "BU2",
            "Internal"
        ],
        "Allocation": [
            "Allocated",
            "Unallocated",
            "Allocated",
            "Allocated"
        ],
        "Entities": [
            "Entity1",
            "Entity1",
            "Entity2",
            "Entity3"
        ]
    })

## ---------------------------------------------------------------------
# General Tests
## ---------------------------------------------------------------------

def test_controller_fixture_runs(controller):
    # Just check that the controller is created and has a dataframe
    assert hasattr(controller, "_model")
    assert hasattr(controller._model, "dataframe")

# ---------------------------------------------------------------------
# Weekly Inflow Summary
# ---------------------------------------------------------------------

def test_weekly_inflow_summary(controller):
    summary = controller.get_weekly_inflow_summary()

    assert "Total Inflow (USD)" in summary.columns
    assert summary["Total Inflow (USD)"].sum() == 5000.0
    assert summary["Invoice Count"].sum() == 4


def test_expected_inflow_total(controller):
    total = controller.get_expected_inflow_total()
    # Should exclude dispute
    assert total == 4500.0


def test_dispute_total(controller):
    total = controller.get_dispute_total()
    assert total == 500.0


def test_grand_total(controller):
    assert controller.get_grand_total() == 5000.0


# ---------------------------------------------------------------------
# Due Wise Outstanding
# ---------------------------------------------------------------------

def test_due_wise_outstanding(controller):
    df = controller.get_due_wise_outstanding()

    assert "Total Outstanding (USD)" in df.columns
    assert df["Total Outstanding (USD)"].sum() == 5000.0


def test_credit_memo_total(controller):
    assert controller.get_credit_memo_total() == 500.0


def test_unapplied_total(controller):
    # No unapplied in fixture
    assert controller.get_unapplied_total() == 0.0


# ---------------------------------------------------------------------
# Customer Wise Outstanding
# ---------------------------------------------------------------------

def test_customer_wise_outstanding(controller):
    df = controller.get_customer_wise_outstanding()

    assert "Customer Name" in df.columns
    assert "Total Outstanding (USD)" in df.columns
    assert df["Total Outstanding (USD)"].sum() == 5000.0


# ---------------------------------------------------------------------
# Business Wise Outstanding
# ---------------------------------------------------------------------

def test_business_wise_outstanding(controller):
    df = controller.get_business_wise_outstanding()

    # Internal BU should be excluded
    assert "Internal" not in df["Bus Unit Name"].values
    assert df["Total Outstanding (USD)"].sum() == 3500.0


# ---------------------------------------------------------------------
# Allocation Wise Outstanding
# ---------------------------------------------------------------------

def test_allocation_wise_outstanding(controller):
    df = controller.get_allocation_wise_outstanding()

    assert "Allocation" in df.columns
    assert df["Total Outstanding (USD)"].sum() == 5000.0


# ---------------------------------------------------------------------
# Entities Wise Outstanding
# ---------------------------------------------------------------------

def test_entities_wise_outstanding(controller):
    df = controller.get_entities_wise_outstanding()

    assert "Entities" in df.columns
    assert df["Total Outstanding (USD)"].sum() == 5000.0


# ---------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------

def test_refresh(sample_df):
    mock_model = MagicMock()
    mock_model.load.return_value.dataframe = sample_df

    controller = ProjectionController(mock_model)
    controller.refresh()

    assert controller.df.equals(sample_df)

@pytest.fixture
def controller(sample_df):
    class DummyModel:
        @property
        def dataframe(self):
            return sample_df
    return ProjectionController(DummyModel())

@pytest.fixture
def df_missing_due_cols(sample_df):
    # Remove "Current Due" and "Overdue" from Remarks to ensure they are missing in the pivot
    df = sample_df.copy()
    df = df[df["Remarks"] != "Current Due"]
    df = df[df["Remarks"] != "Overdue"]
    return df

def test_get_customer_wise_outstanding_adds_due_cols(df_missing_due_cols):
    class DummyModel:
        @property
        def dataframe(self):
            return df_missing_due_cols
    controller = ProjectionController(DummyModel())
    result = controller.get_customer_wise_outstanding()
    assert "Current Due" in result.columns
    assert "Overdue" in result.columns
    assert (result["Current Due"] == 0.0).all()
    assert (result["Overdue"] == 0.0).all()

def test_get_business_wise_outstanding_adds_due_cols(df_missing_due_cols):
    class DummyModel:
        @property
        def dataframe(self):
            return df_missing_due_cols
    controller = ProjectionController(DummyModel())
    result = controller.get_business_wise_outstanding()
    assert "Current Due" in result.columns
    assert "Overdue" in result.columns
    assert (result["Current Due"] == 0.0).all()
    assert (result["Overdue"] == 0.0).all()

def test_get_allocation_wise_outstanding_adds_due_cols(df_missing_due_cols):
    class DummyModel:
        @property
        def dataframe(self):
            return df_missing_due_cols
    controller = ProjectionController(DummyModel())
    result = controller.get_allocation_wise_outstanding()
    assert "Current Due" in result.columns
    assert "Overdue" in result.columns
    assert (result["Current Due"] == 0.0).all()
    assert (result["Overdue"] == 0.0).all()

def test_get_entities_wise_outstanding_adds_due_cols(df_missing_due_cols):
    class DummyModel:
        @property
        def dataframe(self):
            return df_missing_due_cols
    controller = ProjectionController(DummyModel())
    result = controller.get_entities_wise_outstanding()
    assert "Current Due" in result.columns
    assert "Overdue" in result.columns
    assert (result["Current Due"] == 0.0).all()
    assert (result["Overdue"] == 0.0).all()

def test_sort_key_next_month():
    # Covers the "next month" special case in _sort_key
    key = ProjectionController._sort_key("Next Month")
    # Should be (98, 99, 'next month')
    assert key[0] == 98
    assert key[2] == "next month"