"""
View layer – all Streamlit rendering logic.

This module is purely presentational.  It receives pre-computed data
from the Controller and renders it using Streamlit + Plotly.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from config.settings import chart_config
from utils.formatters import fmt_number, fmt_usd

# ======================================================================
# Helpers
# ======================================================================


def _get_remark_cols(df: pd.DataFrame, id_col: str) -> list[str]:
    """Return the list of remark/category columns (everything except id & total)."""
    skip = {id_col, "Total Outstanding (USD)"}
    return [c for c in df.columns if c not in skip]


def _remark_color(remark: str) -> str:
    """Return the configured color for a Remarks value, with a fallback."""
    return chart_config.REMARKS_COLORS.get(remark, chart_config.PRIMARY_COLOR)


def _selected_points(event: Any) -> list[dict[str, Any]]:
    """Safely extract selected points from a Plotly chart event."""
    try:
        if event and hasattr(event, "selection") and event.selection:
            return event.selection.get("points", [])
    except Exception as ex:
        logging.warning("Error extracting selected points: %s", ex)
    return []


def _extract_remark_from_point(
    point: dict[str, Any], fallback_list: list[str]
) -> str | None:
    """
    Extract the remark/category name from a Plotly selection point.
    Tries customdata first, then falls back to curve_number index.
    """
    customdata = point.get("customdata")
    if customdata:
        return customdata[0] if isinstance(customdata, list) else str(customdata)
    curve_num = point.get("curve_number", point.get("curveNumber"))
    if curve_num is not None and int(curve_num) < len(fallback_list):
        return fallback_list[int(curve_num)]
    return None


def _append_grand_total(
    df: pd.DataFrame, id_col: str, remark_cols: list[str]
) -> pd.DataFrame:
    """Append a Grand Total row to a summary DataFrame and format USD columns."""
    totals: dict[str, Any] = {id_col: "Grand Total"}
    for rc in remark_cols:
        totals[rc] = float(df[rc].sum()) if rc in df.columns else 0.0
    totals["Total Outstanding (USD)"] = float(df["Total Outstanding (USD)"].sum())
    result = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
    for col in remark_cols + ["Total Outstanding (USD)"]:
        if col in result.columns:
            result[col] = result[col].apply(fmt_usd)
    return result


def _render_drill_down_dataframe(
    detail_df: pd.DataFrame, column_config: dict[str, Any]
) -> None:
    """Format and render a drill-down invoice detail dataframe."""
    display = detail_df.copy()
    display["Total in USD"] = display["Total in USD"].apply(fmt_usd)
    total_val = detail_df["Total in USD"].sum()
    st.caption(
        f"**{len(detail_df):,} invoices** · Total: **{fmt_usd(total_val)}**"
    )
    st.dataframe(display, width="stretch", hide_index=True, column_config=column_config)


# Shared column_config blocks
_COMMON_COLS: dict[str, Any] = {
    "Customer Name": st.column_config.TextColumn("Customer Name", width="large"),
    "Reference":     st.column_config.TextColumn("Reference",     width="medium"),
    "New Org Name":  st.column_config.TextColumn("Business Unit", width="large"),
    "AR Status":     st.column_config.TextColumn("AR Status",     width="medium"),
    "AR Comments":   st.column_config.TextColumn("AR Comments",   width="large"),
    "Remarks":       st.column_config.TextColumn("Remarks",       width="medium"),
    "Projection":    st.column_config.TextColumn("Projection",    width="medium"),
    "Allocation":    st.column_config.TextColumn("Allocation",    width="medium"),
    "Entities":      st.column_config.TextColumn("Entity",        width="medium"),
    "Total in USD":  st.column_config.TextColumn("Total (USD)",   width="medium"),
}


# ======================================================================
# Page Configuration
# ======================================================================


def render_page_header(file_info: dict[str, Any] | None = None) -> None:
    """Render the main dashboard title and description.

    Args:
        file_info: Optional dict with file metadata (name, local_time, etc.).
                   If not provided, no file info is displayed.
    """
    st.title("AR Inflow Projection Dashboard")
    st.divider()

    if file_info:
        st.markdown(
            f"<b>Latest Sheet Update:</b> {file_info['local_time'].strftime('%m-%d-%Y %H:%M:%S %Z')}<br>"
            f"<b>File Name:</b> {file_info['name']}<br>",
            unsafe_allow_html=True,
        )

    css_path = pathlib.Path(__file__).parent / "styles.css"
    if css_path.exists():
        with open(css_path) as css_file:
            st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)

    sections = [
        ("Weekly Inflow Projection",    "ar-weekly_inflow"),
        ("AR Status Wise Outstanding",  "ar-status_wise"),
        ("Due Wise Outstanding",        "ar-due_wise"),
        ("Customer Wise Outstanding",   "ar-customer_wise"),
        ("Business Wise Outstanding",   "ar-business_wise"),
        ("Allocation Wise Outstanding", "ar-allocation_wise"),
        ("Entities Wise Outstanding",   "ar-entities_wise"),
    ]

    nav_items_html = "\n".join(
        f'<a class="nav-link" data-target="{anchor}" href="#">{label}</a>'
        for label, anchor in sections
    )

    components.html(
        f"""
        <style>
          * {{ margin: 0; padding: 0; box-sizing: border-box; }}
          body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
          .ar-navbar-container {{
            width: 100%; display: flex; justify-content: center; padding: 8px 16px;
          }}
          .ar-navbar-pro {{
            display: flex; flex-direction: row; flex-wrap: wrap; gap: 8px;
            justify-content: center; align-items: center; padding: 12px 20px;
            background: linear-gradient(135deg, #FFF6E8 0%, #FFF0D9 100%);
            border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.12);
            font-family: 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            max-width: 100%;
          }}
          .nav-link {{
            color: #333333; background: rgba(255,255,255,0.7); padding: 8px 16px;
            border-radius: 10px; text-decoration: none; font-weight: 500; font-size: 13px;
            letter-spacing: 0.01em; border: 1px solid rgba(0,0,0,0.08);
            transition: all 0.2s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            white-space: nowrap; cursor: pointer;
          }}
          .nav-link:hover {{
            background: #F2D7B6; color: #000000; border-color: #c9a66b;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15); transform: translateY(-1px);
          }}
          .nav-link:active {{ transform: translateY(0); box-shadow: 0 2px 6px rgba(0,0,0,0.1); }}
          @media (max-width: 800px) {{
            .nav-link {{ padding: 6px 12px; font-size: 12px; }}
            .ar-navbar-pro {{ gap: 6px; padding: 10px 14px; }}
          }}
        </style>
        <div class="ar-navbar-container">
          <div class="ar-navbar-pro">{nav_items_html}</div>
        </div>
        <script>
        document.querySelectorAll('.nav-link').forEach(function(link) {{
            link.addEventListener('click', function(e) {{
                e.preventDefault();
                var targetId = this.getAttribute('data-target');
                var parentDoc = window.parent.document;
                var target = parentDoc.getElementById(targetId);
                if (target) {{
                    target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }} else {{
                    var iframes = parentDoc.querySelectorAll('iframe');
                    for (var i = 0; i < iframes.length; i++) {{
                        try {{
                            var el = iframes[i].contentDocument.getElementById(targetId);
                            if (el) {{
                                el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                                break;
                            }}
                        }} catch(err) {{}}
                    }}
                }}
            }});
        }});
        </script>
        """,
        height=70,
        scrolling=False,
    )

    st.markdown(
        "<div style='margin-bottom:1.2rem;'>"
        "<hr style='border:0; border-top:1.5px solid #e0e0e0; margin:0;'>"
        "</div>",
        unsafe_allow_html=True,
    )


# ======================================================================
# KPI Metric Cards
# ======================================================================


def render_kpi_cards(
    grand_total: float,
    expected_inflow: float,
    next_month_1st_week: float,
    dispute_total: float,
    invoice_count: int,
    credit_memo_total: float = 0.0,
    current_due: float = 0.0,
    future_due: float = 0.0,
    overdue_total: float = 0.0,
    unapplied_total: float = 0.0,
    legal_total: float = 0.0,
    next_month_name: str = "",
) -> None:
    """Render top-level KPI metric cards."""
    col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns(9)

    with col1:
        st.metric("Grand Total",                             fmt_usd(grand_total))
    with col2:
        st.metric("Expected Projection",                     fmt_usd(expected_inflow))
    with col3:
        st.metric(f"{next_month_name} 1st Week Projection",  fmt_usd(next_month_1st_week))
    with col4:
        st.metric("Overdue",                                 fmt_usd(overdue_total))
    with col5:
        st.metric("Current Due",                             fmt_usd(current_due))
    with col6:
        st.metric("Future Due",                              fmt_usd(future_due))
    with col7:
        st.metric("In Dispute",                              fmt_usd(dispute_total))
    with col8:
        st.metric("Credits (CM+UA)",                         fmt_usd(credit_memo_total + unapplied_total))
    with col9:
        st.metric("Total Invoices",                          fmt_number(invoice_count))

    st.divider()


def render_kpi_cards_no_credit_unapplied(
    grand_total: float,
    expected_inflow: float,
    dispute_total: float,
    invoice_count: int,
    credit_memo_total: float = 0.0,   # fix: was missing → st.metric had no value
    unapplied_total: float = 0.0,     # fix: was missing → st.metric had no value
) -> None:
    """Render top-level KPI metric cards."""
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric("Grand Total (USD)",    fmt_usd(grand_total))
    with col2:
        st.metric("Expected Inflow (USD)", fmt_usd(expected_inflow))
    with col3:
        st.metric("In Dispute (USD)",     fmt_usd(dispute_total))
    with col4:
        st.metric("Total Invoices",       fmt_number(invoice_count))
    with col5:
        st.metric("Credit Memo (USD)",    fmt_usd(credit_memo_total))
    with col6:
        st.metric("Unapplied (USD)",      fmt_usd(unapplied_total))

    st.divider()


# ======================================================================
# Weekly Inflow Projection
# ======================================================================


def render_weekly_inflow_section(
    summary_df: pd.DataFrame,
    controller: Any = None,
) -> None:
    st.markdown('<a id="ar-weekly_inflow"></a>', unsafe_allow_html=True)
    st.subheader("Weekly Inflow Projection")
    st.caption("Click any bar to see invoice-level detail for that projection week.")

    fig = px.bar(
        summary_df,
        x="Projection",
        y="Total Inflow (USD)",
        text="Total Inflow (USD)",
        color="Projection",
        color_discrete_sequence=list(chart_config.BAR_COLOR_SEQUENCE),
        template=chart_config.CHART_TEMPLATE,
    )
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig.update_layout(
        height=chart_config.CHART_HEIGHT,
        xaxis_title="Projection Week",
        yaxis_title="Total Inflow (USD)",
        showlegend=False,
        yaxis=dict(tickformat="$,.0f"),
        clickmode="event+select",
    )

    event = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode="points",
        key="weekly_inflow_chart",
    )

    points = _selected_points(event)
    if points and controller is not None:
        clicked_projection = str(points[0].get("x") or points[0].get("label") or "")
        if clicked_projection:
            st.markdown("---")
            st.markdown(f"#### Detail — **{clicked_projection}**")
            detail_df = controller.get_projection_detail(clicked_projection)
            if detail_df.empty:
                st.info("No invoice records found for this projection.")
            else:
                _render_drill_down_dataframe(
                    detail_df,
                    {k: _COMMON_COLS[k] for k in
                     ["Customer Name", "Reference", "New Org Name", "AR Status", "Total in USD"]},
                )

    st.markdown("**Summary of Weekly Inflow Projection**")
    display_df = summary_df.copy()
    display_df["Total Inflow (USD)"] = display_df["Total Inflow (USD)"].apply(fmt_usd)
    display_df["% of Total"] = display_df["% of Total"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(display_df, width="stretch", hide_index=True)


# ======================================================================
# AR Status Wise Outstanding
# ======================================================================


def render_ar_status_wise_outstanding(
    status_df: pd.DataFrame, controller: Any = None
) -> None:
    """Render AR Status wise outstanding breakdown with bar-click drill-down."""
    st.markdown('<a id="ar-status_wise"></a>', unsafe_allow_html=True)
    st.subheader("AR Status Wise Outstanding")
    st.caption("Click any bar to see invoice-level detail for that AR Status & Remarks category.")

    if status_df.empty:
        st.info("No data available.")
        return

    remark_cols = _get_remark_cols(status_df, "AR Status")

    overdue_total     = float(status_df["Overdue"].sum())     if "Overdue"     in status_df.columns else 0.0
    current_due_total = float(status_df["Current Due"].sum()) if "Current Due" in status_df.columns else 0.0
    future_due_total  = float(status_df["Future Due"].sum())  if "Future Due"  in status_df.columns else 0.0
    credit_memo_total = float(status_df["Credit Memo"].sum()) if "Credit Memo" in status_df.columns else 0.0
    unapplied_total   = float(status_df["Unapplied"].sum())   if "Unapplied"   in status_df.columns else 0.0
    legal_total       = float(status_df["Legal"].sum())       if "Legal"       in status_df.columns else 0.0

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("AR Statuses",           fmt_number(len(status_df)))
    with m2:
        st.metric("Invoice",               fmt_usd(current_due_total + overdue_total + future_due_total))
    with m3:
        st.metric("Credits",               fmt_usd(credit_memo_total + unapplied_total))
    with m4:
        st.metric("Legal",                 fmt_usd(legal_total))
    with m5:
        st.metric("Total (Invoice+Legal)", fmt_usd(current_due_total + overdue_total + future_due_total + legal_total))

    st.markdown("")

    remark_order = ["Current Due", "Future Due", "Overdue"]
    ordered_remarks = [r for r in remark_order if r in remark_cols]
    ordered_remarks += [r for r in remark_cols if r not in remark_order]

    fig = go.Figure()
    for remark in ordered_remarks:
        if remark not in status_df.columns:
            continue
        fig.add_trace(go.Bar(
            x=status_df["AR Status"],
            y=status_df[remark],
            name=remark,
            marker=dict(color=_remark_color(remark), line=dict(color="rgba(0,0,0,0.1)", width=0.5)),
            text=status_df[remark].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
            textposition="outside",
            textfont=dict(size=10),
            customdata=[remark] * len(status_df),
        ))

    fig.update_layout(
        barmode="group",
        height=chart_config.CHART_HEIGHT,
        template=chart_config.CHART_TEMPLATE,
        xaxis=dict(title="AR Status", tickfont=dict(size=11), tickangle=-45),
        yaxis=dict(tickformat="$,.0f", title="Outstanding (USD)", gridcolor="rgba(0,0,0,0.05)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=12)),
        margin=dict(l=10, r=30, t=40, b=100),
        bargap=0.25, bargroupgap=0.1, clickmode="event+select",
    )

    event = st.plotly_chart(fig, width="stretch", on_select="rerun",
                            selection_mode="points", key="ar_status_wise_chart")

    points = _selected_points(event)
    if points and controller is not None:
        point = points[0]
        clicked_status = str(point.get("x") or point.get("label") or "")
        clicked_remark = _extract_remark_from_point(point, ordered_remarks)

        if clicked_status and clicked_remark:
            st.markdown("---")
            st.markdown(f"#### Detail — **{clicked_status}** · **{clicked_remark}**")
            detail_df = controller.get_ar_status_remark_detail(clicked_status, clicked_remark)
            if detail_df.empty:
                st.info(f"No invoice records found for {clicked_status} — {clicked_remark}.")
            else:
                _render_drill_down_dataframe(
                    detail_df,
                    {k: _COMMON_COLS[k] for k in
                     ["Customer Name", "Reference", "New Org Name", "Allocation",
                      "AR Comments", "AR Status", "Remarks", "Projection", "Total in USD"]},
                )

    st.markdown("**Summary of AR Status Wise Outstanding**")
    st.dataframe(
        _append_grand_total(status_df, "AR Status", remark_cols),
        width="stretch", hide_index=True,
    )


# ======================================================================
# Due Wise Outstanding
# ======================================================================


def render_due_wise_outstanding(due_df: pd.DataFrame, controller: Any = None) -> None:
    """Render outstanding amounts split by Remarks categories with drill-down."""
    st.markdown('<a id="ar-due_wise"></a>', unsafe_allow_html=True)
    st.subheader("Due Wise Outstanding")
    st.caption("Click any bar to see invoice-level detail for that category.")

    if due_df.empty:
        st.info("No data available.")
        return

    col_chart, col_table = st.columns([2, 1])

    with col_chart:
        color_map = {r: _remark_color(r) for r in due_df["Remarks"]}
        fig = px.bar(
            due_df,
            x="Remarks", y="Total Outstanding (USD)",
            text="Total Outstanding (USD)",
            color="Remarks", color_discrete_map=color_map,
            template=chart_config.CHART_TEMPLATE,
        )
        fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
        fig.update_layout(
            height=chart_config.CHART_HEIGHT,
            xaxis_title="", yaxis_title="Outstanding (USD)",
            showlegend=False,
            yaxis=dict(tickformat="$,.0f"),
            clickmode="event+select",
        )
        event = st.plotly_chart(fig, width="stretch", on_select="rerun",
                                selection_mode="points", key="due_wise_chart")

    with col_table:
        st.markdown("**Summary of Due Wise Outstanding**")
        display_df = due_df.copy()
        total_outstanding = float(display_df["Total Outstanding (USD)"].sum())
        total_row = pd.DataFrame({
            "Remarks": ["Grand Total"],
            "Total Outstanding (USD)": [total_outstanding],
            "Invoice Count": [display_df["Invoice Count"].sum()],
            "% of Total": [100.0 if total_outstanding > 0 else 0.0],
        })
        display_df = pd.concat([display_df, total_row], ignore_index=True)
        display_df["Total Outstanding (USD)"] = display_df["Total Outstanding (USD)"].apply(fmt_usd)
        display_df["% of Total"] = display_df["% of Total"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(display_df, width="stretch", hide_index=True)

    points = _selected_points(event)
    if points and controller is not None:
        clicked_remark = str(points[0].get("x") or points[0].get("label") or "")
        if clicked_remark:
            st.markdown("---")
            st.markdown(f"#### Detail — **{clicked_remark}**")
            detail_df = controller.get_due_wise_detail(clicked_remark)
            if detail_df.empty:
                st.info("No invoice records found for this category.")
            else:
                _render_drill_down_dataframe(
                    detail_df,
                    {k: _COMMON_COLS[k] for k in
                     ["Customer Name", "Reference", "New Org Name",
                      "AR Comments", "AR Status", "Total in USD"]},
                )


# ======================================================================
# Customer Wise Outstanding
# ======================================================================


def render_customer_wise_outstanding(
    cust_df: pd.DataFrame, controller: Any = None
) -> None:
    """Render customer-level outstanding breakdown with drill-down."""
    st.markdown('<a id="ar-customer_wise"></a>', unsafe_allow_html=True)
    st.subheader("Customer Wise Outstanding")

    if cust_df.empty:
        st.info("No data available.")
        return

    remark_cols = _get_remark_cols(cust_df, "Customer Name")

    overdue_count = int((cust_df.get("Overdue", pd.Series(dtype=float)) > 0).sum())
    m1, m2 = st.columns(2)
    with m1:
        st.metric("Total Customers",        fmt_number(len(cust_df)))
    with m2:
        st.metric("Customers with Overdue", fmt_number(overdue_count))
    st.markdown("")

    pie_df = cust_df[["Customer Name", "Total Outstanding (USD)"]].copy()
    pie_df = pie_df.sort_values("Total Outstanding (USD)", ascending=False)
    top10 = pie_df.head(10)
    others_sum = float(pie_df["Total Outstanding (USD)"].iloc[10:].sum())
    pie_labels: list[str] = list(top10["Customer Name"])
    pie_values: list[float] = list(top10["Total Outstanding (USD)"])
    if others_sum > 0:
        pie_labels.append("Others")
        pie_values.append(others_sum)

    fig = go.Figure(go.Pie(
        labels=pie_labels, values=pie_values,
        textinfo="percent", hoverinfo="label+value+percent",
        marker=dict(line=dict(color="#fff", width=1)),
        sort=False, textposition="inside",
    ))
    fig.update_layout(
        margin=dict(l=40, r=40, t=60, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="center", x=0.5, font=dict(size=12)),
        showlegend=True,
    )
    st.plotly_chart(fig, width="stretch", key="customer_wise_pie")

    if controller is not None:
        st.markdown("---")
        st.markdown("#### Choose a customer to view invoice details")
        all_customers = sorted(cust_df["Customer Name"].unique().tolist())
        selected_customer = st.selectbox(
            "---",
            options=["— Select a customer —"] + all_customers,
            index=0,
            key="customer_wise_selectbox",
        )
        if selected_customer != "— Select a customer —":
            detail_df = controller.get_customer_wise_detail(selected_customer)
            if detail_df.empty:
                st.info("No invoice records found for this customer.")
            else:
                _render_drill_down_dataframe(
                    detail_df,
                    {k: _COMMON_COLS[k] for k in
                     ["Customer Name", "Reference", "New Org Name",
                      "AR Comments", "AR Status", "Remarks", "Total in USD"]},
                )

    st.markdown("**Summary of Customer Wise Outstanding**")
    st.dataframe(
        _append_grand_total(cust_df, "Customer Name", remark_cols),
        width="stretch", hide_index=True,
    )


# ======================================================================
# Business Wise Outstanding
# ======================================================================


def render_business_wise_outstanding(
    biz_df: pd.DataFrame, controller: Any = None
) -> None:
    """Render business-unit-level outstanding breakdown with drill-down."""
    st.markdown('<a id="ar-business_wise"></a>', unsafe_allow_html=True)
    st.subheader("Business Wise Outstanding")
    st.caption("Select a business unit from the dropdown to see invoice-level detail.")

    if biz_df.empty:
        st.info("No data available.")
        return

    remark_cols = _get_remark_cols(biz_df, "New Org Name")

    overdue_count = int((biz_df.get("Overdue", pd.Series(dtype=float)) > 0).sum())
    m1, m2 = st.columns(2)
    with m1:
        st.metric("Business Units",     fmt_number(len(biz_df)))
    with m2:
        st.metric("Units with Overdue", fmt_number(overdue_count))
    st.markdown("")

    pie_df = biz_df[["New Org Name", "Total Outstanding (USD)"]].copy()
    pie_df = pie_df.sort_values("Total Outstanding (USD)", ascending=False)
    top10 = pie_df.head(10)
    others_sum = float(pie_df["Total Outstanding (USD)"].iloc[10:].sum())
    pie_labels = list(top10["New Org Name"])
    pie_values = list(top10["Total Outstanding (USD)"])
    if others_sum > 0:
        pie_labels.append("Others")
        pie_values.append(others_sum)

    fig = go.Figure(go.Pie(
        labels=pie_labels, values=pie_values,
        textinfo="percent", hoverinfo="label+value+percent",
        marker=dict(line=dict(color="#fff", width=1)),
        sort=False, textposition="inside",
    ))
    fig.update_layout(
        margin=dict(l=40, r=40, t=60, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="center", x=0.5, font=dict(size=12)),
        showlegend=True,
    )
    st.plotly_chart(fig, width="stretch", key="business_wise_pie")

    if controller is not None:
        st.markdown("---")
        st.markdown("#### Choose a business unit to view invoice details:")
        all_units = sorted(biz_df["New Org Name"].unique().tolist())
        selected_unit = st.selectbox(
            "---",
            options=["— Select a business unit —"] + all_units,
            index=0,
            key="business_wise_selectbox",
        )
        if selected_unit != "— Select a business unit —":
            detail_df = controller.get_business_wise_detail(selected_unit)
            if detail_df.empty:
                st.info("No invoice records found for this business unit.")
            else:
                _render_drill_down_dataframe(
                    detail_df,
                    {k: _COMMON_COLS[k] for k in
                     ["Customer Name", "Reference", "New Org Name",
                      "AR Comments", "AR Status", "Remarks", "Total in USD"]},
                )

    st.markdown("**Summary of Business Wise Outstanding**")
    st.dataframe(
        _append_grand_total(biz_df, "New Org Name", remark_cols),
        width="stretch", hide_index=True,
    )


# ======================================================================
# Allocation Wise Outstanding
# ======================================================================


def render_allocation_wise_outstanding(
    alloc_df: pd.DataFrame, controller: Any = None
) -> None:
    """Render allocation-level outstanding breakdown with bar-click drill-down."""
    st.markdown('<a id="ar-allocation_wise"></a>', unsafe_allow_html=True)
    st.subheader("Allocation Wise Outstanding")
    st.caption("Click any bar to see invoice-level detail for that allocation & category.")

    if alloc_df.empty:
        st.info("No data available.")
        return

    remark_cols = _get_remark_cols(alloc_df, "Allocation")

    overdue_count = int((alloc_df.get("Overdue", pd.Series(dtype=float)) > 0).sum())
    m1, m2 = st.columns(2)
    with m1:
        st.metric("Allocations",              fmt_number(len(alloc_df)))
    with m2:
        st.metric("Allocations with Overdue", fmt_number(overdue_count))
    st.markdown("")

    fig = go.Figure()
    for remark in remark_cols:
        if remark not in alloc_df.columns:
            continue
        fig.add_trace(go.Bar(
            x=alloc_df["Allocation"],
            y=alloc_df[remark],
            name=remark,
            marker=dict(color=_remark_color(remark), line=dict(color="rgba(0,0,0,0.1)", width=0.5)),
            text=alloc_df[remark].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
            textposition="outside", textfont=dict(size=11),
            customdata=[remark] * len(alloc_df),
        ))

    fig.update_layout(
        barmode="group",
        height=chart_config.CHART_HEIGHT,
        template=chart_config.CHART_TEMPLATE,
        xaxis=dict(title="Allocation", tickfont=dict(size=12)),
        yaxis=dict(tickformat="$,.0f", title="Outstanding (USD)", gridcolor="rgba(0,0,0,0.05)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="center", x=0.5, font=dict(size=12)),
        margin=dict(l=10, r=30, t=40, b=40),
        bargap=0.25, bargroupgap=0.1, clickmode="event+select",
    )

    event = st.plotly_chart(fig, width="stretch", on_select="rerun",
                            selection_mode="points", key="allocation_wise_chart")

    points = _selected_points(event)
    if points and controller is not None:
        point = points[0]
        clicked_allocation = str(point.get("x") or point.get("label") or "")
        clicked_remark = _extract_remark_from_point(point, remark_cols)
        if clicked_allocation and clicked_remark:
            st.markdown("---")
            st.markdown(f"#### Detail — **{clicked_allocation}** · **{clicked_remark}**")
            detail_df = controller.get_allocation_remark_detail(clicked_allocation, clicked_remark)
            if detail_df.empty:
                st.info(f"No invoice records found for {clicked_allocation} — {clicked_remark}.")
            else:
                _render_drill_down_dataframe(
                    detail_df,
                    {k: _COMMON_COLS[k] for k in
                     ["Customer Name", "Reference", "New Org Name", "Allocation",
                      "AR Comments", "AR Status", "Remarks", "Total in USD"]},
                )

    st.markdown("**Summary of Allocation Wise Outstanding**")
    st.dataframe(
        _append_grand_total(alloc_df, "Allocation", remark_cols),
        width="stretch", hide_index=True,
    )


# ======================================================================
# Entities Wise Outstanding
# ======================================================================


def render_entities_wise_outstanding(
    ent_df: pd.DataFrame, controller: Any = None
) -> None:
    """Render entity-level outstanding breakdown with bar-click drill-down."""
    st.markdown('<a id="ar-entities_wise"></a>', unsafe_allow_html=True)
    st.subheader("Entities Wise Outstanding")
    st.caption("Click any bar to see invoice-level detail for that entity & category.")

    if ent_df.empty:
        st.info("No data available.")
        return

    remark_cols = _get_remark_cols(ent_df, "Entities")

    overdue_count = int((ent_df.get("Overdue", pd.Series(dtype=float)) > 0).sum())
    m1, m2 = st.columns(2)
    with m1:
        st.metric("Entities",              fmt_number(len(ent_df)))
    with m2:
        st.metric("Entities with Overdue", fmt_number(overdue_count))
    st.markdown("")

    fig = go.Figure()
    for remark in remark_cols:
        if remark not in ent_df.columns:
            continue
        fig.add_trace(go.Bar(
            x=ent_df["Entities"],
            y=ent_df[remark],
            name=remark,
            marker=dict(color=_remark_color(remark), line=dict(color="rgba(0,0,0,0.1)", width=0.5)),
            text=ent_df[remark].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
            textposition="outside", textfont=dict(size=11),
            customdata=[remark] * len(ent_df),
        ))

    fig.update_layout(
        barmode="group",
        height=chart_config.CHART_HEIGHT,
        template=chart_config.CHART_TEMPLATE,
        xaxis=dict(title="Entity", tickfont=dict(size=12)),
        yaxis=dict(tickformat="$,.0f", title="Outstanding (USD)", gridcolor="rgba(0,0,0,0.05)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="center", x=0.5, font=dict(size=12)),
        margin=dict(l=10, r=30, t=40, b=40),
        bargap=0.25, bargroupgap=0.1, clickmode="event+select",
    )

    event = st.plotly_chart(fig, width="stretch", on_select="rerun",
                            selection_mode="points", key="entities_wise_chart")

    points = _selected_points(event)
    if points and controller is not None:
        point = points[0]
        clicked_entity = str(point.get("x") or point.get("label") or "")
        clicked_remark = _extract_remark_from_point(point, remark_cols)
        if clicked_entity and clicked_remark:
            st.markdown("---")
            st.markdown(f"#### Detail — **{clicked_entity}** · **{clicked_remark}**")
            detail_df = controller.get_entities_remark_detail(clicked_entity, clicked_remark)
            if detail_df.empty:
                st.info(f"No invoice records found for {clicked_entity} — {clicked_remark}.")
            else:
                _render_drill_down_dataframe(
                    detail_df,
                    {k: _COMMON_COLS[k] for k in
                     ["Customer Name", "Reference", "New Org Name", "Entities", "Allocation",
                      "AR Comments", "AR Status", "Remarks", "Total in USD"]},
                )

    st.markdown("**Summary of Entities Wise Outstanding**")
    st.dataframe(
        _append_grand_total(ent_df, "Entities", remark_cols),
        width="stretch", hide_index=True,
    )
