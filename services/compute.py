import pandas as pd
import streamlit as st
from typing import Union
from utils.types import KPIMetrics, ColumnMapping
from utils.helper import to_cr


# ---------- Internal utilities (date/tax/filter standardization) ----------
def _parse_and_normalize_dates(df: pd.DataFrame, column_map: ColumnMapping) -> pd.DataFrame:
    """Parse date columns with dayfirst=True and normalize to midnight."""
    d = df.copy()
    date_cols = [
        column_map.booking_col,
        column_map.reg_date_col,
        column_map.actual_payment_col,
        column_map.budgeted_date_col,
        column_map.demand_gen_col,
    ]
    for c in date_cols:
        if c and c in d.columns:
            d[c] = pd.to_datetime(d[c], errors='coerce', dayfirst=True)
            d[c] = d[c].dt.normalize()
    return d


def _net_payment(series_payment: pd.Series, series_tax: pd.Series) -> pd.Series:
    """Compute net payment after tax with lower bound at 0."""
    return (series_payment.fillna(0) - series_tax.fillna(0)).clip(lower=0)


def _demand_generated_mask(d: pd.DataFrame, column_map: ColumnMapping, today: pd.Timestamp) -> pd.Series:
    return d[column_map.demand_gen_col].notna() & (d[column_map.demand_gen_col] < today)


def _budget_passed_not_raised_mask(d: pd.DataFrame, column_map: ColumnMapping, today: pd.Timestamp) -> pd.Series:
    return d[column_map.budgeted_date_col].notna() & (d[column_map.budgeted_date_col] <= today) & (d[column_map.demand_gen_col].isna())


def _expected_future_demand_mask(d: pd.DataFrame, column_map: ColumnMapping, today: pd.Timestamp) -> pd.Series:
    return d[column_map.budgeted_date_col].notna() & (d[column_map.budgeted_date_col] > today) & (d[column_map.demand_gen_col].isna())


# ---------- Public preprocessing helper ----------
@st.cache_data(ttl=900)
def preprocess_df(df: pd.DataFrame, column_map: ColumnMapping) -> pd.DataFrame:
    """Standardize dates and numeric fields across the app."""
    d = _parse_and_normalize_dates(df, column_map)
    # Ensure numeric for amounts that are commonly used
    num_cols = [
        column_map.total_agreement_col,
        column_map.other_charges,
        column_map.amount_due_col,
        column_map.payment_received_col,
        column_map.tax_col,
    ]
    for c in num_cols:
        if c and c in d.columns:
            # Handle INR-formatted strings like "₹1,23,456" by stripping symbols/commas first
            d[c] = pd.to_numeric(d[c].astype(str).str.replace(r'[₹,]', '', regex=True), errors='coerce')
    return d


@st.cache_data(ttl=900)
def compute_kpis(
    df: pd.DataFrame,
    today: pd.Timestamp,
    column_map: ColumnMapping,
    overdue_threshold: float = 0.0,
) -> KPIMetrics:
    """
    Compute all KPIs for the dashboard header using standardized logic.
    Returns KPIMetrics dataclass with all 7 metrics.
    """
    today = pd.to_datetime(today).normalize()
    d = preprocess_df(df, column_map)

    # Basic counts
    total_units = len(d[column_map.application_booking_id].dropna().unique())
    units_registered = len(d[d[column_map.reg_date_col].notna()][column_map.application_booking_id].unique())
    units_unregistered = total_units - units_registered
    total_units_sold = total_units  # Same as total units for now

    # Value calculations per booking
    booking_summary = d.groupby(column_map.application_booking_id).agg({
        column_map.total_agreement_col: 'first',
        column_map.other_charges: 'first',
        column_map.amount_due_col: 'sum',
        column_map.payment_received_col: 'sum',
        column_map.tax_col: 'sum',
    }).reset_index()

    # Value of Units (Agreement + Corpus/Maintenance)
    value_of_units = (
        booking_summary[column_map.total_agreement_col].fillna(0) +
        booking_summary[column_map.other_charges].fillna(0)
    ).sum()

    # Total Corpus+Maintenance (deduped per unique property)
    # Each row may repeat corpus/maintenance per milestone; we take first value per property
    if column_map.property_name in d.columns and column_map.other_charges in d.columns:
        property_summary = d.groupby(column_map.property_name).agg({column_map.other_charges: 'first'}).reset_index()
        total_corpus_maintenance = property_summary[column_map.other_charges].fillna(0).sum()
    else:
        total_corpus_maintenance = 0.0

    # Total Demand Generated (where demand date < today)
    total_demand_generated = d.loc[_demand_generated_mask(d, column_map, today), column_map.amount_due_col].sum()

    # Demand Generated + Tax and Tax on Demand
    demand_tax = d.loc[_demand_generated_mask(d, column_map, today), column_map.tax_col].sum()
    total_demand_plus_tax = (total_demand_generated or 0) + (demand_tax or 0)
    tax_on_demand = demand_tax or 0

    # Total Collection (Net Payment after tax, per booking)
    collection_per_booking = booking_summary[[
        column_map.application_booking_id,
        column_map.payment_received_col,
        column_map.tax_col,
    ]].copy()
    collection_per_booking['net_payment'] = _net_payment(
        collection_per_booking[column_map.payment_received_col],
        collection_per_booking[column_map.tax_col]
    )
    total_collection = collection_per_booking['net_payment'].sum()

    # Tax on Collections (gross tax summed)
    tax_on_collections = collection_per_booking[column_map.tax_col].sum()

    # Amount Yet to be Collected
    # Per milestone outstanding = max(Amount Due - Payment Received (gross), 0)
    # Apply to all milestone rows; treat missing payments as 0
    amt_due = d[column_map.amount_due_col].fillna(0)
    pay_gross = d[column_map.payment_received_col].fillna(0)
    outstanding_row = (amt_due - pay_gross).clip(lower=0)
    # Sum across milestones per booking, then across bookings
    outstanding_per_booking = outstanding_row.groupby(d[column_map.application_booking_id]).sum()
    amount_yet_to_be_collected = outstanding_per_booking.sum()

    return KPIMetrics(
        total_units=total_units,
        value_of_units_cr=to_cr(value_of_units),
        total_units_sold=total_units_sold,
        total_demand_generated_cr=to_cr(total_demand_generated),
        total_demand_plus_tax_cr=to_cr(total_demand_plus_tax),
        tax_on_demand_cr=to_cr(tax_on_demand),
        total_collection_cr=to_cr(total_collection),
        tax_on_collections_cr=to_cr(tax_on_collections),
        amount_yet_to_be_collected_cr=to_cr(amount_yet_to_be_collected),
        total_corpus_maintenance_cr=to_cr(total_corpus_maintenance),
        units_registered=units_registered,
        units_unregistered=units_unregistered,
    )


