import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
# from ..connexion_function import login, logout
from shares.config import API_URL, USER_ID, PORTEFEUILLES
from shares.connexion_function import logout
from openai import OpenAI

# import requests
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

# OPENAI_API_KEY='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'

# # st.write(f"Utilisation de l'API Key: {'Définie' if OPENAI_API_KEY else 'Non définie'}")
# if 'openai_api_key' not in st.session_state:
#     st.session_state.openai_api_key = OPENAI_API_KEY
# st.title("📊 Analyse générale du Portefeuille")

#     # Vérification de la clé
# if not OPENAI_API_KEY:
#     st.error("❌ Veuillez entrer votre clé API OpenAI")
#     st.info("Vous pouvez obtenir une clé sur : https://platform.openai.com/api-keys")
#     st.stop()
# else:
#     st.success(f"✅ API Key configurée: {OPENAI_API_KEY[:8]}...")

instructions = (
        "Tu es analyste financier. On te donne une liste d'actions détenues dans un portefeuille. "
        "Pour chaque action à la BRVM, je veux que tu associes le dernier cours connu et la quantité détenue. "
        "Réponds uniquement à la question posée, sans inventer de données. "
)  
# boutton pour actualiser les données (dernier_cours) de chaque action via chatgpt

# def generate_summary(text, model="gpt-4o-mini"):
#     try:
#         client = OpenAI(api_key=OPENAI_API_KEY)
        
#         response = client.chat.completions.create(
#             model=model,
#             messages=[
#                 {"role": "system", "content": instructions},
#                 {"role": "user", "content": text}
#             ],
#             max_tokens=2000,
#             temperature=0.1
#         )
        
#         return response.choices[0].message.content
        
#     except Exception as e:
#         st.error(f"❌ Erreur lors de la génération du résumé: {str(e)}")
#         return None



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

# Exemple d'utilisation

# if st.button("Tcheck"):
#     with st.spinner("Chargement"):
#         url_bourse = "https://www.sikafinance.com/marches/aaz" # Remplacez par l'URL réelle
#         df_quotes = extraire_table_bourse()
#         if df_quotes is not None:
#             print(df_quotes.head())
#             st.write(f"Portefeuille sélectionné : {st.session_state['nom_selectionne']} (ID: {st.session_state["portefeuille_id"]})")

  


# if st.button("🔄 Actualiser les données du marché"):
#     with st.spinner("Mise à jour des données via OpenAI..."):
#         summary = generate_summary("Je veux la liste des actions à la BRVM et leur dernier cours connu.", model="gpt-4o-mini")
#         if summary:
#             st.success("✅ Données mises à jour avec succès !")
#             st.text_area("Résumé des mises à jour :", summary, height=200)

portefeuille_map = {p["nom_portefeuille"]: p["id"] for p in portefeuille_list}
with st.form("get_data_form"):
    with st.spinner("Chargement des portefeuilles..."):
        submit = st.form_submit_button("👆 Afficher l'analyse")

        if submit:
                try:
                    df_quotes = extraire_table_bourse()
                    
                        # Mettre à jour la table actions dans la BD avec les nouveaux cours
                        # response = requests.post(f"{API_URL}/actions/update_prices", json=df_quotes[['nom_entreprise','date_mise_a_jour', 'dernier_cours']].to_dict(orient='records'))
                        # if response.status_code == 200:
                        #     st.success("✅ Cours des actions mis à jour dans la base de données.")
                        # else:
                        #     st.error("❌ Échec de la mise à jour des cours dans la base de données.")
                # 1. Récupération des données via l'API
                    @st.cache_data(ttl=60) # Cache pour éviter de surcharger l'API
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
                        portfolio['+/- Value marché'] = (portfolio['dernier_cours'] - portfolio['CMP']) 
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
                        st.divider()
                        col2.write("Répartition des Titres du Portefeuille")
                        col2.bar_chart(portfolio.groupby('symbole')['current_qty'].sum())
                        col3.write("Répartition des Plus-Values Absolues")
                        col3.bar_chart(portfolio.groupby('symbole')['+/- Value'].sum(),color="#009A76")
                        col4.write("Répartition des symboles par Secteur")
                        col4.plotly_chart(
                            px.pie(portfolio, values='current_qty', names='secteur', hole=0.4),
                            use_container_width=True
                        )
                        st.divider()
                      
                        # Nettoyage des colonnes pour l'utilisateur
                        df_final = portfolio[[
                            'symbole', 'nom_entreprise','secteur', 'current_qty', 'CMP', 
                            'dernier_cours','+/- Value marché', '+/- Value', '+/- %'
                        ]].copy()

                        # Renommer les colonnes
                        df_final.columns = ['Symbole', 'Société', 'Secteur', 'Qté', 'CMP (XOF)', 'Prix Marché', 'Plus-Value Marché', 'Plus-Value Abs.', 'Plus-Value %']
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
                            use_container_width=True,
                            hide_index=True
                        ) 
                        st.divider()
                        # df_quotes['Cours Clôture (FCFA)'] = df_quotes['Cours Clôture (FCFA)'].str.replace(' ','').astype(float)
                        df_quotes[['Cours Ouverture (FCFA)','Cours veille (FCFA)','Cours Clôture (FCFA)','Volume']] = df_quotes[['Cours Ouverture (FCFA)','Cours veille (FCFA)','Cours Clôture (FCFA)','Volume']].replace(' ','', regex=True).astype(float)
                        if df_quotes is not None:
                            st.title("💹 Cours Actuels des Actions à la BRVM")
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
# #     if st.sidebar.button("👆 Déconnexion"):
# #         logout()
    
# #     st.title("🏠 Accueil Portefeuille")
# #     st.write(f"Bonjour **{st.session_state['username']}**, utilisez le menu à gauche pour piloter vos investissements.")
# #     st.info("Sélectionnez 'Dashboard' pour voir vos gains ou 'Trading' pour passer des ordres.")
# # Récupérer les données via API en utilisant st.session_state["user_id"]
# # ... (Insère ici ton code de graphiques précédent)
