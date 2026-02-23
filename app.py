import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random
import base64

# =====================================================
# CONFIGURATION & LOGO
# =====================================================
st.set_page_config(page_title="GEN-Z GABON", page_icon="🇬🇦", layout="centered")

def get_base64_logo(file_path):
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""

LOGO_B64 = get_base64_logo("logo.png")  # Placez un fichier logo.png dans le répertoire

# =====================================================
# SYSTÈME DE GESTION (RAM UNIQUEMENT)
# =====================================================
@st.cache_resource
def init_vault():
    return {"FLUX": {}, "PRESENCE": {}}

VAULT = init_vault()

def secure_id(key):
    if not key:
        return None
    h = f"{key}-{datetime.datetime.now().strftime('%Y-%m-%d-%H')}"
    return hashlib.sha256(h.encode()).hexdigest()[:12].upper()

# =====================================================
# DESIGN "FUTURISTIC GABON" (CSS)
# =====================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600&display=swap');
    
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: linear-gradient(180deg, #050505 0%, #0a1a12 100%); }
    
    /* Logo central */
    .logo-container { text-align: center; padding: 20px; }
    .logo-img { width: 120px; filter: drop-shadow(0 0 15px #00ffaa); }

    /* Glassmorphism Cards */
    .post-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(12px);
        border-radius: 24px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        transition: 0.3s;
    }
    .post-card:hover { border: 1px solid #00ffaa; }

    /* Status Presence */
    .status-active { color: #00ffaa; font-size: 0.8em; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Header */
    .app-title { 
        background: linear-gradient(90deg, #00ffaa, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5em; font-weight: 800; text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# INTERFACE PRINCIPALE
# =====================================================
st.markdown('<div class="logo-container">', unsafe_allow_html=True)
if LOGO_B64:
    st.markdown(f'<img src="data:image/png;base64,{LOGO_B64}" class="logo-img">', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<h1 class="app-title">GEN-Z GABON</h1>', unsafe_allow_html=True)
st.caption("<center>L'espace où ta voix est souveraine. Éphémère. Indestructible.</center>", unsafe_allow_html=True)

# Connexion
secret_key = st.text_input("🔑 CLÉ DU TUNNEL", type="password", placeholder="Entre ton code secret...").strip().upper()
session_id = secure_id(secret_key)

if session_id:
    # Initialisation de la session utilisateur
    if "user_token" not in st.session_state:
        st.session_state.user_token = random.randint(1000, 9999)
    
    # Mise à jour de la présence
    presence_key = f"{session_id}-{st.session_state.user_token}"
    VAULT["PRESENCE"][presence_key] = time.time()
    
    # Nettoyage des présences expirées (plus de 15 secondes)
    current_time = time.time()
    expired_presence = [k for k, t in VAULT["PRESENCE"].items() if current_time - t > 15]
    for k in expired_presence:
        VAULT["PRESENCE"].pop(k, None)
    
    # Initialisation du flux pour cette session si nécessaire
    if session_id not in VAULT["FLUX"]:
        VAULT["FLUX"][session_id] = []
    
    # Nettoyage des messages de plus de 60 minutes
    VAULT["FLUX"][session_id] = [p for p in VAULT["FLUX"][session_id] if (current_time - p.get("time_obj", 0)) < 3600]
    
    # Vérification de la présence d'autres utilisateurs
    active_peers = [k for k in VAULT["PRESENCE"].keys() if k.startswith(session_id) and k != presence_key]
    if active_peers:
        st.markdown('<p class="status-active">● SIGNAL DÉTECTÉ : TA SŒUR EST EN LIGNE</p>', unsafe_allow_html=True)

    # --- FIL D'ACTUALITÉ ---
    st.markdown("### 🌟 Fil d'Actualité")
    feed_placeholder = st.empty()
    
    with feed_placeholder.container():
        posts = VAULT["FLUX"][session_id]
        if not posts:
            st.info("Le tunnel est vide. Brise le silence.")
        else:
            # Afficher les messages du plus récent au plus ancien
            for i, p in enumerate(reversed(posts)):
                st.markdown('<div class="post-card">', unsafe_allow_html=True)
                st.caption(f"🕒 {p['time']}")
                try:
                    # Reconstruction triadique
                    raw = p["f1"] + p["f2"] + p["f3"]
                    data = Fernet(p["k"]).decrypt(raw)
                    
                    if p["is_txt"]:
                        st.markdown(f"**{data.decode()}**")
                    else:
                        st.write(f"📁 {p['name']}")
                        if "image" in p["type"]:
                            st.image(data)
                        elif "video" in p["type"]:
                            st.video(data)
                        elif "audio" in p["type"] or p["name"].lower().endswith(('.aac', '.m4a', '.wav', '.mp3')):
                            st.audio(data)
                        else:
                            st.download_button("💾 Aspirer", data, file_name=p["name"], key=f"dl_{i}")
                except Exception as e:
                    st.error(f"Erreur de signal : {str(e)}")
                st.markdown('</div>', unsafe_allow_html=True)

    # --- BARRE D'ENVOI ---
    st.markdown("---")
    with st.container():
        mode = st.radio("Publier :", ["💬 Texte", "📸 Média"], horizontal=True)
        
        content, name, m_type, is_txt = None, "", "", False
        
        if mode == "💬 Texte":
            msg = st.chat_input("Exprime-toi...")
            if msg:
                content = msg.encode()
                name = "txt"
                m_type = "text"
                is_txt = True
        else:
            f = st.file_uploader("Upload tout média (AAC, MP4, JPG...)", type=None)
            if f:
                content = f.getvalue()
                name = f.name
                m_type = f.type or "application/octet-stream"
                is_txt = False

        if content:
            # Chiffrement triadique
            key = Fernet.generate_key()
            cipher = Fernet(key)
            encrypted = cipher.encrypt(content)
            l = len(encrypted)
            fragment1 = encrypted[:l//3]
            fragment2 = encrypted[l//3:2*l//3]
            fragment3 = encrypted[2*l//3:]
            
            # Ajout au flux avec timestamp
            VAULT["FLUX"][session_id].append({
                "f1": fragment1,
                "f2": fragment2,
                "f3": fragment3,
                "k": key,
                "name": name,
                "type": m_type,
                "is_txt": is_txt,
                "time": datetime.datetime.now().strftime("%H:%M"),
                "time_obj": time.time()  # Pour le nettoyage
            })
            st.balloons()
            st.rerun()

    # Rafraîchissement automatique toutes les 5 secondes pour voir les nouveaux messages
    time.sleep(5)
    st.rerun()

else:
    st.warning("Tunnel scellé. Entre ton secret pour voir le flux.")