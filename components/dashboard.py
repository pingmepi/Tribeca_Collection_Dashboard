import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.helper import get_column ,bucket, percent,highlight_rows


## List/Report of issues 


def render_dashboard(df,today):
        st.dataframe(df) #->Initial dataframe
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


        
    ## Alloted flat data 

        ## Total amount due 
        # filtered_due_df = df[df[budgeted_date_col] < today]
        # due_totals = filtered_due_df.groupby(property_name)[amount_due_col].sum().reset_index()
        # due_totals.columns = [property_name, 'Total Principle Amount Due']
        # df = df.merge(due_totals, on=property_name, how='left')
        # df['Total Principle Amount Due'] = df['Total Principle Amount Due'].fillna(0)

        ## Demand genrated till date
        # Step 1: Filter rows where demand generation date is present and less than today

    ## Calculation (Column formation) 

        df['Agreement value'] = df.groupby(application_booking_id)[amount_due_col].transform('sum')
        
        ## Total payment recived
        filtered_pay_df = df[df[payment_received_col].notnull()]
        property_totals = filtered_pay_df.groupby(application_booking_id)[payment_received_col].sum().reset_index()
        property_totals.columns = [application_booking_id,'Total Payment Received']
        df = df.merge(property_totals, on=application_booking_id, how='left')
        df['Total Payment Received'] = df['Total Payment Received'].fillna(0)


        

        ## Amount due calculation
        filtered_due_df = df[df[demand_gen_col].notna() &(df[demand_gen_col] < today)]
        due_totals = filtered_due_df.groupby(application_booking_id)[amount_due_col].sum().reset_index()
        due_totals.columns = [application_booking_id, 'Total Demand Generated Till Date']
        df = df.merge(due_totals, on=application_booking_id, how='left')
        df['Total Demand Generated Till Date'] = df['Total Demand Generated Till Date'].fillna(0)

        delayed_demand_df = df[df[budgeted_date_col].notna() &(df[budgeted_date_col] <= today) &(df[demand_gen_col].isna())]
        delayed_totals = delayed_demand_df.groupby(application_booking_id)[amount_due_col].sum().reset_index()
        delayed_totals.columns = [application_booking_id, 'Budget Passed, Demand Not Generated']
        df = df.merge(delayed_totals, on=application_booking_id, how='left')
        df['Budget Passed, Demand Not Generated'] = df['Budget Passed, Demand Not Generated'].fillna(0)

        future_demand_df = df[df[budgeted_date_col].notna() &(df[budgeted_date_col] > today) &(df[demand_gen_col].isna())]
        future_total=future_demand_df.groupby(application_booking_id)[amount_due_col].sum().reset_index()
        future_total.columns = [application_booking_id, 'Expected Future Demand']
        df = df.merge(future_total, on=application_booking_id, how='left')
        df['Expected Future Demand'] = df['Expected Future Demand'].fillna(0)

        ## Balance
        # df['Calculated Tax'] = (gst_percentage / 100) * df[amount_due_col]
        # df['Balance'] = 0  # default
        # due_condition = df[budgeted_date_col] < today
        # df.loc[due_condition, 'Balance'] = (
        # df.loc[due_condition, payment_received_col] - 
        # df.loc[due_condition, amount_due_col] - 
        # df.loc[due_condition, 'Calculated Tax']
        #                                                                             )
        # balance_totals = df.groupby(property_name)['Balance'].sum().reset_index()
        # balance_totals.columns = [property_name, 'Outstanding Balance']
        # df = df.merge(balance_totals, on=property_name, how='left')

        # overdue_props = balance_totals[balance_totals['Outstanding Balance'] < 0]


## Net payment recived
        # Filter and calculate
        filtered = df[df[demand_gen_col].notnull()].copy()
        filtered['Net payment received (AV)'] = filtered.apply(
            lambda row: row[payment_received_col] - row[tax] if row[payment_received_col] > row[tax] else 0,
            axis=1
        )
        filtered['Amount Overdue'] = filtered[amount_due_col] - filtered['Net payment received (AV)']
        copy_df=filtered.copy()
        filtered_copy=filtered[filtered['Amount Overdue']>1000]

        overdue_df = filtered.groupby(application_booking_id)[['Net payment received (AV)', 'Amount Overdue']].sum().reset_index()

    
        

        # Merge back to df
        df = df.merge(
            overdue_df[[application_booking_id, 'Net payment received (AV)', 'Amount Overdue']],
            on=application_booking_id,
            how='left'
        )

        df['Amount Overdue'] = df['Amount Overdue'].fillna(0)
        df['Net payment received (AV)'] = df['Net payment received (AV)'].fillna(0)

        overdue=df[df['Amount Overdue']>1000]



        # Step 1: Filter rows where demand is generated and date is before or on today
