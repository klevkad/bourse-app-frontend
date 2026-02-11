import streamlit as st
from shares.connexion_function import login, logout

st.set_page_config(page_title="Authentification BRVM", layout="wide", initial_sidebar_state="expanded", page_icon="🏦", )

# Vérification de l'état de connexion
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    login()
    # On cache les autres pages en mode Sidebar si pas connecté
    st.markdown("<style>ul[data-testid='main-menu-list'] {display: none;}</style>", unsafe_allow_html=True)
else:
    st.sidebar.success(f"Connecté : {st.session_state['username']}")
    if st.sidebar.button("Déconnexion"):
        logout()
    st.title("🏠 Accueil Portefeuille")
    st.write(f"Bonjour **{st.session_state['username']}**, utilisez le menu à gauche pour piloter vos investissements.")
    # st.info("Sélectionnez 'Dashboard' pour voir vos gains ou 'Trading' pour passer des ordres.")
    st.sidebar.markdown("### Menu")
    portefeuille_list = st.session_state["portefeuilles"] if "portefeuilles" in st.session_state else []
    portefeuille_map = {p["nom_portefeuille"]: p["id"] for p in portefeuille_list}
    # with st.sidebar.form("get_data_form"):
    nom_selectionne = st.selectbox("Choisir un portefeuille", options=portefeuille_map.keys())
    portefeuille_id = portefeuille_map[nom_selectionne] if nom_selectionne else None
    st.session_state["portefeuille_id"] = portefeuille_id
    st.session_state['nom_selectionne'] = nom_selectionne
    
        # submit = st.form_submit_button("👆 Afficher l'analyse")

