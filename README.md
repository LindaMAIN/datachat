# DataChat

**Agent conversationnel IA sur données business - Anthropic API + Streamlit.**  
Permet à n'importe quel utilisateur de poser des questions en langage naturel sur un dataset de ventes et d'obtenir des réponses chiffrées, des graphiques interactifs et des recommandations business sans écrire une seule ligne de code.

Construit avec l'API Anthropic (Claude), Streamlit et pandas. Testé sur le dataset Superstore Sales (9 994 transactions, 2014-2017).

---

## Pourquoi ce projet existe

La plupart des outils BI (Power BI, Tableau, Looker) nécessitent une formation pour être utilisés efficacement. Un manager qui veut savoir "quels sont mes 3 états les plus rentables ce trimestre ?" doit soit attendre qu'un analyste lui prépare un rapport, soit apprendre à construire lui-même un visuel dans l'outil. Les deux options sont coûteuses en temps.

DataChat supprime cette friction : l'utilisateur pose sa question en français, l'agent comprend l'intention, execute l'analyse sur les vraies données et retourne une réponse structurée avec tableau et graphique. Aucune connaissance technique requise côté utilisateur.

C'est le cas d'usage que les ESN comme Davidson, Artefact ou Ekimetrics vendent à leurs clients sous le nom de "data democratization" ou "self-service analytics augmenté par l'IA".

---

## Demo rapide

```
Utilisateur : "Quels sont les 3 états les plus rentables ?"

DataChat :
  → choisit l'outil query_data
  → génère le code pandas adapté
  → execute sur le dataset réel
  → retourne :

  | Rang | État       | Profit Total |
  |------|------------|-------------|
  | 1    | California | $76 381     |
  | 2    | New York   | $74 038     |
  | 3    | Washington | $33 402     |

  "La Californie est l'état le plus rentable avec $76 381 de profit,
  suivie de très près par New York ($74 038). Ces deux états dominent
  largement Washington qui arrive en 3ème position avec $33 402,
  soit environ deux fois moins que les deux premiers."

  Source : Superstore Sales Dataset, 9 994 transactions
```

---

## Installation

```bash
git clone https://github.com/LindaMAIN/datachat.git
cd datachat
pip install -r requirements.txt
```

Crée un fichier `.env` à la racine :

```
ANTHROPIC_API_KEY=ta_cle_api_ici
```

Lance l'application :

```bash
streamlit run app.py
```

**Prérequis :** Python 3.8+, clé API Anthropic (console.anthropic.com)

---

## Architecture : comment fonctionne l'agent

### Pourquoi "agent" et pas un simple chatbot

Un chatbot classique répond à partir de ce qu'il a appris à l'entraînement. Il ne peut pas accéder à tes données réelles, ne peut pas executer du code, et ne peut pas générer un graphique Plotly à la volée.

Un agent est différent : il a accès à des **outils** qu'il peut appeler selon le contexte. Quand l'utilisateur pose une question, Claude ne répond pas directement, il décide d'abord quel outil utiliser, appelle cet outil avec les bons paramètres, reçoit le résultat, et formule ensuite une réponse en langage naturel basée sur les vraies données.

### Le cycle agentique

```
Question utilisateur
        ↓
Claude analyse l'intention
        ↓
Claude choisit un outil parmi les 5 disponibles
        ↓
Claude génère les paramètres de l'outil (code pandas, type de graphique...)
        ↓
DataChat execute l'outil sur le dataset réel
        ↓
Le résultat est renvoyé à Claude
        ↓
Claude formule une réponse en français avec interprétation business
        ↓
DataChat affiche : texte + tableau + graphique + badge outil utilisé
```

