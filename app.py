import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# CŒUR DU SYSTÈME : LOGIQUE TST (THERMODYNAMIQUE)
# =====================================================
@st.cache_resource
def init_tst_vault():
    # Initialisation du coffre-fort en RAM
    return {"FLUX": {}, "PRESENCE": {}, "HISTORY": set()}

VAULT = init_tst_vault()

def calculate_tst_entropy(key):
    if not key: return None
    # Cycle de Derime : Rotation horaire de la clé
    grain = datetime.datetime.now().strftime("%Y-%m-%d-%H")
    return hashlib.sha256(f"{key}-{grain}".encode()).hexdigest()[:12].upper()

# =====================================================
# DESIGN "GLASS-GABON" & INTERFACE LUDIQUE
# =====================================================
st.set_page_config(page_title="GEN-Z GABON", page_icon="🇬🇦", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: linear-gradient(180deg, #050505 0%, #0a1a12 100%); }
    
    /* Bulles de conversation Style WhatsApp/Insta */
    .message-container { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
    
    .bubble {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(12px);
        border-radius: 20px 20px 20px 5px;
        padding: 15px;
        border: 1px solid rgba(0, 255, 170, 0.2);
        max-width: 85%;
        align-self: flex-start;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }

    .tst-timer {
        font-size: 0.7em; color: #00ffaa; font-weight: bold;
        text-transform: uppercase; margin-top: 8px; display: block;
    }

    /* Logo et Header */
    .app-title {
        text-align: center; font-weight: 900; font-size: 2.8em;
        background: linear-gradient(90deg, #00ffaa, #00d4ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    
    /* Emojis Reactions */
    .react-bar { font-size: 1.2em; cursor: pointer; margin-top: 5px; opacity: 0.7; }
    .react-bar:hover { opacity: 1; }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# EN-TÊTE ET ACCÈS
# =====================================================
st.markdown('<h1 class="app-title">GEN-Z GABON</h1>', unsafe_allow_html=True)
st.caption("<center>⚡ Propulsé par le modèle thermodynamique TST</center>", unsafe_allow_html=True)

# Ici, on pourrait mettre le logo (image locale ou URL)
# st.image("logo_genz.png", width=100) 

with st.expander("🔑 CLÉ DU TUNNEL TST", expanded=True):
    user_key = st.text_input("SECRET", type="password", label_visibility="collapsed").strip().upper()

session_id = calculate_tst_entropy(user_key)

if session_id:
    # Présence temps réel
    if "u_token" not in st.session_state: st.session_state.u_token = random.randint(100, 999)
    VAULT["PRESENCE"][f"{session_id}-{st.session_state.u_token}"] = time.time()
    
    if session_id not in VAULT["FLUX"]: VAULT["FLUX"][session_id] = []

    # Détection de signal
    active_peers = [k for k, v in VAULT["PRESENCE"].items() if k.startswith(session_id) and (time.time() - v) < 20]
    if len(active_peers) > 1:
        st.success(f"🟢 SIGNAL ÉTABLI : {len(active_peers)} UNITÉS TST EN LIGNE")

    # =====================================================
    # FIL D'ACTUALITÉ (LES PLUS RÉCENTS EN BAS)
    # =====================================================
    # Nettoyage TST : On supprime ce qui a plus de 3600 secondes
    VAULT["FLUX"][session_id] = [p for p in VAULT["FLUX"][session_id] if (time.time() - p["ts"]) < 3600]

    st.markdown("---")
    chat_space = st.container()
    
    with chat_space:
        posts = VAULT["FLUX"][session_id]
        if not posts:
            st.info("👻 Aucune donnée thermodynamique dans le tunnel.")
        else:
            for i, p in enumerate(posts):
                st.markdown(f'<div class="bubble">', unsafe_allow_html=True)
                try:
                    # Déchiffrement Triadique
                    raw = Fernet(p["k"]).decrypt(p["f1"] + p["f2"] + p["f3"])
                    
                    if p["is_txt"]:
                        st.markdown(f"**{raw.decode()}**")
                    else:
                        st.caption(f"📎 {p['name']}")
                        if "image" in p["type"]: st.image(raw)
                        elif "video" in p["type"]: st.video(raw)
                        elif "audio" in p["type"]: st.audio(raw)
                        st.download_button("📥", raw, file_name=p["name"], key=f"dl_{i}_{p['ts']}")
                    
                    # Réactions style WhatsApp
                    st.markdown('<div class="react-bar">❤️ 😂 🔥 🙌 😮</div>', unsafe_allow_html=True)
                except:
                    st.error("Signal corrompu")
                
                # Timer TST
                rem = int(3600 - (time.time() - p["ts"]))
                st.markdown(f'<span class="tst-timer">⏳ ÉVAPORATION DANS {rem // 60} MIN</span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # =====================================================
    # ZONE DE SAISIE (BAS DE PAGE)
    # =====================================================
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.container():
        mode = st.tabs(["💬 Texte", "📸 Caméra", "🎙️ Micro", "📂"])
        
        data, fname, mtype, istxt = None, "", "", False

        with mode[0]:
            msg = st.chat_input("Partage ton Kongossa...")
            if msg: data, fname, mtype, istxt = msg.encode(), "txt", "text", True
        with mode[1]:
            cam = st.camera_input("Capture instantanée")
            if cam: data, fname, mtype = cam.getvalue(), "img.jpg", "image/jpeg"
        with mode[2]:
            mic = st.audio_input("Message vocal")
            if mic: data, fname, mtype = mic.getvalue(), "audio.wav", "audio/wav"
        with mode[3]:
            upl = st.file_uploader("Document", label_visibility="collapsed")
            if upl: data, fname, mtype = upl.getvalue(), upl.name, upl.type

        if data:
            # Hash anti-doublon
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

    # Rafraîchissement automatique stable
    time.sleep(10)
    st.rerun()

else:
    st.info("💡 Connectez-vous au tunnel TST pour échanger en toute liberté.")
