import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# CONFIGURATION & MÉMOIRE (RAM UNIQUEMENT)
# =====================================================
st.set_page_config(page_title="GEN-Z GABON", page_icon="🇬🇦", layout="centered")

@st.cache_resource
def init_vault():
    # Utilisation d'un dictionnaire simple pour une stabilité maximale
    return {"FLUX": {}, "PRESENCE": {}, "HISTORY": set()}

VAULT = init_vault()

def secure_id(key):
    if not key: return None
    # Rotation horaire pour briser le traçage
    h = f"{key}-{datetime.datetime.now().strftime('%Y-%m-%d-%H')}"
    return hashlib.sha256(h.encode()).hexdigest()[:12].upper()

# =====================================================
# DESIGN DARK MODE (INSTAGRAM STYLE)
# =====================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background-color: #000000; }
    
    .chat-bubble {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        width: fit-content;
        max-width: 90%;
    }
    
    .timer { color: #ff4b2b; font-size: 0.7em; font-weight: bold; margin-top: 5px; display: block; }
    .status { color: #00ffaa; font-size: 0.8em; text-align: center; font-weight: bold; margin-bottom: 10px; }
    
    /* Optimisation pour mobile */
    .stButton>button { border-radius: 20px; }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# ACCÈS SÉCURISÉ
# =====================================================
st.markdown('<h1 style="text-align:center; color:#00ffaa; font-weight:900;">GEN-Z GABON</h1>', unsafe_allow_html=True)

with st.expander("🔑 CLÉ DU TUNNEL", expanded=True):
    secret_key = st.text_input("SECRET", type="password", label_visibility="collapsed").strip().upper()

session_id = secure_id(secret_key)

if session_id:
    # Présence
    if "u_token" not in st.session_state: st.session_state.u_token = random.randint(100, 999)
    VAULT["PRESENCE"][f"{session_id}-{st.session_state.u_token}"] = time.time()
    
    if session_id not in VAULT["FLUX"]: VAULT["FLUX"][session_id] = []

    # UI Presence
    others = [k for k, v in VAULT["PRESENCE"].items() if k.startswith(session_id) and (time.time() - v) < 20]
    if len(others) > 1:
        st.markdown(f'<div class="status">● SIGNAL ACTIF : TA SŒUR EST EN LIGNE</div>', unsafe_allow_html=True)

    # =====================================================
    # 1. FIL DE DISCUSSION (CHRONOLOGIQUE - BAS)
    # =====================================================
    # Nettoyage automatique des vieux messages (1h)
    VAULT["FLUX"][session_id] = [p for p in VAULT["FLUX"][session_id] if (time.time() - p["ts"]) < 3600]
    
    st.markdown("---")
    container = st.container()
    with container:
        posts = VAULT["FLUX"][session_id]
        if not posts:
            st.caption("<center>Tunnel vide. Émettez un signal.</center>", unsafe_allow_html=True)
        else:
            for i, p in enumerate(posts):
                st.markdown('<div class="chat-bubble">', unsafe_allow_html=True)
                try:
                    # Reconstruction Triadique avec vérification
                    if all(k in p for k in ["f1", "f2", "f3", "k"]):
                        raw = Fernet(p["k"]).decrypt(p["f1"] + p["f2"] + p["f3"])
                        
                        if p["is_txt"]:
                            st.markdown(f"{raw.decode()}")
                        else:
                            st.caption(f"📁 {p['name']}")
                            if "image" in p["type"]: st.image(raw)
                            elif "video" in p["type"]: st.video(raw)
                            elif "audio" in p["type"] or p["name"].lower().endswith(('.aac', '.m4a', '.wav', '.mp3')):
                                st.audio(raw)
                            st.download_button("💾 Aspirer", raw, file_name=p["name"], key=f"dl_{i}_{p['ts']}")
                    else:
                        st.error("⚠️ Fragment manquant")
                except Exception:
                    st.error("🔒 Erreur de déchiffrement")
                
                rem = int(3600 - (time.time() - p["ts"]))
                st.markdown(f'<span class="timer">🔥 AUTO-DESTRUCT : {rem // 60}m</span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # =====================================================
    # 2. ZONE D'ENVOI (ANTI-DOUBLON)
    # =====================================================
    st.markdown("---")
    with st.container():
        mode = st.tabs(["💬", "📷", "🎙️", "📂"])
        
        data, fname, mtype, istxt = None, "", "", False

        with mode[0]:
            txt = st.chat_input("Écris ici...")
            if txt: data, fname, mtype, istxt = txt.encode(), "txt", "text", True
        with mode[1]:
            cam = st.camera_input("Photo")
            if cam: data, fname, mtype = cam.getvalue(), "img.jpg", "image/jpeg"
        with mode[2]:
            mic = st.audio_input("Vocal")
            if mic: data, fname, mtype = mic.getvalue(), "audio.wav", "audio/wav"
        with mode[3]:
            upl = st.file_uploader("Fichier", label_visibility="collapsed")
            if upl: data, fname, mtype = upl.getvalue(), upl.name, upl.type

        if data:
            # Création d'une empreinte unique pour éviter la répétition
            msg_id = hashlib.md5(data + str(round(time.time(), 1)).encode()).hexdigest()
            
            if msg_id not in VAULT["HISTORY"]:
                k = Fernet.generate_key()
                box = Fernet(k).encrypt(data)
                l = len(box)
                
                VAULT["FLUX"][session_id].append({
                    "f1": box[:l//3], "f2": box[l//3:2*l//3], "f3": box[2*l//3:],
                    "k": k, "name": fname, "type": mtype, "is_txt": istxt,
                    "ts": time.time(), "id": msg_id
                })
                VAULT["HISTORY"].add(msg_id)
                st.rerun()

    # Contrôle souverain
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🧨 DISPERSER LE TUNNEL", use_container_width=True):
        VAULT["FLUX"][session_id] = []
        st.rerun()

    # Refresh automatique stable
    time.sleep(8)
    st.rerun()

else:
    st.info("👋 Entrez votre clé secrète pour ouvrir la GEN-Z GABON.")
