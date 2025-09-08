import pandas as pd
from typing import Dict, Any
from utils.types import ColumnMapping
from services.compute import preprocess_df, _net_payment


def validate_tax_vs_payment(df: pd.DataFrame, column_map: ColumnMapping) -> Dict[str, Any]:
    d = preprocess_df(df, column_map)
    pay = d[column_map.payment_received_col]
    tax = d[column_map.tax_col]

    mask_applicable = pay.notna() & tax.notna()
    mask_issue = mask_applicable & (tax > pay)

    issues_df = d.loc[mask_issue, [
        column_map.application_booking_id,
        column_map.payment_received_col,
        column_map.tax_col,
    ]].copy()

    result = {
        "type": "tax_vs_payment",
        "count": int(mask_issue.sum()),
        "details": issues_df,
        "message": (
            f"{int(mask_issue.sum())} rows where Tax > Payment Received. Net payment was capped at 0 for these rows."
            if mask_issue.any() else ""
        )
    }
    return result


def validate_date_consistency(df: pd.DataFrame, column_map: ColumnMapping) -> Dict[str, Any]:
    d = preprocess_df(df, column_map)
    msgs = []
    details: Dict[str, pd.DataFrame] = {}

    # Registration earlier than booking
    if column_map.reg_date_col and column_map.booking_col:
        mask = d[column_map.reg_date_col].notna() & d[column_map.booking_col].notna() & \
               (d[column_map.reg_date_col] < d[column_map.booking_col])
        if mask.any():
            msgs.append(f"{int(mask.sum())} rows where Registration Date < Booking Date.")
            details["reg_before_booking"] = d.loc[mask, [column_map.application_booking_id, column_map.booking_col, column_map.reg_date_col]].copy()

    # Payment earlier than booking
    if column_map.actual_payment_col and column_map.booking_col:
        mask = d[column_map.actual_payment_col].notna() & d[column_map.booking_col].notna() & \
               (d[column_map.actual_payment_col] < d[column_map.booking_col])
        if mask.any():
            msgs.append(f"{int(mask.sum())} rows where Payment Date < Booking Date.")
            details["payment_before_booking"] = d.loc[mask, [column_map.application_booking_id, column_map.booking_col, column_map.actual_payment_col]].copy()

    # Demand generated earlier than booking
    if column_map.demand_gen_col and column_map.booking_col:
        mask = d[column_map.demand_gen_col].notna() & d[column_map.booking_col].notna() & \
               (d[column_map.demand_gen_col] < d[column_map.booking_col])
        if mask.any():
            msgs.append(f"{int(mask.sum())} rows where Demand Generation Date < Booking Date.")
            details["demand_before_booking"] = d.loc[mask, [column_map.application_booking_id, column_map.booking_col, column_map.demand_gen_col]].copy()

    return {
        "type": "date_consistency",
        "count": sum(len(v) for v in details.values()),
        "details": details,
        "message": "; ".join(msgs) if msgs else ""
    }


def run_validations(df: pd.DataFrame, column_map: ColumnMapping) -> Dict[str, Any]:
    """Run all validations and return structured results."""
    results = []
    results.append(validate_tax_vs_payment(df, column_map))
    results.append(validate_date_consistency(df, column_map))

    messages = [r["message"] for r in results if r.get("message")]
    return {
        "results": results,
        "messages": messages,
    }

