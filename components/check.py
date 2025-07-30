import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.helper import get_column

def check(df,today):
    df.columns = df.columns.str.strip() # -> Quality check for columns name.
    ## List of columns 
    # today = pd.to_datetime(st.sidebar.date_input("📅 Calculate Due As of Date", value=pd.to_datetime("today")))
    # gst_percentage = st.sidebar.number_input("💰 GST Percentage", min_value=0.0, max_value=100.0, value=5.0, step=0.1)

    ## column entry 
    # Get dynamic mappings with fallback if default is missing
    other_charges=get_column(df,"Other Charges (Corpus+Maintenance)","Other Charges (Corpus+Maintenance)")
    booking_col = get_column(df, "Booking Date", "Booking Date")
    reg_date_col = get_column(df, "Agreement Registration Date", "Agreement Registration Date")
    actual_payment_col = get_column(df, "Actual Payment Date", "Actual Payment Date")
    amount_due_col = get_column(df, "Total Amount Due", "Total Amount Due")
    payment_received_col = get_column(df, "Payment Received", "Payment Received")
    total_agreement_col = get_column(df, "Total Agreement Value", "Total Agreement Value")
    budgeted_date_col = get_column(df, "Budgeted Date", "Budgeted Date")
    percentage_col=get_column(df, "Amount Percent", "Amount Percent")
    demand_gen_col = get_column(df, "Demand generation date", "Demand Generation Date")
    milestone_status_col = get_column(df, "Is Milestone Completed", "Milestone Completion Status")
    property_name = get_column(df, "Property Name", "Unit/Property Name (Application / Booking ID)")
    customer_name = get_column(df, "Customer Name", "Customer Name")
    active= get_column(df, "Active", "Active")
    application_booking_id = get_column(df, "Application / Booking ID", "Application / Booking ID (Unique and Not Null)")
    tax = get_column(df, "Total Service Tax On PPD", "Application / Booking ID (Unique and Not Null)")
    tower = get_column(df, "Tower", "Tower")
    type = get_column(df, "Type", "Type")
    milestone_name = get_column(df, "Milestone Name", "Milestone Name")


    df[booking_col] = pd.to_datetime(df[booking_col], errors='coerce', dayfirst=True)
    df[total_agreement_col] = pd.to_numeric(df[total_agreement_col].astype(str).str.replace(r'[₹,]', '', regex=True), errors='coerce')
    df[reg_date_col] = pd.to_datetime(df[reg_date_col], errors='coerce', dayfirst=True)
    df[actual_payment_col] = pd.to_datetime(df[actual_payment_col], errors='coerce', dayfirst=True)
    df[amount_due_col] = pd.to_numeric(df[amount_due_col].astype(str).str.replace(r'[₹,]', '', regex=True), errors='coerce')
    df[payment_received_col] = pd.to_numeric(df[payment_received_col].astype(str).str.replace(r'[₹,]', '', regex=True), errors='coerce')
    df[demand_gen_col] = pd.to_datetime(df[demand_gen_col], errors='coerce', dayfirst=True)
    df[budgeted_date_col] = pd.to_datetime(df[budgeted_date_col], errors='coerce', dayfirst=True)
    df[property_name] = df[property_name].astype(str).str.strip()
    df[tax]= pd.to_numeric(df[tax].astype(str).str.replace(r'[₹,]', '', regex=True), errors='coerce')




