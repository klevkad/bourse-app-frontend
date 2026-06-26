import streamlit as st
import requests
from shares.config import API_URL

def login():
    st.title("🔐 Connexion Investisseur")
    
    with st.form("login_form"):
        # user_id = st.number_input("Entrez votre ID Utilisateur (ex: 1)", min_value=1, step=1)
        user_email = st.text_input("Entrez votre email (ex: utilisateur@example.com)")
        user_password = st.text_input("Entrez votre mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")
         
        if submit:
            try:
                response = requests.get(f"{API_URL}/users/login", params={"email": user_email, "password": user_password})
                if response.status_code == 200:
                    user_data = response.json()
                    # Sauvegarde de la session
                    st.session_state["authenticated"] = True
                    st.session_state["user_id"] = user_data["id"]
                    st.session_state["username"] = user_data["nom_utilisateur"]
                    st.session_state["portefeuilles"] = user_data["portefeuilles"]
                    st.success(f"Bienvenue {user_data['nom_utilisateur']} !")
                    st.rerun()
                else:
                    st.error("Email ou mot de passe incorrect.")
            except Exception as e:
                st.error("L'API ne répond pas. Lancez uvicorn !")

def logout():
    st.session_state["authenticated"] = False
    st.rerun()