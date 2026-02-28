"""
Assistant de Voyage avec Mémoire PAR UTILISATEUR - Interface Streamlit
=======================================================================
Chaque utilisateur a sa propre mémoire isolée grâce à un ID unique.
Utilise Groq (gratuit) + Streamlit + JSON par utilisateur
Lancement : streamlit run My_travel_chatbot.py
"""

import streamlit as st
import requests
import json
import os
import uuid
from datetime import datetime

# ============================================================
# CONFIG PAGE
# ============================================================
st.set_page_config(
    page_title="Marco - Assistant Voyage",
    page_icon="✈️",
    layout="centered"
)

# ============================================================
# CSS PERSONNALISÉ
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

    .stApp {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        min-height: 100vh;
    }

    .titre {
        font-family: 'Playfair Display', serif;
        font-size: 2.8rem;
        color: #f0c040;
        text-align: center;
        margin-bottom: 0.2rem;
        text-shadow: 0 2px 10px rgba(240,192,64,0.3);
    }

    .sous-titre {
        text-align: center;
        color: #a8d8ea;
        font-size: 1rem;
        margin-bottom: 2rem;
    }

    .bulle-user {
        background: linear-gradient(135deg, #f0c040, #e8a020);
        color: #1a1a1a;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0 8px 20%;
        font-size: 0.95rem;
        font-weight: 500;
        box-shadow: 0 4px 15px rgba(240,192,64,0.2);
    }

    .bulle-assistant {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(168,216,234,0.3);
        color: #e8f4f8;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 20% 8px 0;
        font-size: 0.95rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }

    .label-user {
        text-align: right;
        color: #f0c040;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 5px;
        margin-bottom: 2px;
    }

    .label-assistant {
        color: #a8d8ea;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 5px;
        margin-bottom: 2px;
    }

    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONFIG GROQ
# ============================================================
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
MEMORY_DIR = "memories"  # 📁 Dossier qui contiendra un fichier JSON par utilisateur

SYSTEM_PROMPT = """Tu es Marco, un assistant de voyage passionné et expert en voyages abordables.
Tu aides les utilisateurs à planifier leurs voyages selon leur budget et leurs préférences.

Règles IMPORTANTES :
- Tu te souviens de TOUT ce que l'utilisateur a dit (destination, budget, dates, préférences, prénom)
- Tu restes toujours dans ton rôle d'expert voyage
- Tu donnes des suggestions concrètes, des prix approximatifs, des conseils pratiques
- Tu rappelles les détails passés dans tes réponses pour montrer ta mémoire
- Tu réponds toujours en français, de façon chaleureuse et enthousiaste
- Tes réponses sont concises (max 150 mots)
"""

# ============================================================
# GESTION DE L'ID UNIQUE PAR UTILISATEUR
# ============================================================
# Chaque visiteur reçoit un ID unique stocké dans sa session navigateur.
# Cet ID ne change pas entre les visites → mémoire persistante et isolée.

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())  # ex: "a3f2c1d4-..."

USER_ID = st.session_state.user_id
USER_MEMORY_FILE = os.path.join(MEMORY_DIR, f"{USER_ID}.json")

# Créer le dossier memories s'il n'existe pas
os.makedirs(MEMORY_DIR, exist_ok=True)

# ============================================================
# FONCTIONS MÉMOIRE JSON (une par utilisateur)
# ============================================================
def charger_memoire() -> list:
    """Charge l'historique de CET utilisateur uniquement."""
    if os.path.exists(USER_MEMORY_FILE):
        with open(USER_MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("historique", [])
    return []

def sauvegarder_memoire(historique: list):
    """Sauvegarde l'historique dans le fichier propre à CET utilisateur."""
    with open(USER_MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "user_id": USER_ID,
            "derniere_mise_a_jour": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "historique": historique
        }, f, ensure_ascii=False, indent=2)

# ============================================================
# INITIALISATION SESSION
# ============================================================
if "conversation_history" not in st.session_state:
    # 🧠 Charge la mémoire de CET utilisateur (invisible dans l'interface)
    st.session_state.conversation_history = charger_memoire()

if "messages_visibles" not in st.session_state:
    # 👁️ Seulement les messages de la session actuelle sont affichés
    st.session_state.messages_visibles = []

# ============================================================
# FONCTION CHAT (Groq)
# ============================================================
def chat(user_message: str) -> str:
    st.session_state.conversation_history.append({
        "role": "user", "content": user_message
    })

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.conversation_history,
        "max_tokens": 300
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        assistant_message = response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        assistant_message = f"❌ Erreur : {str(e)}"

    st.session_state.conversation_history.append({
        "role": "assistant", "content": assistant_message
    })

    # 👁️ Visible uniquement dans cette session
    st.session_state.messages_visibles.append({"role": "user", "content": user_message})
    st.session_state.messages_visibles.append({"role": "assistant", "content": assistant_message})

    # 💾 Sauvegarde dans le fichier propre à cet utilisateur
    sauvegarder_memoire(st.session_state.conversation_history)

    return assistant_message

# ============================================================
# INTERFACE
# ============================================================
st.markdown('<div class="titre">✈️ Marco</div>', unsafe_allow_html=True)
st.markdown('<div class="sous-titre">Ton assistant voyage personnel • Propulsé par Groq</div>', unsafe_allow_html=True)

if not st.session_state.messages_visibles:
    st.markdown("""
    <div style='text-align:center; color:#a8d8ea; padding: 40px 0; opacity:0.7;'>
        👋 Bonjour ! Je suis Marco, ton expert en voyages abordables.<br>
        Dis-moi où tu rêves d'aller ! 🌍
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in st.session_state.messages_visibles:
        if msg["role"] == "user":
            st.markdown('<div class="label-user">👤 Toi</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bulle-user">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="label-assistant">✈️ Marco</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bulle-assistant">{msg["content"]}</div>', unsafe_allow_html=True)

user_input = st.chat_input("Dis-moi où tu veux voyager...")
if user_input:
    with st.spinner("Marco réfléchit... ✈️"):
        chat(user_input)
    st.rerun()
