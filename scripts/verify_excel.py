import sys
import pandas as pd
from utils.types import ColumnMapping
from services.compute import compute_working_data
from utils.helper import percent

# Path to Excel file; allow override via argv
path = sys.argv[1] if len(sys.argv) > 1 else 'VTTS _ Cullinan.xlsx'

# Read Excel
xl = pd.read_excel(path)
xl.columns = xl.columns.str.strip()

# Utility to pick first existing column

def pick(df, *candidates):
    for c in candidates:
        if c and c in df.columns:
            return c
    return None

# Build ColumnMapping using same candidates as dashboard
column_map = ColumnMapping(
    booking_col=pick(xl, "Booking Date"),
    reg_date_col=pick(xl, "Agreement Registration Date", "Registration Date"),
    actual_payment_col=pick(xl, "Actual Payment Date", "Payment Received Date", "Receipt Date"),
    amount_due_col=pick(xl, "Total Amount Due", "Amount Due", "Due Amount"),
    payment_received_col=pick(xl, "Payment Received", "Amount Received"),
    total_agreement_col=pick(xl, "Total Agreement Value", "Agreement Value", "Agreement Amount"),
    budgeted_date_col=pick(xl, "Budgeted Date", "Planned Demand Date"),
    demand_gen_col=pick(xl, "Demand Generation Date", "Demand generation date", "Demand Raised Date", "Invoice Date"),
    milestone_status_col=pick(xl, "Is Milestone Completed", "Milestone Completion Status", "Milestone Completed"),
    property_name=pick(xl, "Unit/Property Name (Application / Booking ID)", "Property Name", "Unit / Property Name"),
    customer_name=pick(xl, "Customer Name", "Account Name", "Ledger Name"),
    active_col=pick(xl, "Active", "Is Active", "Status"),
    application_booking_id=pick(xl, "Application / Booking ID", "Booking ID", "Agreement/Booking ID", "Opportunity/Booking ID"),
    tax_col=pick(xl, "Total Service Tax On PPD", "Tax Amount", "GST Amount", "Total Tax"),
    tower_col=pick(xl, "Tower"),
    type_col=pick(xl, "Type"),
    milestone_name=pick(xl, "Milestone Name"),
    other_charges=pick(xl, "Other Charges (Corpus+Maintenance)", "Corpus+Maintenance", "Corpus Maintenance", "Other Charges"),
)

# Today (normalize)
today = pd.Timestamp.today().normalize()

# Compute working data
wd = compute_working_data(xl, today, column_map)

d = wd["df"]
reg_df = wd["reg_df"]
unreg_df = wd["unreg_df"]
totals = wd["totals"]
booking_id = column_map.application_booking_id

# Overdue threshold like UI default
overdue_threshold = 1000

# Assemble summary values as in dashboard
# Row 1: Budget Passed, Demand Not Raised
all_due_n = percent(totals["total_due_n"], totals["total_sales"])
reg_due_n = percent(reg_df.groupby(booking_id).tail(1)['Budget Passed, Demand Not Generated'].sum(), totals["reg_sales"])
unreg_due_n = percent(unreg_df.groupby(booking_id).tail(1)['Budget Passed, Demand Not Generated'].sum(), totals["unreg_sales"])

# Row 2: Expected Future Demand
all_due_nn = percent(totals["total_due_nn"], totals["total_sales"])
reg_due_nn = percent(reg_df.groupby(booking_id).tail(1)['Expected Future Demand'].sum(), totals["reg_sales"])
unreg_due_nn = percent(unreg_df.groupby(booking_id).tail(1)['Expected Future Demand'].sum(), totals["unreg_sales"])

# Row 3: Amount Overdue
overdue = d[d['Amount Overdue'] > overdue_threshold].copy()
all_overdue_amt = percent(overdue.groupby(booking_id)['Amount Overdue'].sum().sum(), totals["total_sales"])
reg_overdue_amt = percent(reg_df.groupby(booking_id).tail(1)['Amount Overdue'].sum(), totals["reg_sales"])
unreg_overdue_amt = percent(unreg_df.groupby(booking_id).tail(1)['Amount Overdue'].sum(), totals["unreg_sales"])

print("Financial Summary Details (as dashboard)")
print("Metric, All Units, Registered Users, Unregistered Users")
print(", ".join([
    "Budget Passed, Demand Not Raised", all_due_n, reg_due_n, unreg_due_n
]))
print(", ".join([
    "Expected Future Demand", all_due_nn, reg_due_nn, unreg_due_nn
]))
print(", ".join([
    "Amount Overdue", all_overdue_amt, reg_overdue_amt, unreg_overdue_amt
]))

