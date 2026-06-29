import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from shares.config import API_URL, USER_ID, PORTEFEUILLES
from shares.connexion_function import logout
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="Portefeuille BRVM", layout="wide")

user_id = USER_ID
portefeuille_list = (
    st.session_state["portefeuilles"]
    if "portefeuilles" in st.session_state
    else []
)


# ─────────────────────────────────────────────
# SCRAPING BRVM
# ─────────────────────────────────────────────
def extraire_table_bourse():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(
        "https://www.brvm.org/fr/cours-actions/0", headers=headers, verify=False
    )
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find(
            "table",
            {"class": "table table-hover table-striped sticky-enabled"},
        )
        if table:
            data = []
            for row in table.find_all("tr"):
                cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
                if cols:
                    data.append(cols)
            return pd.DataFrame(data[1:], columns=data[0])
    return None


# ─────────────────────────────────────────────
# INDICATEURS DE PERFORMANCE
# ─────────────────────────────────────────────
def compute_indicators(portfolio: pd.DataFrame, total_dividendes: float) -> dict:
    """Calcule les indicateurs avancés à partir du DataFrame portefeuille."""
    total_inv = portfolio["Investissement"].sum()
    total_val = portfolio["Valeur Actuelle"].sum()
    total_pv  = portfolio["+/- Value"].sum()
    total_pv_pct = (total_pv / total_inv * 100) if total_inv else 0

    # --- Rendement total incluant dividendes ---
    rendement_total = ((total_pv + total_dividendes) / total_inv * 100) if total_inv else 0

    # --- Concentration (Herfindahl-Hirschman Index) ---
    # HHI proche de 1 = très concentré, proche de 0 = très diversifié
    
    poids = portfolio["Valeur Actuelle"] / total_val
    hhi = (poids ** 2).sum()
    diversification_score = round((1 - hhi) * 100, 1)  # 0–100, 100 = parfaitement diversifié

    # --- Plus et moins performant ---
    best  = portfolio.loc[portfolio["+/- %"].idxmax()]
    worst = portfolio.loc[portfolio["+/- %"].idxmin()]

    # --- Poids moyen par secteur ---
    secteur_poids = (
        portfolio.groupby("secteur")["Valeur Actuelle"]
        .sum()
        .div(total_val)
        .mul(100)
        .round(1)
    )
    secteur_dominant = secteur_poids.idxmax()
    secteur_dominant_pct = secteur_poids.max()

    # --- Nombre de titres en plus-value vs moins-value ---
    n_positif = (portfolio["+/- %"] > 0).sum()
    n_negatif = (portfolio["+/- %"] <= 0).sum()

    # --- Valeur à risque simplifiée : perte potentielle si -10% sur tous les titres ---
    var_10 = total_val * 0.10

    # --- Ratio gain/perte (titres positifs vs négatifs en valeur absolue) ---
    gains = portfolio.loc[portfolio["+/- Value"] > 0, "+/- Value"].sum()
    pertes = abs(portfolio.loc[portfolio["+/- Value"] <= 0, "+/- Value"].sum())
    ratio_gain_perte = round(gains / pertes, 2) if pertes > 0 else float("inf")

    # --- Titre avec le plus gros poids ---
    heaviest = portfolio.loc[portfolio["Valeur Actuelle"].idxmax()]
    heaviest_pct = round(heaviest["Valeur Actuelle"] / total_val * 100, 1)

    return dict(
        total_inv=total_inv,
        total_val=total_val,
        total_pv=total_pv,
        total_pv_pct=total_pv_pct,
        rendement_total=rendement_total,
        diversification_score=diversification_score,
        hhi=hhi,
        best_symbole=best["Symbole"],
        best_pct=best["+/- %"],
        worst_symbole=worst["Symbole"],
        worst_pct=worst["+/- %"],
        secteur_dominant=secteur_dominant,
        secteur_dominant_pct=secteur_dominant_pct,
        n_positif=int(n_positif),
        n_negatif=int(n_negatif),
        var_10=var_10,
        ratio_gain_perte=ratio_gain_perte,
        heaviest_symbole=heaviest["Symbole"],
        heaviest_pct=heaviest_pct,
        secteur_poids=secteur_poids,
    )


