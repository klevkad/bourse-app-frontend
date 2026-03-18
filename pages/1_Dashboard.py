import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from openai import OpenAI
import matplotlib.pyplot as plt
from shares.config import API_URL, USER_ID, PORTEFEUILLES
from shares.connexion_function import logout
from bs4 import BeautifulSoup


if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("Veuillez vous connecter sur la page d'accueil.")
    st.stop()
else:
    st.sidebar.success(f"Connecté : {st.session_state['username']}")
    if st.sidebar.button("👆 Déconnexion"):
        logout()
user_id = USER_ID
portefeuille_list = st.session_state["portefeuilles"] if "portefeuilles" in st.session_state else []


def extraire_table_bourse():
    # 1. Envoyer la requête à la page web
    headers = {'User-Agent': 'Mozilla/5.0'} # Pour éviter d'être bloqué par le site
    response = requests.get("https://www.brvm.org/fr/cours-actions/0", headers=headers,verify=False)
    
    if response.status_code == 200:
        # 2. Analyser le contenu HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        # 3. Trouver la table par son ID
        table = soup.find('table', {'class': 'table table-hover table-striped sticky-enabled'})
        if table:
            # 4. Parcourir les lignes (tr) et les cellules (td)
            data = []
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                cols = [ele.text.strip() for ele in cols]
                if cols: # Éviter les lignes vides
                    data.append(cols)
            df = pd.DataFrame(data[1:], columns=data[0]) # data[0] contient souvent les entêtes
            return df
        else:
            print("Table 'tabQuotes' non trouvée sur la page.")
            return None
    else:
        print(f"Erreur lors du chargement de la page : {response.status_code}")
        return None


portefeuille_map = {p["nom_portefeuille"]: p["id"] for p in portefeuille_list}

if st.button("🔄 Actualiser les données"):
    st.cache_data.clear()  # Vide le cache de fetch_all_data()
    st.rerun()
try:
    df_quotes = extraire_table_bourse()
    st.write(f"Portefeuille sélectionné : {st.session_state['nom_selectionne']} (ID: {st.session_state['portefeuille_id']})")
  
