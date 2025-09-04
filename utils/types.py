from typing import Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd

@dataclass
class KPIMetrics:
    total_units: int
    value_of_units_cr: float
    total_units_sold: int
    total_demand_generated_cr: float
    total_collection_cr: float
    units_registered: int
    units_unregistered: int

@dataclass
class ColumnMapping:
    booking_col: str
    reg_date_col: str
    actual_payment_col: str
    amount_due_col: str
    payment_received_col: str
    total_agreement_col: str
    budgeted_date_col: str
    demand_gen_col: str
    milestone_status_col: str
    property_name: str
    customer_name: str
    active_col: str
    application_booking_id: str
    tax_col: str
    tower_col: str
    type_col: str
    milestone_name: str
    other_charges: str

