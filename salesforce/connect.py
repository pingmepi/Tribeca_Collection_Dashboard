import streamlit as st
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from requests.exceptions import RequestException

@st.cache_resource(show_spinner=False)
def connect_to_salesforce():
    try:
        creds = st.secrets["salesforce"]
        sf = Salesforce(
            username=creds["username"],
            password=creds["password"],
            security_token=creds["security_token"],
            domain=creds.get("domain", "login")
        )
        return sf
    except SalesforceAuthenticationFailed:
        st.error("❌ Invalid Salesforce credentials or token.")
        st.stop()
    except RequestException:
        st.error("❌ Network error while connecting to Salesforce.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        st.stop()
