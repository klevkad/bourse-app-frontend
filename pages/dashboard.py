import streamlit as st
import requests
import pandas as pd
import plotly.express as px
# from ..connexion_function import login, logout
from shares.config import API_URL, USER_ID
from shares.connexion_function import logout

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("Veuillez vous connecter sur la page d'accueil.")
    st.stop()
else:
    st.sidebar.success(f"Connecté : {st.session_state['username']}")
    if st.sidebar.button("Déconnexion"):
        logout()
user_id = USER_ID

st.title("📊 Analyse Détaillée du Portefeuille")

# 1. Récupération des données via l'API
@st.cache_data(ttl=60) # Cache pour éviter de surcharger l'API
def fetch_all_data():
    trans = requests.get(f"{API_URL}/users/{user_id}/transactions").json()
    stocks = requests.get(f"{API_URL}/stocks/").json()
    market = requests.get(f"{API_URL}/market-data/").json()
    return pd.DataFrame(trans), pd.DataFrame(stocks), pd.DataFrame(market)

df_t, df_stocks, df_market = fetch_all_data()

if not df_t.empty:
    # --- CALCUL DU PORTFOLIO ---
    
    # A. Calcul de la quantité nette et du CMP
    # On filtre sur les achats pour le CMP
    df_buys = df_t[df_t['transaction_type'] == 'buy'].copy()
    df_buys['total_cost'] = df_buys['quantity'] * df_buys['price_per_share']
    
    # Agrégation par stock
    portfolio = df_buys.groupby('stock_id').agg({
        'quantity': 'sum',
        'total_cost': 'sum'
    }).reset_index()
    
    portfolio['CMP'] = portfolio['total_cost'] / portfolio['quantity']
    
    # B. Ajustement avec les ventes (pour la quantité actuelle)
    df_sells = df_t[df_t['transaction_type'] == 'sell']
    if not df_sells.empty:
        sell_qty = df_sells.groupby('stock_id')['quantity'].sum().reset_index()
        portfolio = portfolio.merge(sell_qty, on='stock_id', how='left', suffixes=('', '_sold'))
        portfolio['quantity_sold'] = portfolio['quantity_sold'].fillna(0)
        portfolio['current_qty'] = portfolio['quantity'] - portfolio['quantity_sold']
    else:
        portfolio['current_qty'] = portfolio['quantity']

    # Filtrer les lignes où on ne possède plus d'actions
    portfolio = portfolio[portfolio['current_qty'] > 0]

    # C. Fusion avec Market Data et Stocks
    portfolio = portfolio.merge(df_stocks[['stock_id', 'symbol', 'company_name']], on='stock_id')
    portfolio = portfolio.merge(df_market[['stock_id', 'current_price']], on='stock_id')

    # D. Calcul de la Plus-value
    portfolio['Valeur Actuelle'] = portfolio['current_qty'] * portfolio['current_price']
    portfolio['Investissement'] = portfolio['current_qty'] * portfolio['CMP']
    portfolio['+/- Value'] = portfolio['Valeur Actuelle'] - portfolio['Investissement']
    portfolio['+/- %'] = (portfolio['+/- Value'] / portfolio['Investissement']) * 100

    # --- AFFICHAGE ---
    
    # Nettoyage des colonnes pour l'utilisateur
    df_final = portfolio[[
        'symbol', 'company_name', 'current_qty', 'CMP', 
        'current_price', '+/- Value', '+/- %'
    ]].copy()

    # Renommer les colonnes
    df_final.columns = ['Symbole', 'Société', 'Qté', 'CMP (XOF)', 'Prix Marché', 'Plus-Value Abs.', 'Plus-Value %']

    # Formatage et coloration
    def style_plus_value(val):
        color = 'green' if val > 0 else 'red'
        return f'color: {color}; font-weight: bold'

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

    # Métriques globales
    total_pv = portfolio['+/- Value'].sum()
    st.divider()
    col1, col2, col3 = st.columns(2)
    col1.metric("Plus-Value Totale", f"{total_pv:,.0f} XOF", delta=f"{total_pv:,.0f}")
    col2.metric("Valeur Totale Portfolio", f"{portfolio['Valeur Actuelle'].sum():,.0f} XOF")
    fig = px.pie(portfolio, values='qty_signed', names='symbol', title="Répartition des titres", hole=0.4)
#         st.plotly_chart(fig, use_container_width=True)
    col3.plotly_chart(fig, use_container_width=True)
else:
    st.info("Effectuez votre première transaction pour voir l'analyse.")

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
