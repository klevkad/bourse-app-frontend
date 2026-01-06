import streamlit as st
import requests
from shares.config import API_URL

def login():
    st.title("🔐 Connexion Investisseur")
    
    with st.form("login_form"):
        user_id = st.number_input("Entrez votre ID Utilisateur (ex: 1)", min_value=1, step=1)
        submit = st.form_submit_button("Se connecter")
        
        if submit:
            try:
                response = requests.get(f"{API_URL}/users/{user_id}")
                if response.status_code == 200:
                    user_data = response.json()
                    # Sauvegarde de la session
                    st.session_state["authenticated"] = True
                    st.session_state["user_id"] = user_id
                    st.session_state["username"] = user_data["username"]
                    st.success(f"Bienvenue {user_data['username']} !")
                    st.rerun()
                else:
                    st.error("ID inconnu. Veuillez vérifier votre identifiant.")
            except Exception as e:
                st.error("L'API ne répond pas. Lancez uvicorn !")

def logout():
    st.session_state["authenticated"] = False
    st.rerun()