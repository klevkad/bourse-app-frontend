import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import plotly.express as px
from shares.config import API_URL, USER_ID
from shares.connexion_function import logout

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("Veuillez vous connecter sur la page d'accueil.")
    st.stop()
else:
    st.sidebar.success(f"Connecté : {st.session_state['username']}")
    if st.sidebar.button("Déconnexion"):
        logout()

def get_actions():
    return requests.get(f"{API_URL}/actions/").json()

def post_transaction(data):
    return requests.post(f"{API_URL}/transactions/", json=data)


st.title("🚀 Terminal de Trading")
tab1, tab2 = st.tabs(["📊 Historique transaction", "📈 Faire une transaction"])

with tab1:
    # --- SECTION 3 : HISTORIQUE ---
    trans_res = requests.get(f"{API_URL}/users/{USER_ID}/transactions")
    if trans_res.status_code == 200 and trans_res.json():
        df_t = pd.DataFrame(trans_res.json())
        if 'df_t' in locals() and not df_t.empty:
            # On garde les ID pour savoir quoi modifier
            df_to_edit = df_t[['transaction_id', 'transaction_date', 'transaction_type', 'quantity', 'price_per_share','fees']]

            # Utilisation du data_editor
            edited_df = st.data_editor(
                df_to_edit,
                key="transaction_editor",
                num_rows="dynamic", # Permet de supprimer des lignes
                use_container_width=True,
                hide_index=True,
                column_config={
                    "transaction_type": st.column_config.SelectboxColumn(
                        "Type", options=["buy", "sell"], required=True
                    ),
                    "quantity": st.column_config.NumberColumn("Quantité", min_value=1),
                }
            )

            # Bouton pour envoyer les modifications à l'API
            if st.button("💾 Sauvegarder les modifications"):
                # Logique pour détecter les lignes modifiées
                # Note: Dans un cas réel, on compare edited_df avec df_to_edit
                for index, row in edited_df.iterrows():
                    trans_id = row['transaction_id']
                    payload = {
                        "quantity": row['quantity'],
                        "price_per_share": row['price_per_share'],
                        "transaction_type": row['transaction_type'],
                        "fees": row['fees'],
                        "transaction_date": row['transaction_date']
                    }
                    # Appel API PATCH
                    requests.patch(f"{API_URL}/transactions/{trans_id}", json=payload)
                
                st.success("Toutes les modifications ont été enregistrées !")
                st.rerun()
        # with st.expander("📜 Historique complet des transactions"):
        # if 'df_t' in locals() and not df_t.empty:
        #     # 1. Préparation des données (Jointure pour le symbole)
        #     stocks_data = requests.get(f"{API_URL}/stocks/").json()
        #     df_stocks = pd.DataFrame(stocks_data)
        #     df_display = df_t.merge(df_stocks[['stock_id', 'symbol']], on='stock_id', how='left')

        #     # 2. Sélection et réorganisation des colonnes
        #     df_display = df_display[['transaction_date', 'symbol', 'transaction_type', 'quantity', 'price_per_share']]

        #     # 3. Fonction de coloration
        #     def color_type(val):
        #         if val.lower() == 'buy':
        #             return 'background-color: #d4edda; color: #155724; font-weight: bold' # Vert clair
        #         elif val.lower() == 'sell':
        #             return 'background-color: #f8d7da; color: #721c24; font-weight: bold' # Rouge clair
        #         return ''

        #     # 4. Application du style et affichage
        #     st.write("### 📜 Historique des transactions")
            
        #     styled_df = df_display.style.applymap(color_type, subset=['transaction_type'])
            
        #     # Utilisation de dataframe pour un rendu plus moderne et scrollable
        #     st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # else:
        #     st.info("Aucune transaction à afficher.")
with tab2:
    stocks = get_actions()
    stock_options = {s['symbol']: s['stock_id'] for s in stocks}
    selected_stock_sym = st.selectbox("Action", list(stock_options.keys()))
    type_ordre = st.selectbox("Type", ["BUY", "SELL"])
    quantite = st.number_input("Quantité", min_value=1, value=1)
    prix = st.number_input("Prix unitaire (XOF)", min_value=1.0, value=1500.0)

    if st.button("Valider l'ordre"):
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
            st.success("Ordre exécuté !")
            st.rerun()
        else:
            st.error(f"Erreur: {res.json().get('detail')}")

# ... (Insère ici ton code de formulaire POST /transactions/)