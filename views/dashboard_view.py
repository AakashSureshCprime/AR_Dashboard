"""
View layer – all Streamlit rendering logic.

This module is purely presentational.  It receives pre-computed data
from the Controller and renders it using Streamlit + Plotly.
"""

import streamlit as st
import plotly.express as px
import pandas as pd

from config.settings import chart_config
from utils.formatters import fmt_usd, fmt_number


# ======================================================================
# Page Configuration
# ======================================================================

def render_page_header() -> None:
    """Render the main dashboard title and description."""
    st.title("AR Inflow Projection Dashboard")
    st.divider()


# ======================================================================
# KPI Metric Cards
# ======================================================================

def render_kpi_cards(
    grand_total: float,
    expected_inflow: float,
    dispute_total: float,
    invoice_count: int,
) -> None:
    """Render top-level KPI metric cards."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Grand Total (USD)",
            value=fmt_usd(grand_total),
        )
    with col2:
        st.metric(
            label="Expected Inflow (USD)",
            value=fmt_usd(expected_inflow),
        )
    with col3:
        st.metric(
            label="In Dispute (USD)",
            value=fmt_usd(dispute_total),
        )
    with col4:
        st.metric(
            label="Total Invoices",
            value=fmt_number(invoice_count),
        )
    st.divider()


# ======================================================================
# Weekly Inflow Projection Chart & Table
# ======================================================================

def render_weekly_inflow_section(summary_df: pd.DataFrame) -> None:
    """
    Render the main weekly inflow projection bar chart and summary table.
    """
    st.subheader("Weekly Inflow Projection")

    # --- Bar chart ---
    fig = px.bar(
        summary_df,
        x="Projection",
        y="Total Inflow (USD)",
        text="Total Inflow (USD)",
        color="Projection",
        color_discrete_sequence=list(chart_config.BAR_COLOR_SEQUENCE),
        template=chart_config.CHART_TEMPLATE,
    )
    fig.update_traces(
        texttemplate="$%{text:,.0f}",
        textposition="outside",
    )
    fig.update_layout(
        height=chart_config.CHART_HEIGHT,
        xaxis_title="Projection Week",
        yaxis_title="Total Inflow (USD)",
        showlegend=False,
        yaxis=dict(tickformat="$,.0f"),
    )
    st.plotly_chart(fig, width="stretch")

    # --- Summary table ---
    display_df = summary_df.copy()
    display_df["Total Inflow (USD)"] = display_df["Total Inflow (USD)"].apply(fmt_usd)
    display_df["% of Total"] = display_df["% of Total"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(display_df, width="stretch", hide_index=True)
