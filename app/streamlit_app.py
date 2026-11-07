"""ClaimLens entry point:  streamlit run app/streamlit_app.py"""
import streamlit as st

st.set_page_config(page_title="ClaimLens: claims analytics and payment integrity", page_icon="🩺", layout="wide",
                   initial_sidebar_state="expanded")

st.navigation([
    st.Page("views/overview.py", title="Overview", default=True),
    st.Page("views/cost_drivers.py", title="Cost drivers"),
    st.Page("views/utilization_quality.py", title="Utilization and quality"),
    st.Page("views/pharmacy.py", title="Pharmacy"),
    st.Page("views/payment_integrity.py", title="Payment integrity"),
    st.Page("views/method.py", title="Method and data"),
]).run()