#         due_df = df[df[demand_gen_col].notna() & (df[demand_gen_col] <= today)]


# # Step 2: Fill blank payment values with 0
#         due_df[payment_received_col] = due_df[payment_received_col].fillna(0)

# # Step 3: Calculate tax
#         due_df['Calculated Tax'] = (gst_percentage / 100) * due_df[amount_due_col]

# # Step 4: Compute balance
#         due_df['Balance'] = (
#         due_df[payment_received_col] -
#         due_df[tax] -
#         due_df[amount_due_col]
#     )

# # Step 5: Aggregate balance by booking ID
#         balance_totals = due_df.groupby(application_booking_id)['Balance'].sum().reset_index()
#         balance_totals.columns = [application_booking_id, 'Outstanding Balance']

# # Step 6: Merge and fill missing balances
#         df = df.merge(balance_totals, on=application_booking_id, how='left')
#         df['Outstanding Balance'] = df['Outstanding Balance'].fillna(0)

# Step 7: Find overdue bookings
        

        # def calc_due_amount(row, today):
        #     due_date = row.get('Budgeted Date', pd.NaT)
        #     if pd.notna(due_date) and pd.to_datetime(today) >= pd.to_datetime(due_date):
        #         return row.get('Total Amount Due', 0)
        #     return 0    
        
        
        # df['Amount Due'] = df.apply(lambda row: calc_due_amount(row, today), axis=1)    

    #--------------------------------------------------------------------------------------------------------------------------------------------------------
    ## Metric to show 

        
        #unit

        # 1. Base filters
        total_units = df[property_name].nunique()
        booked_df = df[df[application_booking_id].notnull()]
        reg_df = booked_df[booked_df[reg_date_col].notnull()]
        unreg_df = booked_df[booked_df[reg_date_col].isnull()]
        


        #unit
        booked_units = booked_df[application_booking_id].nunique()
        reg_units = booked_df[booked_df[reg_date_col].notnull()][application_booking_id].nunique()
        unreg_units = booked_df[booked_df[reg_date_col].isnull()][application_booking_id].nunique()

        # Sales
        total_sales_act = df.groupby(application_booking_id)[total_agreement_col].first().sum()
        reg_sales_act = reg_df.groupby(application_booking_id)[total_agreement_col].first().sum()
        unreg_sales_act = unreg_df.groupby(application_booking_id)[total_agreement_col].first().sum()


        # Sales
        total_saless = df.groupby(application_booking_id)[other_charges].first().sum()
        reg_saless = reg_df.groupby(application_booking_id)[other_charges].first().sum()
        unreg_saless = unreg_df.groupby(application_booking_id)[other_charges].first().sum()

        # Sales
        total_sales = df.groupby(application_booking_id)['Agreement value'].first().sum()
        reg_sales = reg_df.groupby(application_booking_id)['Agreement value'].first().sum()
        unreg_sales = unreg_df.groupby(application_booking_id)['Agreement value'].first().sum()


        #Amount due -
         ## Demand till date
        total_due = filtered_due_df[amount_due_col].sum()
        reg_due = reg_df.groupby(application_booking_id).tail(1)['Total Demand Generated Till Date'].sum()
        unreg_due = unreg_df.groupby(application_booking_id).tail(1)['Total Demand Generated Till Date'].sum()
         ## Demand not genrated 
        total_due_n = delayed_demand_df[amount_due_col].sum()
        reg_due_n = reg_df.groupby(application_booking_id).tail(1)['Budget Passed, Demand Not Generated'].sum()
        unreg_due_n = unreg_df.groupby(application_booking_id).tail(1)['Budget Passed, Demand Not Generated'].sum()
         ## Budgeted is not passed and demand is also not generated
        total_due_nn = future_demand_df[amount_due_col].sum()
        reg_due_nn = reg_df.groupby(application_booking_id).tail(1)['Expected Future Demand'].sum()
        unreg_due_nn = unreg_df.groupby(application_booking_id).tail(1)['Expected Future Demand'].sum()


        # #Amount collected
        # total_collected = filtered_pay_df[payment_received_col].sum()
        # reg_collected = reg_df.groupby(application_booking_id).tail(1)['Total Payment Received'].sum()
        # unreg_collected = unreg_df.groupby(application_booking_id).tail(1)['Total Payment Received'].sum()

        #Amount collected (Without tax)
        total_collected_notax =  df.groupby(application_booking_id).tail(1)['Net payment received (AV)'].sum()
        reg_collected_notax = reg_df.groupby(application_booking_id).tail(1)['Net payment received (AV)'].sum()
        unreg_collected_notax = unreg_df.groupby(application_booking_id).tail(1)['Net payment received (AV)'].sum()


        check_recived= (df[payment_received_col]-df[tax]).sum()


        #Amount overdue
        # Total Overdue: from full overdue set
        total_overdue =  overdue.groupby(application_booking_id).tail(1)['Amount Overdue'].sum()
        reg_overdue = reg_df.groupby(application_booking_id).tail(1)['Amount Overdue'].sum()
        unreg_overdue =unreg_df.groupby(application_booking_id).tail(1)['Amount Overdue'].sum()

        st.dataframe(df)

        uncompleted_milestones = df[df[milestone_status_col] == 0]
        expected_future_collection = uncompleted_milestones['Total Amount Due'].sum()/1e7
  
        col1, col2,= st.columns(2)

        col1.metric(label="Total Units", value=total_units)
        col2.metric(
            label="Expected Future Total Collection",
            value=f"₹{expected_future_collection:,.2f} Cr",
            help="This is the total amount due from all milestones that are not yet marked as completed."
    )
        # Build dataframe
        summary_df = {
            "Metric": [
                "Total Units Booked",
                "Total Agreement Value",
                "Corpus+Maintenance",
                "Total Agreement Value (Added Corpus+Maintenance)",
                "Total Agreement Value (Sum of All Dues)",
                "Total Demand Till Date",
                "Budgeted Passed, Demand Not Raised",
                "Expected Future Demand",
                "Amount Collected (Without TAX)",
                "Amount Overdue"
            ],
            "All Units": [
                booked_units,
                f"₹{float(total_sales_act)/1e7:,.2f} Cr",
                f"₹{float(total_saless)/1e7:,.2f} Cr",
                f"₹{(float(total_sales_act + total_saless)) / 1e7:,.2f} Cr",
                f"₹ {float(total_sales) / 1e7:,.2f} Cr",
                
                percent(total_due, total_sales),
                percent(total_due_n, total_sales),
                percent(total_due_nn, total_sales),

                percent(total_collected_notax, total_sales),
                percent(total_overdue, total_sales)
            ],
            "Registered Users": [
                reg_units,
                f"₹ {float(reg_sales_act)/1e7:,.2f} Cr",
                f"₹ {float(reg_saless)/1e7:,.2f} Cr",
                f"₹ {(float(reg_sales_act + reg_saless))/ 1e7:,.2f} Cr",
                f"₹ {float(reg_sales) / 1e7:,.2f} Cr",
                
                percent(reg_due, reg_sales),
                percent(reg_due_n, reg_sales),
                percent(reg_due_nn, reg_sales),

                percent(reg_collected_notax, reg_sales),
                percent(reg_overdue, reg_sales)
            ],
            "Unregistered Users": [
                unreg_units,
                f"₹ {float(unreg_sales_act)/1e7:,.2f} Cr",
                f"₹ {float(unreg_saless)/1e7:,.2f} Cr",
                f"₹ {float(unreg_sales_act + unreg_saless)/ 1e7:,.2f} Cr",
                f"₹ {float(unreg_sales) / 1e7:,.2f} Cr",
                
                percent(unreg_due, unreg_sales),
                percent(unreg_due_n, unreg_sales),
                percent(unreg_due_nn, unreg_sales),

                percent(unreg_collected_notax, unreg_sales),
                percent(unreg_overdue, unreg_sales)
            ]
        }
        # Convert to DataFrame
        summary_df = pd.DataFrame(summary_df)
        styled_df = summary_df.style \
    .apply(highlight_rows, axis=1) \
    .set_properties(**{
        'text-align': 'center',
        'font-size': '16px'
    }) \
    .set_table_styles([
        dict(selector='th', props=[
            ('background-color', '#f0f0f5'),
            ('color', '#333'),
            ('font-weight', 'bold')
        ])
    ])