@st.cache_data(ttl=900)
def compute_monthly_trend(df: pd.DataFrame, today: pd.Timestamp, column_map: ColumnMapping):
    """Compute 24-month expected vs actual trend data with standardized net payment and dates."""
    today = pd.to_datetime(today).normalize()
    d = preprocess_df(df, column_map)

    # Expected (by Budgeted Date)
    expected_df = d[d[column_map.budgeted_date_col].notna()].copy()
    expected_df['month'] = expected_df[column_map.budgeted_date_col].dt.to_period('M')
    expected_monthly = expected_df.groupby('month')[column_map.amount_due_col].sum()

    # Actuals (by Payment Date)
    actual_df = d[d[column_map.actual_payment_col].notna()].copy()
    actual_df['month'] = actual_df[column_map.actual_payment_col].dt.to_period('M')
    actual_df['net_payment'] = _net_payment(
        actual_df[column_map.payment_received_col],
        actual_df[column_map.tax_col]
    )
    actual_monthly = actual_df.groupby('month')['net_payment'].sum()

    # Combine and calculate misses
    all_months = pd.period_range(start=today - pd.DateOffset(months=24), end=today, freq='M')
    trend_df = pd.DataFrame(index=all_months)
    trend_df['Expected'] = expected_monthly.reindex(all_months, fill_value=0)
    trend_df['Actuals'] = actual_monthly.reindex(all_months, fill_value=0)
    trend_df['Misses'] = (trend_df['Expected'] - trend_df['Actuals']).clip(lower=0)

    return trend_df


