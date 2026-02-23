import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# CONFIGURATION & MÉMOIRE (RAM SÉCURISÉE)
# =====================================================
st.set_page_config(page_title="GEN-Z GABON", page_icon="🇬🇦", layout="centered")

@st.cache_resource
def init_vault():
    # Initialisation propre avec toutes les clés nécessaires
    return {
        "FLUX": {}, 
        "PRESENCE": {}, 
        "HISTORY": set(),
        "SEEN_IDS": set() # Ajout explicite pour éviter le KeyError
    }

VAULT = init_vault()

def secure_id(key):
    if not key: return None
    h = f"{key}-{datetime.datetime.now().strftime('%Y-%m-%d-%H')}"
    return hashlib.sha256(h.encode()).hexdigest()[:12].upper()

# =====================================================
# DESIGN DARK MODE (GLASSMORPHISM)
# =====================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background-color: #000000; color: #ffffff; }
    
    .chat-bubble {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(12px);
        border-radius: 22px;
        padding: 18px;
        margin: 12px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        width: fit-content;
        max-width: 88%;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    
    .timer { color: #ff4b2b; font-size: 0.75em; font-weight: bold; margin-top: 8px; display: block; }
    .status-active { color: #00ffaa; font-size: 0.85em; text-align: center; font-weight: 600; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# LOGIQUE D'ACCÈS
# =====================================================
st.markdown('<h1 style="text-align:center; color:#00ffaa; font-weight:900; letter-spacing:-1px;">GEN-Z GABON</h1>', unsafe_allow_html=True)

with st.expander("🔑 CLÉ DU TUNNEL", expanded=True):
    secret_key = st.text_input("SECRET", type="password", label_visibility="collapsed").strip().upper()

session_id = secure_id(secret_key)

if session_id:
    # Gestion de présence & Initialisation session
    if "u_token" not in st.session_state: 
        st.session_state.u_token = random.randint(100, 999)
    
    VAULT["PRESENCE"][f"{session_id}-{st.session_state.u_token}"] = time.time()
    
    if session_id not in VAULT["FLUX"]: 
        VAULT["FLUX"][session_id] = []

    # Affichage présence de la sœur
    others = [k for k, v in VAULT["PRESENCE"].items() if k.startswith(session_id) and (time.time() - v) < 20]
    if len(others) > 1:
        st.markdown(f'<div class="status-active">● SIGNAL ACTIF : CONNEXION ÉTABLIE</div>', unsafe_allow_html=True)

    # =====================================================
    # 1. FIL DE DISCUSSION (FLUX CHRONOLOGIQUE)
    # =====================================================
    # Nettoyage auto des messages de plus de 60 min
    VAULT["FLUX"][session_id] = [p for p in VAULT["FLUX"][session_id] if (time.time() - p["ts"]) < 3600]
    
    st.markdown("---")
    chat_container = st.container()
    with chat_container:
        posts = VAULT["FLUX"][session_id]
        if not posts:
            st.caption("<center>Aucun message. Le tunnel est vide.</center>", unsafe_allow_html=True)
        else:
            for i, p in enumerate(posts):
                st.markdown('<div class="chat-bubble">', unsafe_allow_html=True)
                try:
                    # Reconstruction Triadique Sécurisée
                    k_obj = p.get("k")
                    fragments = p.get("f1", b"") + p.get("f2", b"") + p.get("f3", b"")
                    
                    if k_obj and fragments:
                        data = Fernet(k_obj).decrypt(fragments)
                        
                        if p.get("is_txt"):
                            st.markdown(f"{data.decode()}")
                        else:
                            st.caption(f"📁 {p['name']}")
                            if "image" in p["type"]: st.image(data)
                            elif "video" in p["type"]: st.video(data)
                            elif "audio" in p["type"] or p["name"].lower().endswith(('.aac', '.m4a', '.wav', '.mp3')):
                                st.audio(data)
                            st.download_button("💾 Aspirer", data, file_name=p["name"], key=f"dl_{i}_{p['ts']}")
                except:
                    st.error("🔒 Fragment illisible")
                
                rem = int(3600 - (time.time() - p["ts"]))
                st.markdown(f'<span class="timer">🔥 AUTO-DESTRUCT : {rem // 60} min</span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # =====================================================
    # 2. CAPTURE & ENVOI (ANTI-BOUCLE)
    # =====================================================
    st.markdown("---")
    with st.container():
        mode = st.tabs(["💬", "📸", "🎙️", "📂"])
        
        raw_to_send, f_name, m_type, is_txt = None, "", "", False

        with mode[0]:
            t_in = st.chat_input("Message...")
            if t_in: raw_to_send, f_name, m_type, is_txt = t_in.encode(), "txt", "text", True
        with mode[1]:
            cam = st.camera_input("Shoot")
            if cam: raw_to_send, f_name, m_type = cam.getvalue(), "img.jpg", "image/jpeg"
        with mode[2]:
            mic = st.audio_input("Vocal")
            if mic: raw_to_send, f_name, m_type = mic.getvalue(), "audio.wav", "audio/wav"
        with mode[3]:
            upl = st.file_uploader("Fichier", label_visibility="collapsed")
            if upl: raw_to_send, f_name, m_type = upl.getvalue(), upl.name, upl.type

        if raw_to_send:
            # Hash unique pour bloquer les doublons (Audio/Photo)
            msg_id = hashlib.md5(raw_to_send + str(round(time.time(), 1)).encode()).hexdigest()
            
            # Sécurité supplémentaire : On vérifie si SEEN_IDS existe avant l'usage
            if "HISTORY" not in VAULT: VAULT["HISTORY"] = set()
            
            if msg_id not in VAULT["HISTORY"]:
                k = Fernet.generate_key()
                box = Fernet(k).encrypt(raw_to_send)
                l = len(box)
                
                VAULT["FLUX"][session_id].append({
                    "f1": box[:l//3], "f2": box[l//3:2*l//3], "f3": box[2*l//3:],
                    "k": k, "name": f_name, "type": m_type, "is_txt": is_txt,
                    "ts": time.time(), "msg_id": msg_id
                })
                VAULT["HISTORY"].add(msg_id)
                st.rerun()

    # Contrôle de destruction globale
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🧨 DISPERSER TOUT LE TUNNEL", use_container_width=True):
        VAULT["FLUX"][session_id] = []
        st.rerun()

    # Rafraîchissement stable (10s) pour éviter les lags serveurs
    time.sleep(10)
    st.rerun()

else:
    st.info("🔐 Entrez la clé secrète pour manifester la GEN-Z GABON.")