def gauge_chart(value: float, title: str, min_val=0, max_val=100, suffix="%") -> go.Figure:
    """Mini jauge Plotly réutilisable."""
    color = "#22c55e" if value >= 60 else "#f59e0b" if value >= 30 else "#ef4444"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix, "font": {"size": 22}},
        title={"text": title, "font": {"size": 13}},
        gauge={
            "axis": {"range": [min_val, max_val], "tickfont": {"size": 10}},
            "bar": {"color": color},
            "bgcolor": "white",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 33], "color": "#d16969"},
                {"range": [33, 66], "color": "#065fd2"},
                {"range": [66, 100], "color": "#dcfce7"},
            ],
        },
    ))
    fig.update_layout(height=180, margin=dict(t=30, b=10, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)")
    return fig


# ─────────────────────────────────────────────
# SIGNAUX AUTOMATIQUES
# ─────────────────────────────────────────────
def generate_signals(ind: dict, portfolio: pd.DataFrame) -> list[dict]:
    signals = []

    if ind["secteur_dominant_pct"] > 50:
        signals.append({
            "type": "warning",
            "icon": "⚠️",
            "titre": f"Concentration sectorielle ({ind['secteur_dominant']})",
            "detail": f"{ind['secteur_dominant']} représente {ind['secteur_dominant_pct']:.1f}% du portefeuille. "
                      "Un choc sectoriel impacterait lourdement vos actifs.",
        })

    if ind["heaviest_pct"] > 30:
        signals.append({
            "type": "warning",
            "icon": "⚠️",
            "titre": f"Sur-pondération de {ind['heaviest_symbole']}",
            "detail": f"{ind['heaviest_symbole']} représente {ind['heaviest_pct']}% du portefeuille. "
                      "Envisagez de rééquilibrer.",
        })

    if ind["diversification_score"] < 50:
        signals.append({
            "type": "danger",
            "icon": "🔴",
            "titre": "Diversification insuffisante",
            "detail": f"Score de diversification : {ind['diversification_score']}/100. "
                      "Moins de 5 titres décorrélés génèrent un risque idiosyncratique élevé.",
        })
    elif ind["diversification_score"] >= 70:
        signals.append({
            "type": "success",
            "icon": "🟢",
            "titre": "Bonne diversification",
            "detail": f"Score : {ind['diversification_score']}/100. Votre portefeuille est bien réparti.",
        })

    if ind["rendement_total"] > 15:
        signals.append({
            "type": "success",
            "icon": "🟢",
            "titre": "Rendement total solide",
            "detail": f"+{ind['rendement_total']:.1f}% dividendes inclus. "
                      "Performance au-dessus de la moyenne BRVM.",
        })
    elif ind["rendement_total"] < 0:
        signals.append({
            "type": "danger",
            "icon": "🔴",
            "titre": "Rendement global négatif",
            "detail": f"{ind['rendement_total']:.1f}%. Vérifiez vos positions les plus perdantes.",
        })

    losing = portfolio[portfolio["+/- %"] < -10]
    for _, r in losing.iterrows():
        signals.append({
            "type": "danger",
            "icon": "🔴",
            "titre": f"{r['Symbole']} en forte moins-value",
            "detail": f"{r['Symbole']} affiche {r['+/- %']:.1f}%. "
                      "Vérifiez les fondamentaux avant de renforcer.",
        })

    return signals


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
portefeuille_map = {p["nom_portefeuille"]: p["id"] for p in portefeuille_list}

if st.button("🔄 Actualiser les données"):
    st.cache_data.clear()
    st.rerun()

try:
    df_quotes = extraire_table_bourse()

    st.write(
        f"Portefeuille sélectionné : **{st.session_state['nom_selectionne']}** "
        f"(ID : {st.session_state['portefeuille_id']})"
    )

    @st.cache_data(ttl=300)
    def fetch_all_data():
        trans  = requests.get(f"{API_URL}/portefeuille/{st.session_state['portefeuille_id']}/transactions").json()
        stocks = requests.get(f"{API_URL}/actions/").json()
        market = requests.get(f"{API_URL}/transactions/").json()
        return pd.DataFrame(trans), pd.DataFrame(stocks), pd.DataFrame(market)

    df_t, df_stocks, df_market = fetch_all_data()

    if not df_t.empty and not df_stocks.empty:

        # ── Calcul portefeuille ──────────────────────────────
        df_t["type_transaction"] = df_t["type_transaction"].str.strip().str.lower()
        df_buys = df_t[df_t["type_transaction"] == "achat"].copy()
        df_buys["total_cost"] = df_buys["quantite"] * df_buys["prix_unitaire"] + df_buys["frais_courtage"]

        portfolio = df_buys.groupby("action_id").agg(
            quantite=("quantite", "sum"),
            total_cost=("total_cost", "sum"),
        ).reset_index()
        portfolio["CMP"] = portfolio["total_cost"] / portfolio["quantite"]

        df_sells = df_t[df_t["type_transaction"] == "vente"]
        if not df_sells.empty:
            sell_qty = df_sells.groupby("action_id")["quantite"].sum().reset_index()
            portfolio = portfolio.merge(sell_qty, on="action_id", how="left", suffixes=("", "_sold"))
            portfolio["current_qty"] = portfolio["quantite"] - portfolio["quantite_sold"].fillna(0)
        else:
            portfolio["current_qty"] = portfolio["quantite"]

        portfolio = portfolio[portfolio["current_qty"] > 0]
        portfolio.rename(columns={"action_id": "id"}, inplace=True)
        portfolio = portfolio.merge(df_stocks[["id", "symbole", "nom_entreprise", "secteur"]], on="id")
        portfolio["dernier_cours"] = portfolio["symbole"].map(
            df_quotes.set_index("Symbole")["Cours Clôture (FCFA)"]
            .str.replace(" ", "")
            .astype(float)
        )

        portfolio["Valeur Actuelle"]   = portfolio["current_qty"] * portfolio["dernier_cours"]
        portfolio["Investissement"]    = portfolio["current_qty"] * portfolio["CMP"]
        portfolio["+/- Value"]         = portfolio["Valeur Actuelle"] - portfolio["Investissement"]
        portfolio["+/- %"]             = (portfolio["+/- Value"] / portfolio["Investissement"]) * 100
        portfolio["+/- Value marché"]  = portfolio["dernier_cours"] - portfolio["CMP"]

        total_dividendes = df_t[df_t["type_transaction"] == "dividende"]["prix_unitaire"].sum()

        # ── Renommage pour affichage ─────────────────────────
        df_display = portfolio.rename(columns={
            "symbole": "Symbole",
            "nom_entreprise": "Société",
            "secteur": "secteur",
            "current_qty": "Quantité",
            "dernier_cours": "Prix Marché",
        })

        ind = compute_indicators(df_display, total_dividendes)
        signals = generate_signals(ind, df_display)

        # ════════════════════════════════════════════════════
        # SECTION 1 – MÉTRIQUES GLOBALES
        # ════════════════════════════════════════════════════
        st.title("📈 Analyse du Portefeuille")
        st.divider()

        c1, c2, c3, c4, c5 = st.columns(5)
        for p in portefeuille_list:
            c1.metric("💰 Liquidités disponibles", f"{p['solde_especes']:,.0f} XOF")
        c2.metric("📊 Investissements", f"{ind['total_inv']:,.0f} XOF")
        c3.metric("💵 Valeur du portefeuille",   f"{ind['total_val']:,.0f} XOF")
        c4.metric("📥 Dividendes perçus",         f"{total_dividendes:,.0f} XOF")
        delta_color = "violet" if ind["total_pv"] >= 0 else "red"
        c5.metric(
            "💹 Plus-Value totale",
            f"{ind['total_pv']:,.0f} XOF",
            delta=f"{ind['total_pv_pct']:+.2f}%",
            delta_color=delta_color,
        )
        

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 Rendement total (div. inclus)", f"{ind['rendement_total']:+.2f}%")
        c2.metric("🏆 Meilleur titre",  f"{ind['best_symbole']}  {ind['best_pct']:+.1f}%")
        c3.metric("📉 Moins bon titre", f"{ind['worst_symbole']}  {ind['worst_pct']:+.1f}%")
        c4.metric("⚖️ Ratio gain/perte", f"{ind['ratio_gain_perte']:.2f}x")

        st.divider()

        # ════════════════════════════════════════════════════
        # SECTION 2 – INDICATEURS VISUELS
        # ════════════════════════════════════════════════════
        st.subheader("🎯 Indicateurs de performance")

        g1, g2, g3 = st.columns(3)
        with g1:
            st.plotly_chart(
                gauge_chart(ind["diversification_score"], "Diversification", suffix="/100"),
                use_container_width=True,
            )
            st.caption(
                f"HHI : {ind['hhi']:.2f} — "
                f"{ind['n_positif']} titre(s) en hausse / {ind['n_negatif']} en baisse"
            )
        with g2:
            BENCHMARK_ANNUEL = 8.0  # rendement moyen BRVM en %
            perf_relative = ind["total_pv_pct"] - BENCHMARK_ANNUEL
            perf_norm = min(max(perf_relative + 50, 0), 100)
            st.plotly_chart(
                gauge_chart(perf_norm, "Performance (centrée 0%)", suffix="%"),
                use_container_width=True,
            )
            st.caption(f"Plus-value réelle : {ind['total_pv_pct']:+.2f}%")
        with g3:
            # Ratio gain/perte normalisé sur 100 (cap à 5x → 100)
            rg_norm = min(ind["ratio_gain_perte"] / 5 * 100, 100) if ind["ratio_gain_perte"] != float("inf") else 100
            st.plotly_chart(
                gauge_chart(rg_norm, "Ratio gains / pertes", suffix="%"),
                use_container_width=True,
            )
            st.caption(f"Ratio brut : {ind['ratio_gain_perte']:.2f}x  |  VaR –10% : {ind['var_10']:,.0f} XOF")

        st.divider()

        # ════════════════════════════════════════════════════
        # SECTION 3 – GRAPHIQUES
        # ════════════════════════════════════════════════════
        st.subheader("📊 Répartition et performance")
        col1, col2 = st.columns(2)

        with col1:
            fig_pie = px.pie(
                df_display,
                values="Valeur Actuelle",
                names="Symbole",
                title="Poids des titres dans le portefeuille",
                hole=0.4,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            fig_perf = px.bar(
                df_display.sort_values("+/- %"),
                x="Symbole",
                y="+/- %",
                color="+/- %",
                color_continuous_scale=["#ef4444", "#f5610b", "#1b7a00"],
                title="Performance par titre (%)",
                text=df_display.sort_values("+/- %")["+/- %"].map(lambda v: f"{v:+.1f}%"),
            )
            fig_perf.update_traces(textposition="outside")
            fig_perf.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_perf, use_container_width=True)

        col3, col4 = st.columns(2)

        with col3:
            secteur_df = ind["secteur_poids"].reset_index()
            secteur_df.columns = ["Secteur", "Poids (%)"]
            fig_sec = px.bar(
                secteur_df,
                x="Secteur",
                y="Poids (%)",
                title="Poids sectoriel (%)",
                color="Poids (%)",
                color_continuous_scale=["#bfdbfe", "#1d4ed8"],
                text=secteur_df["Poids (%)"].map(lambda v: f"{v:.1f}%"),
            )
            fig_sec.update_traces(textposition="outside")
            fig_sec.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_sec, use_container_width=True)

        with col4:
            # Plus-value absolue par secteur
            pv_sec = (
                df_display.groupby("secteur")["+/- Value"]
                .sum()
                .reset_index()
                .rename(columns={"secteur": "Secteur", "+/- Value": "Plus-Value (XOF)"})
            )
            fig_pv_sec = px.bar(
                pv_sec,
                x="Secteur",
                y="Plus-Value (XOF)",
                title="Plus-Value absolue par Secteur (XOF)",
                color="Plus-Value (XOF)",
                color_continuous_scale=["#ef4444", "#22c55e"],
                text=pv_sec["Plus-Value (XOF)"].map(lambda v: f"{v:,.0f}"),
            )
            fig_pv_sec.update_traces(textposition="outside")
            fig_pv_sec.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_pv_sec, use_container_width=True)

        # Bubble chart : poids × perf × valeur
        st.subheader("🔵 Vue d'ensemble — Risque / Performance")
        fig_bubble = px.scatter(
            df_display,
            x="+/- %",
            y="Valeur Actuelle",
            size="Valeur Actuelle",
            color="secteur",
            text="Symbole",
            hover_data=["Société", "CMP", "Prix Marché"],
            title="Investissement vs Performance par titre",
            labels={"+/- %": "Performance (%)", "Valeur Actuelle": "Valeur (XOF)"},
            size_max=60,
        )
        fig_bubble.update_traces(textposition="top center")
        fig_bubble.add_vline(x=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_bubble, use_container_width=True)

        
        # Matrice de corrélation +/- % / quantite / Investissement
        st.subheader("📉 Matrice de corrélation")
        corr_cols = ["Quantité", "CMP", "Investissement", "Valeur Actuelle", "+/- Value", "+/- %"]
        corr_matrix = df_display[corr_cols].corr()
        fig_corr = px.imshow(
            corr_matrix,
            text_auto=True,
            color_continuous_scale="RdBu_r",
            title="Matrice de corrélation des indicateurs clés",
            width=900,
            height=600
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        st.divider()
        # ════════════════════════════════════════════════════
        # SECTION 4 – SIGNAUX AUTOMATIQUES
        # ════════════════════════════════════════════════════
        st.subheader("🚦 Signaux d'alerte & opportunités")

        if signals:
            for s in signals:
                if s["type"] == "success":
                    st.success(f"**{s['icon']} {s['titre']}** — {s['detail']}")
                elif s["type"] == "warning":
                    st.warning(f"**{s['icon']} {s['titre']}** — {s['detail']}")
                else:
                    st.error(f"**{s['icon']} {s['titre']}** — {s['detail']}")
        else:
            st.info("Aucun signal particulier détecté. Portefeuille équilibré.")

        st.divider()

        # ════════════════════════════════════════════════════
        # SECTION 5 – TABLEAU DÉTAILLÉ
        # ════════════════════════════════════════════════════
        st.title("🗒️ Analyse détaillée du Portefeuille")

        df_final = df_display[[
            "Symbole", "Société", "secteur", "Quantité", "CMP",
            "Investissement", "Valeur Actuelle", "Prix Marché",
            "+/- Value marché", "+/- Value", "+/- %",
        ]].copy()
        df_final.columns = [
            "Symbole", "Société", "Secteur", "Quantité", "CMP (XOF)",
            "Investissement", "Valeur Actuelle", "Prix Marché",
            "Plus-Value Marché", "Plus-Value Abs.", "Plus-Value %",
        ]
        df_final["CMP (XOF)"]      = df_final["CMP (XOF)"].round(0).astype(int)
        df_final["Investissement"]  = df_final["Investissement"].round(0).astype(int)
        df_final["Valeur Actuelle"] = df_final["Valeur Actuelle"].round(0).astype(int)
        df_final["Quantité"]        = df_final["Quantité"].astype(int)

        # Poids dans le portefeuille
        df_final["Poids (%)"] = (
            df_final["Valeur Actuelle"] / df_final["Valeur Actuelle"].sum() * 100
        ).round(1)

        def style_pv(val):
            color = "#792ced" if val > 0 else "#dc2626"
            return f"color: {color}; font-weight: bold"

        st.dataframe(
            df_final.style
            .format({
                "CMP (XOF)":        "{:,.0f}",
                "Prix Marché":      "{:,.0f}",
                "Investissement":   "{:,.0f}",
                "Valeur Actuelle":  "{:,.0f}",
                "Plus-Value Marché":"{:,.0f}",
                "Plus-Value Abs.":  "{:,.0f}",
                "Plus-Value %":     "{:+,.2f}%",
                "Poids (%)":        "{:.1f}%",
            })
            .map(style_pv, subset=["Plus-Value Marché", "Plus-Value Abs.", "Plus-Value %"]),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        # ════════════════════════════════════════════════════
        # SECTION 6 – COURS BRVM
        # ════════════════════════════════════════════════════
        if df_quotes is not None:
            df_quotes[
                ["Cours Ouverture (FCFA)", "Cours veille (FCFA)", "Cours Clôture (FCFA)", "Volume"]
            ] = df_quotes[
                ["Cours Ouverture (FCFA)", "Cours veille (FCFA)", "Cours Clôture (FCFA)", "Volume"]
            ].replace(" ", "", regex=True).astype(float)

            st.title("💹 Cours Actuels des Actions à la BRVM")

            if "secteur" not in df_quotes.columns:
                df_quotes = df_quotes.merge(
                    df_stocks[["symbole", "secteur"]],
                    left_on="Symbole", right_on="symbole", how="left",
                ).drop(columns=["symbole"])

            col1, col2 = st.columns(2)
            with col1:
                fig_cours = px.bar(
                    df_quotes, x="Symbole", y="Cours Clôture (FCFA)",
                    title="Cours de Clôture (FCFA)",
                )
                st.plotly_chart(fig_cours, use_container_width=True)
            with col2:
                secteur_counts = df_quotes["secteur"].value_counts()
                fig_sec2 = px.pie(
                    values=secteur_counts.values, names=secteur_counts.index,
                    title="Répartition des sociétés par Secteur", hole=0.4,
                )
                st.plotly_chart(fig_sec2, use_container_width=True)

            fig_var = px.bar(
                df_quotes, x="Nom", y="Variation (%)",
                title="Variation des cours des Actions à la BRVM",
                color="Variation (%)",
                color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
            )
            fig_var.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_var, use_container_width=True)

            st.title("📋 Données Complètes des Actions à la BRVM")
            st.dataframe(df_quotes, use_container_width=True, hide_index=True)
            st.divider()

        # ════════════════════════════════════════════════════
        # SECTION 7 – HISTORIQUE TRANSACTIONS
        # ════════════════════════════════════════════════════
        st.title("📜 Historique des Transactions")
        df_stocks.rename(columns={"id": "action_id"}, inplace=True)
        df_t = df_t.merge(
            df_stocks[["action_id", "symbole", "nom_entreprise"]],
            how="inner", on="action_id",
        )
        df_hist = df_t[[
            "symbole", "nom_entreprise", "type_transaction",
            "quantite", "prix_unitaire", "frais_courtage", "date_transaction",
        ]].copy()
        df_hist.columns = [
            "Symbole", "Société", "Type Transaction",
            "Quantité", "Prix Unit.", "Frais Courtage", "Date Transaction",
        ]
        df_hist["Date Transaction"] = pd.to_datetime(df_hist["Date Transaction"]).dt.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        if "deleted_transactions_rows" not in st.session_state:
            st.session_state.deleted_transactions_rows = set()

        df_trans_display = (
            df_hist.sort_values("Date Transaction", ascending=False)
            .reset_index()
            .rename(columns={"index": "row_id"})
        )

        headers = ["Symbole", "Société", "Type", "Quantité", "Prix Unit.", "Frais", "Date", "✏️", "🗑️"]
        col_widths = [1.2, 2.0, 1.4, 0.9, 1.1, 1.1, 2.0, 0.7, 0.7]
        header_cols = st.columns(col_widths)
        for i, h in enumerate(headers):
            header_cols[i].write(f"**{h}**")

        for _, row in df_trans_display.iterrows():
            row_id = int(row["row_id"])
            if row_id in st.session_state.deleted_transactions_rows:
                continue
            cols = st.columns(col_widths)
            cols[0].write(row["Symbole"])
            cols[1].write(row["Société"])
            cols[2].write(row["Type Transaction"])
            cols[3].write(f"{int(row['Quantité']):,}")
            cols[4].write(f"{int(row['Prix Unit.']):,}")
            cols[5].write(f"{int(row['Frais Courtage']):,}")
            cols[6].write(row["Date Transaction"])
            if cols[7].button("✏️", key=f"edit_{row_id}"):
                st.session_state.editing_transaction_row = row_id
                st.rerun()
            if cols[8].button("🗑️", key=f"del_{row_id}"):
                st.session_state.deleted_transactions_rows.add(row_id)
                st.rerun()

        if st.session_state.deleted_transactions_rows:
            st.info(f"📌 {len(st.session_state.deleted_transactions_rows)} transaction(s) masquée(s)")
            if st.button("↩️ Annuler les suppressions"):
                st.session_state.deleted_transactions_rows.clear()
                st.rerun()

    else:
        st.info("Effectuez votre première transaction pour voir l'analyse.")

except Exception as e:
    st.error(f"Erreur lors du chargement du portefeuille : {str(e)}")