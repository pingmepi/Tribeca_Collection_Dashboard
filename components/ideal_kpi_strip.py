import pandas as pd
import streamlit as st
import plotly.express as px

from utils.helper import to_cr
from services.compute import preprocess_df
from utils.types import ColumnMapping


def _fmt_count(n: int) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def render_ideal_kpi_strip(df, today, column_map: ColumnMapping):
    """
    Render an additional KPI strip based on docs/ideal_metrics definitions, directly below the
    existing KPI strip. This does not modify or remove the original KPI strip.
    """
    # Normalize inputs
    today = pd.to_datetime(today).normalize()
    d = preprocess_df(df, column_map)

    # Column aliases
    bid = column_map.application_booking_id
    book_date = column_map.booking_col
    reg_date = column_map.reg_date_col
    agreement_col = column_map.total_agreement_col
    other_charges = column_map.other_charges
    tax_col = column_map.tax_col
    amount_due_col = column_map.amount_due_col
    actual_payment_col = column_map.actual_payment_col
    demand_gen_col = column_map.demand_gen_col

    # ---------------- Top Multi Bar Chart ----------------
    # Compute key totals for the overview chart
    booking_summary_top = d.groupby(bid).agg({
        agreement_col: 'first',
        other_charges: 'first',
    }).reset_index() if bid in d.columns else pd.DataFrame()
    av_total_top = booking_summary_top[agreement_col].fillna(0).sum() if not booking_summary_top.empty else 0.0
    corpus_total_top = booking_summary_top[other_charges].fillna(0).sum() if not booking_summary_top.empty else 0.0
    amount_ac_top = av_total_top + corpus_total_top

    demand_mask_top = d[demand_gen_col].notna() & (d[demand_gen_col] < today) if demand_gen_col in d.columns else pd.Series(False, index=d.index)
    due_total_top = d.loc[demand_mask_top, amount_due_col].fillna(0).sum() if amount_due_col in d.columns else 0.0
    tax_on_demand_top = d.loc[demand_mask_top, tax_col].fillna(0).sum() if tax_col in d.columns else 0.0
    demand_wo_tax_top = due_total_top - tax_on_demand_top

    collection_total_top = d.loc[demand_mask_top, column_map.payment_received_col].fillna(0).sum() if column_map.payment_received_col in d.columns else 0.0

    chart_df = pd.DataFrame({
        'Metric': ['Amount (Agreement + Corpus)', 'Demand (Without Tax)', 'Collection'],
        'Value (₹ Cr)': [to_cr(amount_ac_top), to_cr(demand_wo_tax_top), to_cr(collection_total_top)],
    })
    fig = px.bar(
        chart_df,
        x='Metric',
        y='Value (₹ Cr)',
        color='Metric',
        text='Value (₹ Cr)',
        title='Project Totals (₹ Cr)',
        color_discrete_map={
            'Amount (Agreement + Corpus)': '#001f3f',  # navy
            'Demand (Without Tax)': '#0074D9',         # blue
            'Collection': '#7F8C8D',                   # grey
        }
    )
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig.update_layout(yaxis_title='₹ Cr', xaxis_title='', showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    demand_gen_col = column_map.demand_gen_col

    # ---------------- Row 1 ----------------
    st.markdown("#### Property Unit Metrics")
    r1 = st.columns(5)
    # Total units
    total_units = d[bid].dropna().nunique()
    # total units sold: booking date present
    total_units_sold = d[d[book_date].notna()][bid].nunique() if book_date in d.columns else 0
    # total units unsold
    total_units_unsold = total_units - total_units_sold
    # total units registered
    total_units_registered = d[d[reg_date].notna()][bid].nunique() if reg_date in d.columns else 0
    # total units unregistered
    total_units_unregistered = total_units - total_units_registered

    with r1[0]:
        st.metric("Total Units", _fmt_count(total_units))
    with r1[1]:
        st.metric("Total Units Sold", _fmt_count(total_units_sold))
    with r1[2]:
        st.metric("Total Units Unsold", _fmt_count(total_units_unsold))
    with r1[3]:
        st.metric("Total Units Registered", _fmt_count(total_units_registered))
    with r1[4]:
        st.metric("Total Units Unregistered", _fmt_count(total_units_unregistered))

    st.divider()

    # ---------------- Row 2 ----------------
    st.markdown("#### Property Sales Metrics")
    r2 = st.columns(3)
    booking_summary = d.groupby(bid).agg({
        agreement_col: 'first',
        other_charges: 'first',
    }).reset_index() if bid in d.columns else pd.DataFrame()
    total_agreement_value = booking_summary[agreement_col].fillna(0).sum() if not booking_summary.empty else 0.0
    total_corpus_maint_bookings = booking_summary[other_charges].fillna(0).sum() if not booking_summary.empty else 0.0
    # Total Amount (Agreement + Corpus), excludes tax per requirement
    total_amount_ac = total_agreement_value + total_corpus_maint_bookings

    with r2[0]:
        st.metric("Total Agreement Value", f"₹{to_cr(total_agreement_value):.2f} Cr")
    with r2[1]:
        st.metric("Total Corpus + Maintenance", f"₹{to_cr(total_corpus_maint_bookings):.2f} Cr")
    with r2[2]:
        st.metric("Total Amount (Agreement + Corpus)", f"₹{to_cr(total_amount_ac):.2f} Cr")

    st.divider()

    # ---------------- Row 3 ----------------
    st.markdown("#### Property Demand Metrics")
    r3 = st.columns(3)
    demand_mask = d[demand_gen_col].notna() & (d[demand_gen_col] < today) if demand_gen_col in d.columns else pd.Series(False, index=d.index)
    total_due = d.loc[demand_mask, amount_due_col].fillna(0).sum() if amount_due_col in d.columns else 0.0
    total_tax_on_demand = d.loc[demand_mask, tax_col].fillna(0).sum() if tax_col in d.columns else 0.0
    total_demand_generated_without_tax = total_due - total_tax_on_demand

    with r3[0]:
        st.metric("Total Demand (Without Tax)", f"₹{to_cr(total_demand_generated_without_tax):.2f} Cr")
    with r3[1]:
        st.metric("Total Tax on Demand", f"₹{to_cr(total_tax_on_demand):.2f} Cr")
    with r3[2]:
        st.metric("Total Due (With Tax)", f"₹{to_cr(total_due):.2f} Cr")

    st.divider()

    # ---------------- Row 4 ----------------
    st.markdown("#### Property Collection Metrics")
    r4 = st.columns(3)
    # total collection where demand generated
    total_collection_demand = d.loc[demand_mask, column_map.payment_received_col].fillna(0).sum() if column_map.payment_received_col in d.columns else 0.0
    # % collected from demand due (guard against divide-by-zero)
    pct_collected = (total_collection_demand / total_due * 100.0) if total_due else 0.0
    # total collection without corpus (agreement/corpus from row 2, deduped per booking)
    total_collection_without_corpus = total_collection_demand - (total_corpus_maint_bookings or 0.0)

    with r4[0]:
        st.metric("Total Collection", f"₹{to_cr(total_collection_demand):.2f} Cr")
    with r4[1]:
        st.metric("% Collected from Demand Due", f"{pct_collected:.2f}%")
    with r4[2]:
        st.metric("Total Collection (Without Corpus)", f"₹{to_cr(total_collection_without_corpus):.2f} Cr")

    st.divider()

