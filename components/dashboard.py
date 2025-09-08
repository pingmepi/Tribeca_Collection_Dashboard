import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.types import ColumnMapping
from utils.helper import get_column, highlight_rows, bucket, percent
from services.compute import (
    compute_kpis as compute_kpis_service,
    compute_monthly_trend,
    compute_working_data,
    preprocess_df,
)
from services.validation import run_validations
from components.kpi_strip import render_kpi_strip
from components.monthly_trend import render_monthly_trend

# ---------- Utilities ----------

def fmt_inr(amount):
    if amount is None or (isinstance(amount, float) and pd.isna(amount)):
        amount = 0.0
    return f"₹{float(amount):,.2f}"


def to_cr(amount):
    if amount is None or (isinstance(amount, float) and pd.isna(amount)):
        return 0.0
    return float(amount) / 1e7


def _to_datetime(series):
    return pd.to_datetime(series, errors='coerce', dayfirst=True)


def _to_numeric_inr(series):
    # Remove ₹ and commas and coerce to numeric
    return pd.to_numeric(series.astype(str).str.replace(r'[₹,]', '', regex=True), errors='coerce')



# ---------- Core Renderer ----------

def render_dashboard(df: pd.DataFrame, today):
    """Main dashboard renderer with KPI strip and enhanced visuals"""
    today = pd.to_datetime(today).normalize()

    # Clean data
    df = df.copy()
    df.columns = df.columns.str.strip()

    # Create column mapping
    column_map = ColumnMapping(
        booking_col=get_column(df, "Booking Date", label="Booking Date"),
        reg_date_col=get_column(df, "Agreement Registration Date", "Registration Date", label="Registration Date"),
        actual_payment_col=get_column(df, "Actual Payment Date", "Payment Received Date", "Receipt Date", label="Payment Date"),
        amount_due_col=get_column(df, "Total Amount Due", "Amount Due", "Due Amount", label="Amount Due"),
        payment_received_col=get_column(df, "Payment Received", "Amount Received", label="Payment Received"),
        total_agreement_col=get_column(df, "Total Agreement Value", "Agreement Value", "Agreement Amount", label="Agreement Value"),
        budgeted_date_col=get_column(df, "Budgeted Date", "Planned Demand Date", label="Budgeted Date"),
        demand_gen_col=get_column(df, "Demand Generation Date", "Demand generation date", "Demand Raised Date", "Invoice Date", label="Demand Generation Date"),
        milestone_status_col=get_column(df, "Is Milestone Completed", "Milestone Completion Status", "Milestone Completed", label="Milestone Status"),
        property_name=get_column(df, "Unit/Property Name (Application / Booking ID)", "Property Name", "Unit / Property Name", label="Property Name"),
        customer_name=get_column(df, "Customer Name", "Account Name", "Ledger Name", label="Customer Name"),
        active_col=get_column(df, "Active", "Is Active", "Status", label="Active Status"),
        application_booking_id=get_column(df, "Application / Booking ID", "Booking ID", "Agreement/Booking ID", "Opportunity/Booking ID", label="Booking ID"),
        tax_col=get_column(df, "Total Service Tax On PPD", "Tax Amount", "GST Amount", "Total Tax", label="Tax Amount"),
        tower_col=get_column(df, "Tower", label="Tower"),
        type_col=get_column(df, "Type", label="Type"),
        milestone_name=get_column(df, "Milestone Name", label="Milestone Name"),
        other_charges=get_column(df, "Other Charges (Corpus+Maintenance)", "Corpus+Maintenance", "Corpus Maintenance", "Other Charges", label="Other Charges")
    )

    # Types are standardized in the service layer via preprocess_df
    # Bind column names to local variables for legacy logic below
    booking_col = column_map.booking_col
    reg_date_col = column_map.reg_date_col
    actual_payment_col = column_map.actual_payment_col
    amount_due_col = column_map.amount_due_col
    payment_received_col = column_map.payment_received_col
    total_agreement_col = column_map.total_agreement_col
    budgeted_date_col = column_map.budgeted_date_col
    demand_gen_col = column_map.demand_gen_col
    milestone_status_col = column_map.milestone_status_col
    property_name = column_map.property_name
    customer_name = column_map.customer_name
    active_col = column_map.active_col
    application_booking_id = column_map.application_booking_id
    tax_col = column_map.tax_col
    tower_col = column_map.tower_col
    type_col = column_map.type_col
    milestone_name_col = column_map.milestone_name
    other_charges = column_map.other_charges
    # Sidebar controls
    st.sidebar.markdown("### ⚙️ Threshold Settings")
    overdue_threshold = st.sidebar.number_input(
        "Overdue Amount Threshold (₹)",
        min_value=0,
        value=1000,
        step=100,
        help="Minimum amount to consider for overdue analysis"
    )


    # Run validation and show warnings upfront
    validations = run_validations(df, column_map)
    for msg in validations.get("messages", []):
        if msg:
            st.sidebar.warning(msg)

    # Produce working data for legacy visualizations (centralized in services)
    data = compute_working_data(df, today, column_map)

    # Compute KPIs and trend via services
    kpis = compute_kpis_service(df, today, column_map, overdue_threshold=overdue_threshold)
    trend_data = compute_monthly_trend(df, today, column_map)

    # Render Ideal KPI strip at the top (replaces older strip)
    from components.ideal_kpi_strip import render_ideal_kpi_strip
    render_ideal_kpi_strip(df, today, column_map)

    # Per-property Corpus + Maintenance breakdown (deduped per property)
    d_kpi = preprocess_df(df, column_map)
    try:
        prop_col = column_map.property_name
        corpus_col = column_map.other_charges
    except Exception:
        prop_col = None
        corpus_col = None

    if prop_col and corpus_col and (prop_col in d_kpi.columns) and (corpus_col in d_kpi.columns):
        # Build per-property metrics
        amt_col = column_map.amount_due_col
        pay_col = column_map.payment_received_col
        tax_col_local = column_map.tax_col
        reg_col = column_map.reg_date_col
        bud_col = column_map.budgeted_date_col
        dem_col = column_map.demand_gen_col

        dpp = d_kpi.copy()
        # Net payment after tax (clip at 0)
        if pay_col in dpp.columns and tax_col_local in dpp.columns:
            dpp['__net_payment__'] = (dpp[pay_col].fillna(0) - dpp[tax_col_local].fillna(0)).clip(lower=0)
        else:
            dpp['__net_payment__'] = 0

        # Agreement Value per property = sum of dues
        agreement_by_prop = dpp.groupby(prop_col)[amt_col].sum()
        # Corpus + Maintenance per property = first value
        corpus_by_prop = dpp.groupby(prop_col)[corpus_col].first()
        # Value of Unit = Agreement + Corpus
        value_unit_by_prop = agreement_by_prop.add(corpus_by_prop.fillna(0), fill_value=0)

        # Total Demand Generated (< today)
        demand_mask = dpp[dem_col].notna() & (dpp[dem_col] < today)
        demand_by_prop = dpp.loc[demand_mask].groupby(prop_col)[amt_col].sum()

        # Expected Future Demand (> today & demand not generated)
        future_mask = dpp[bud_col].notna() & (dpp[bud_col] > today) & (dpp[dem_col].isna())
        future_by_prop = dpp.loc[future_mask].groupby(prop_col)[amt_col].sum()

        # Budget Passed, Demand Not Generated (<= today & demand not generated)
        budget_passed_mask = dpp[bud_col].notna() & (dpp[bud_col] <= today) & (dpp[dem_col].isna())
        budget_passed_by_prop = dpp.loc[budget_passed_mask].groupby(prop_col)[amt_col].sum()

        # Total Collection (sum of net payment)
        collection_by_prop = dpp.groupby(prop_col)['__net_payment__'].sum()

        # Amount Overdue (on rows where demand exists): (due - net), clipped at 0
        overdue_rows = dpp[dpp[dem_col].notna()].copy()
        overdue_rows['__overdue__'] = (overdue_rows[amt_col] - overdue_rows['__net_payment__']).clip(lower=0)
        overdue_by_prop = overdue_rows.groupby(prop_col)['__overdue__'].sum()

        # Registration status per property
        reg_status = dpp.groupby(prop_col)[reg_col].apply(lambda s: 'Registered' if s.notna().any() else 'Not Registered')

        # Assemble table
        prop_index = sorted(set(dpp[prop_col].dropna().unique()))
        import pandas as _pd
        metrics_df = _pd.DataFrame(index=prop_index)
        metrics_df['Agreement Value (₹ Cr)'] = agreement_by_prop.reindex(prop_index).fillna(0).apply(to_cr)
        metrics_df['Corpus + Maintenance (₹ Cr)'] = corpus_by_prop.reindex(prop_index).fillna(0).apply(to_cr)
        metrics_df['Value of Unit (₹ Cr)'] = value_unit_by_prop.reindex(prop_index).fillna(0).apply(to_cr)
        metrics_df['Total Demand Generated (₹ Cr)'] = demand_by_prop.reindex(prop_index).fillna(0).apply(to_cr)
        metrics_df['Total Collection (₹ Cr)'] = collection_by_prop.reindex(prop_index).fillna(0).apply(to_cr)
        metrics_df['Amount Overdue (₹ Cr)'] = overdue_by_prop.reindex(prop_index).fillna(0).apply(to_cr)
        metrics_df['Expected Future Demand (₹ Cr)'] = future_by_prop.reindex(prop_index).fillna(0).apply(to_cr)
        metrics_df['Budget Passed, Demand Not Generated (₹ Cr)'] = budget_passed_by_prop.reindex(prop_index).fillna(0).apply(to_cr)
        metrics_df['Registration Status'] = reg_status.reindex(prop_index).fillna('Not Registered')

        metrics_df = metrics_df.reset_index().rename(columns={'index': 'Property'})
        # Sort by Value of Unit descending
        metrics_df = metrics_df.sort_values(by='Value of Unit (₹ Cr)', ascending=False)

        # Amount Yet to be Collected by Booking (per spec: sum of positive (Amount Due - Payment Received) across milestones)
        booking_col = column_map.application_booking_id
        amt_col2 = column_map.amount_due_col
        pay_col2 = column_map.payment_received_col
        if all(c in d_kpi.columns for c in [booking_col, amt_col2, pay_col2]):
            cust_col = column_map.customer_name
            prop_col2 = column_map.property_name
            cols = [booking_col, amt_col2, pay_col2] + [c for c in [cust_col, prop_col2] if c in d_kpi.columns]
            d_ayc = d_kpi[cols].copy()
            d_ayc[pay_col2] = d_ayc[pay_col2].fillna(0)
            d_ayc[amt_col2] = d_ayc[amt_col2].fillna(0)
            d_ayc['__outstanding_row__'] = (d_ayc[amt_col2] - d_ayc[pay_col2]).clip(lower=0)
            # Aggregate per booking, carry representative Property and Customer (first non-null)
            group_fields = {"__outstanding_row__": 'sum'}
            show_cols = {'__outstanding_row__': 'Amount Yet to be Collected', booking_col: 'Booking ID'}
            if cust_col in d_ayc.columns:
                group_fields[cust_col] = 'first'
                show_cols[cust_col] = 'Customer Name'
            if prop_col2 in d_ayc.columns:
                group_fields[prop_col2] = 'first'
                show_cols[prop_col2] = 'Property Name'

            per_booking = (
                d_ayc.groupby(booking_col)
                    .agg(group_fields)
                    .reset_index()
                    .rename(columns=show_cols)
            )
            per_booking['Amount Yet to be Collected (₹)'] = per_booking['Amount Yet to be Collected'].apply(fmt_inr)
            per_booking['Amount Yet to be Collected (₹ Cr)'] = per_booking['Amount Yet to be Collected'].apply(to_cr)
            # Prefer showing Booking ID, Customer, Property, and the two display columns
            display_cols = [c for c in ['Booking ID', 'Customer Name', 'Property Name', 'Amount Yet to be Collected (₹)', 'Amount Yet to be Collected (₹ Cr)'] if c in per_booking.columns]
            per_booking = per_booking[display_cols]
            per_booking = per_booking.sort_values(by='Amount Yet to be Collected (₹ Cr)', ascending=False)

            with st.expander("📄 Amount Yet to be Collected by Booking", expanded=False):
                st.dataframe(per_booking, use_container_width=True)
                total_outstanding = (d_ayc['__outstanding_row__'].groupby(d_ayc[booking_col]).sum()).sum()
                st.caption(f"Total: {fmt_inr(total_outstanding)} (₹{to_cr(total_outstanding):.2f} Cr)")


    # Separator before trend
    st.markdown("---")

    # Separator before trend
    st.markdown("---")
    render_monthly_trend(trend_data)

    # Sidebar controls
    st.sidebar.markdown("### ⚙️ Threshold Settings")
    # overdue_threshold already captured above

    booking_mismatch_tolerance = st.sidebar.number_input(
        "Booking Mismatch Tolerance (₹)",
        min_value=0,
        value=1000,
        step=100,
        help="Tolerance for agreement value vs total due mismatch"
    )
    # Toggle to display the working dataset used for visuals
    show_raw = st.sidebar.checkbox("Show raw working tables", value=False)


    # Continue with existing dashboard logic...
    # (Keep all existing charts and tables, just add the new components above)

    d = data["df"]
    booked_df = data["booked_df"]
    reg_df = data["reg_df"]
    unreg_df = data["unreg_df"]
    filtered_due_df = data["filtered_due_df"]
    delayed_demand_df = data["delayed_demand_df"]
    future_demand_df = data["future_demand_df"]
    copy_df = data["copy_df"]
    totals = data["totals"]
    overdue_all = data["overdue_all"]

    # Re-apply threshold now for presentation
    overdue = d[d['Amount Overdue'] > overdue_threshold].copy()

    # ---------- Header KPIs ----------




    # Section: Detailed Analysis
    st.markdown("---")
    st.markdown("### 📋 Detailed Analysis")

    # ---------- Ageing Analysis ----------
    bucket_order = ['< 30 Days', '31 - 60 Days', '61 - 90 Days', '> 90 Days']
    st.subheader("⏳ Ageing Analysis")
    col5, col6, col7 = st.columns(3)

    with col5:
        st.markdown("**Unregistered User Ageing (Days Since Booking)**")
        unreg_booking_dt = pd.to_datetime(unreg_df[booking_col], errors='coerce', dayfirst=True)
        unreg_age = (
            unreg_df.assign(days_since_booking=(today - unreg_booking_dt).dt.days)
                    .assign(booking_age_bucket=lambda d: d['days_since_booking'].apply(bucket))
        )
        bucket_counts = (
            unreg_age.groupby('booking_age_bucket')[application_booking_id]
                    .nunique()
                    .reindex(bucket_order, fill_value=0)
                    .reset_index()
        )
        bucket_counts.columns = ['Ageing Bucket', 'User Count']
        st.dataframe(bucket_counts, use_container_width=True)
        st.bar_chart(bucket_counts.set_index('Ageing Bucket'))

    with col6:
        st.markdown("**Registered User TAT (Booking to Registration)**")
        reg_booking_dt = pd.to_datetime(reg_df[booking_col], errors='coerce', dayfirst=True)
        reg_reg_dt = pd.to_datetime(reg_df[reg_date_col], errors='coerce', dayfirst=True)
        reg_age = (
            reg_df.assign(tat_days=(reg_reg_dt - reg_booking_dt).dt.days)
                  .assign(tat_bucket=lambda d: d['tat_days'].apply(bucket))
        )
        bucket_counts_registered = (
            reg_age.groupby('tat_bucket')[application_booking_id]
                   .nunique()
                   .reindex(bucket_order, fill_value=0)
                   .reset_index()
        )
        bucket_counts_registered.columns = ['TAT Bucket', 'User Count']
        st.dataframe(bucket_counts_registered, use_container_width=True)
        st.bar_chart(bucket_counts_registered.set_index('TAT Bucket'))

    with col7:
        st.markdown("**Overdue Ageing**")
        overdue_filtered = d.copy()
        # Only consider rows with a demand and positive overdue
        overdue_filtered = overdue_filtered[overdue_filtered[demand_gen_col].notnull()].copy()
        # Compute overdue_days from demand date + 15 days
        demand_dt = pd.to_datetime(overdue_filtered[demand_gen_col], errors='coerce', dayfirst=True)
        overdue_filtered['overdue_days'] = (today - (demand_dt + pd.to_timedelta(15, unit='D'))).dt.days
        # Apply threshold
        overdue_filtered = overdue_filtered[overdue_filtered['Amount Overdue'] > overdue_threshold].copy()
        overdue_filtered['overdue_bucket'] = overdue_filtered['overdue_days'].apply(bucket)

        bucket_summary = (
            overdue_filtered.groupby('overdue_bucket')
                            .agg({'Amount Overdue': 'sum', application_booking_id: pd.Series.nunique})
                            .reindex(bucket_order)
                            .fillna(0)
                            .reset_index()
        )
        bucket_summary['Amount Overdue'] = bucket_summary['Amount Overdue'].apply(to_cr)
        bucket_summary.columns = ['Overdue Bucket', 'Overdue Amt (Cr)', 'User Count']
        st.dataframe(bucket_summary, use_container_width=True)
        st.bar_chart(bucket_summary.set_index('Overdue Bucket')[['User Count']])

    # ---------- Overdue Customers ----------
    overdue_customers = d[d['Amount Overdue'] > overdue_threshold].copy()
    customer_table = (
        overdue_customers.groupby([customer_name, property_name])['Amount Overdue']
                         .sum()
                         .reset_index()
                         .sort_values(by='Amount Overdue', ascending=False)
    )
    customer_table['Amount Overdue (Lakhs)'] = customer_table['Amount Overdue'] / 1e5
    customer_table = customer_table.drop(columns=['Amount Overdue'])
    with st.expander(f"👥 Overdue Customers Details ({len(customer_table)} found)", expanded=False):
        st.dataframe(customer_table, use_container_width=True)


    # ---------- Expected Future Total Collection ----------
    st.markdown("""
        ### 📅 Expected Future Total Collection
        <small>
        <sup>ℹ️</sup>
        <span title="This table shows expected collections grouped by Budgeted Date month (future only). Amounts in ₹ Cr.">
        <em>What does this mean?</em></span>
        </small>
    """, unsafe_allow_html=True)

    future_demand_df = future_demand_df.copy()
    future_demand_df['Due Month'] = pd.to_datetime(future_demand_df[budgeted_date_col].dt.to_period("M").astype(str), errors='coerce')
    today_month = pd.to_datetime(today).replace(day=1)
    future_dues = future_demand_df[future_demand_df['Due Month'] >= today_month]

    monthly_due = future_dues.groupby('Due Month')[amount_due_col].sum().reset_index()
    monthly_due['Expected Due (₹ Cr)'] = monthly_due[amount_due_col].apply(to_cr)
    monthly_due = monthly_due.rename(columns={'Due Month': 'Month_dt'})
    monthly_due['Month'] = monthly_due['Month_dt'].dt.strftime('%b %Y')
    monthly_due = monthly_due.sort_values(by='Month_dt')
    monthly_due.set_index('Month', inplace=True)

    fig3 = px.bar(
        monthly_due.reset_index(),
        x='Month',
        y='Expected Due (₹ Cr)',
        title="Expected Future Total Collection (₹ Cr)",
        labels={'Month': 'Month', 'Expected Due (₹ Cr)': 'Amount (₹ Cr)'},
        text='Expected Due (₹ Cr)'
    )
    fig3.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig3.update_layout(xaxis_tickangle=-90)
    st.plotly_chart(fig3, use_container_width=True)

    with st.expander('📄 View Full Table'):
        st.dataframe(monthly_due.reset_index(), use_container_width=True)

    # ---------- Raw tables toggle ----------
    if show_raw:
        with st.expander("📄 View Full Project Dataset (Working)", expanded=False):
            st.dataframe(d, use_container_width=True)

