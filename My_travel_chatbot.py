"""
Assistant de Voyage avec Mémoire PERSISTANTE - Interface Streamlit
==================================================================
Exercice : Role-Based Assistant avec Chat Memory
Utilise Ollama (100% gratuit, local) + Streamlit + JSON (mémoire persistante)

Lancement : streamlit run app_travel.py
"""

import streamlit as st
import requests
import json
import os
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

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

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
        backdrop-filter: blur(10px);
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

    .memoire-box {
        background: rgba(0,0,0,0.3);
        border: 1px solid rgba(168,216,234,0.2);
        border-radius: 12px;
        padding: 15px;
        margin-top: 10px;
        color: #a8d8ea;
        font-size: 0.82rem;
        font-family: 'Courier New', monospace;
        white-space: pre-wrap;
    }

    .badge-persistant {
        background: rgba(80,200,120,0.2);
        border: 1px solid rgba(80,200,120,0.4);
        color: #50c878;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.8rem;
        font-weight: 600;
        text-align: center;
        margin-bottom: 1rem;
    }

    .stButton > button {
        background: linear-gradient(135deg, #f0c040, #e8a020);
        color: #1a1a1a;
        border: none;
        border-radius: 25px;
        font-weight: 600;
        padding: 8px 20px;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(240,192,64,0.4);
    }

    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# ÉTAPE 1 : Rôle de l'assistant
# ============================================================
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

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma3:1b"
MEMORY_FILE = "chat_memory.json"  # 💾 Fichier de sauvegarde


# ============================================================
# FONCTIONS DE SAUVEGARDE / CHARGEMENT JSON
# ============================================================
def charger_memoire() -> list:
    """Charge l'historique depuis le fichier JSON si il existe."""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("historique", [])
    return []


def sauvegarder_memoire(historique: list):
    """Sauvegarde l'historique dans le fichier JSON après chaque message."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "derniere_mise_a_jour": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "nb_tours": len([m for m in historique if m["role"] == "user"]),
            "historique": historique
        }, f, ensure_ascii=False, indent=2)


def effacer_memoire():
    """Efface la mémoire RAM + fichier JSON."""
    st.session_state.conversation_history = []
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)


# ============================================================
# ÉTAPE 2 : Initialisation — charge depuis JSON au démarrage
# ============================================================
if "conversation_history" not in st.session_state:
    # 🧠 Charge l'historique complet en mémoire (invisible pour l'utilisateur)
    st.session_state.conversation_history = charger_memoire()

if "messages_visibles" not in st.session_state:
    # 👁️ Seulement les messages de la session actuelle sont affichés
    st.session_state.messages_visibles = []

if "show_memory" not in st.session_state:
    st.session_state.show_memory = False


# ============================================================
# FONCTION CHAT
# ============================================================
def chat(user_message: str) -> str:
    """Envoie un message, maintient et sauvegarde l'historique."""

    st.session_state.conversation_history.append({
        "role": "user",
        "content": user_message
    })

    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.conversation_history,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        assistant_message = response.json()["message"]["content"]
    except requests.exceptions.ConnectionError:
        assistant_message = "❌ Ollama n'est pas lancé ! Tape `ollama serve` dans ton terminal."
    except Exception as e:
        assistant_message = f"❌ Erreur : {str(e)}"

    st.session_state.conversation_history.append({
        "role": "assistant",
        "content": assistant_message
    })

    # 👁️ Ajoute aux messages visibles (session actuelle uniquement)
    st.session_state.messages_visibles.append({"role": "user", "content": user_message})
    st.session_state.messages_visibles.append({"role": "assistant", "content": assistant_message})

    # 💾 Sauvegarde automatique après chaque échange
    sauvegarder_memoire(st.session_state.conversation_history)

    return assistant_message


# ============================================================
# INTERFACE
# ============================================================

st.markdown('<div class="titre">✈️ Marco</div>', unsafe_allow_html=True)
st.markdown('<div class="sous-titre">Ton assistant voyage personnel • Propulsé par Ollama</div>', unsafe_allow_html=True)

# Badge mémoire persistante (affiché seulement si un fichier existe)


# Affichage — seulement les messages de cette session (historique ancien = caché)
if not st.session_state.messages_visibles:
    st.markdown("""
    <div style='text-align:center; color:#a8d8ea; padding: 40px 0; opacity:0.7;'>
        👋 Bonjour ! Je suis Marco, ton expert en voyages abordables.<br>
        Dis-moi où tu rêves d'aller ! 🌍
    </div>
    """, unsafe_allow_html=True)
else:
    # 👁️ Seulement ce que l'utilisateur a tapé dans cette session est visible
    for msg in st.session_state.messages_visibles:
        if msg["role"] == "user":
            st.markdown('<div class="label-user">👤 Toi</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bulle-user">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="label-assistant">✈️ Marco</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bulle-assistant">{msg["content"]}</div>', unsafe_allow_html=True)

# Input utilisateur
user_input = st.chat_input("Dis-moi où tu veux voyager...")

if user_input:
    with st.spinner("Marco réfléchit... ✈️"):
        chat(user_input)
    st.rerun()