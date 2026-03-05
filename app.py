"""
AR Inflow Projection Dashboard — Main Application Entry Point.
Run with: streamlit run app.py
"""

import logging
import sys
from pathlib import Path
from typing import Literal

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from config.settings import app_config
from controllers.projection_controller import ProjectionController
from models.ar_model import ARDataModel
from utils.persistent_session import (
    try_restore_from_cookie,
    write_cookie_after_login,
)
from utils.session_manager import SessionManager
from utils.sharepoint_fetch import get_latest_file_info
from views.admin_view import render_admin_page
from views.auth_view import handle_oauth_callback, render_login_page
from views.dashboard_view import (
    render_allocation_wise_outstanding,
    render_ar_status_wise_outstanding,
    render_business_wise_outstanding,
    render_customer_wise_outstanding,
    render_due_wise_outstanding,
    render_entities_wise_outstanding,
    render_kpi_cards,
    render_page_header,
    render_weekly_inflow_section,
)

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

log_file = PROJECT_ROOT / "ar_dashboard.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# app_config.LAYOUT is a plain str at runtime but set_page_config expects
# Literal["centered", "wide"].  Cast it explicitly so mypy is satisfied while
# preserving the runtime value.
_VALID_LAYOUTS = {"centered", "wide"}
_layout_value = str(getattr(app_config, "LAYOUT", "wide"))
_layout: Literal["centered", "wide"] = (
    _layout_value if _layout_value in _VALID_LAYOUTS else "wide"  # type: ignore[assignment]
)

st.set_page_config(
    page_title=app_config.APP_TITLE,
    page_icon=app_config.PAGE_ICON,
    layout=_layout,
)


@st.cache_data(ttl=300, show_spinner=False)
def _get_file_info() -> dict:
    """Poll SharePoint every 5 min. Returns file info dict for caching and display."""
    try:
        info = get_latest_file_info()
        if info and info.get("utc_time"):
            logger.info(
                "SharePoint file version: %s | %s", info["utc_time"], info.get("name")
            )
            return info
    except Exception as e:
        logger.warning("Could not check SharePoint file version: %s", e)
    return {"utc_time": "unknown", "name": "unknown", "local_time": None}


@st.cache_data(show_spinner="Loading AR data …")
def _load_data(cache_key: str) -> pd.DataFrame:
    """Load AR data. Reruns whenever cache_key changes."""
    logger.info("Loading AR data — cache_key: %s", cache_key)
    model = ARDataModel()
    model.load()
    return model._df


@st.cache_resource(ttl=300)
def _build_controller(cache_key: str) -> ProjectionController:
    """Build and cache the controller. Reruns when cache_key changes."""
    model = ARDataModel()
    model._df = _load_data(cache_key)
    controller = ProjectionController(model)
    controller._df = model._df
    return controller


def _render_sidebar(session: SessionManager) -> str:
    with st.sidebar:
        st.markdown("### AR Dashboard")
        st.divider()
        user = session.current_user()
        if user:
            st.markdown(
                f"**{user.get('display_name', '')}**  \n"
                f"<span style='color:#888;font-size:0.82rem;'>{user.get('email', '')}</span>  \n"
                f"<span style='background:#0078D4;color:white;padding:1px 8px;"
                f"border-radius:10px;font-size:0.75rem;'>{session.current_role()}</span>",
                unsafe_allow_html=True,
            )
            st.divider()

        pages = ["Dashboard"]
        if session.is_admin():
            pages.append("Access Management")

        selected = st.radio("Navigation", pages, label_visibility="collapsed")
        st.divider()

        if st.button("Refresh Data", use_container_width=True):
            _load_data.clear()
            _get_file_info.clear()
            _build_controller.clear()
            st.rerun()

        if st.button("Sign Out", use_container_width=True):
            session.logout()
            st.rerun()

    return selected  # type: ignore[return-value]


def main() -> None:
    if (
        st.query_params.get("healthcheck") == ["1"]
        or st.query_params.get("healthcheck") == "1"
    ):
        st.markdown("Application is up and running.")
        return

    try_restore_from_cookie()
    session = SessionManager()

    if not session.is_authenticated():
        if not handle_oauth_callback(session):
            render_login_page()
        return

    write_cookie_after_login()

    if st.query_params.get("sid"):
        st.query_params.clear()

    selected_page = _render_sidebar(session)

    if selected_page == "Access Management":
        render_admin_page(session)
        return

    file_info = _get_file_info()
    cache_key = file_info.get("utc_time", "unknown")
    controller = _build_controller(cache_key)

    render_page_header(file_info=file_info)

    kpi_metrics = controller.get_all_kpi_metrics()
    render_kpi_cards(
        grand_total=kpi_metrics["grand_total"],
        expected_inflow=kpi_metrics["expected_inflow"],
        next_month_1st_week=kpi_metrics["next_month_1st_week"],
        dispute_total=kpi_metrics["dispute_total"],
        invoice_count=kpi_metrics["invoice_count"],
        credit_memo_total=kpi_metrics["credit_memo_total"],
        current_due=kpi_metrics["current_due"],
        future_due=kpi_metrics["future_due"],
        unapplied_total=kpi_metrics["unapplied_total"],
        overdue_total=kpi_metrics["overdue_total"],
        legal_total=kpi_metrics["legal_total"],
        next_month_name=kpi_metrics["next_month_name"],
    )

    render_weekly_inflow_section(controller.get_weekly_inflow_summary(), controller=controller)
    render_ar_status_wise_outstanding(controller.get_ar_status_wise_outstanding(), controller=controller)
    render_due_wise_outstanding(controller.get_due_wise_outstanding(), controller=controller)
    render_customer_wise_outstanding(controller.get_customer_wise_outstanding(), controller=controller)
    render_business_wise_outstanding(controller.get_business_wise_outstanding(), controller=controller)
    render_allocation_wise_outstanding(controller.get_allocation_wise_outstanding(), controller=controller)
    render_entities_wise_outstanding(controller.get_entities_wise_outstanding(), controller=controller)


if __name__ == "__main__":
    main()
