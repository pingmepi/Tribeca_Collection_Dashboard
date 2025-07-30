# import requests
# import pandas as pd
# import streamlit as st

# def get_salesforce_report(sf, report_id):
#     try:
#         headers = {
#             'Authorization': f"Bearer {sf.session_id}",
#             'Content-Type': 'application/json'
#         }
#         url = f"{sf.base_url}analytics/reports/{report_id}?includeDetails=true"
#         response = requests.get(url, headers=headers)

#         if response.status_code != 200:
#             st.error(f"❌ Report fetch failed: {response.status_code} - {response.text}")
#             return pd.DataFrame()

#         report_data = response.json()
#         fact_map = report_data.get("factMap", {})
#         all_rows = []

#         for key, section in fact_map.items():
#             if key == "T!T":
#                 continue
#             rows = section.get("rows", [])
#             for row in rows:
#                 row_data = [cell.get("label", '') for cell in row.get("dataCells", [])]
#                 all_rows.append(row_data)

#         column_metadata = report_data.get("reportMetadata", {}).get("detailColumns", [])
#         column_info = report_data.get("reportExtendedMetadata", {}).get("detailColumnInfo", {})
#         column_labels = [
#             column_info.get(col, {}).get("label", col)
#             for col in column_metadata
#         ]

#         return pd.DataFrame(all_rows, columns=column_labels)

#     except Exception as e:
#         st.error(f"❌ Error fetching Salesforce report: {e}")
#         return pd.DataFrame()


import requests
import pandas as pd
import streamlit as st

def get_salesforce_report(sf, report_id):
    try:
        headers = {
            'Authorization': f"Bearer {sf.session_id}",
            'Content-Type': 'application/json'
        }

        base_url = f"{sf.base_url}analytics/reports/{report_id}?includeDetails=true"
        all_rows = []
        first_response = requests.get(base_url, headers=headers)

        if first_response.status_code != 200:
            st.error(f"❌ Initial report fetch failed: {first_response.status_code} - {first_response.text}")
            return pd.DataFrame()

        # Parse first page
        response_data = first_response.json()
        all_rows += extract_rows(response_data)

        # Extract column labels
        column_metadata = response_data.get("reportMetadata", {}).get("detailColumns", [])
        column_info = response_data.get("reportExtendedMetadata", {}).get("detailColumnInfo", {})
        column_labels = [column_info.get(col, {}).get("label", col) for col in column_metadata]

        # Handle pagination
        next_page_url = response_data.get("nextPageUrl")
        while next_page_url:
            paged_url = f"{sf.base_url.rstrip('/')}{next_page_url}"
            response = requests.get(paged_url, headers=headers)
            if response.status_code != 200:
                st.warning(f"⚠️ Pagination fetch failed: {response.status_code} - {response.text}")
                break

            response_data = response.json()
            all_rows += extract_rows(response_data)
            next_page_url = response_data.get("nextPageUrl")

        return pd.DataFrame(all_rows, columns=column_labels)

    except Exception as e:
        st.error(f"❌ Error fetching Salesforce report: {e}")
        return pd.DataFrame()

def extract_rows(response_data):
    """Extracts data rows from a Salesforce report response"""
    rows = []
    fact_map = response_data.get("factMap", {})
    for key, section in fact_map.items():
        if key == "T!T":
            continue
        for row in section.get("rows", []):
            row_data = [cell.get("label", '') for cell in row.get("dataCells", [])]
            rows.append(row_data)
    return rows
