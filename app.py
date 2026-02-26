"""
AR Inflow Projection Dashboard — Main Application Entry Point.
Run with: streamlit run app.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from config.settings import app_config
from controllers.projection_controller import ProjectionController
from models.ar_model import ARDataModel
from utils.session_manager import SessionManager
from utils.persistent_session import try_restore_from_cookie, write_cookie_after_login
from utils.sharepoint_fetch import get_latest_file_info
from views.auth_view import handle_oauth_callback, render_login_page
from views.admin_view import render_admin_page
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=app_config.APP_TITLE,
    page_icon=app_config.PAGE_ICON,
    layout=app_config.LAYOUT,
)


@st.cache_data(ttl=300, show_spinner=False)
def _get_file_version() -> str:
    """Poll SharePoint every 5 min. Returns last-modified timestamp as cache key."""
    try:
        info = get_latest_file_info()
        if info and info.get("utc_time"):
            logger.info("SharePoint file version: %s | %s", info["utc_time"], info.get("name"))
            return info["utc_time"]
    except Exception as e:
        logger.warning("Could not check SharePoint file version: %s", e)
    return "unknown"


@st.cache_data(show_spinner="Loading AR data …")
def _load_data(cache_key: str) -> pd.DataFrame:
    """Load AR data. Reruns whenever cache_key changes."""
    logger.info("Loading AR data — cache_key: %s", cache_key)
    model = ARDataModel()
    model.load()
    return model.dataframe


def _build_controller() -> ProjectionController:
    cache_key = _get_file_version()
    model = ARDataModel()
    model._df = _load_data(cache_key)
    controller = ProjectionController(model)
    controller._df = model.dataframe
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
            # Clear both caches synchronously before rerun
            # so the very next _get_file_version() and _load_data() calls
            # are guaranteed cache misses that re-fetch from SharePoint
            _load_data.clear()
            _get_file_version.clear()
            st.rerun()

        if st.button("Sign Out", use_container_width=True):
            session.logout()
            st.rerun()

    return selected


def main() -> None:
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

    controller = _build_controller()

    render_page_header()
    render_kpi_cards(
        grand_total=controller.get_grand_total(),
        expected_inflow=controller.get_expected_inflow_total(),
        dispute_total=controller.get_dispute_total(),
        invoice_count=len(controller.df),
        credit_memo_total=controller.get_credit_memo_total(),
        unapplied_total=controller.get_unapplied_total(),
    )
    weekly_summary = controller.get_weekly_inflow_summary()
    render_weekly_inflow_section(weekly_summary, controller=controller)
    ar_status_summary = controller.get_ar_status_wise_outstanding()
    render_ar_status_wise_outstanding(ar_status_summary, controller=controller)
    due_summary = controller.get_due_wise_outstanding()
    render_due_wise_outstanding(due_summary, controller=controller)
    customer_summary = controller.get_customer_wise_outstanding()
    render_customer_wise_outstanding(customer_summary, controller=controller)
    business_summary = controller.get_business_wise_outstanding()
    render_business_wise_outstanding(business_summary, controller=controller)
    allocation_summary = controller.get_allocation_wise_outstanding()
    render_allocation_wise_outstanding(allocation_summary, controller=controller)
    entities_summary = controller.get_entities_wise_outstanding()
    render_entities_wise_outstanding(entities_summary, controller=controller)


if __name__ == "__main__":
    main()