# Display the styled dataframe
        st.dataframe(styled_df, use_container_width=True)
        col1, col2 = st.columns([1.2, 1.2])
        with col1:
            booked_df['Registration Status'] = booked_df[reg_date_col].notna().map({
            True: 'Registered',
            False: 'Not Registered'
})

# Step 3: Drop duplicates to count each unit only once (if needed)
            unit_status = booked_df.drop_duplicates(subset=[application_booking_id])

# Step 5: Get counts per status
            reg_summary = unit_status['Registration Status'].value_counts().reset_index()
            reg_summary.columns = ['Registration Status', 'Count']
    # Step : Create the pie chart
            fig1 = px.pie(reg_summary, names='Registration Status', values='Count', 
            title='Registration Status of Units', hole=0.4)
            st.plotly_chart(fig1, use_container_width=True)
        # filtered_df_due = df[df[demand_gen_col] <= today]

        with col2:
            labels = ['Amount Collected (Without Tax)', 'Amount Overdue']
            values = [total_collected_notax, total_overdue]

            dff = pd.DataFrame({'Status': labels, 'Amount (Cr)': values})

            # Pie chart
            fig2 = px.pie(dff, names='Status', values='Amount (Cr)', title='Collection Due vs Not Due', hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------



        bucket_order = ['< 30 Days', '31 - 60 Days', '61 - 90 Days', '> 90 Days']


        st.subheader("⏳ Ageing Analysis")
        col5, col6 , col7= st.columns(3)
        with col5:
            st.markdown("**Unregistered User Ageing (Days Since Booking)**")
            unreg_df.loc[:,'days_since_booking'] = (today - unreg_df[booking_col]).dt.days
            unreg_df.loc[:,'booking_age_bucket'] = unreg_df['days_since_booking'].apply(bucket)     
            bucket_counts  = (
                    unreg_df
        .groupby('booking_age_bucket')[application_booking_id]  # or 'Customer ID'
        .nunique()
        .reindex(bucket_order, fill_value=0)
        .reset_index()
                                        )
            bucket_counts.columns = ['Ageing Bucket', 'User Count']
            st.dataframe(bucket_counts, use_container_width=True)
            st.bar_chart(bucket_counts.set_index('Ageing Bucket'))
        with col6:
            st.markdown("**Registered User TAT (Booking to Registration)**")
            reg_df.loc[:,'tat_days'] = (reg_df[reg_date_col] - reg_df[booking_col]).dt.days
            reg_df.loc[:,'tat_bucket'] = reg_df['tat_days'].apply(bucket)
            bucket_counts_registered = (
        reg_df
        .groupby('tat_bucket')[property_name]  # or 'Customer ID'
        .nunique()
        .reindex(bucket_order, fill_value=0)
        .reset_index()
    )
           

            bucket_counts_registered.columns = ['TAT Bucket', 'User Count']
            st.dataframe(bucket_counts_registered, use_container_width=True)
            st.bar_chart(bucket_counts_registered.set_index('TAT Bucket'))

        with col7:
            st.markdown("**Overdue Ageing**")
            filtered['overdue_days'] = (today - (filtered[demand_gen_col] + pd.to_timedelta(15, unit='D'))).dt.days
            filtered['overdue_bucket'] = filtered['overdue_days'].apply(bucket)

            bucket_summary = filtered.groupby('overdue_bucket')['Amount Overdue'].sum().reindex(bucket_order).fillna(0).reset_index()
            bucket_summary['Amount Overdue'] = bucket_summary['Amount Overdue'] /1e7
            bucket_summary.columns = ['Overdue Bucket', 'Total Overdue Amount']
            st.dataframe(bucket_summary, use_container_width=True)
            st.bar_chart(bucket_summary.set_index('Overdue Bucket'))




    #--------------------------------------------------------------------------------------------------------------------------------------------------------------

        copy_df['Month'] = copy_df[actual_payment_col].dt.to_period("M").astype(str)
        copy_df['Month'] = pd.to_datetime(copy_df['Month'])  # Convert to datetime for filtering
        two_years_ago = pd.to_datetime(today) - pd.DateOffset(years=2)
        filtered_df = copy_df[copy_df['Month'] >= two_years_ago]

        # Group and summarize
        monthly_summary = (
            filtered_df.groupby('Month')['Net payment received (AV)']
            .sum()
            .reset_index()
        )
        monthly_summary['Net payment received (AV)'] = monthly_summary['Net payment received (AV)'] / 1e7  # ₹ Cr

        # Format for display
        monthly_summary['Month_str'] = monthly_summary['Month'].dt.strftime('%b %Y')

        # Plot with px.bar
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

        # Optional full table
        with st.expander("📄 View Full Table"):
            full_table = copy_df.groupby('Month')['Net payment received (AV)'].sum().reset_index()
            full_table['Net payment received (AV)'] = full_table['Net payment received (AV)'] / 1e7
            full_table['Month'] = full_table['Month'].dt.strftime('%b %Y')
            full_table = full_table.rename(columns={'Net payment received (AV)': "Actual Collection (₹ Cr)"})
            st.dataframe(full_table, use_container_width=True)


    #--------------------------------------------------------------------------------------------------------------------------------------------------------------

    #     st.subheader("📅 Expected Previous Monthly Collection [Monthly Due History (till now)]")
    #     df['Due Month'] = df[demand_gen_col].dt.to_period("M").astype(str)
    #     df['Due Month'] = pd.to_datetime(df['Due Month'])
    #     old_dues = df[df['Due Month'] < today]
    #     due_summary = old_dues.groupby('Due Month')[amount_due_col].sum().reset_index()
    #     due_summary.columns = ['Month', 'Expected Due']
    #     due_summary['Expected Due'] = due_summary['Expected Due'] /1e7
    #     # Format month for better display
    #     two_years_ago = pd.to_datetime(today) - pd.DateOffset(years=2)
    #     due_summary['Month'] = pd.to_datetime(due_summary['Month'])
    #     plot_data = due_summary[due_summary['Month'] >= two_years_ago].sort_values(by='Month')
    #     plot_data.set_index('Month', inplace=True)

    #     fig = px.bar(
    #     plot_data.reset_index(),
    #     x='Month',
    #     y='Expected Due',
    #     title="Expected Previous Monthly Collection (₹ Cr)",
    #     labels={'Month': 'Month', 'Expected Due (₹ Cr)': 'Amount (₹ Cr)'},
    #     text='Expected Due'
    # )
    #     fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    #     fig.update_layout(xaxis_tickangle=-90)
    #     st.plotly_chart(fig, use_container_width=True)
        
    #     with st.expander('📄 View Full Table'):
    #         due_summary = due_summary.rename(columns={"Expected Due": "Expected Due (₹ Cr)"})
    #         st.dataframe(due_summary)

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------

        st.markdown("""
            ### 📅 Expected Future Total Collection
            <small>
            <sup>ℹ️</sup> 
            <span title="This table shows how much money is expected to be collected from customers in the upcoming months, based on the Budgeted Date (planned date for raising payment demand). Only future dates are included, and amounts are grouped month-wise in ₹ Lakhs.">
            <em>What does this mean?</em></span>
            </small>
            """, unsafe_allow_html=True)

        # Step 1: Create Due Month from Budgeted Date
        future_demand_df['Due Month'] = future_demand_df[budgeted_date_col].dt.to_period("M").astype(str)
        future_demand_df['Due Month'] = pd.to_datetime(future_demand_df['Due Month'], errors='coerce')

        today_month = pd.to_datetime(today).replace(day=1)

        # Step 2: Filter future dates
        future_dues = future_demand_df[future_demand_df['Due Month'] >= today_month]

        # Step 3: Group and compute expected amount in Cr
        monthly_due = future_dues.groupby('Due Month')[amount_due_col].sum().reset_index()
        monthly_due['Expected Due (₹ Cr)'] = monthly_due[amount_due_col] / 1e7
        monthly_due.drop(columns='Total Amount Due', inplace=True)

        # Step 4: Rename and format Month
        monthly_due = monthly_due.rename(columns={'Due Month': 'Month_dt'})
        monthly_due['Month'] = monthly_due['Month_dt'].dt.strftime('%b %Y')
        monthly_due = monthly_due.sort_values(by='Month_dt')
        monthly_due.set_index('Month', inplace=True)
        
        fig = px.bar(
        monthly_due.reset_index(),
        x='Month',
        y='Expected Due (₹ Cr)',
        title="Expected Future Total Collection (₹ Cr)",
        labels={'Month': 'Month', 'Expected Due (₹ Cr)': 'Amount (₹ Cr)'},
        text='Expected Due (₹ Cr)'
    )
        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig.update_layout(xaxis_tickangle=-90)

        st.plotly_chart(fig, use_container_width=True)

        # Step 6: Show full table
        with st.expander('📄 View Full Table'):
            st.dataframe(monthly_due.reset_index())


    #--------------------------------------------------------------------------------------------------------------------------------------------------------------

        with st.expander("📄 View Full Project Dataset"):
                st.dataframe(df, use_container_width=True)