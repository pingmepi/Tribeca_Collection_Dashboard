import pandas as pd
import streamlit as st
from utils.types import KPIMetrics, ColumnMapping
from utils.helper import to_cr


@st.cache_data(ttl=900)
def compute_kpis(df: pd.DataFrame, today: pd.Timestamp, column_map: ColumnMapping) -> KPIMetrics:
    """
    Compute all KPIs for the dashboard header.
    Returns KPIMetrics dataclass with all 7 metrics.
    """
    today = pd.to_datetime(today).normalize()
    d = df.copy()

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
        column_map.demand_gen_col: lambda x: x.notna().any()
    }).reset_index()

    # Value of Units (Agreement + Corpus/Maintenance)
    value_of_units = (booking_summary[column_map.total_agreement_col].fillna(0) +
                     booking_summary[column_map.other_charges].fillna(0)).sum()

    # Total Demand Generated (where demand date < today)
    demand_generated_df = d[d[column_map.demand_gen_col].notna() &
                           (d[column_map.demand_gen_col] < today)]
    total_demand_generated = demand_generated_df[column_map.amount_due_col].sum()

    # Total Collection (Net Payment after tax, per booking)
    collection_df = d[d[column_map.payment_received_col].notna()]
    collection_per_booking = collection_df.groupby(column_map.application_booking_id).agg({
        column_map.payment_received_col: 'sum',
        column_map.tax_col: 'sum'
    }).reset_index()
    collection_per_booking['net_payment'] = (
        collection_per_booking[column_map.payment_received_col] -
        collection_per_booking[column_map.tax_col]
    ).clip(lower=0)
    total_collection = collection_per_booking['net_payment'].sum()

    return KPIMetrics(
        total_units=total_units,
        value_of_units_cr=to_cr(value_of_units),
        total_units_sold=total_units_sold,
        total_demand_generated_cr=to_cr(total_demand_generated),
        total_collection_cr=to_cr(total_collection),
        units_registered=units_registered,
        units_unregistered=units_unregistered
    )


@st.cache_data(ttl=900)
def compute_monthly_trend(df: pd.DataFrame, today: pd.Timestamp, column_map: ColumnMapping):
    """Compute 24-month expected vs actual trend data"""
    today = pd.to_datetime(today).normalize()

    # Expected (by Budgeted Date)
    expected_df = df[df[column_map.budgeted_date_col].notna()].copy()
    expected_df['month'] = expected_df[column_map.budgeted_date_col].dt.to_period('M')
    expected_monthly = expected_df.groupby('month')[column_map.amount_due_col].sum()

    # Actuals (by Payment Date)
    actual_df = df[df[column_map.actual_payment_col].notna()].copy()
    actual_df['month'] = actual_df[column_map.actual_payment_col].dt.to_period('M')
    actual_df['net_payment'] = (actual_df[column_map.payment_received_col] -
                               actual_df[column_map.tax_col]).clip(lower=0)
    actual_monthly = actual_df.groupby('month')['net_payment'].sum()

    # Combine and calculate misses
    all_months = pd.period_range(start=today - pd.DateOffset(months=24),
                                end=today, freq='M')
    trend_df = pd.DataFrame(index=all_months)
    trend_df['Expected'] = expected_monthly.reindex(all_months, fill_value=0)
    trend_df['Actuals'] = actual_monthly.reindex(all_months, fill_value=0)
    trend_df['Misses'] = (trend_df['Expected'] - trend_df['Actuals']).clip(lower=0)

    return trend_df

