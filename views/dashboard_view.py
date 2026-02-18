"""
View layer – all Streamlit rendering logic.

This module is purely presentational.  It receives pre-computed data
from the Controller and renders it using Streamlit + Plotly.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
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


# ======================================================================
# Due Wise Outstanding
# ======================================================================

def render_due_wise_outstanding(due_df: pd.DataFrame) -> None:
    """
    Render a section showing outstanding amounts split by
    Current Due vs Overdue (from the Remarks column).
    """
    st.subheader("Due Wise Outstanding")

    if due_df.empty:
        st.info("No data available.")
        return

    col_chart, col_table = st.columns([2, 1])

    # --- Bar chart ---
    with col_chart:
        color_map = {
            "Current Due": chart_config.SUCCESS_COLOR,
            "Overdue": chart_config.DANGER_COLOR,
        }
        fig = px.bar(
            due_df,
            x="Remarks",
            y="Total Outstanding (USD)",
            text="Total Outstanding (USD)",
            color="Remarks",
            color_discrete_map=color_map,
            template=chart_config.CHART_TEMPLATE,
        )
        fig.update_traces(
            texttemplate="$%{text:,.0f}",
            textposition="outside",
        )
        fig.update_layout(
            height=chart_config.CHART_HEIGHT,
            xaxis_title="",
            yaxis_title="Outstanding (USD)",
            showlegend=False,
            yaxis=dict(tickformat="$,.0f"),
        )
        st.plotly_chart(fig, width="stretch")

    # --- Summary table ---
    with col_table:
        display_df = due_df.copy()
        total_outstanding = display_df["Total Outstanding (USD)"].sum()
        total_invoices = display_df["Invoice Count"].sum()

        total_row = pd.DataFrame(
            {
                "Remarks": ["Grand Total"],
                "Total Outstanding (USD)": [total_outstanding],
                "Invoice Count": [total_invoices],
                "% of Total": [100.0 if total_outstanding > 0 else 0.0],
            }
        )
        display_df = pd.concat([display_df, total_row], ignore_index=True)
        display_df["Total Outstanding (USD)"] = display_df["Total Outstanding (USD)"].apply(fmt_usd)
        display_df["% of Total"] = display_df["% of Total"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(display_df, width="stretch", hide_index=True)


# ======================================================================
# Customer Wise Outstanding
# ======================================================================

def render_customer_wise_outstanding(cust_df: pd.DataFrame) -> None:
    """
    Render a professional customer-level outstanding breakdown with
    grouped bar chart, summary metrics, and styled data table.
    """
    st.subheader("Customer Wise Outstanding")

    if cust_df.empty:
        st.info("No data available.")
        return

    # ── Summary metric cards ──────────────────────────────────────────
    total_customers = len(cust_df)
    total_current = cust_df["Current Due"].sum()
    total_overdue = cust_df["Overdue"].sum()
    customers_with_overdue = int((cust_df["Overdue"] > 0).sum())

    m1, m2 = st.columns(2)
    with m1:
        st.metric("Total Customers", fmt_number(total_customers))
    with m2:
        st.metric("Customers with Overdue", fmt_number(customers_with_overdue))

    st.markdown("")

    # ── Grouped bar chart (top 15) ────────────────────────────────────
    top_n = cust_df.head(15).copy()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=top_n["Customer Name"],
        x=top_n["Current Due"],
        name="Current Due",
        orientation="h",
        marker=dict(
            color=chart_config.SUCCESS_COLOR,
            line=dict(color="rgba(0,0,0,0.1)", width=0.5),
        ),
        text=top_n["Current Due"].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
        textposition="auto",
        textfont=dict(size=11),
    ))

    fig.add_trace(go.Bar(
        y=top_n["Customer Name"],
        x=top_n["Overdue"],
        name="Overdue",
        orientation="h",
        marker=dict(
            color=chart_config.DANGER_COLOR,
            line=dict(color="rgba(0,0,0,0.1)", width=0.5),
        ),
        text=top_n["Overdue"].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
        textposition="auto",
        textfont=dict(size=11),
    ))

    fig.update_layout(
        barmode="group",
        height=max(500, len(top_n) * 50),
        template=chart_config.CHART_TEMPLATE,
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=12),
        ),
        xaxis=dict(
            tickformat="$,.0f",
            title="Outstanding (USD)",
            gridcolor="rgba(0,0,0,0.05)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
        margin=dict(l=10, r=30, t=40, b=40),
        bargap=0.25,
        bargroupgap=0.1,
    )

    st.plotly_chart(fig, width="stretch")

    # ── Full data table ───────────────────────────────────────────────
    display_df = cust_df.copy()

    # Append grand total row
    total_row = pd.DataFrame({
        "Customer Name": ["Grand Total"],
        "Current Due": [total_current],
        "Overdue": [total_overdue],
        "Total Outstanding (USD)": [total_current + total_overdue],
    })
    display_df = pd.concat([display_df, total_row], ignore_index=True)

    for col in ("Current Due", "Overdue", "Total Outstanding (USD)"):
        display_df[col] = display_df[col].apply(fmt_usd)
    st.dataframe(display_df, width="stretch", hide_index=True)


# ======================================================================
# Business Wise Outstanding
# ======================================================================

def render_business_wise_outstanding(biz_df: pd.DataFrame) -> None:
    """
    Render business-unit-level outstanding breakdown with
    grouped bar chart, summary metrics, and data table.
    """
    st.subheader("Business Wise Outstanding")

    if biz_df.empty:
        st.info("No data available.")
        return

    # ── Summary metric cards ──────────────────────────────────────────
    total_units = len(biz_df)
    total_current = biz_df["Current Due"].sum()
    total_overdue = biz_df["Overdue"].sum()
    units_with_overdue = int((biz_df["Overdue"] > 0).sum())

    m1, m2 = st.columns(2)
    with m1:
        st.metric("Business Units", fmt_number(total_units))
    with m2:
        st.metric("Units with Overdue", fmt_number(units_with_overdue))

    st.markdown("")

    # ── Grouped bar chart ─────────────────────────────────────────────
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=biz_df["Bus Unit Name"],
        x=biz_df["Current Due"],
        name="Current Due",
        orientation="h",
        marker=dict(
            color=chart_config.SUCCESS_COLOR,
            line=dict(color="rgba(0,0,0,0.1)", width=0.5),
        ),
        text=biz_df["Current Due"].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
        textposition="auto",
        textfont=dict(size=11),
    ))

    fig.add_trace(go.Bar(
        y=biz_df["Bus Unit Name"],
        x=biz_df["Overdue"],
        name="Overdue",
        orientation="h",
        marker=dict(
            color=chart_config.DANGER_COLOR,
            line=dict(color="rgba(0,0,0,0.1)", width=0.5),
        ),
        text=biz_df["Overdue"].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
        textposition="auto",
        textfont=dict(size=11),
    ))

    fig.update_layout(
        barmode="group",
        height=max(400, len(biz_df) * 55),
        template=chart_config.CHART_TEMPLATE,
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=12),
        ),
        xaxis=dict(
            tickformat="$,.0f",
            title="Outstanding (USD)",
            gridcolor="rgba(0,0,0,0.05)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
        margin=dict(l=10, r=30, t=40, b=40),
        bargap=0.25,
        bargroupgap=0.1,
    )

    st.plotly_chart(fig, width="stretch")

    # ── Full data table ───────────────────────────────────────────────
    display_df = biz_df.copy()

    total_row = pd.DataFrame({
        "Bus Unit Name": ["Grand Total"],
        "Current Due": [total_current],
        "Overdue": [total_overdue],
        "Total Outstanding (USD)": [total_current + total_overdue],
    })
    display_df = pd.concat([display_df, total_row], ignore_index=True)

    for col in ("Current Due", "Overdue", "Total Outstanding (USD)"):
        display_df[col] = display_df[col].apply(fmt_usd)
    st.dataframe(display_df, width="stretch", hide_index=True)


# ======================================================================
# Allocation Wise Outstanding
# ======================================================================

def render_allocation_wise_outstanding(alloc_df: pd.DataFrame) -> None:
    """
    Render allocation-level outstanding breakdown with
    grouped bar chart, summary metrics, and data table.
    """
    st.subheader("Allocation Wise Outstanding")

    if alloc_df.empty:
        st.info("No data available.")
        return

    # -- Summary metric cards ------------------------------------------
    total_allocations = len(alloc_df)
    total_current = alloc_df["Current Due"].sum()
    total_overdue = alloc_df["Overdue"].sum()
    allocs_with_overdue = int((alloc_df["Overdue"] > 0).sum())

    m1, m2 = st.columns(2)
    with m1:
        st.metric("Allocations", fmt_number(total_allocations))
    with m2:
        st.metric("Allocations with Overdue", fmt_number(allocs_with_overdue))

    st.markdown("")

    # -- Vertical bar chart --------------------------------------------
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=alloc_df["Allocation"],
        y=alloc_df["Current Due"],
        name="Current Due",
        marker=dict(
            color=chart_config.SUCCESS_COLOR,
            line=dict(color="rgba(0,0,0,0.1)", width=0.5),
        ),
        text=alloc_df["Current Due"].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
        textposition="outside",
        textfont=dict(size=11),
    ))

    fig.add_trace(go.Bar(
        x=alloc_df["Allocation"],
        y=alloc_df["Overdue"],
        name="Overdue",
        marker=dict(
            color=chart_config.DANGER_COLOR,
            line=dict(color="rgba(0,0,0,0.1)", width=0.5),
        ),
        text=alloc_df["Overdue"].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
        textposition="outside",
        textfont=dict(size=11),
    ))

    fig.update_layout(
        barmode="group",
        height=chart_config.CHART_HEIGHT,
        template=chart_config.CHART_TEMPLATE,
        xaxis=dict(
            title="Allocation",
            tickfont=dict(size=12),
        ),
        yaxis=dict(
            tickformat="$,.0f",
            title="Outstanding (USD)",
            gridcolor="rgba(0,0,0,0.05)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
        margin=dict(l=10, r=30, t=40, b=40),
        bargap=0.25,
        bargroupgap=0.1,
    )

    st.plotly_chart(fig, width="stretch")

    # -- Full data table -----------------------------------------------
    display_df = alloc_df.copy()

    total_row = pd.DataFrame({
        "Allocation": ["Grand Total"],
        "Current Due": [total_current],
        "Overdue": [total_overdue],
        "Total Outstanding (USD)": [total_current + total_overdue],
    })
    display_df = pd.concat([display_df, total_row], ignore_index=True)

    for col in ("Current Due", "Overdue", "Total Outstanding (USD)"):
        display_df[col] = display_df[col].apply(fmt_usd)
    st.dataframe(display_df, width="stretch", hide_index=True)


# ======================================================================
# Entities Wise Outstanding
# ======================================================================

def render_entities_wise_outstanding(ent_df: pd.DataFrame) -> None:
    """
    Render entity-level outstanding breakdown with
    vertical bar chart, summary metrics, and data table.
    """
    st.subheader("Entities Wise Outstanding")

    if ent_df.empty:
        st.info("No data available.")
        return

    # -- Summary metric cards ------------------------------------------
    total_entities = len(ent_df)
    total_current = ent_df["Current Due"].sum()
    total_overdue = ent_df["Overdue"].sum()
    entities_with_overdue = int((ent_df["Overdue"] > 0).sum())

    m1, m2 = st.columns(2)
    with m1:
        st.metric("Entities", fmt_number(total_entities))
    with m2:
        st.metric("Entities with Overdue", fmt_number(entities_with_overdue))

    st.markdown("")

    # -- Vertical bar chart --------------------------------------------
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=ent_df["Entities"],
        y=ent_df["Current Due"],
        name="Current Due",
        marker=dict(
            color=chart_config.SUCCESS_COLOR,
            line=dict(color="rgba(0,0,0,0.1)", width=0.5),
        ),
        text=ent_df["Current Due"].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
        textposition="outside",
        textfont=dict(size=11),
    ))

    fig.add_trace(go.Bar(
        x=ent_df["Entities"],
        y=ent_df["Overdue"],
        name="Overdue",
        marker=dict(
            color=chart_config.DANGER_COLOR,
            line=dict(color="rgba(0,0,0,0.1)", width=0.5),
        ),
        text=ent_df["Overdue"].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
        textposition="outside",
        textfont=dict(size=11),
    ))

    fig.update_layout(
        barmode="group",
        height=chart_config.CHART_HEIGHT,
        template=chart_config.CHART_TEMPLATE,
        xaxis=dict(
            title="Entity",
            tickfont=dict(size=12),
        ),
        yaxis=dict(
            tickformat="$,.0f",
            title="Outstanding (USD)",
            gridcolor="rgba(0,0,0,0.05)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
        margin=dict(l=10, r=30, t=40, b=40),
        bargap=0.25,
        bargroupgap=0.1,
    )

    st.plotly_chart(fig, width="stretch")

    # -- Full data table -----------------------------------------------
    display_df = ent_df.copy()

    total_row = pd.DataFrame({
        "Entities": ["Grand Total"],
        "Current Due": [total_current],
        "Overdue": [total_overdue],
        "Total Outstanding (USD)": [total_current + total_overdue],
    })
    display_df = pd.concat([display_df, total_row], ignore_index=True)

    for col in ("Current Due", "Overdue", "Total Outstanding (USD)"):
        display_df[col] = display_df[col].apply(fmt_usd)
    st.dataframe(display_df, width="stretch", hide_index=True)
