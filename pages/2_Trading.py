import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import plotly.express as px
from shares.config import API_URL, USER_ID, PORTEFEUILLES
from shares.connexion_function import logout

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("Veuillez vous connecter sur la page d'accueil.")
    st.stop()
else:
    st.sidebar.success(f"Connecté : {st.session_state['username']}")
    if st.sidebar.button("👆 Déconnexion"):
        logout()

def get_actions():
    return requests.get(f"{API_URL}/actions/").json()

def post_transaction(data):
    return requests.post(f"{API_URL}/transactions/", json=data)


st.title("🚀 Terminal de Trading")
tab1, tab2 = st.tabs(["📊 Historique transaction", "📈 Faire une transaction"])

with tab1:
    # --- SECTION 3 : HISTORIQUE ---
    portefeuille_map = {p["nom_portefeuille"]: p["id"] for p in PORTEFEUILLES}
    with st.form("get_data_form"):
        nom_selectionne = st.selectbox("Choisir un portefeuille", options=portefeuille_map.keys())
        portefeuille_id = portefeuille_map[nom_selectionne] if nom_selectionne else 1
        submit = st.form_submit_button("👆 Afficher l'analyse")
        
        if submit:
                try:
                    st.write(f"Portefeuille sélectionné : {nom_selectionne} (ID: {portefeuille_id})")
                    # 1. Récupération des données via l'API
                    @st.cache_data(ttl=60) # Cache pour éviter de surcharger l'API
                    def fetch_all_data():
                        trans = requests.get(f"{API_URL}/portefeuille/{portefeuille_id}/transactions").json()
                        stocks = requests.get(f"{API_URL}/actions/").json()
                        market = requests.get(f"{API_URL}/transactions/").json()
                        return pd.DataFrame(trans), pd.DataFrame(stocks), pd.DataFrame(market)

                    df_t, df_stocks, df_market = fetch_all_data()
                    st.write(f"Données récupérées : {len(df_t)} transactions, {len(df_stocks)} actions.")
                    if not df_t.empty and not df_stocks.empty:
                        
                        # --- CALCUL DU PORTFOLIO ---
                        df_t["type_transaction"] = df_t["type_transaction"].str.strip().str.lower()
                        # A. Calcul du CMP par action
                        df_buys = df_t[df_t['type_transaction'] == 'achat'].copy()
                        
                        df_buys['total_cost'] = df_buys['quantite'] * df_buys['prix_unitaire'] + df_buys['frais_courtage']
                        
                        # Agrégation par stock
                        portfolio = df_buys.groupby('action_id').agg({
                            'quantite': 'sum',
                            'total_cost': 'sum'
                        }).reset_index()

                        portfolio['CMP'] = portfolio['total_cost'] / portfolio['quantite']
                        
                        # B. Ajustement avec les ventes (pour la quantité actuelle)
                        df_sells = df_t[df_t['type_transaction'] == 'vente']
                        if not df_sells.empty:
                            sell_qty = df_sells.groupby('action_id')['quantite'].sum().reset_index()
                            portfolio = portfolio.merge(sell_qty, on='action_id', how='left', suffixes=('', '_sold'))
                            portfolio['quantity_sold'] = portfolio['quantite_sold'].fillna(0)
                            portfolio['current_qty'] = portfolio['quantite'] - portfolio['quantity_sold']
                        else:
                            portfolio['current_qty'] = portfolio['quantite']

                        # Filtrer les lignes où on ne possède plus d'actions
                        portfolio = portfolio[portfolio['current_qty'] > 0]

                        dernier_cours = df_stocks.sort_values('date_mise_a_jour').drop_duplicates(subset=['id'], keep='last')
                        df_market = dernier_cours[['id', 'dernier_cours']]
                        portfolio['dernier_cours'] = portfolio['action_id'].map(df_market.set_index('id')['dernier_cours'])
                        portfolio['benefice_potentiel'] = (portfolio['dernier_cours']* portfolio['current_qty'] - portfolio['CMP']) * portfolio['current_qty']
                        # C. Fusion avec Market Data et Stocks
                        portfolio.rename(columns={'action_id': 'id'}, inplace=True)
                        portfolio = portfolio.merge(df_stocks[['id', 'symbole', 'nom_entreprise']], on='id')
                        
                        # D. Calcul de la Plus-value
                        portfolio['Valeur Actuelle'] = portfolio['current_qty'] * portfolio['dernier_cours']
                        portfolio['Investissement'] = portfolio['current_qty'] * portfolio['CMP']
                        portfolio['+/- Value'] = portfolio['Valeur Actuelle'] - portfolio['Investissement']
                        portfolio['+/- %'] = (portfolio['+/- Value'] / portfolio['Investissement']) * 100

                        # --- AFFICHAGE ---
                    
                        st.divider()
                       

                        ## titre historique transactions
                        st.title("📜 Historique des Transactions")
                        # df_t=df_t[['action_id', 'type_transaction', 'quantite', 'prix_unitaire', 'frais_courtage', 'date_transaction']]
                        df_stocks.rename(columns={ 'id': 'action_id'}, inplace=True)
                        df_t = df_t.merge(df_stocks[['action_id', 'symbole', 'nom_entreprise']], how='inner', on='action_id')
                        
                        df_final = df_t[[
                            'symbole', 'nom_entreprise', 'type_transaction', 'quantite', 'prix_unitaire', 'frais_courtage', 'date_transaction'
                        ]].copy()

                        # Renommer les colonnes
                        df_final.columns = ['Symbole', 'Société', 'Type Transaction', 'Quantité', 'Prix Unit.', 'Frais Courtage', 'Date Transaction']
                        
                        st.dataframe(df_final.sort_values(by='Date Transaction', ascending=False), use_container_width=True, hide_index=True)
                        
                    else:
                        st.info("Effectuez votre première transaction pour voir l'analyse.")
                    # Ici, tu peux ajouter du code pour récupérer et afficher les données spécifiques au portefeuille sélectionné

                except Exception as e:
                    st.error(f"Erreur lors de la sélection du portefeuille.{str(e)}")


with tab2:
    stocks = get_actions()
    
    stock_options = {s['symbole']: s['id'] for s in stocks}
    selected_stock_sym = st.selectbox("Action", list(stock_options.keys()))
    type_ordre = st.selectbox("Type", ["achat", "appro","retrait", "vente"])
    quantite = st.number_input("Quantité", min_value=1, value=1)
    prix = st.number_input("Prix unitaire (XOF)", min_value=1.0, value=1500.0)
    frais_courtage = st.number_input("Frais de courtage (XOF 1%)", min_value=0.0, value=prix * quantite * 0.01 )
    if st.button("👆 Valider l'ordre"):
        payload = {
            # "id": 11,
            "portefeuille_id": portefeuille_id,
            "action_id": stock_options[selected_stock_sym],
            "type_transaction": type_ordre.lower(),
            "quantite": quantite,
            "prix_unitaire": prix,
            "frais_courtage": frais_courtage, # Simulation de 1% de frais
            "date_transaction": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        res = post_transaction(payload)
        if res.status_code == 200:
            st.success("Ordre exécuté !")
            selected_stock_sym = ""
            type_ordre = "achat"
            quantite = 1
            prix = 00.0
            frais_courtage = 0.0
            st.rerun()
        else:
            st.error(f"Erreur: {res.json().get('detail')}")

# ... (Insère ici ton code de formulaire POST /transactions/)