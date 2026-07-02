## 🚀 Nouveautés ajoutées

Cette mise à jour apporte une analyse financière approfondie du portefeuille, de nouvelles visualisations dynamiques ainsi qu'un système d'alertes automatiques pour optimiser la gestion des risques.

### 📈 Nouveaux Indicateurs de Performance (`compute_indicators`)
* **Rendement Total :** Prise en compte des dividendes perçus en plus de la simple plus-value latente.
* **Score de Diversification (0–100) :** Basé sur l'indice de *Herfindahl-Hirschman (HHI)* pour mesurer scientifiquement la concentration réelle du portefeuille.
    - Interprétation
    HHI	Niveau de concentration
    1. < 0,10	Très bien diversifié
    2. 0,10 à 0,18	Diversification correcte
    3. 0,18 à 0,25	Portefeuille assez concentré
    4. > 0,25	Portefeuille fortement concentré
* **Ratio Gain/Perte :** Rapport précis entre la somme des plus-values et la somme des moins-values.
Interprétation
1. > 2 : excellent
Entre 1 et 2 : satisfaisant
2. = 1 : gains = pertes
3. < 1 : les pertes dépassent les gains

* ** Ratio Rendement / Risque :**
| Ratio | Niveau    |
| ----- | --------- |
| <1    | faible    |
| 1–2   | correct   |
| 2–3   | bon       |
| >3    | excellent |

* **VaR Simplifiée (Value at Risk) à -10% :** Estimation de la perte potentielle en cas de baisse globale du marché de 10%.
* **Détection Automatique :** Identification instantanée du meilleur et du pire titre du portefeuille.
* **Analyse Sectorielle :** Identification automatique du secteur dominant et calcul de son poids exact.
* **Le nombre effectif :** Vous possédez bien 5 actions, mais votre portefeuille se comporte presque comme si vous n'en aviez que 1,5.
  Pourquoi ?
  Parce que 80 % de votre argent est investi dans une seule action. Si cette action chute, tout le portefeuille en souffre.
### 📊 Jauges et Graphiques Dynamiques (Plotly)
* **3 Jauges Visuelles Interactives :** Affichage de la *Diversification*, de la *Performance Globale* et du *Ratio Gains/Pertes* avec un code couleur dynamique (Vert / Orange / Rouge).
* **4 Graphiques Améliorés :**
  1. **Camembert des poids par titre :** Répartition sectorielle avec affichage des pourcentages intégrés.
  2. **Barres de performance par titre :** Visualisation des gains/pertes individuels avec code couleur conditionnel.
  3. **Analyses sectorielles croisées :** Graphique combinant le poids sectoriel (en %) et la plus-value absolue par secteur.
  4. **Bubble Chart (Risque × Performance × Taille) :** Graphique à trois dimensions idéal pour identifier en un coup d'œil les titres moteurs ou à risque du portefeuille.
  # Lecture du Bubble Chart — Les 4 zones

    ## 🟢 Zone idéale (droite · haut)
    Titres **bien pondérés ET très performants**.
    > À conserver et potentiellement renforcer.
    ## 🟡 Zone vigilance (gauche · haut)
    Titres **lourds mais qui sous-performent**.
    > Capital important mal rentabilisé.
    ## 🔵 Zone opportunité (droite · bas)
    Titres **très performants mais sous-pondérés**.
    > Candidats au renforcement.
    ## 🔴 Zone risque (gauche · bas)
    **Petites positions qui perdent de la valeur**.
    > Surveiller ou arbitrer.
### 🚨 Signaux et Alertes Automatiques (`generate_signals`)
Le système surveille désormais le portefeuille en temps réel et génère des alertes de gestion des risques :
* **Alerte de concentration sectorielle :** Déclenchée si un seul secteur dépasse **50%** de l'allocation globale.
* **Alerte de concentration de titre :** Déclenchée si une seule ligne dépasse **30%** du poids total.
* **Signal de tendance globale :** Évaluation positive ou négative automatisée sur le rendement global.
* **Alerte de Stop-Loss individuelle :** Notification visuelle sur les titres subissant une moins-value critique supérieure à **-10%**.

### 🧮 Tableaux de Données Enrichis
* **Optimisation des tableaux :** Intégration de la colonne **Poids (%)** sur chaque ligne pour un suivi granulaire de l'exposition de chaque actif directement dans les vues tabulaires.