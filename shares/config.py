import streamlit as st
API_URL = "https://bourse-app-backend.onrender.com"
USER_ID = st.session_state["user_id"] if "user_id" in st.session_state else 1
PORTEFEUILLES = st.session_state["portefeuilles"] if "portefeuilles" in st.session_state else []