#-----------------------------------------------------------------------------------------------------------------------------------------------------
# Checks

    ## is register or not
    df['is_registered'] = df[reg_date_col].notna() # if not available means not register

    # Step 3: Flag Invalid Registrations
    # Define condition for invalid registrations: has booking ID but no property name
    invalid_book = df[(df[application_booking_id].notna()) & (df[property_name].isna())]
    invalid_book_df = invalid_book[[customer_name, application_booking_id ]].drop_duplicates()

    if not invalid_book_df.empty:
        st.subheader("⚠️ Invalid Booking (Booked but Property Not Assigned)")
        st.warning(f"{len(invalid_book_df)} invalid Booking found!")
        st.dataframe(invalid_book_df)
    else:
        st.success("✅ All bookings are correctly mapped to properties.")

        
        
    invalid_regs = df[(df["is_registered"]) & (df[application_booking_id].isna())]
    invalid_regs_df = invalid_regs[[customer_name ]].drop_duplicates()
    if not invalid_regs.empty:
        st.subheader("⚠️ Invalid Registrations (Registered but not Booked)")
        st.warning(f"{len(invalid_regs)} invalid registrations found!")
        st.dataframe(invalid_regs_df)
    else:
        st.success("✅ All registrations are valid (booked).")



    # Check 4: Payment Received Without Demand Raised
    invalid_payment = df[(df[payment_received_col].notna())&(df[payment_received_col]>0) & (df[demand_gen_col].isna())]
    invalid_payment_df = invalid_payment[[property_name,application_booking_id,customer_name, payment_received_col]].drop_duplicates()
    if not invalid_payment_df.empty:
        st.subheader("⚠️ Payment Received Without Demand Raised")
        st.warning(f"{len(invalid_payment_df)} such cases found!")
        st.dataframe(invalid_payment_df)
    else:
        st.success("✅ All payments are preceded by valid demands.")

    
    # Check 7: Milestone Done but No Demand Raised
    milestone_done_no_demand = df[(df[milestone_status_col] == 1) & (df[demand_gen_col].isna())]
    milestone_done_no_demand_df = milestone_done_no_demand[[property_name,customer_name, milestone_name]].drop_duplicates()
    if not milestone_done_no_demand_df.empty:
        st.subheader("⚠️ Milestone Completed But No Demand Raised")
        st.warning(f"{len(milestone_done_no_demand_df)} such milestones found!")
        st.dataframe(milestone_done_no_demand_df)
    else:
        st.success("✅ All completed milestones have demand raised.")

    # Check 12: Budgeted Date Passed but No Demand Raised
    budget_passed_no_demand = df[(df[budgeted_date_col] < pd.Timestamp.today()) & (df[demand_gen_col].isna())]
    budget_passed_no_demand_df = budget_passed_no_demand[[property_name,customer_name, milestone_name, budgeted_date_col]].drop_duplicates()
    if not budget_passed_no_demand_df.empty:
        st.subheader("⚠️ Budgeted Date Passed But No Demand Raised")
        st.warning(f"{len(budget_passed_no_demand_df)} such milestones found!")
        st.dataframe(budget_passed_no_demand_df)
    else:
        st.success("✅ All overdue milestones have raised demands.")


    # Check 15: Booking Financial Mismatch - Agreement + Other Charges vs Total Due
    grouped = df.groupby(application_booking_id).agg({
        property_name: 'first',
        total_agreement_col: 'first',         # Take the single value
        other_charges: 'first',               # Take the single value
        amount_due_col: 'sum'                 # Sum for booking
    }).reset_index()

    grouped['diff'] = (grouped[total_agreement_col] + grouped[other_charges]) - grouped[amount_due_col]

    invalid_financial = grouped[(grouped['diff'] < -1000) | (grouped['diff'] > 1000)]
    invalid_financial_df = invalid_financial[[property_name, application_booking_id, total_agreement_col, other_charges, amount_due_col, 'diff']]

    if not invalid_financial_df.empty:
        st.subheader("⚠️ Booking Value Mismatch")
        st.warning(f"{len(invalid_financial_df)} entries found with mismatched booking values!")
        st.dataframe(invalid_financial_df)
    else:
        st.success("✅ All booking value entries are within acceptable range.")



    
    # Check 11: Duplicate Payments for Same Milestone
    dup_payments = df[df.duplicated(subset=[application_booking_id, milestone_name, actual_payment_col], keep=False)]
    dup_payments_df = dup_payments[[property_name,customer_name, application_booking_id, milestone_name, actual_payment_col]].drop_duplicates()
    if not dup_payments_df.empty:
        st.subheader("⚠️ Duplicate Payments for Same Milestone")
        st.warning(f"{len(dup_payments_df)} duplicate payment entries found!")
        st.dataframe(dup_payments_df)
    else:
        st.success("✅ No duplicate milestone payments found.")


    # Check 13: Total Milestone Percentage Not Equal to 100
    milestone_sum_check = df.groupby(application_booking_id)[percentage_col].sum().reset_index()
    invalid_percentage_sum = milestone_sum_check[milestone_sum_check[percentage_col] != 100]

    if not invalid_percentage_sum.empty:
        st.subheader("⚠️ Total Milestone Percentage Not Equal to 100")
        st.warning(f"{len(invalid_percentage_sum)} such bookings found!")
        
        # Merge with customer name for display
        invalid_percentage_df = invalid_percentage_sum.merge(
            df[[property_name,application_booking_id, customer_name]].drop_duplicates(), 
            on=application_booking_id, 
            how='left'
        )[[property_name,application_booking_id, customer_name, percentage_col]].drop_duplicates()
        
        st.dataframe(invalid_percentage_df.rename(columns={
            property_name: "Property Name",
            application_booking_id: "Booking ID",
            customer_name: "Customer Name",
            percentage_col: "Total %"
        }))
    else:
        st.success("✅ All bookings have milestone percentages summing up to 100.")



    # Check 14: Tax Greater Than Payment Received
    invalid_tax = df[(df[tax] > df[payment_received_col])]
    invalid_tax_df = invalid_tax[[property_name,customer_name, tax, payment_received_col]].drop_duplicates()
    if not invalid_tax_df.empty:
        st.subheader("⚠️ GST/TAX Greater Than Payment Received")
        st.warning(f"{len(invalid_tax_df)} entries found where tax exceeds payment!")
        st.dataframe(invalid_tax_df)
    else:
        st.success("✅ All tax entries are valid against payments.")

    

    


    

