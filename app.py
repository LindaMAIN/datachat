import streamlit as st
from src.data_loader import load_superstore, get_schema, get_quick_stats
from src.agent import DataChatAgent

# ─── CONFIG PAGE ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DataChat",
    page_icon="💬",
    layout="wide"
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1F4E79;
        margin-bottom: 0;
    }
    .sub-header {
        color: #888;
        font-size: 0.9rem;
        margin-top: 0;
    }
    .stat-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 4px solid #1F4E79;
    }
    .tool-badge {
        background: #e8f4f8;
        color: #1F4E79;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ─── CHARGEMENT DES DONNEES ────────────────────────────────────────────────────
@st.cache_resource
def init_agent():
    df = load_superstore('src/data/superstore.csv')
    schema = get_schema(df)
    agent = DataChatAgent(df, schema)
    return agent, get_quick_stats(df)


agent, stats = init_agent()


# ─── HEADER ───────────────────────────────────────────────────────────────────
col_title, col_reset = st.columns([5, 1])
with col_title:
    st.markdown('<p class="main-header">DataChat</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Agent conversationnel sur donnees Superstore Sales — Anthropic API</p>',
                unsafe_allow_html=True)
with col_reset:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Reinitialiser", type="secondary"):
        agent.reset()
        st.session_state.messages = []
        st.rerun()

st.divider()

# ─── STATS DASHBOARD ──────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Commandes", f"{stats['nb_orders']:,}")
c2.metric("Clients", f"{stats['nb_customers']:,}")
c3.metric("Produits", f"{stats['nb_products']:,}")
c4.metric("Ventes totales", f"${stats['total_sales']:,.0f}")
c5.metric("Profit total", f"${stats['total_profit']:,.0f}")

st.caption(f"Periode : {stats['date_range']} | Regions : {', '.join(stats['regions'])} | Categories : {', '.join(stats['categories'])}")

st.divider()

# ─── QUESTIONS SUGGÉREES ──────────────────────────────────────────────────────
st.markdown("**Questions suggérées :**")
suggestions = [
    "Quels sont les 5 produits les plus vendus ?",
    "Compare les ventes 2016 et 2017",
    "Montre-moi un graphique des ventes par categorie",
    "Quelle region est la moins rentable et pourquoi ?",
    "Quels clients ont le panier moyen le plus élevé ?"
]

cols = st.columns(len(suggestions))
for i, (col, suggestion) in enumerate(zip(cols, suggestions)):
    with col:
        if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
            st.session_state.pending_message = suggestion

st.divider()

# ─── HISTORIQUE DE CONVERSATION ───────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Affiche l'historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("table"):
            import pandas as pd
            df_result = pd.DataFrame(
                msg["table"]["data"],
                columns=msg["table"]["columns"]
            )
            st.dataframe(df_result, use_container_width=True)
        if msg.get("chart"):
            st.plotly_chart(msg["chart"], use_container_width=True)
        if msg.get("export"):
            st.download_button(
                label="Telecharger les resultats",
                data=msg["export"]["data"],
                file_name=msg["export"]["filename"],
                mime="text/csv" if msg["export"]["format"] == "csv" else
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        if msg.get("tool_used"):
            st.markdown(f'<span class="tool-badge">Outil : {msg["tool_used"]}</span>',
                        unsafe_allow_html=True)


# ─── INPUT UTILISATEUR ────────────────────────────────────────────────────────
# Gere les messages venant des boutons suggestion
if "pending_message" in st.session_state:
    user_input = st.session_state.pending_message
    del st.session_state.pending_message
else:
    user_input = st.chat_input("Posez une question sur les données Superstore...")


if user_input:
    # Affiche le message utilisateur
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Appel agent
    with st.chat_message("assistant"):
        with st.spinner("Analyse en cours..."):
            result = agent.chat(user_input)

        st.markdown(result["text"])

        if result.get("table"):
            import pandas as pd
            df_result = pd.DataFrame(
                result["table"]["data"],
                columns=result["table"]["columns"]
            )
            st.dataframe(df_result, use_container_width=True)

        if result.get("chart"):
            st.plotly_chart(result["chart"], use_container_width=True)

        if result.get("export"):
            st.download_button(
                label="Telecharger les resultats",
                data=result["export"]["data"],
                file_name=result["export"]["filename"],
                mime="text/csv"
            )

        if result.get("tool_used"):
            st.markdown(f'<span class="tool-badge">Outil : {result["tool_used"]}</span>',
                        unsafe_allow_html=True)

    # Sauvegarde dans l'historique
    st.session_state.messages.append({
        "role": "assistant",
        "content": result["text"],
        "table": result.get("table"),
        "chart": result.get("chart"),
        "export": result.get("export"),
        "tool_used": result.get("tool_used")
    })