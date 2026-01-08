import streamlit as st
import requests
import pandas as pd
import plotly.express as px
# from ..connexion_function import login, logout
from shares.config import API_URL, USER_ID, PORTEFEUILLES
from shares.connexion_function import logout

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("Veuillez vous connecter sur la page d'accueil.")
    st.stop()
else:
    st.sidebar.success(f"Connecté : {st.session_state['username']}")
    if st.sidebar.button("Déconnexion"):
        logout()
user_id = USER_ID

st.title("📊 Analyse générale du Portefeuille")

portefeuille_map = {p["nom_portefeuille"]: p["id"] for p in PORTEFEUILLES}
st.write("Sélectionnez un portefeuille pour afficher son analyse détaillée.")
with st.form("login_form"):
    nom_selectionne = st.selectbox("Choisir un portefeuille", options=portefeuille_map.keys())
    portefeuille_id = portefeuille_map[nom_selectionne]
    submit = st.form_submit_button("Afficher l'analyse")
    
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
                    # A. Calcul de la quantité nette et du CMP
                    # On filtre sur les achats pour le CMP
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
                    # st.write(df_buys.head())
                    # st.write(df_sells.head())
                    if not df_sells.empty:
                        sell_qty = df_sells.groupby('action_id')['quantite'].sum().reset_index()
                        portfolio = portfolio.merge(sell_qty, on='action_id', how='left', suffixes=('', '_sold'))
                        # st.write(portfolio.head())
                        # certain portfolio['quantite_sold'] peuvent être None si vente inexistante
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
                    
                   
                    
                    
                   
                   # Métriques globales
                    total_pv = portfolio['+/- Value'].sum()
                    st.divider()
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Plus-Value Totale", f"{total_pv:,.0f} XOF", delta=f"{total_pv:,.0f}")
                    col2.metric("Valeur Totale Portfolio", f"{portfolio['Valeur Actuelle'].sum():,.0f} XOF")
                    fig = px.pie(portfolio, values='current_qty', names='symbole', title="Répartition des titres", hole=0.4)
                #         st.plotly_chart(fig, use_container_width=True)
                    col3.markdown("#### Répartition des Titres")
                    col3.plotly_chart(fig, use_container_width=True)

                    st.divider()
                     # Nettoyage des colonnes pour l'utilisateur
                    df_final = portfolio[[
                        'symbole', 'nom_entreprise', 'current_qty', 'CMP', 
                        'dernier_cours', '+/- Value', '+/- %'
                    ]].copy()

                    # Renommer les colonnes
                    df_final.columns = ['Symbole', 'Société', 'Qté', 'CMP (XOF)', 'Prix Marché', 'Plus-Value Abs.', 'Plus-Value %']

                    # Formatage et coloration
                    def style_plus_value(val):
                        color = 'green' if val > 0 else 'red'
                        return f'color: {color}; font-weight: bold'
                    # Portefeuille titres détenus
                    st.title("📈 Analyse du Portefeuille")
                    st.dataframe(
                        df_final.style.format({
                            'CMP (XOF)': '{:,.0f}',
                            'Prix Marché': '{:,.0f}',
                            'Plus-Value Abs.': '{:,.0f}',
                            'Plus-Value %': '{:,.2f}%'
                        }).applymap(style_plus_value, subset=['Plus-Value Abs.', 'Plus-Value %']),
                        use_container_width=True,
                        hide_index=True
                    )
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


# # Récupérer les transactions pour calculer le portefeuille
# trans_res = requests.get(f"{API_URL}/users/{USER_ID}/transactions")
# if trans_res.status_code == 200 and trans_res.json():
#     df_t = pd.DataFrame(trans_res.json())
    
#     # Calculer les quantités nettes par action
#     df_t['qty_signed'] = df_t.apply(lambda x: x['quantity'] if x['transaction_type'] == 'buy' else -x['quantity'], axis=1)
#     portfolio = df_t.groupby('stock_id')['qty_signed'].sum().reset_index()
#     portfolio = portfolio[portfolio['qty_signed'] > 0] # Garder seulement ce qu'on possède
    
#     # Fusionner avec les noms des stocks
#     stocks_df = pd.DataFrame(stocks)
#     portfolio = portfolio.merge(stocks_df, on='stock_id')
    
#     # Affichage
#     col1, col2 = st.columns([2, 1])
    
#     with col1:
#         st.dataframe(portfolio[['symbol', 'company_name', 'qty_signed', 'sector']], use_container_width=True)
    
#     with col2:
#         fig = px.pie(portfolio, values='qty_signed', names='symbol', title="Répartition des titres", hole=0.4)
#         st.plotly_chart(fig, use_container_width=True)
# else:
#     st.info("Aucune transaction enregistrée pour le moment.")


# # Vérification de l'état de connexion
# # if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
# #     login()
# #     # On cache les autres pages en mode Sidebar si pas connecté
# #     st.markdown("<style>ul[data-testid='main-menu-list'] {display: none;}</style>", unsafe_allow_html=True)
# # else:
# #     st.sidebar.success(f"Connecté : {st.session_state['username']}")
# #     if st.sidebar.button("Déconnexion"):
# #         logout()
    
# #     st.title("🏠 Accueil Portefeuille")
# #     st.write(f"Bonjour **{st.session_state['username']}**, utilisez le menu à gauche pour piloter vos investissements.")
# #     st.info("Sélectionnez 'Dashboard' pour voir vos gains ou 'Trading' pour passer des ordres.")
# # Récupérer les données via API en utilisant st.session_state["user_id"]
# # ... (Insère ici ton code de graphiques précédent)