# 1. Récupération des données via l'API
    @st.cache_data(ttl=300) # Cache pour éviter de surcharger l'API
    def fetch_all_data():
        trans = requests.get(f"{API_URL}/portefeuille/{st.session_state["portefeuille_id"]}/transactions").json()
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
        if not df_sells.empty:
            sell_qty = df_sells.groupby('action_id')['quantite'].sum().reset_index()
            portfolio = portfolio.merge(sell_qty, on='action_id', how='left', suffixes=('', '_sold'))

            # certain portfolio['quantite_sold'] peuvent être None si vente inexistante
            portfolio['quantity_sold'] = portfolio['quantite_sold'].fillna(0)
            portfolio['current_qty'] = portfolio['quantite'] - portfolio['quantity_sold']
        else:
            portfolio['current_qty'] = portfolio['quantite']
        # Filtrer les lignes où on ne possède plus d'actions
        portfolio = portfolio[portfolio['current_qty'] > 0]
        
        dernier_cours = df_stocks.sort_values('date_mise_a_jour').drop_duplicates(subset=['id'], keep='last')
        df_market = dernier_cours[['id', 'dernier_cours']]
            # C. Fusion avec Market Data et Stocks
        portfolio.rename(columns={'action_id': 'id'}, inplace=True)
        portfolio = portfolio.merge(df_stocks[['id', 'symbole', 'nom_entreprise','secteur']], on='id')
        # dernier_cours de type float avec suppression des espaces
        portfolio['dernier_cours']= portfolio['symbole'].map(df_quotes.set_index('Symbole')['Cours Clôture (FCFA)'].str.replace(' ','').astype(float))
        st.title("📈 Analyse du Portefeuille")
        st.divider()
        # D. Calcul de la Plus-value
        portfolio['Valeur Actuelle'] = portfolio['current_qty'] * portfolio['dernier_cours']
        portfolio['Investissement'] = portfolio['current_qty'] * portfolio['CMP']
        portfolio['+/- Value'] = portfolio['Valeur Actuelle'] - portfolio['Investissement']
        portfolio['+/- %'] = (portfolio['+/- Value'] / portfolio['Investissement']) * 100
        portfolio['+/- Value marché'] = portfolio['dernier_cours'] - portfolio['CMP']
        # --- AFFICHAGE ---
    
    # Métriques globales
        total_pv = portfolio['+/- Value'].sum()
        total_inv = portfolio['Investissement'].sum()
        total_plus_value_pct = (total_pv/total_inv)*100
        col1, col2,col3, col4 = st.columns(4)
        col1.metric("Plus-Value % Totale", f"{total_plus_value_pct:,.2f} %", delta=f"{total_plus_value_pct:,.0f}")
        col1.metric("Plus-Value Totale", f"{total_pv:,.0f} XOF", delta=f"{total_pv:,.0f}")
        col1.metric("Valeur Totale portefeuille", f"{portfolio['Valeur Actuelle'].sum():,.0f} XOF")
        col1.metric("Investissement Total", f"{total_inv:,.0f} XOF")
        
        col2.write("Répartition des Titres du Portefeuille")
        col2.bar_chart(portfolio.groupby('symbole')['current_qty'].sum())
        col3.write("Répartition des Plus-Values Absolues")
        col3.bar_chart(portfolio.groupby('symbole')['+/- Value'].sum(),color="#009A76")
        # Répartition des +/- Value par Secteur
        col4.write("Répartition des Plus-Values Absolues par Secteur")
        col4.bar_chart(portfolio.groupby('secteur')['+/- Value'].sum(),color="#CDCD28")
        
        st.divider()
        
        # Nettoyage des colonnes pour l'utilisateur
        df_final = portfolio[['symbole', 'nom_entreprise','secteur', 'current_qty', 'CMP','Investissement', 'Valeur Actuelle', 'dernier_cours', '+/- Value marché', '+/- Value', '+/- %']].copy()

        # Renommer les colonnes
        df_final.columns = ['Symbole', 'Société', 'Secteur', 'Quantité', 'CMP (XOF)','Investissement', 'Valeur Actuelle', 'Prix Marché', 'Plus-Value Marché', 'Plus-Value Abs.', 'Plus-Value %']
        # Formatage et coloration
        def style_plus_value(val):
            color = 'green' if val > 0 else 'red'
            return f'color: {color}; font-weight: bold'
        # Portefeuille titres détenus
        st.title("🗒️ Analyse détaillée du Portefeuille")
        st.dataframe(
            df_final.style.format({
                'CMP (XOF)': '{:,.0f}',
                'Prix Marché': '{:,.0f}',
                'Plus-Value Marché': '{:,.0f}',
                'Plus-Value Abs.': '{:,.0f}',
                'Plus-Value %': '{:,.2f}%'
            }).applymap(style_plus_value, subset=['Plus-Value Marché', 'Plus-Value Abs.', 'Plus-Value %']),
            width='content',
            hide_index=True
        ) 
        st.divider()
        df_quotes[['Cours Ouverture (FCFA)','Cours veille (FCFA)','Cours Clôture (FCFA)','Volume']] = df_quotes[['Cours Ouverture (FCFA)','Cours veille (FCFA)','Cours Clôture (FCFA)','Volume']].replace(' ','', regex=True).astype(float)
        if df_quotes is not None:
            st.title("💹 Cours Actuels des Actions à la BRVM")
            # Ajouter le secteur si besoin
            if 'secteur' not in df_quotes.columns:
                df_quotes = df_quotes.merge(df_stocks[['symbole','secteur']], left_on='Symbole', right_on='symbole', how='left').drop(columns=['symbole'])
            # camembert des secteurs
            col1, col2 = st.columns(2)
            with col1:
                fig_cours = px.bar(df_quotes, x='Symbole', y='Cours Clôture (FCFA)', title="Cours de Clôture des Actions à la BRVM")
                fig_cours.update_layout(yaxis_title='Cours Clôture (FCFA)', xaxis_title='Symbole')
                st.plotly_chart(fig_cours, width='content')
            with col2:
                secteur_counts = df_quotes['secteur'].value_counts()
                fig_secteur = px.pie(values=secteur_counts.values, names=secteur_counts.index, title="Répartition des société par Secteur", hole=0.4)
                st.plotly_chart(fig_secteur, width='content')
            st.divider()

            fig_cours = px.bar(df_quotes, x='Nom', y='Variation (%)', title="Variation des cours des Actions à la BRVM")
            fig_cours.update_layout(yaxis_title='Variation (%)', xaxis_title='Societé')
            st.plotly_chart(fig_cours, width='content')
            st.title("📋 Données Complètes des Actions à la BRVM")
            st.write(df_quotes)
        st.divider()
        ## titre historique transactions
        st.title("📜 Historique des Transactions")
        df_stocks.rename(columns={ 'id': 'action_id'}, inplace=True)
        df_t = df_t.merge(df_stocks[['action_id', 'symbole', 'nom_entreprise']], how='inner', on='action_id')
        
        df_final = df_t[[
            'symbole', 'nom_entreprise', 'type_transaction', 'quantite', 'prix_unitaire', 'frais_courtage', 'date_transaction'
        ]].copy()

        # Renommer les colonnes
        df_final.columns = ['Symbole', 'Société', 'Type Transaction', 'Quantité', 'Prix Unit.', 'Frais Courtage', 'Date Transaction']
        
        st.dataframe(df_final.sort_values(by='Date Transaction', ascending=False), width='content', hide_index=True)
        
    else:
        st.info("Effectuez votre première transaction pour voir l'analyse.")
    # Ici, tu peux ajouter du code pour récupérer et afficher les données spécifiques au portefeuille sélectionné

except Exception as e:
    st.error(f"Erreur lors de la sélection du portefeuille.{str(e)}")

