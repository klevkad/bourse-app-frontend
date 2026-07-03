import streamlit as st
import requests
from shares.config import API_URL


def login():
    st.title("🔐 Connexion Investisseur")
    
    with st.form("login_form"):
        user_email = st.text_input("Entrez votre email (ex: utilisateur@example.com)")
        user_password = st.text_input("Entrez votre mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")
         
        if submit:
            if not user_email or not user_password:
                st.warning("Veuillez remplir tous les champs.")
                return

            try:
                # Envoi des données en JSON (parfaitement compatible avec le LoginRequest de FastAPI ci-dessus)
                response = requests.post(
                    f"{API_URL}/users/login", 
                    json={"email": user_email, "password": user_password}
                )
                st.write(f"Réponse de l'API : {response}")  # Debugging line
                if response.status_code == 200:
                    user_data = response.json()
                    
                    # Sauvegarde de la session de l'investisseur
                    st.session_state["authenticated"] = True
                    st.session_state["user_id"] = user_data["id"]
                    st.session_state["username"] = user_data["nom_utilisateur"]
                    st.session_state["portefeuilles"] = user_data.get("portefeuilles", [])
                    
                    st.success(f"Bienvenue {user_data['nom_utilisateur']} !")
                    st.rerun()
                elif response.status_code == 401 or response.status_code == 404:
                    st.error("Email ou mot de passe incorrect.")
                else:
                    st.error(f"Une erreur est survenue (Code : {response.status_code})")
                    
            except requests.exceptions.ConnectionError:
                st.error("L'API ne répond pas. Veuillez lancer le serveur Uvicorn !")
            except Exception as e:
                st.error(f"Erreur inattendue : {str(e)}")

def logout():
    st.session_state["authenticated"] = False
    st.session_state["user_id"] = None
    st.session_state["username"] = ""   
    st.session_state["portefeuilles"] = []
    st.rerun()