Ce cycle peut se répéter : Claude peut utiliser plusieurs outils en séquence si la question le demande (ex: d'abord query_data pour calculer les chiffres, puis plot_chart pour les visualiser).

### Pourquoi cette approche est plus robuste qu'un prompt direct

Une alternative simple serait de demander à Claude "réponds à cette question sur ce dataset" et de lui coller les données dans le prompt. Cette approche a trois problèmes :

- **Limite de contexte :** un dataset de 10 000 lignes ne rentre pas dans un prompt.
- **Hallucination :** Claude pourrait inventer des chiffres plausibles mais faux.
- **Pas de graphiques :** Claude ne peut pas générer du code Plotly et l'executer en même temps.

L'approche agentique avec tool use résout les trois : Claude génère du code pandas qui s'execute sur les vraies données, les chiffres sont donc exacts par construction, et les graphiques sont générés et affichés dynamiquement.

---

## Les 5 outils disponibles

Claude choisit automatiquement l'outil approprié selon la question posée.

### Outil 1 - `query_data`

**Quand Claude l'utilise :** questions quantitatives , "combien", "quels sont", "top X", "quel pourcentage".

**Ce qu'il fait :** Claude génère du code pandas adapté à la question, DataChat l'execute sur le DataFrame réel, et retourne le résultat sous forme de tableau.

**Exemple de code généré par Claude :**
```python
result = df.groupby('State')['Profit'].sum().sort_values(ascending=False).head(3).reset_index()
result.columns = ['État', 'Profit Total ($)']
result['Profit Total ($)'] = result['Profit Total ($)'].round(2)
```

**Sécurité :** le code s'execute dans un environnement isolé avec uniquement accès au DataFrame et à pandas. Aucun accès au système de fichiers ni à internet.

---

### Outil 2 - `plot_chart`

**Quand Claude l'utilise :** questions visuelles — "montre-moi", "graphique", "visualise", "répartition".

**Ce qu'il fait :** Claude génère du code Plotly adapté (bar, line, pie, scatter, treemap), DataChat l'execute et affiche le graphique interactif dans l'interface Streamlit.

**Types de graphiques supportés :** bar, line, pie, scatter, treemap.

**Exemple :** "Montre-moi un graphique des ventes par catégorie" → graphique bar Plotly avec valeurs affichées sur chaque barre, coloré par catégorie.

---

### Outil 3 - `get_schema`

**Quand Claude l'utilise :** questions sur la structure des données - "quelles colonnes", "quelles données sont disponibles", "que contient ce dataset".

**Ce qu'il fait :** retourne le schéma complet du dataset (colonnes, types, valeurs uniques, exemples) pour que Claude puisse guider l'utilisateur sur ce qu'il peut demander.

---

### Outil 4 - `compare_periods`

**Quand Claude l'utilise :** questions temporelles - "compare 2016 et 2017", "évolution", "croissance", "tendance".

**Ce qu'il fait :** même logique que query_data mais sémantiquement distinct pour que Claude choisisse le bon angle d'analyse quand une comparaison temporelle est demandée.

**Exemple :** "Compare les ventes 2016 et 2017 par région" → tableau avec les deux années côte à côte et le delta en pourcentage.

---

### Outil 5 - `export_results`

**Quand Claude l'utilise :** quand l'utilisateur demande à télécharger ou exporter les résultats.

**Ce qu'il fait :** génère un fichier CSV ou Excel téléchargeable à partir des derniers résultats affichés, avec un bouton de téléchargement dans l'interface.

---

## Mémoire de conversation

DataChat maintient un historique des 10 derniers échanges. Cela permet des conversations en contexte :

```
Utilisateur : "Quels sont les 5 produits les plus vendus ?"
DataChat : [retourne le top 5]

Utilisateur : "Et leur profit ?"
DataChat : [comprend que "leur" fait référence aux 5 produits précédents
            et ajoute la colonne profit sans redemander lesquels]

Utilisateur : "Exporte ces résultats"
DataChat : [exporte le dernier tableau affiché]
```

La mémoire est gérée côté Python dans `src/memory.py` , les messages sont stockés dans le format attendu par l'API Anthropic et passés à chaque appel.

---

## Structure du code

```
datachat/
├── app.py                    # Interface Streamlit  dashboard, chat, affichage résultats
├── requirements.txt
├── README.md
├── .env                      # Clé API (jamais pushée sur GitHub)
├── .env.example              # Template pour les nouveaux utilisateurs
└── src/
    ├── data_loader.py        # Charge le CSV, construit le schéma, stats rapides
    ├── agent.py              # Orchestration — appels API, boucle agentique, routing outils
    ├── tools.py              # 5 outils + définitions JSON pour l'API Anthropic
    ├── memory.py             # Historique de conversation, stockage dernier résultat
    └── data/
        └── Superstore.csv    # Dataset Superstore Sales (9 994 transactions)
```

### Rôle de chaque module

**`data_loader.py`** construit le contexte que Claude reçoit au démarrage : noms des colonnes, types de données, valeurs uniques, exemples. Ce contexte est injecté dans le system prompt pour que Claude sache exactement quelles données sont disponibles avant même que l'utilisateur pose sa première question.

**`agent.py`** orchestre la boucle agentique. Il envoie la question à Claude avec le system prompt et la définition des outils, détecte si Claude veut utiliser un outil (`stop_reason == "tool_use"`), execute l'outil via `tools.py`, renvoie le résultat à Claude, et répète jusqu'à ce que Claude formule sa réponse finale.

**`tools.py`** contient deux choses : les fonctions Python qui executent vraiment les outils (query_data, plot_chart, etc.) et les définitions JSON de ces outils au format attendu par l'API Anthropic (nom, description, paramètres). Claude lit ces définitions pour savoir quels outils sont disponibles et comment les appeler.

**`memory.py`** maintient la liste des messages au format API Anthropic. Il gère aussi le stockage du dernier résultat tabulaire pour permettre l'export en un seul message ("exporte ces résultats").

---

## Dataset utilisé

**Superstore Sales** - dataset de référence de la communauté BI/Data Science.  
Données de ventes d'une chaine de distribution américaine, 2014-2017.

| Indicateur | Valeur |
|------------|--------|
| Transactions | 9 994 |
| Commandes uniques | 5 009 |
| Clients | 793 |
| Produits | 1 862 |
| Ventes totales | $2 297 201 |
| Profit total | $286 397 |
| Régions | South, West, Central, East |
| Catégories | Furniture, Office Supplies, Technology |
| Période | 2014-01-03 - 2017-12-30 |

**Colonnes disponibles :** Row ID, Order ID, Order Date, Ship Date, Ship Mode, Customer ID, Customer Name, Segment, Country, City, State, Postal Code, Region, Product ID, Category, Sub-Category, Product Name, Sales, Quantity, Discount, Profit.

---

## Exemples de questions testées

| Question | Outil utilisé | Type de résultat |
|----------|---------------|-----------------|
| "Quels sont les 3 états les plus rentables ?" | query_data | Tableau + analyse |
| "Montre-moi un graphique des ventes par catégorie" | plot_chart | Bar chart Plotly |
| "Compare les ventes 2016 et 2017" | compare_periods | Tableau comparatif |
| "Quelles données sont disponibles ?" | get_schema | Description du dataset |
| "Exporte ces résultats en CSV" | export_results | Fichier téléchargeable |
| "Quels clients ont le panier moyen le plus élevé ?" | query_data | Tableau + analyse |
| "Quelle région est la moins rentable et pourquoi ?" | query_data | Tableau + diagnostic |

---

## Choix techniques

**Pourquoi Anthropic API et pas OpenAI :**
Claude est le modèle le plus fiable pour la génération de code pandas valide en une seule passe. Les tests sur ce projet montrent un taux d'erreur d'execution très faible , Claude comprend le contexte du schéma injecté dans le system prompt et génère du code qui fonctionne du premier coup dans la grande majorité des cas.

**Pourquoi Streamlit et pas Flask/FastAPI :**
Streamlit permet de construire une interface data interactive en Python pur, sans HTML ni JavaScript. Pour un projet portfolio démontrant des compétences data et IA, c'est le choix le plus lisible et le plus rapide à déployer. Une version production utiliserait React + FastAPI.

**Pourquoi tool use et pas function calling :**
L'API Anthropic appelle ça "tool use" , c'est l'équivalent du function calling d'OpenAI. L'avantage par rapport à un prompt qui demande à Claude de "générer du JSON" est la fiabilité : Claude est entraîné à appeler les outils avec les bons types de paramètres, et l'API garantit la structure de la réponse.

**Pourquoi pandas et pas SQL :**
Le dataset est un fichier CSV local. Pandas est plus simple à déployer, et Claude génère du code pandas de très bonne qualité. Une version avancée connecterait l'agent à une vraie base de données SQL via SQLAlchemy.

---

## Stack technique

- **Python 3.8+** - orchestration et logique agent
- **Anthropic API (claude-sonnet-4-6)** - compréhension langage naturel, génération de code, tool use
- **Streamlit** - interface utilisateur
- **pandas** - manipulation et analyse des données
- **Plotly** - graphiques interactifs
- **python-dotenv** - gestion de la clé API

---