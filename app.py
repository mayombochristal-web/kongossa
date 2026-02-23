import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# CONFIGURATION & MÉMOIRE VIVE (RAM)
# =====================================================
st.set_page_config(page_title="GEN-Z GABON", page_icon="🇬🇦", layout="centered")

@st.cache_resource
def init_vault():
    # Un dictionnaire central unique pour éviter les boucles de données
    return {"FLUX": {}, "PRESENCE": {}}

VAULT = init_vault()

def secure_id(key):
    if not key: return None
    # L'ID change toutes les heures : protection contre le traçage long terme
    h = f"{key}-{datetime.datetime.now().strftime('%Y-%m-%d-%H')}"
    return hashlib.sha256(h.encode()).hexdigest()[:12].upper()

# =====================================================
# DESIGN IMMERSIF (INSTAGRAM DARK MODE)
# =====================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: #000000; }
    
    /* Bulles de conversation */
    .chat-bubble {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 18px;
        padding: 15px;
        margin: 8px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        width: fit-content;
        max-width: 85%;
    }
    
    .timer-text {
        color: #ff4b2b; font-size: 0.65em; font-weight: bold;
        display: block; margin-top: 5px; text-transform: uppercase;
    }
    
    .presence-bar {
        background: rgba(0, 255, 170, 0.1);
        color: #00ffaa; padding: 5px 15px; border-radius: 20px;
        font-size: 0.8em; text-align: center; margin-bottom: 20px;
    }

    /* Fixer la zone d'envoi en bas sur mobile */
    div[data-testid="stExpander"] { border: none !important; }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# LOGIQUE DE SESSION
# =====================================================
st.markdown('<h1 style="text-align:center; color:#00ffaa; font-weight:900;">GEN-Z GABON</h1>', unsafe_allow_html=True)

with st.expander("🔑 CLÉ DU TUNNEL", expanded=True):
    secret_key = st.text_input("SECRET", type="password", label_visibility="collapsed").strip().upper()

session_id = secure_id(secret_key)

if session_id:
    # Système de présence (anti-ghosting)
    if "u_token" not in st.session_state: st.session_state.u_token = random.randint(100, 999)
    VAULT["PRESENCE"][f"{session_id}-{st.session_state.u_token}"] = time.time()
    
    if session_id not in VAULT["FLUX"]: VAULT["FLUX"][session_id] = []

    # Vérifier si la sœur est là
    others = [k for k, v in VAULT["PRESENCE"].items() if k.startswith(session_id) and (time.time() - v) < 15]
    if len(others) > 1:
        st.markdown('<div class="presence-bar">● TA SŒUR EST EN LIGNE</div>', unsafe_allow_html=True)

    # =====================================================
    # 1. FIL DE CONVERSATION (LES DERNIERS EN BAS)
    # =====================================================
    # Nettoyage automatique des messages expirés (3600s = 1h)
    VAULT["FLUX"][session_id] = [p for p in VAULT["FLUX"][session_id] if (time.time() - p["timestamp"]) < 3600]
    
    chat_container = st.container()
    with chat_container:
        posts = VAULT["FLUX"][session_id]
        if not posts:
            st.caption("<center>Aucun message. Le tunnel est vierge.</center>", unsafe_allow_html=True)
        else:
            for i, p in enumerate(posts): # Ordre chronologique : premier arrivé en haut
                with st.container():
                    st.markdown('<div class="chat-bubble">', unsafe_allow_html=True)
                    try:
                        # Reconstitution Triadique
                        data = Fernet(p["k"]).decrypt(p["f1"] + p["f2"] + p["f3"])
                        
                        if p["is_txt"]:
                            st.markdown(f"**{data.decode()}**")
                        else:
                            st.caption(f"📎 {p['name']}")
                            if "image" in p["type"]: st.image(data)
                            elif "video" in p["type"]: st.video(data)
                            elif "audio" in p["type"] or p["name"].endswith(('.aac', '.m4a', '.wav')):
                                st.audio(data)
                            st.download_button("💾 Aspirer", data, file_name=p["name"], key=f"dl_{i}")
                    except:
                        st.error("🔒 Fragment corrompu")
                    
                    # Timer visuel
                    rem = int(3600 - (time.time() - p["timestamp"]))
                    st.markdown(f'<span class="timer-text">🔥 DISSIPATION DANS {rem // 60} min</span>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

    # =====================================================
    # 2. PANNEAU D'ENVOI (EN BAS)
    # =====================================================
    st.markdown("---")
    with st.expander("➕ ENVOYER UN SIGNAL", expanded=True):
        mode = st.tabs(["💬 Texte", "📷 Caméra", "🎙️ Micro", "📂"])
        
        content, name, m_type, is_txt = None, "", "", False

        with mode[0]:
            msg = st.chat_input("Kongossa...")
            if msg: content, name, m_type, is_txt = msg.encode(), "txt", "text", True
        with mode[1]:
            photo = st.camera_input("Shoot")
            if photo: content, name, m_type = photo.getvalue(), "img.jpg", "image/jpeg"
        with mode[2]:
            vocal = st.audio_input("Vocal")
            if vocal: content, name, m_type = vocal.getvalue(), "voice.wav", "audio/wav"
        with mode[3]:
            f = st.file_uploader("Fichier", label_visibility="collapsed")
            if f: content, name, m_type = f.getvalue(), f.name, f.type

        if content:
            # Sécurité Triadique (Chiffrement + Éclatement)
            key = Fernet.generate_key()
            box = Fernet(key).encrypt(content)
            l = len(box)
            VAULT["FLUX"][session_id].append({
                "f1": box[:l//3], "f2": box[l//3:2*l//3], "f3": box[2*l//3:],
                "k": key, "name": name, "type": m_type, "is_txt": is_txt,
                "timestamp": time.time()
            })
            st.rerun()

    # =====================================================
    # 3. ANTI-RAM ET AUTO-REFRESH
    # =====================================================
    # Rafraîchissement lent (10s) pour éviter de faire ramer Streamlit
    time.sleep(10)
    st.rerun()

else:
    st.info("🔐 Le tunnel attend votre clé secrète pour se manifester.")
