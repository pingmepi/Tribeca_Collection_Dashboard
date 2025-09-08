import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.helper import get_column

def check(df, today):
    df.columns = df.columns.str.strip() # -> Quality check for columns name.
    ## List of columns
    # today = pd.to_datetime(st.sidebar.date_input("📅 Calculate Due As of Date", value=pd.to_datetime("today")))
    # gst_percentage = st.sidebar.number_input("💰 GST Percentage", min_value=0.0, max_value=100.0, value=5.0, step=0.1)

    ## column entry
    # Get dynamic mappings with fallback if default is missing
    other_charges = get_column(df, "Other Charges (Corpus+Maintenance)", label="Other Charges (Corpus+Maintenance)")
    booking_col = get_column(df, "Booking Date", label="Booking Date")
    reg_date_col = get_column(df, "Agreement Registration Date", "Registration Date", label="Registration Date")
    actual_payment_col = get_column(df, "Actual Payment Date", "Payment Received Date", "Receipt Date", label="Payment Date")
    amount_due_col = get_column(df, "Total Amount Due", "Amount Due", "Due Amount", label="Amount Due")
    payment_received_col = get_column(df, "Payment Received", "Amount Received", label="Payment Received")
    total_agreement_col = get_column(df, "Total Agreement Value", "Agreement Value", "Agreement Amount", label="Agreement Value")
    budgeted_date_col = get_column(df, "Budgeted Date", "Planned Demand Date", label="Budgeted Date")
    percentage_col = get_column(df, "Amount Percent", label="Amount Percent")
    demand_gen_col = get_column(df, "Demand Generation Date", "Demand generation date", "Demand Raised Date", "Invoice Date", label="Demand Generation Date")
    milestone_status_col = get_column(df, "Is Milestone Completed", "Milestone Completion Status", "Milestone Completed", label="Milestone Status")
    property_name = get_column(df, "Unit/Property Name (Application / Booking ID)", "Property Name", "Unit / Property Name", label="Property Name")
    customer_name = get_column(df, "Customer Name", "Account Name", label="Customer Name")
    active = get_column(df, "Active", "Is Active", "Status", label="Active Status")
    application_booking_id = get_column(df, "Application / Booking ID", "Booking ID", "Agreement/Booking ID", "Opportunity/Booking ID", label="Booking ID")
    tax_col = get_column(df, "Total Service Tax On PPD", "Tax Amount", "GST Amount", "Total Tax", label="Tax Amount")
    tower = get_column(df, "Tower", label="Tower")
    type_col = get_column(df, "Type", label="Type")
    milestone_name = get_column(df, "Milestone Name", label="Milestone Name")


    df[booking_col] = pd.to_datetime(df[booking_col], errors='coerce', dayfirst=True)
    df[total_agreement_col] = pd.to_numeric(df[total_agreement_col].astype(str).str.replace(r'[₹,]', '', regex=True), errors='coerce')
    df[reg_date_col] = pd.to_datetime(df[reg_date_col], errors='coerce', dayfirst=True)
    df[actual_payment_col] = pd.to_datetime(df[actual_payment_col], errors='coerce', dayfirst=True)
    df[amount_due_col] = pd.to_numeric(df[amount_due_col].astype(str).str.replace(r'[₹,]', '', regex=True), errors='coerce')
    df[payment_received_col] = pd.to_numeric(df[payment_received_col].astype(str).str.replace(r'[₹,]', '', regex=True), errors='coerce')
    df[demand_gen_col] = pd.to_datetime(df[demand_gen_col], errors='coerce', dayfirst=True)
    df[budgeted_date_col] = pd.to_datetime(df[budgeted_date_col], errors='coerce', dayfirst=True)
    df[property_name] = df[property_name].astype(str).str.strip()
    df[tax_col] = pd.to_numeric(df[tax_col].astype(str).str.replace(r'[₹,]', '', regex=True), errors='coerce')




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
        with st.expander(f"⚠️ Invalid Booking Details ({len(invalid_book_df)} found)", expanded=False):
            st.dataframe(invalid_book_df)
    else:
        st.success("✅ All bookings are correctly mapped to properties.")



    invalid_regs = df[(df["is_registered"]) & (df[application_booking_id].isna())]
    invalid_regs_df = invalid_regs[[customer_name ]].drop_duplicates()
    if not invalid_regs.empty:
        st.subheader("⚠️ Invalid Registrations (Registered but not Booked)")
        st.warning(f"{len(invalid_regs)} invalid registrations found!")
        with st.expander(f"⚠️ Invalid Registration Details ({len(invalid_regs_df)} found)", expanded=False):
            st.dataframe(invalid_regs_df)
    else:
        st.success("✅ All registrations are valid (booked).")



    # Check 4: Payment Received Without Demand Raised
    invalid_payment = df[(df[payment_received_col].notna())&(df[payment_received_col]>0) & (df[demand_gen_col].isna())]
    invalid_payment_df = invalid_payment[[property_name,application_booking_id,customer_name, payment_received_col]].drop_duplicates()
    if not invalid_payment_df.empty:
        st.subheader("⚠️ Payment Received Without Demand Raised")
        st.warning(f"{len(invalid_payment_df)} such cases found!")
        with st.expander(f"⚠️ Payment Without Demand Details ({len(invalid_payment_df)} found)", expanded=False):
            st.dataframe(invalid_payment_df)
    else:
        st.success("✅ All payments are preceded by valid demands.")


    # Check 7: Milestone Done but No Demand Raised
    milestone_done_no_demand = df[(df[milestone_status_col] == 1) & (df[demand_gen_col].isna())]
    milestone_done_no_demand_df = milestone_done_no_demand[[property_name,customer_name, milestone_name]].drop_duplicates()
    if not milestone_done_no_demand_df.empty:
        st.subheader("⚠️ Milestone Completed But No Demand Raised")
        st.warning(f"{len(milestone_done_no_demand_df)} such milestones found!")
        with st.expander(f"⚠️ Milestone Completed Without Demand Details ({len(milestone_done_no_demand_df)} found)", expanded=False):
            st.dataframe(milestone_done_no_demand_df)
    else:
        st.success("✅ All completed milestones have demand raised.")

    # Check 12: Budgeted Date Passed but No Demand Raised
    budget_passed_no_demand = df[(df[budgeted_date_col] < pd.Timestamp.today()) & (df[demand_gen_col].isna())]
    budget_passed_no_demand_df = budget_passed_no_demand[[property_name,customer_name, milestone_name, budgeted_date_col]].drop_duplicates()
    if not budget_passed_no_demand_df.empty:
        st.subheader("⚠️ Budgeted Date Passed But No Demand Raised")
        st.warning(f"{len(budget_passed_no_demand_df)} such milestones found!")
        with st.expander(f"⚠️ Budget Passed Without Demand Details ({len(budget_passed_no_demand_df)} found)", expanded=False):
            st.dataframe(budget_passed_no_demand_df)
    else:
        st.success("✅ All overdue milestones have raised demands.")


    # Check 15: Booking Financial Mismatch - Agreement + Other Charges vs Total Due
    grouped = df.groupby(application_booking_id).agg({
        property_name: 'first',
        total_agreement_col: 'first',  # Take the single value
        other_charges: 'first',        # Take the single value
        amount_due_col: 'sum'          # Sum for booking
    }).reset_index()

    grouped['diff'] = (grouped[total_agreement_col] + grouped[other_charges]) - grouped[amount_due_col]

    invalid_financial = grouped[(grouped['diff'] < -1000) | (grouped['diff'] > 1000)]
    invalid_financial_df = invalid_financial[[property_name, application_booking_id, total_agreement_col, other_charges, amount_due_col, 'diff']]

    if not invalid_financial_df.empty:
        st.subheader("⚠️ Booking Value Mismatch")
        st.warning(f"{len(invalid_financial_df)} entries found with mismatched booking values!")
        with st.expander(f"⚠️ Booking Value Mismatch Details ({len(invalid_financial_df)} found)", expanded=False):
            st.dataframe(invalid_financial_df)
    else:
        st.success("✅ All booking value entries are within acceptable range.")


    # Check 12.5: Date Consistency Tables (Registration/Payment earlier than Booking)
    reg_issue = df[(df[reg_date_col].notna()) & (df[booking_col].notna()) & (df[reg_date_col] < df[booking_col])][[
        property_name, customer_name, application_booking_id, booking_col, reg_date_col
    ]].drop_duplicates()
    pay_issue = df[(df[actual_payment_col].notna()) & (df[booking_col].notna()) & (df[actual_payment_col] < df[booking_col])][[
        property_name, customer_name, application_booking_id, booking_col, actual_payment_col, payment_received_col
    ]].drop_duplicates()

    if not reg_issue.empty or not pay_issue.empty:
        st.subheader("⚠️ Date Consistency Issues")
        st.warning(f"{len(reg_issue)} rows where Registration Date < Booking Date; {len(pay_issue)} rows where Payment Date < Booking Date.")
        c1, c2 = st.columns(2)
        def _download_link(df_in: pd.DataFrame, name: str):
            csv = df_in.to_csv(index=False).encode('utf-8')
            st.download_button(label=f"📥 Download {name}", data=csv, file_name=f"{name.lower().replace(' ', '_')}.csv", mime="text/csv")

        # Render as two expanders stacked vertically
        reg_tbl = reg_issue.rename(columns={
            property_name: "Property Name",
            customer_name: "Customer Name",
            application_booking_id: "Booking ID",
            booking_col: "Booking Date",
            reg_date_col: "Registration Date",
        })
        pay_tbl = pay_issue.rename(columns={
            property_name: "Property Name",
            customer_name: "Customer Name",
            application_booking_id: "Booking ID",
            booking_col: "Booking Date",
            actual_payment_col: "Payment Date",
            payment_received_col: "Payment Received",
        })

        if not reg_tbl.empty:
            with st.expander(f"Registration Date < Booking Date ({len(reg_tbl)} rows)", expanded=False):
                st.dataframe(reg_tbl, use_container_width=True)
                _download_link(reg_tbl, "registration_before_booking")

        if not pay_tbl.empty:
            with st.expander(f"Payment Date < Booking Date ({len(pay_tbl)} rows)", expanded=False):
                st.dataframe(pay_tbl, use_container_width=True)
                _download_link(pay_tbl, "payment_before_booking")
    else:
        st.success("✅ No date consistency issues found.")




    # Check 11: Duplicate Payments for Same Milestone
    # Duplicates = multiple payment rows for the same Booking + Milestone (any payment date)
    has_payment = df[payment_received_col].fillna(0) > 0
    pay_rows = df.loc[has_payment].copy()
    dup_groups = (
        pay_rows.groupby([application_booking_id, milestone_name])
                .size()
                .reset_index(name='count')
    )
    dup_keys = dup_groups[dup_groups['count'] > 1][[application_booking_id, milestone_name]]
    dup_payments_df = pay_rows.merge(dup_keys, on=[application_booking_id, milestone_name], how='inner')

    if not dup_payments_df.empty:
        st.subheader("⚠️ Duplicate Payments for Same Milestone")
        st.warning(f"{len(dup_payments_df)} rows across {len(dup_keys)} milestones with multiple payments found!")
        cols = [property_name, customer_name, application_booking_id, milestone_name, actual_payment_col, payment_received_col, amount_due_col, tax_col]
        cols = [c for c in cols if c in dup_payments_df.columns]
        dup_payments_df = dup_payments_df[cols].sort_values([application_booking_id, milestone_name, actual_payment_col])
        with st.expander(f"⚠️ Duplicate Payment Details ({len(dup_payments_df)} rows)", expanded=False):
            st.dataframe(dup_payments_df, use_container_width=True)
            csv = dup_payments_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download duplicate_payments.csv", csv, file_name="duplicate_payments.csv", mime="text/csv")
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

        with st.expander(f"⚠️ Milestone Percentage Issues Details ({len(invalid_percentage_df)} found)", expanded=False):
            st.dataframe(invalid_percentage_df.rename(columns={
                property_name: "Property Name",
                application_booking_id: "Booking ID",
                customer_name: "Customer Name",
                percentage_col: "Total %"
            }))
    else:
        st.success("✅ All bookings have milestone percentages summing up to 100.")



    # Check 14: Tax Greater Than Payment Received
    invalid_tax = df[(df[tax_col] > df[payment_received_col])]
    invalid_tax_df = invalid_tax[[property_name, customer_name, tax_col, payment_received_col]].drop_duplicates()
    if not invalid_tax_df.empty:
        st.subheader("⚠️ GST/TAX Greater Than Payment Received")
        st.warning(f"{len(invalid_tax_df)} entries found where tax exceeds payment!")
        with st.expander(f"⚠️ Tax Greater Than Payment Details ({len(invalid_tax_df)} found)", expanded=False):
            st.dataframe(invalid_tax_df)
    else:
        st.success("✅ All tax entries are valid against payments.")








