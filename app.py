"""
AR Inflow Projection Dashboard — Main Application Entry Point.

Run with:
    streamlit run app.py
"""

import logging
import sys
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so relative imports resolve correctly.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import app_config
from models.ar_model import ARDataModel
from controllers.projection_controller import ProjectionController
from views.dashboard_view import (
    render_page_header,
    render_kpi_cards,
    render_weekly_inflow_section,
    render_due_wise_outstanding,
    render_customer_wise_outstanding,
    render_business_wise_outstanding,
    render_allocation_wise_outstanding,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Streamlit page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=app_config.APP_TITLE,
    page_icon=app_config.PAGE_ICON,
    layout=app_config.LAYOUT,
)


# ---------------------------------------------------------------------------
# Data bootstrap (cached so it survives Streamlit reruns)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading AR data …")
def _load_data() -> "pd.DataFrame":
    """Load and cache AR data via the Model layer."""
    model = ARDataModel()
    model.load()
    return model.dataframe


def _build_controller() -> ProjectionController:
    """Construct a controller backed by cached data."""
    model = ARDataModel()
    model._df = _load_data()          # Inject cached frame directly
    controller = ProjectionController(model)
    controller._df = model.dataframe   # Ensure controller also has it
    return controller


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------
def main() -> None:
    """Orchestrate the full dashboard render cycle."""

    controller = _build_controller()

    # ── Header ────────────────────────────────────────────────────────
    render_page_header()

    # ── KPI Cards ─────────────────────────────────────────────────────
    render_kpi_cards(
        grand_total=controller.get_grand_total(),
        expected_inflow=controller.get_expected_inflow_total(),
        dispute_total=controller.get_dispute_total(),
        invoice_count=len(controller.df),
    )

    # ── Weekly inflow projection ──────────────────────────────────────
    weekly_summary = controller.get_weekly_inflow_summary()
    render_weekly_inflow_section(weekly_summary)

    # ── Due wise outstanding ─────────────────────────────────────────
    due_summary = controller.get_due_wise_outstanding()
    render_due_wise_outstanding(due_summary)

    # ── Customer wise outstanding ─────────────────────────────────────
    customer_summary = controller.get_customer_wise_outstanding()
    render_customer_wise_outstanding(customer_summary)

    # ── Business wise outstanding ─────────────────────────────────────
    business_summary = controller.get_business_wise_outstanding()
    render_business_wise_outstanding(business_summary)

    # -- Allocation wise outstanding ------------------------------------
    allocation_summary = controller.get_allocation_wise_outstanding()
    render_allocation_wise_outstanding(allocation_summary)


if __name__ == "__main__":
    main()
