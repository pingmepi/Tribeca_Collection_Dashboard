
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# We keep using the helper functions but add a safe local resolver
try:
    from utils.helper import get_column, bucket, percent, highlight_rows
except Exception:
    # Minimal fallbacks so module can be imported for static checks (won't affect real app where utils exists)
    def get_column(df, primary, fallback=None):
        return primary if primary in df.columns else (fallback if fallback in df.columns else primary)
    def bucket(x):
        if x is None or pd.isna(x):
            return None
        try:
            x = int(x)
        except Exception:
            return None
        if x < 31: return "< 30 Days"
        if x < 61: return "31 - 60 Days"
        if x < 91: return "61 - 90 Days"
        return "> 90 Days"
    def percent(num, den):
        if not den or pd.isna(den) or den == 0:
            return "0.00%"
        return f"{(float(num) / float(den)) * 100:.2f}%"
    def highlight_rows(_row):  # no-op style fallback
        return [''] * len(_row)

# ---------- Utilities ----------

def resolve_column(df: pd.DataFrame, *candidates: str) -> str:
    """Return the first column name that exists in df from the given candidates."""
    for c in candidates:
        if c and c in df.columns:
            return c
    # As a last resort, return the first candidate (will raise later if missing at use site)
    return candidates[0]

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
    """Render the CXO dashboard. Expects one row per milestone/line item."""
    # Normalize 'today' to a date boundary to avoid partial day drift
    today = pd.to_datetime(today).normalize()

    # Early preview (raw) for debugging
    st.dataframe(df, use_container_width=True)

    # Clean column names
    df = df.copy()
    df.columns = df.columns.str.strip()

    # Resolve columns with multiple fallback options where relevant
    other_charges = resolve_column(df, "Other Charges (Corpus+Maintenance)", "Corpus+Maintenance", "Corpus Maintenance", "Other Charges")
    booking_col = resolve_column(df, "Booking Date")
    reg_date_col = resolve_column(df, "Agreement Registration Date", "Registration Date")
    actual_payment_col = resolve_column(df, "Actual Payment Date", "Payment Received Date", "Receipt Date")
    amount_due_col = resolve_column(df, "Total Amount Due", "Amount Due", "Due Amount")
    payment_received_col = resolve_column(df, "Payment Received", "Amount Received")
    total_agreement_col = resolve_column(df, "Total Agreement Value", "Agreement Value", "Agreement Amount")
    budgeted_date_col = resolve_column(df, "Budgeted Date", "Planned Demand Date")
    demand_gen_col = resolve_column(df, "Demand Generation Date", "Demand generation date", "Demand Raised Date", "Invoice Date")
    milestone_status_col = resolve_column(df, "Is Milestone Completed", "Milestone Completion Status", "Milestone Completed")
    property_name = resolve_column(df, "Unit/Property Name (Application / Booking ID)", "Property Name", "Unit / Property Name")
    customer_name = resolve_column(df, "Customer Name", "Account Name", "Ledger Name")
    active_col = resolve_column(df, "Active", "Is Active", "Status")
    application_booking_id = resolve_column(df, "Application / Booking ID", "Booking ID", "Agreement/Booking ID", "Opportunity/Booking ID")
    tax_col = resolve_column(df, "Total Service Tax On PPD", "Tax Amount", "GST Amount", "Total Tax")
    tower_col = resolve_column(df, "Tower", "Block", "Building")
    type_col = resolve_column(df, "Type", "Unit Type")
    milestone_name_col = resolve_column(df, "Milestone Name", "Milestone", "Stage Name")

    # Type normalization
    for c in [booking_col, reg_date_col, actual_payment_col, demand_gen_col, budgeted_date_col]:
        df[c] = _to_datetime(df[c])

    for c in [total_agreement_col, amount_due_col, payment_received_col, tax_col, other_charges]:
        df[c] = _to_numeric_inr(df[c])

    df[property_name] = df[property_name].astype(str).str.strip()

    # Sidebar parameters
    overdue_threshold = st.sidebar.number_input("Overdue threshold (₹)", min_value=0, value=1000, step=500)
    show_raw = st.sidebar.checkbox("Show raw working tables", value=False)

    # ---------- Computations (cached) ----------
    @st.cache_data(ttl=900)
    def compute_kpis(_df: pd.DataFrame, _today: pd.Timestamp):
        d = _df.copy()

        # Agreement value per booking = sum of dues
        d['Agreement value'] = d.groupby(application_booking_id)[amount_due_col].transform('sum')

        # Total Payment Received per booking (gross sum of payments on any row with payment date present)
        filtered_pay_df = d[d[payment_received_col].notnull()].copy()
        total_pay_per_booking = (
            filtered_pay_df.groupby(application_booking_id)[payment_received_col].sum().reset_index()
            .rename(columns={payment_received_col: 'Total Payment Received'})
        )
        d = d.merge(total_pay_per_booking, on=application_booking_id, how='left')
        d['Total Payment Received'] = d['Total Payment Received'].fillna(0)

        # Total Demand Generated Till Date (sum dues where demand_gen < today)
        filtered_due_df = d[d[demand_gen_col].notna() & (d[demand_gen_col] < _today)].copy()
        due_totals = (
            filtered_due_df.groupby(application_booking_id)[amount_due_col].sum().reset_index()
            .rename(columns={amount_due_col: 'Total Demand Generated Till Date'})
        )
        d = d.merge(due_totals, on=application_booking_id, how='left')
        d['Total Demand Generated Till Date'] = d['Total Demand Generated Till Date'].fillna(0)

        # Budget Passed, Demand Not Generated
        delayed_demand_df = d[
            d[budgeted_date_col].notna() & (d[budgeted_date_col] <= _today) & (d[demand_gen_col].isna())
        ].copy()
        delayed_totals = (
            delayed_demand_df.groupby(application_booking_id)[amount_due_col].sum().reset_index()
            .rename(columns={amount_due_col: 'Budget Passed, Demand Not Generated'})
        )
        d = d.merge(delayed_totals, on=application_booking_id, how='left')
        d['Budget Passed, Demand Not Generated'] = d['Budget Passed, Demand Not Generated'].fillna(0)

        # Expected Future Demand
        future_demand_df = d[
            d[budgeted_date_col].notna() & (d[budgeted_date_col] > _today) & (d[demand_gen_col].isna())
        ].copy()
        future_total = (
            future_demand_df.groupby(application_booking_id)[amount_due_col].sum().reset_index()
            .rename(columns={amount_due_col: 'Expected Future Demand'})
        )
        d = d.merge(future_total, on=application_booking_id, how='left')
        d['Expected Future Demand'] = d['Expected Future Demand'].fillna(0)

        # Net payment received (after tax) and Amount Overdue at line level for rows where demand exists
        filtered = d[d[demand_gen_col].notnull()].copy()
        filtered['Net payment received (AV)'] = (filtered[payment_received_col] - filtered[tax_col]).clip(lower=0)
        filtered['Amount Overdue'] = filtered[amount_due_col] - filtered['Net payment received (AV)']

        # Aggregate overdue & net payment per booking
        overdue_df = (
            filtered.groupby(application_booking_id)[['Net payment received (AV)', 'Amount Overdue']]
            .sum().reset_index()
        )
        d = d.merge(overdue_df, on=application_booking_id, how='left')
        d['Amount Overdue'] = d['Amount Overdue'].fillna(0)
        d['Net payment received (AV)'] = d['Net payment received (AV)'].fillna(0)

        # Registered/Unregistered partitions
        booked_df = d[d[application_booking_id].notnull()].copy()
        reg_df = booked_df[booked_df[reg_date_col].notnull()].copy()
        unreg_df = booked_df[booked_df[reg_date_col].isnull()].copy()

        # Latest row per booking (by demand then budget date) for some per-booking rollups
        sort_cols = [application_booking_id, demand_gen_col, budgeted_date_col]
        d_sorted = d.sort_values(sort_cols)
        last_by_booking = d_sorted.groupby(application_booking_id, as_index=False).last()

        # Aggregate KPIs
        total_units = d[property_name].nunique()
        booked_units = booked_df[application_booking_id].nunique()
        reg_units = reg_df[application_booking_id].nunique()
        unreg_units = unreg_df[application_booking_id].nunique()

        # Agreement totals
        total_sales_act = booked_df.groupby(application_booking_id)[total_agreement_col].first().sum()
        reg_sales_act = reg_df.groupby(application_booking_id)[total_agreement_col].first().sum()
        unreg_sales_act = unreg_df.groupby(application_booking_id)[total_agreement_col].first().sum()

        total_corpus = booked_df.groupby(application_booking_id)[other_charges].first().sum()
        reg_corpus = reg_df.groupby(application_booking_id)[other_charges].first().sum()
        unreg_corpus = unreg_df.groupby(application_booking_id)[other_charges].first().sum()

        total_sales = booked_df.groupby(application_booking_id)['Agreement value'].first().sum()
        reg_sales = reg_df.groupby(application_booking_id)['Agreement value'].first().sum()
        unreg_sales = unreg_df.groupby(application_booking_id)['Agreement value'].first().sum()

        # Demand buckets
        total_due = filtered_due_df[amount_due_col].sum()
        reg_due = reg_df.groupby(application_booking_id).tail(1)['Total Demand Generated Till Date'].sum()
        unreg_due = unreg_df.groupby(application_booking_id).tail(1)['Total Demand Generated Till Date'].sum()

        total_due_n = delayed_demand_df[amount_due_col].sum()
        reg_due_n = reg_df.groupby(application_booking_id).tail(1)['Budget Passed, Demand Not Generated'].sum()
        unreg_due_n = unreg_df.groupby(application_booking_id).tail(1)['Budget Passed, Demand Not Generated'].sum()

        total_due_nn = future_demand_df[amount_due_col].sum()
        reg_due_nn = reg_df.groupby(application_booking_id).tail(1)['Expected Future Demand'].sum()
        unreg_due_nn = unreg_df.groupby(application_booking_id).tail(1)['Expected Future Demand'].sum()

        # Collections (no tax)
        total_collected_notax = last_by_booking['Net payment received (AV)'].sum()
        reg_collected_notax = (
            reg_df.sort_values(sort_cols).groupby(application_booking_id).last()['Net payment received (AV)'].sum()
            if not reg_df.empty else 0
        )
        unreg_collected_notax = (
            unreg_df.sort_values(sort_cols).groupby(application_booking_id).last()['Net payment received (AV)'].sum()
            if not unreg_df.empty else 0
        )

        # Overdue (apply threshold at the very end in presenter)
        overdue_all = d[d['Amount Overdue'] > 0].copy()

        # For ageing: prepare copies
        copy_df = filtered.copy()

        return {
            "df": d,
            "booked_df": booked_df,
            "reg_df": reg_df,
            "unreg_df": unreg_df,
            "filtered_due_df": filtered_due_df,
            "delayed_demand_df": delayed_demand_df,
            "future_demand_df": future_demand_df,
            "copy_df": copy_df,
            "totals": {
                "total_units": total_units,
                "booked_units": booked_units,
                "reg_units": reg_units,
                "unreg_units": unreg_units,
                "total_sales_act": total_sales_act,
                "reg_sales_act": reg_sales_act,
                "unreg_sales_act": unreg_sales_act,
                "total_corpus": total_corpus,
                "reg_corpus": reg_corpus,
                "unreg_corpus": unreg_corpus,
                "total_sales": total_sales,
                "reg_sales": reg_sales,
                "unreg_sales": unreg_sales,
                "total_due": total_due,
                "reg_due": reg_due,
                "unreg_due": unreg_due,
                "total_due_n": total_due_n,
                "reg_due_n": reg_due_n,
                "unreg_due_n": unreg_due_n,
                "total_due_nn": total_due_nn,
                "reg_due_nn": reg_due_nn,
                "unreg_due_nn": unreg_due_nn,
                "total_collected_notax": total_collected_notax,
                "reg_collected_notax": reg_collected_notax,
                "unreg_collected_notax": unreg_collected_notax,
            },
            "overdue_all": overdue_all,
        }

    data = compute_kpis(df, today)

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
    st.dataframe(d, use_container_width=True)

    # Expected Future Collection from uncompleted milestones (uses amount_due_col variable consistently)
    uncompleted_milestones = d[d[milestone_status_col] == 0] if milestone_status_col in d.columns else d.head(0)
    expected_future_collection_cr = to_cr(uncompleted_milestones[amount_due_col].sum())

    col1, col2 = st.columns(2)
    col1.metric(label="Total Units", value=int(totals["total_units"]))
    col2.metric(
        label="Expected Future Total Collection",
        value=f"{fmt_inr(expected_future_collection_cr)} Cr".replace('₹', ''),  # show only Cr formatted number
        help="Total amount due from milestones not yet completed."
    )

    # ---------- Summary Table ----------
    summary_df = pd.DataFrame({
        "Metric": [
            "Total Units Booked",
            "Total Agreement Value",
            "Corpus+Maintenance",
            "Total Agreement Value (Added Corpus+Maintenance)",
            "Total Agreement Value (Sum of All Dues)",
            "Total Demand Till Date",
            "Budget Passed, Demand Not Raised",
            "Expected Future Demand",
            "Amount Collected (Without TAX)",
            "Amount Overdue"
        ],
        "All Units": [
            int(totals["booked_units"]),
            f"₹{to_cr(totals['total_sales_act']):,.2f} Cr",
            f"₹{to_cr(totals['total_corpus']):,.2f} Cr",
            f"₹{to_cr(totals['total_sales_act'] + totals['total_corpus']):,.2f} Cr",
            f"₹{to_cr(totals['total_sales']):,.2f} Cr",
            percent(totals["total_due"], totals["total_sales"]),
            percent(totals["total_due_n"], totals["total_sales"]),
            percent(totals["total_due_nn"], totals["total_sales"]),
            percent(totals["total_collected_notax"], totals["total_sales"]),
            percent(overdue.groupby(application_booking_id)['Amount Overdue'].sum().sum(), totals["total_sales"])
        ],
        "Registered Users": [
            int(totals["reg_units"]),
            f"₹{to_cr(totals['reg_sales_act']):,.2f} Cr",
            f"₹{to_cr(totals['reg_corpus']):,.2f} Cr",
            f"₹{to_cr(totals['reg_sales_act'] + totals['reg_corpus']):,.2f} Cr",
            f"₹{to_cr(totals['reg_sales']):,.2f} Cr",
            percent(reg_df.groupby(application_booking_id).tail(1)['Total Demand Generated Till Date'].sum(), totals["reg_sales"]),
            percent(reg_df.groupby(application_booking_id).tail(1)['Budget Passed, Demand Not Generated'].sum(), totals["reg_sales"]),
            percent(reg_df.groupby(application_booking_id).tail(1)['Expected Future Demand'].sum(), totals["reg_sales"]),
            percent(reg_df.groupby(application_booking_id).tail(1)['Net payment received (AV)'].sum(), totals["reg_sales"]),
            percent(reg_df.groupby(application_booking_id).tail(1)['Amount Overdue'].sum(), totals["reg_sales"])
        ],
        "Unregistered Users": [
            int(totals["unreg_units"]),
            f"₹{to_cr(totals['unreg_sales_act']):,.2f} Cr",
            f"₹{to_cr(totals['unreg_corpus']):,.2f} Cr",
            f"₹{to_cr(totals['unreg_sales_act'] + totals['unreg_corpus']):,.2f} Cr",
            f"₹{to_cr(totals['unreg_sales']):,.2f} Cr",
            percent(unreg_df.groupby(application_booking_id).tail(1)['Total Demand Generated Till Date'].sum(), totals["unreg_sales"]),
            percent(unreg_df.groupby(application_booking_id).tail(1)['Budget Passed, Demand Not Generated'].sum(), totals["unreg_sales"]),
            percent(unreg_df.groupby(application_booking_id).tail(1)['Expected Future Demand'].sum(), totals["unreg_sales"]),
            percent(unreg_df.groupby(application_booking_id).tail(1)['Net payment received (AV)'].sum(), totals["unreg_sales"]),
            percent(unreg_df.groupby(application_booking_id).tail(1)['Amount Overdue'].sum(), totals["unreg_sales"])
        ]
    })

    styled_df = summary_df.style \
        .apply(highlight_rows, axis=1) \
        .set_properties(**{'text-align': 'center', 'font-size': '16px'}) \
        .set_table_styles([dict(selector='th', props=[('background-color', '#f0f0f5'), ('color', '#333'), ('font-weight', 'bold')])])

    st.dataframe(styled_df, use_container_width=True)

    # ---------- Pie Charts ----------
    col1, col2 = st.columns(2)
    with col1:
        tmp = booked_df.assign(
            **{'Registration Status': booked_df[reg_date_col].notna().map({True: 'Registered', False: 'Not Registered'})}
        )
        unit_status = tmp.drop_duplicates(subset=[application_booking_id])
        reg_summary = unit_status['Registration Status'].value_counts().reset_index()
        reg_summary.columns = ['Registration Status', 'Count']
        fig1 = px.pie(reg_summary, names='Registration Status', values='Count', title='Registration Status of Units', hole=0.4)
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        labels = ['Amount Collected (Without Tax)', 'Amount Overdue']
        values = [
            reg_df.groupby(application_booking_id).tail(1)['Net payment received (AV)'].sum()
            + unreg_df.groupby(application_booking_id).tail(1)['Net payment received (AV)'].sum(),
            overdue.groupby(application_booking_id).tail(1)['Amount Overdue'].sum()
        ]
        dff = pd.DataFrame({'Status': labels, 'Amount (Cr)': list(map(to_cr, values))})
        fig2 = px.pie(dff, names='Status', values='Amount (Cr)', title='Collection Due vs Not Due', hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

    # ---------- Ageing Analysis ----------
    bucket_order = ['< 30 Days', '31 - 60 Days', '61 - 90 Days', '> 90 Days']
    st.subheader("⏳ Ageing Analysis")
    col5, col6, col7 = st.columns(3)

    with col5:
        st.markdown("**Unregistered User Ageing (Days Since Booking)**")
        unreg_age = (
            unreg_df.assign(days_since_booking=(today - unreg_df[booking_col]).dt.days)
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
        reg_age = (
            reg_df.assign(tat_days=(reg_df[reg_date_col] - reg_df[booking_col]).dt.days)
                  .assign(tat_bucket=lambda d: d['tat_days'].apply(bucket))
        )
        bucket_counts_registered = (
            reg_age.groupby('tat_bucket')[property_name]
                   .nunique()
                   .reindex(bucket_order, fill_value=0)
                   .reset_index()
        )
        bucket_counts_registered.columns = ['TAT Bucket', 'User Count']
        st.dataframe(bucket_counts_registered, use_container_width=True)
        st.bar_chart(bucket_counts_registered.set_index('TAT Bucket'))

    with col7:
        st.markdown("**Overdue Ageing**")
        overdue_filtered = (
            d[d[demand_gen_col].notnull()].copy()
             .assign(overdue_days=(today - (d[demand_gen_col] + pd.to_timedelta(15, unit='D'))).dt.days)
        )
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
    st.markdown("**Overdue Customers List**")
    overdue_customers = d[d['Amount Overdue'] > overdue_threshold].copy()
    customer_table = (
        overdue_customers.groupby([customer_name, property_name])['Amount Overdue']
                         .sum()
                         .reset_index()
                         .sort_values(by='Amount Overdue', ascending=False)
    )
    customer_table['Amount Overdue (Lakhs)'] = customer_table['Amount Overdue'] / 1e5
    customer_table = customer_table.drop(columns=['Amount Overdue'])
    st.dataframe(customer_table, use_container_width=True)

    # ---------- Monthly Collections (last 2 years) ----------
    copy_df = copy_df.copy()
    copy_df['Month'] = pd.to_datetime(copy_df[actual_payment_col].dt.to_period("M").astype(str))
    two_years_ago = pd.to_datetime(today) - pd.DateOffset(years=2)
    filtered_mc = copy_df[copy_df['Month'] >= two_years_ago]

    monthly_summary = (
        filtered_mc.groupby('Month')['Net payment received (AV)']
                   .sum()
                   .reset_index()
    )
    monthly_summary['Net payment received (AV)'] = monthly_summary['Net payment received (AV)'].apply(to_cr)
    monthly_summary['Month_str'] = monthly_summary['Month'].dt.strftime('%b %Y')

    fig = px.bar(
        monthly_summary,
        x='Month_str',
        y='Net payment received (AV)',
        title="Monthly Collections (in ₹ Cr)",
        labels={'Month_str': 'Month', 'Net payment received (AV)': '₹ Cr'},
        text='Net payment received (AV)'
    )
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig.update_layout(xaxis_tickangle=-90)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📄 View Full Table"):
        full_table = copy_df.groupby('Month')['Net payment received (AV)'].sum().reset_index()
        full_table['Net payment received (AV)'] = full_table['Net payment received (AV)'].apply(to_cr)
        full_table['Month'] = full_table['Month'].dt.strftime('%b %Y')
        full_table = full_table.rename(columns={'Net payment received (AV)': "Actual Collection (₹ Cr)"})
        st.dataframe(full_table, use_container_width=True)

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
        with st.expander("📄 View Full Project Dataset (Working)"):
            st.dataframe(d, use_container_width=True)

