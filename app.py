import streamlit as st
from shares.connexion_function import login, logout

# 1. Configuration de la page
st.set_page_config(
    page_title="Authentification BRVM", 
    layout="wide", 
    initial_sidebar_state="expanded", 
    page_icon="🏦"
)

# 2. FIX : Initialisation sécurisée du Session State au démarrage
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = "" 
if "portefeuilles" not in st.session_state:
    st.session_state["portefeuilles"] = []

# 3. Contenu de la page d'accueil
def afficher_accueil():
    st.title("🏠 Accueil Portefeuille")
    
    # Sécurité supplémentaire avec .get() et une valeur par défaut
    username = st.session_state.get("username", "Utilisateur")
    st.write(f"Bonjour **{username}**, utilisez le menu à gauche pour piloter vos investissements.")
    
    portefeuille_list = st.session_state.get("portefeuilles", [])
    portefeuille_map = {p["nom_portefeuille"]: p["id"] for p in portefeuille_list if "nom_portefeuille" in p}
    
    if portefeuille_map:
        nom_selectionne = st.selectbox("Choisir un portefeuille", options=list(portefeuille_map.keys()))
        st.session_state["portefeuille_id"] = portefeuille_map[nom_selectionne]
        st.session_state['nom_selectionne'] = nom_selectionne
    else:
        st.info("Aucun portefeuille trouvé pour ce compte.")

# 4. Déclaration des pages pour la navigation
page_accueil = st.Page(afficher_accueil, title="Accueil", icon="🏠")
page_dashboard = st.Page("pages/Dashboard.py", title="Dashboard", icon="📊")
page_trading = st.Page("pages/Trading.py", title="Trading", icon="📈")

# 5. Logique de Navigation et Affichage
if not st.session_state["authenticated"]:
    # Mode Non Connecté
    pg = st.navigation([page_accueil], position="hidden")
    login()
else:
    # Mode Connecté
    pg = st.navigation([page_accueil, page_dashboard, page_trading], position="hidden")
    
    # --- SÉQUENCE DU SIDEBAR (Le bloc de connexion est bien EN HAUT) ---
    st.sidebar.success(f"Connecté : {st.session_state.get('username', 'Utilisateur')}")
    if st.sidebar.button("Déconnexion"):
        logout()
        st.rerun()
        
    st.sidebar.markdown("---") 
    
    # Menu de navigation
    st.sidebar.markdown("### Menu")
    st.sidebar.page_link(page_accueil)
    st.sidebar.page_link(page_dashboard)
    st.sidebar.page_link(page_trading)

# 6. Exécution de la page active
pg.run() 