"""
View layer – all Streamlit rendering logic.

This module is purely presentational.  It receives pre-computed data
from the Controller and renders it using Streamlit + Plotly.
"""

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


def _get_remark_cols(df: pd.DataFrame, id_col: str) -> list:
    """Return the list of remark/category columns (everything except id & total)."""
    skip = {id_col, "Total Outstanding (USD)"}
    return [c for c in df.columns if c not in skip]


def _remark_color(remark: str) -> str:
    """Return the configured color for a Remarks value, with a fallback."""
    return chart_config.REMARKS_COLORS.get(remark, chart_config.PRIMARY_COLOR)


# ======================================================================
# Page Configuration
# ======================================================================


def render_page_header() -> None:
    """Render the main dashboard title and description."""
    st.title("AR Inflow Projection Dashboard")
    st.divider()
    # Show last edit time section
    from utils.sharepoint_fetch import get_latest_file_info

    info = get_latest_file_info()
    if info:
        st.markdown(
            f"<b>Latest Sheet Update:</b> {info['local_time'].strftime('%m-%d-%Y %H:%M:%S %Z')}<br>"
            f"<b>File Name:</b> {info['name']}<br>",
            unsafe_allow_html=True,
        )

    sections = [
        ("Weekly Inflow Projection", "ar-weekly_inflow"),
        ("Due Wise Outstanding", "ar-due_wise"),
        ("Customer Wise Outstanding", "ar-customer_wise"),
        ("Business Wise Outstanding", "ar-business_wise"),
        ("Allocation Wise Outstanding", "ar-allocation_wise"),
        ("Entities Wise Outstanding", "ar-entities_wise"),
    ]

    nav_items_html = "\n".join(
        f'<a class="nav-link" data-target="{anchor}" href="#">{label}</a>'
        for label, anchor in sections
    )

    # Use components.html so the <script> is truly executed (not sandboxed).
    # height is kept small; the iframe is invisible – it only injects JS into
    # the PARENT window via window.parent.
    components.html(
        f"""
        <style>
          body {{ margin: 0; padding: 0; background: transparent; }}

          .ar-navbar-pro {{
            display: flex;
            flex-direction: row;
            flex-wrap: wrap;
            gap: 0.9rem;
            justify-content: center;
            align-items: center;
            padding: 0.65rem 1rem;
            background: #FFF6E8;
            border-radius: 1.5rem;
            box-shadow: 0 2px 16px rgba(0,0,0,0.15);
            font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
          }}

          .nav-link {{
            color: #000000;
            background: #FFF6E8;
            padding: 0.45rem 1.25rem;
            border-radius: 1.1rem;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.97rem;
            letter-spacing: 0.01em;
            border: 1.5px solid transparent;
            transition: background 0.18s, color 0.18s, box-shadow 0.18s;
            box-shadow: 0 1px 4px rgba(0,0,0,0.07);
          }}

          .nav-link:hover {{
            background: #F2D7B6;
            color: #000000;
            border-color: #3a3b41;
            box-shadow: 0 2px 8px rgba(0,0,0,0.18);
          }}
        </style>

        <div class="ar-navbar-pro">
          {nav_items_html}
        </div>

        <script>
          document.querySelectorAll('.nav-link').forEach(function(link) {{
            link.addEventListener('click', function(e) {{
              e.preventDefault();
              var targetId = this.getAttribute('data-target');

              // The navbar lives in a small iframe injected by components.html.
              // The actual section anchors live in the parent Streamlit document.
              var parentDoc = window.parent.document;
              var target = parentDoc.getElementById(targetId);

              if (target) {{
                target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
              }} else {{
                // Fallback: search all iframes inside the parent for the element
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
        height=75,  # just tall enough to show the navbar bar
        scrolling=False,
    )

    st.markdown(
        "<div style='margin-bottom:1.2rem;'>"
        "<hr style='border:0; border-top:1.5px solid #23242a; margin:0;'>"
        "</div>",
        unsafe_allow_html=True,
    )


# ======================================================================
# KPI Metric Cards
# ======================================================================


def render_kpi_cards(
    grand_total: float,
    expected_inflow: float,
    dispute_total: float,
    invoice_count: int,
    credit_memo_total: float = 0.0,
    unapplied_total: float = 0.0,
) -> None:
    """Render top-level KPI metric cards, including Credit Memo and Unapplied."""
    col1, col2, col3, col4, col5, col6 = st.columns(6)

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
            label="Credit Memo (USD)",
            value=fmt_usd(credit_memo_total),
        )
    with col5:
        st.metric(
            label="Unapplied (USD)",
            value=fmt_usd(unapplied_total),
        )
    with col6:
        st.metric(
            label="Total Invoices",
            value=fmt_number(invoice_count),
        )
    st.divider()


def render_kpi_cards_no_credit_unapplied(
    grand_total: float,
    expected_inflow: float,
    dispute_total: float,
    invoice_count: int,
) -> None:
    """Render top-level KPI metric cards."""
    col1, col2, col3, col4, col5, col6 = st.columns(6)

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
    with col5:
        st.metric(
            label="Credit Memo (USD)",
        )
    with col6:
        st.metric(
            label="Unapplied (USD)",
        )
    st.divider()

def render_weekly_inflow_section(
    summary_df: "pd.DataFrame",
    controller=None,
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
        clickmode="event+select",
    )

    # FIX: width="stretch" instead of use_container_width=True
    event = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode="points",
        key="weekly_inflow_chart",
    )

    # ── Drill-down on click ──
    selected_points = (
        event.selection.get("points", [])
        if event and hasattr(event, "selection") and event.selection
        else []
    )

    if selected_points and controller is not None:
        clicked_projection = selected_points[0].get("x") or selected_points[0].get("label")

        if clicked_projection:
            st.markdown("---")
            st.markdown(f"#### Detail — **{clicked_projection}**")

            detail_df = controller.get_projection_detail(clicked_projection)

            if detail_df.empty:
                st.info("No invoice records found for this projection.")
            else:
                display_detail = detail_df.copy()
                display_detail["Total in USD"] = display_detail["Total in USD"].apply(fmt_usd)

                total_val = detail_df["Total in USD"].sum()
                st.caption(
                    f"**{len(detail_df):,} invoices** · "
                    f"Total: **{fmt_usd(total_val)}**"
                )

                st.dataframe(
                    display_detail,
                    width="stretch",          # FIX
                    hide_index=True,
                    column_config={
                        "Customer Name": st.column_config.TextColumn("Customer Name", width="large"),
                        "Reference":     st.column_config.TextColumn("Reference",     width="medium"),
                        "New Org Name":  st.column_config.TextColumn("Business Unit", width="large"),
                        "AR Status":     st.column_config.TextColumn("AR Status",     width="medium"),
                        "Total in USD":  st.column_config.TextColumn("Total (USD)",   width="medium"),
                    },
                )
     
    # --- Summary table ---
    display_df = summary_df.copy()
    display_df["Total Inflow (USD)"] = display_df["Total Inflow (USD)"].apply(fmt_usd)
    display_df["% of Total"] = display_df["% of Total"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(display_df, width="stretch", hide_index=True)


# ======================================================================
# Due Wise Outstanding
# ======================================================================


def render_due_wise_outstanding(due_df: pd.DataFrame, controller=None) -> None:
    """Render outstanding amounts split by Remarks categories with drill-down."""
    st.markdown('<a id="ar-due_wise"></a>', unsafe_allow_html=True)
    st.subheader("Due Wise Outstanding")
    st.caption("💡 Click any bar to see invoice-level detail for that category.")

    if due_df.empty:
        st.info("No data available.")
        return

    col_chart, col_table = st.columns([2, 1])

    # --- Bar chart with click support ---
    with col_chart:
        color_map = {r: _remark_color(r) for r in due_df["Remarks"]}
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
            clickmode="event+select",
        )

        event = st.plotly_chart(
            fig,
            width="stretch",
            on_select="rerun",
            selection_mode="points",
            key="due_wise_chart",
        )

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
        display_df["Total Outstanding (USD)"] = display_df[
            "Total Outstanding (USD)"
        ].apply(fmt_usd)
        display_df["% of Total"] = display_df["% of Total"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(display_df, width="stretch", hide_index=True)

    # ── Drill-down on click ──────────────────────────────────────────
    selected_points = (
        event.selection.get("points", [])
        if event and hasattr(event, "selection") and event.selection
        else []
    )

    if selected_points and controller is not None:
        clicked_remark = selected_points[0].get("x") or selected_points[0].get("label")

        if clicked_remark:
            st.markdown("---")
            st.markdown(f"#### Detail — **{clicked_remark}**")

            detail_df = controller.get_due_wise_detail(clicked_remark)

            if detail_df.empty:
                st.info("No invoice records found for this category.")
            else:
                display_detail = detail_df.copy()
                display_detail["Total in USD"] = display_detail["Total in USD"].apply(fmt_usd)

                total_val = detail_df["Total in USD"].sum()
                st.caption(
                    f"**{len(detail_df):,} invoices** · "
                    f"Total: **{fmt_usd(total_val)}**"
                )

                st.dataframe(
                    display_detail,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Customer Name": st.column_config.TextColumn("Customer Name", width="large"),
                        "Reference":     st.column_config.TextColumn("Reference",     width="medium"),
                        "New Org Name":  st.column_config.TextColumn("Business Unit", width="large"),
                        "AR Comments":   st.column_config.TextColumn("AR Comments",   width="large"),
                        "AR Status":     st.column_config.TextColumn("AR Status",     width="medium"),
                        "Total in USD":  st.column_config.TextColumn("Total (USD)",   width="medium"),
                    },
                )

# ======================================================================
# Customer Wise Outstanding
# ======================================================================


def render_customer_wise_outstanding(cust_df: pd.DataFrame, controller=None) -> None:
    """Render customer-level outstanding breakdown with drill-down."""
    st.markdown('<a id="ar-customer_wise"></a>', unsafe_allow_html=True)
    st.subheader("Customer Wise Outstanding")
    st.caption("💡 Select a customer from the dropdown to see invoice-level detail.")

    if cust_df.empty:
        st.info("No data available.")
        return

    remark_cols = _get_remark_cols(cust_df, "Customer Name")

    # -- Summary metric cards ------------------------------------------
    total_customers = len(cust_df)
    overdue_count = int((cust_df.get("Overdue", pd.Series(dtype=float)) > 0).sum())

    m1, m2 = st.columns(2)
    with m1:
        st.metric("Total Customers", fmt_number(total_customers))
    with m2:
        st.metric("Customers with Overdue", fmt_number(overdue_count))

    st.markdown("")

    # -- Pie chart (display only, no click) ----------------------------
    pie_df = cust_df[["Customer Name", "Total Outstanding (USD)"]].copy()
    pie_df = pie_df.sort_values("Total Outstanding (USD)", ascending=False)
    top10 = pie_df.head(10)
    others_sum = pie_df["Total Outstanding (USD)"].iloc[10:].sum()
    pie_labels = list(top10["Customer Name"])
    pie_values = list(top10["Total Outstanding (USD)"])
    if others_sum > 0:
        pie_labels.append("Others")
        pie_values.append(others_sum)

    fig = go.Figure(
        go.Pie(
            labels=pie_labels,
            values=pie_values,
            textinfo="percent",
            hoverinfo="label+value+percent",
            marker=dict(line=dict(color="#fff", width=1)),
            sort=False,
            textposition="inside",
        )
    )
    fig.update_layout(
        margin=dict(l=40, r=40, t=60, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
        showlegend=True,
    )
    st.plotly_chart(fig, width="stretch", key="customer_wise_pie")

    # ── Drill-down via selectbox ─────────────────────────────────────
    if controller is not None:
        st.markdown("---")
        st.markdown("#### Customer Drill-Down")

        all_customers = sorted(cust_df["Customer Name"].unique().tolist())
        customer_options = ["— Select a customer —"] + all_customers

        selected_customer = st.selectbox(
            "Choose a customer to view invoice details:",
            options=customer_options,
            index=0,
            key="customer_wise_selectbox",
        )

        if selected_customer != "— Select a customer —":
            detail_df = controller.get_customer_wise_detail(selected_customer)

            if detail_df.empty:
                st.info("No invoice records found for this customer.")
            else:
                display_detail = detail_df.copy()
                display_detail["Total in USD"] = display_detail["Total in USD"].apply(
                    fmt_usd
                )

                total_val = detail_df["Total in USD"].sum()
                st.caption(
                    f"**{len(detail_df):,} invoices** · "
                    f"Total: **{fmt_usd(total_val)}**"
                )

                st.dataframe(
                    display_detail,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Customer Name": st.column_config.TextColumn(
                            "Customer Name", width="large"
                        ),
                        "Reference": st.column_config.TextColumn(
                            "Reference", width="medium"
                        ),
                        "New Org Name": st.column_config.TextColumn(
                            "Business Unit", width="large"
                        ),
                        "AR Comments": st.column_config.TextColumn(
                            "AR Comments", width="large"
                        ),
                        "AR Status": st.column_config.TextColumn(
                            "AR Status", width="medium"
                        ),
                        "Remarks": st.column_config.TextColumn(
                            "Remarks", width="medium"
                        ),
                        "Total in USD": st.column_config.TextColumn(
                            "Total (USD)", width="medium"
                        ),
                    },
                )
    
    # -- Full data table -----------------------------------------------
    display_df = cust_df.copy()
    totals = {"Customer Name": "Grand Total"}
    for rc in remark_cols:
        totals[rc] = cust_df[rc].sum() if rc in cust_df.columns else 0.0
    totals["Total Outstanding (USD)"] = cust_df["Total Outstanding (USD)"].sum()
    display_df = pd.concat([display_df, pd.DataFrame([totals])], ignore_index=True)

    for col in remark_cols + ["Total Outstanding (USD)"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(fmt_usd)
    st.dataframe(display_df, width="stretch", hide_index=True)

# ======================================================================
# Business Wise Outstanding
# ======================================================================


def render_business_wise_outstanding(biz_df: pd.DataFrame) -> None:
    """Render business-unit-level outstanding breakdown."""
    st.markdown('<a id="ar-business_wise"></a>', unsafe_allow_html=True)
    st.subheader("Business Wise Outstanding")

    if biz_df.empty:
        st.info("No data available.")
        return

    remark_cols = _get_remark_cols(biz_df, "New Org Name")

    # -- Summary metric cards ------------------------------------------
    total_units = len(biz_df)
    overdue_count = int((biz_df.get("Overdue", pd.Series(dtype=float)) > 0).sum())

    m1, m2 = st.columns(2)
    with m1:
        st.metric("Business Units", fmt_number(total_units))
    with m2:
        st.metric("Units with Overdue", fmt_number(overdue_count))

    st.markdown("")

    # Pie chart for top 10 business units, rest as 'Others'
    pie_df = biz_df[["New Org Name", "Total Outstanding (USD)"]].copy()
    pie_df = pie_df.sort_values("Total Outstanding (USD)", ascending=False)
    top10 = pie_df.head(10)
    others_sum = pie_df["Total Outstanding (USD)"].iloc[10:].sum()
    pie_labels = list(top10["New Org Name"])
    pie_values = list(top10["Total Outstanding (USD)"])
    if others_sum > 0:
        pie_labels.append("Others")
        pie_values.append(others_sum)
    fig = go.Figure(
        go.Pie(
            labels=pie_labels,
            values=pie_values,
            textinfo="percent",
            hoverinfo="label+value+percent",
            marker=dict(line=dict(color="#fff", width=1)),
            sort=False,
            textposition="inside",
        )
    )
    fig.update_layout(
        margin=dict(l=40, r=40, t=60, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
        showlegend=True,
    )
    st.plotly_chart(fig, width="stretch")

    # -- Full data table -----------------------------------------------
    display_df = biz_df.copy()
    totals = {"New Org Name": "Grand Total"}
    for rc in remark_cols:
        totals[rc] = biz_df[rc].sum() if rc in biz_df.columns else 0.0
    totals["Total Outstanding (USD)"] = biz_df["Total Outstanding (USD)"].sum()
    display_df = pd.concat([display_df, pd.DataFrame([totals])], ignore_index=True)

    for col in remark_cols + ["Total Outstanding (USD)"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(fmt_usd)
    st.dataframe(display_df, width="stretch", hide_index=True)


# ======================================================================
# Allocation Wise Outstanding
# ======================================================================


def render_allocation_wise_outstanding(alloc_df: pd.DataFrame) -> None:
    """Render allocation-level outstanding breakdown."""
    st.markdown('<a id="ar-allocation_wise"></a>', unsafe_allow_html=True)
    st.subheader("Allocation Wise Outstanding")

    if alloc_df.empty:
        st.info("No data available.")
        return

    remark_cols = _get_remark_cols(alloc_df, "Allocation")

    # -- Summary metric cards ------------------------------------------
    total_allocations = len(alloc_df)
    overdue_count = int((alloc_df.get("Overdue", pd.Series(dtype=float)) > 0).sum())

    m1, m2 = st.columns(2)
    with m1:
        st.metric("Allocations", fmt_number(total_allocations))
    with m2:
        st.metric("Allocations with Overdue", fmt_number(overdue_count))

    st.markdown("")

    # -- Vertical bar chart --------------------------------------------
    fig = go.Figure()
    for remark in remark_cols:
        if remark not in alloc_df.columns:
            continue
        fig.add_trace(
            go.Bar(
                x=alloc_df["Allocation"],
                y=alloc_df[remark],
                name=remark,
                marker=dict(
                    color=_remark_color(remark),
                    line=dict(color="rgba(0,0,0,0.1)", width=0.5),
                ),
                text=alloc_df[remark].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
                textposition="outside",
                textfont=dict(size=11),
            )
        )

    fig.update_layout(
        barmode="group",
        height=chart_config.CHART_HEIGHT,
        template=chart_config.CHART_TEMPLATE,
        xaxis=dict(title="Allocation", tickfont=dict(size=12)),
        yaxis=dict(
            tickformat="$,.0f", title="Outstanding (USD)", gridcolor="rgba(0,0,0,0.05)"
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
    totals = {"Allocation": "Grand Total"}
    for rc in remark_cols:
        totals[rc] = alloc_df[rc].sum() if rc in alloc_df.columns else 0.0
    totals["Total Outstanding (USD)"] = alloc_df["Total Outstanding (USD)"].sum()
    display_df = pd.concat([display_df, pd.DataFrame([totals])], ignore_index=True)

    for col in remark_cols + ["Total Outstanding (USD)"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(fmt_usd)
    st.dataframe(display_df, width="stretch", hide_index=True)


# ======================================================================
# Entities Wise Outstanding
# ======================================================================


def render_entities_wise_outstanding(ent_df: pd.DataFrame) -> None:
    """Render entity-level outstanding breakdown."""
    st.markdown('<a id="ar-entities_wise"></a>', unsafe_allow_html=True)
    st.subheader("Entities Wise Outstanding")

    if ent_df.empty:
        st.info("No data available.")
        return

    remark_cols = _get_remark_cols(ent_df, "Entities")

    # -- Summary metric cards ------------------------------------------
    total_entities = len(ent_df)
    overdue_count = int((ent_df.get("Overdue", pd.Series(dtype=float)) > 0).sum())

    m1, m2 = st.columns(2)
    with m1:
        st.metric("Entities", fmt_number(total_entities))
    with m2:
        st.metric("Entities with Overdue", fmt_number(overdue_count))

    st.markdown("")

    # -- Vertical bar chart --------------------------------------------
    fig = go.Figure()
    for remark in remark_cols:
        if remark not in ent_df.columns:
            continue
        fig.add_trace(
            go.Bar(
                x=ent_df["Entities"],
                y=ent_df[remark],
                name=remark,
                marker=dict(
                    color=_remark_color(remark),
                    line=dict(color="rgba(0,0,0,0.1)", width=0.5),
                ),
                text=ent_df[remark].apply(lambda v: f"${v:,.0f}" if v > 0 else ""),
                textposition="outside",
                textfont=dict(size=11),
            )
        )

    fig.update_layout(
        barmode="group",
        height=chart_config.CHART_HEIGHT,
        template=chart_config.CHART_TEMPLATE,
        xaxis=dict(title="Entity", tickfont=dict(size=12)),
        yaxis=dict(
            tickformat="$,.0f", title="Outstanding (USD)", gridcolor="rgba(0,0,0,0.05)"
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
    totals = {"Entities": "Grand Total"}
    for rc in remark_cols:
        totals[rc] = ent_df[rc].sum() if rc in ent_df.columns else 0.0
    totals["Total Outstanding (USD)"] = ent_df["Total Outstanding (USD)"].sum()
    display_df = pd.concat([display_df, pd.DataFrame([totals])], ignore_index=True)

    for col in remark_cols + ["Total Outstanding (USD)"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(fmt_usd)
    st.dataframe(display_df, width="stretch", hide_index=True)
