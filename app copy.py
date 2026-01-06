import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuration
API_URL = "https://bourse-app-backend.onrender.com"
USER_ID = 1  # On assume que tu es l'utilisateur 1 (Ehui Louis)

st.set_page_config(page_title="BRVM Trading v2026", layout="wide")

# --- FONCTIONS API ---
def get_user_data():
    response = requests.get(f"{API_URL}/users/{USER_ID}")
    return response.json() if response.status_code == 200 else None

def get_stocks():
    return requests.get(f"{API_URL}/stocks/").json()

def post_transaction(data):
    return requests.post(f"{API_URL}/transactions/", json=data)

# --- SIDEBAR & ENTÊTE ---
user = get_user_data()
if not user:
    st.error("Utilisateur introuvable. Assure-toi que l'API tourne et que l'utilisateur est créé.")
    st.stop()

st.title(f"💼 Portefeuille de {user['username']}")
st.sidebar.metric("Solde Cash", f"{user['cash_balance']:,.0f} XOF")

# --- SECTION 1 : PASSER UN ORDRE ---
st.sidebar.divider()
st.sidebar.subheader("🚀 Passer un ordre")

stocks = get_stocks()
stock_options = {s['symbol']: s['stock_id'] for s in stocks}
selected_stock_sym = st.sidebar.selectbox("Action", list(stock_options.keys()))
type_ordre = st.sidebar.selectbox("Type", ["BUY", "SELL"])
quantite = st.sidebar.number_input("Quantité", min_value=1, value=1)
prix = st.sidebar.number_input("Prix unitaire (XOF)", min_value=1.0, value=1500.0)

if st.sidebar.button("Valider l'ordre"):
    payload = {
        "user_id": USER_ID,
        "stock_id": stock_options[selected_stock_sym],
        "quantity": quantite,
        "price_per_share": prix,
        "fees": prix * quantite * 0.01, # Simulation de 1% de frais
        "transaction_type": type_ordre.lower(),
        "transaction_date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    res = post_transaction(payload)
    if res.status_code == 200:
        st.sidebar.success("Ordre exécuté !")
        st.rerun()
    else:
        st.sidebar.error(f"Erreur: {res.json().get('detail')}")

# --- SECTION 2 : AFFICHAGE DU PORTEFEUILLE ---
st.subheader("📊 Mes Positions")

# Récupérer les transactions pour calculer le portefeuille
trans_res = requests.get(f"{API_URL}/users/{USER_ID}/transactions")
if trans_res.status_code == 200 and trans_res.json():
    df_t = pd.DataFrame(trans_res.json())
    
    # Calculer les quantités nettes par action
    df_t['qty_signed'] = df_t.apply(lambda x: x['quantity'] if x['transaction_type'] == 'buy' else -x['quantity'], axis=1)
    portfolio = df_t.groupby('stock_id')['qty_signed'].sum().reset_index()
    portfolio = portfolio[portfolio['qty_signed'] > 0] # Garder seulement ce qu'on possède
    
    # Fusionner avec les noms des stocks
    stocks_df = pd.DataFrame(stocks)
    portfolio = portfolio.merge(stocks_df, on='stock_id')
    
    # Affichage
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.dataframe(portfolio[['symbol', 'company_name', 'qty_signed', 'sector']], use_container_width=True)
    
    with col2:
        fig = px.pie(portfolio, values='qty_signed', names='symbol', title="Répartition des titres", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucune transaction enregistrée pour le moment.")

# --- SECTION 3 : HISTORIQUE ---
with st.expander("📜 Historique complet des transactions"):
    if 'df_t' in locals():
        st.table(df_t[['transaction_date', 'transaction_type', 'quantity', 'price_per_share']])