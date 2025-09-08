import pandas as pd
import streamlit as st
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
    r2 = st.columns(4)
    booking_summary = d.groupby(bid).agg({
        agreement_col: 'first',
        other_charges: 'first',
    }).reset_index() if bid in d.columns else pd.DataFrame()
    total_agreement_value = booking_summary[agreement_col].fillna(0).sum() if not booking_summary.empty else 0.0
    total_corpus_maint_bookings = booking_summary[other_charges].fillna(0).sum() if not booking_summary.empty else 0.0
    total_tax_all = d[tax_col].fillna(0).sum() if tax_col in d.columns else 0.0
    total_amount = total_agreement_value + total_corpus_maint_bookings + total_tax_all

    with r2[0]:
        st.metric("Total Agreement Value", f"₹{to_cr(total_agreement_value):.2f} Cr")
    with r2[1]:
        st.metric("Total Corpus + Maintenance", f"₹{to_cr(total_corpus_maint_bookings):.2f} Cr")
    with r2[2]:
        st.metric("Total Tax", f"₹{to_cr(total_tax_all):.2f} Cr")
    with r2[3]:
        st.metric("Total Amount", f"₹{to_cr(total_amount):.2f} Cr")

    st.divider()

    # ---------------- Row 3 ----------------
    st.markdown("#### Property Demand Metrics")
    r3 = st.columns(4)
    demand_mask = d[demand_gen_col].notna() & (d[demand_gen_col] < today) if demand_gen_col in d.columns else pd.Series(False, index=d.index)
    total_due = d.loc[demand_mask, amount_due_col].fillna(0).sum() if amount_due_col in d.columns else 0.0
    total_tax_on_demand = d.loc[demand_mask, tax_col].fillna(0).sum() if tax_col in d.columns else 0.0
    total_demand_generated_without_tax = total_due - total_tax_on_demand

    # total corpus+maintenance on demand (deduped per booking among rows with demand)
    if demand_mask.any() and other_charges in d.columns:
        d_dm = d.loc[demand_mask].copy()
        corpus_on_demand = d_dm.groupby(bid)[other_charges].first().fillna(0).sum()
    else:
        corpus_on_demand = 0.0

    with r3[0]:
        st.metric("Total Demand Generated (Without Tax)", f"₹{to_cr(total_demand_generated_without_tax):.2f} Cr")
    with r3[1]:
        st.metric("Total Tax on Demand", f"₹{to_cr(total_tax_on_demand):.2f} Cr")
    with r3[2]:
        st.metric("Total Corpus + Maintenance (On Demand)", f"₹{to_cr(corpus_on_demand):.2f} Cr")
    with r3[3]:
        st.metric("Total Due", f"₹{to_cr(total_due):.2f} Cr")

    st.divider()

    # ---------------- Row 4 ----------------
    st.markdown("#### Property Collection Metrics")
    r4 = st.columns(4)
    # total collection where demand generated
    total_collection_demand = d.loc[demand_mask, column_map.payment_received_col].fillna(0).sum() if column_map.payment_received_col in d.columns else 0.0
    # total tax on collections where payment date present and < today
    pay_mask = d[actual_payment_col].notna() & (d[actual_payment_col] < today) if actual_payment_col in d.columns else pd.Series(False, index=d.index)
    total_tax_on_collections = d.loc[pay_mask, tax_col].fillna(0).sum() if tax_col in d.columns else 0.0
    total_collection_without_tax = total_collection_demand - total_tax_on_collections
    # total collection without tax and corpus (per ideal metrics)
    total_collection_without_tax_and_corpus = total_collection_without_tax - (total_corpus_maint_bookings or 0.0)

    with r4[0]:
        st.metric("Total Collection", f"₹{to_cr(total_collection_demand):.2f} Cr")
    with r4[1]:
        st.metric("Total Tax on Collections", f"₹{to_cr(total_tax_on_collections):.2f} Cr")
    with r4[2]:
        st.metric("Total Collection (Without Tax)", f"₹{to_cr(total_collection_without_tax):.2f} Cr")
    with r4[3]:
        st.metric("Total Collection (Without Tax & Corpus)", f"₹{to_cr(total_collection_without_tax_and_corpus):.2f} Cr")

    st.divider()