@st.cache_data(ttl=900)
def compute_working_data(df: pd.DataFrame, today: pd.Timestamp, column_map: ColumnMapping):
    """Compute working aggregates used by legacy visualizations from a single, centralized place."""
    _today = pd.to_datetime(today).normalize()
    d = preprocess_df(df, column_map)

    booking_id = column_map.application_booking_id
    amount_due_col = column_map.amount_due_col
    payment_received_col = column_map.payment_received_col
    tax_col = column_map.tax_col
    reg_date_col = column_map.reg_date_col
    budgeted_date_col = column_map.budgeted_date_col
    demand_gen_col = column_map.demand_gen_col
    total_agreement_col = column_map.total_agreement_col
    other_charges = column_map.other_charges
    property_name = column_map.property_name

    # Agreement value per booking = sum of dues
    d['Agreement value'] = d.groupby(booking_id)[amount_due_col].transform('sum')

    # Total Payment Received per booking (gross)
    filtered_pay_df = d[d[payment_received_col].notnull()].copy()
    total_pay_per_booking = (
        filtered_pay_df.groupby(booking_id)[payment_received_col].sum().reset_index()
        .rename(columns={payment_received_col: 'Total Payment Received'})
    )
    d = d.merge(total_pay_per_booking, on=booking_id, how='left')
    d['Total Payment Received'] = d['Total Payment Received'].fillna(0)

    # Total Demand Generated Till Date (sum dues where demand_gen < today)
    filtered_due_df = d[_demand_generated_mask(d, column_map, _today)].copy()
    due_totals = (
        filtered_due_df.groupby(booking_id)[amount_due_col].sum().reset_index()
        .rename(columns={amount_due_col: 'Total Demand Generated Till Date'})
    )
    d = d.merge(due_totals, on=booking_id, how='left')
    d['Total Demand Generated Till Date'] = d['Total Demand Generated Till Date'].fillna(0)

    # Budget Passed, Demand Not Generated
    delayed_demand_df = d[_budget_passed_not_raised_mask(d, column_map, _today)].copy()
    delayed_totals = (
        delayed_demand_df.groupby(booking_id)[amount_due_col].sum().reset_index()
        .rename(columns={amount_due_col: 'Budget Passed, Demand Not Generated'})
    )
    d = d.merge(delayed_totals, on=booking_id, how='left')
    d['Budget Passed, Demand Not Generated'] = d['Budget Passed, Demand Not Generated'].fillna(0)

    # Expected Future Demand
    future_demand_df = d[_expected_future_demand_mask(d, column_map, _today)].copy()
    future_total = (
        future_demand_df.groupby(booking_id)[amount_due_col].sum().reset_index()
        .rename(columns={amount_due_col: 'Expected Future Demand'})
    )
    d = d.merge(future_total, on=booking_id, how='left')
    d['Expected Future Demand'] = d['Expected Future Demand'].fillna(0)

    # Net payment received (after tax) and Amount Overdue at line level for rows where demand exists
    filtered = d[d[demand_gen_col].notnull()].copy()
    filtered['Net payment received (AV)'] = _net_payment(filtered[payment_received_col], filtered[tax_col])
    filtered['Amount Overdue'] = filtered[amount_due_col] - filtered['Net payment received (AV)']

    # Aggregate overdue & net payment per booking
    overdue_df = (
        filtered.groupby(booking_id)[['Net payment received (AV)', 'Amount Overdue']]
        .sum().reset_index()
    )
    d = d.merge(overdue_df, on=booking_id, how='left')
    d['Amount Overdue'] = d['Amount Overdue'].fillna(0)
    d['Net payment received (AV)'] = d['Net payment received (AV)'].fillna(0)

    # Registered/Unregistered partitions
    booked_df = d[d[booking_id].notnull()].copy()
    reg_df = booked_df[booked_df[reg_date_col].notnull()].copy()
    unreg_df = booked_df[booked_df[reg_date_col].isnull()].copy()

    # Latest row per booking (by demand then budget date) for some per-booking rollups
    sort_cols = [booking_id, demand_gen_col, budgeted_date_col]
    d_sorted = d.sort_values(sort_cols)
    last_by_booking = d_sorted.groupby(booking_id, as_index=False).last()

    # Aggregate KPIs used by presenter
    total_units = d[property_name].nunique()
    booked_units = booked_df[booking_id].nunique()
    reg_units = reg_df[booking_id].nunique()
    unreg_units = unreg_df[booking_id].nunique()

    # Agreement totals
    total_sales_act = booked_df.groupby(booking_id)[total_agreement_col].first().sum()
    reg_sales_act = reg_df.groupby(booking_id)[total_agreement_col].first().sum()
    unreg_sales_act = unreg_df.groupby(booking_id)[total_agreement_col].first().sum()

    total_corpus = booked_df.groupby(booking_id)[other_charges].first().sum()
    reg_corpus = reg_df.groupby(booking_id)[other_charges].first().sum()
    unreg_corpus = unreg_df.groupby(booking_id)[other_charges].first().sum()

    total_sales = booked_df.groupby(booking_id)['Agreement value'].first().sum()
    reg_sales = reg_df.groupby(booking_id)['Agreement value'].first().sum()
    unreg_sales = unreg_df.groupby(booking_id)['Agreement value'].first().sum()

    # Demand buckets
    total_due = filtered_due_df[amount_due_col].sum()
    reg_due = reg_df.groupby(booking_id).tail(1)['Total Demand Generated Till Date'].sum()
    unreg_due = unreg_df.groupby(booking_id).tail(1)['Total Demand Generated Till Date'].sum()

    total_due_n = delayed_demand_df[amount_due_col].sum()
    reg_due_n = reg_df.groupby(booking_id).tail(1)['Budget Passed, Demand Not Generated'].sum()
    unreg_due_n = unreg_df.groupby(booking_id).tail(1)['Budget Passed, Demand Not Generated'].sum()

    total_due_nn = future_demand_df[amount_due_col].sum()
    reg_due_nn = reg_df.groupby(booking_id).tail(1)['Expected Future Demand'].sum()
    unreg_due_nn = unreg_df.groupby(booking_id).tail(1)['Expected Future Demand'].sum()

    # Collections (no tax)
    total_collected_notax = last_by_booking['Net payment received (AV)'].sum()
    reg_collected_notax = (
        reg_df.sort_values(sort_cols).groupby(booking_id).last()['Net payment received (AV)'].sum()
        if not reg_df.empty else 0
    )
    unreg_collected_notax = (
        unreg_df.sort_values(sort_cols).groupby(booking_id).last()['Net payment received (AV)'].sum()
        if not unreg_df.empty else 0
    )

    # Overdue (un-thresholded)
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

