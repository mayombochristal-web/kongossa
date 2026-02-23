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
    # Structure unique pour éviter les collisions de données
    return {"FLUX": {}, "PRESENCE": {}, "SEEN_IDS": set()}

VAULT = init_vault()

def secure_id(key):
    if not key: return None
    h = f"{key}-{datetime.datetime.now().strftime('%Y-%m-%d-%H')}"
    return hashlib.sha256(h.encode()).hexdigest()[:12].upper()

# =====================================================
# DESIGN DARK MODE INSTAGRAM
# =====================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: #000000; color: #ffffff; }
    
    .chat-bubble {
        background: rgba(255, 255, 255, 0.07);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        width: fit-content;
        max-width: 90%;
        animation: fadeIn 0.3s ease-in;
    }
    @keyframes fadeIn { from {opacity:0; transform: translateY(10px);} to {opacity:1; transform: translateY(0);} }
    
    .timer-text { color: #ff4b2b; font-size: 0.7em; font-weight: bold; margin-top: 8px; display: block; }
    .presence-tag { color: #00ffaa; font-size: 0.8em; text-align: center; margin-bottom: 15px; font-weight: bold; }
    .destruct-btn { background: linear-gradient(45deg, #8b0000, #ff0000) !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# ACCÈS & SÉCURITÉ
# =====================================================
st.markdown('<h1 style="text-align:center; color:#00ffaa; font-weight:900; margin-bottom:0;">GEN-Z GABON</h1>', unsafe_allow_html=True)
st.caption("<center>Communication Souveraine & Éthique</center>", unsafe_allow_html=True)

with st.expander("🔑 ACCÈS AU TUNNEL", expanded=True):
    secret_key = st.text_input("CLE", type="password", label_visibility="collapsed").strip().upper()

session_id = secure_id(secret_key)

if session_id:
    # Présence active
    if "u_token" not in st.session_state: st.session_state.u_token = random.randint(100, 999)
    VAULT["PRESENCE"][f"{session_id}-{st.session_state.u_token}"] = time.time()
    
    if session_id not in VAULT["FLUX"]: VAULT["FLUX"][session_id] = []

    # UI Présence
    others = [k for k, v in VAULT["PRESENCE"].items() if k.startswith(session_id) and (time.time() - v) < 20]
    if len(others) > 1:
        st.markdown(f'<div class="presence-tag">● SIGNAL ÉTABLI ({len(others)} CONNECTÉS)</div>', unsafe_allow_html=True)

    # =====================================================
    # 1. FIL DE CONVERSATION (CHRONOLOGIQUE - BAS)
    # =====================================================
    # Nettoyage automatique des messages expirés (1h)
    VAULT["FLUX"][session_id] = [p for p in VAULT["FLUX"][session_id] if (time.time() - p["timestamp"]) < 3600]
    
    st.markdown("---")
    chat_area = st.container()
    with chat_area:
        posts = VAULT["FLUX"][session_id]
        if not posts:
            st.info("Le tunnel est vide. Brise le silence.")
        else:
            for i, p in enumerate(posts):
                st.markdown('<div class="chat-bubble">', unsafe_allow_html=True)
                try:
                    # Déchiffrement Triadique
                    raw_data = Fernet(p["k"]).decrypt(p["f1"] + p["f2"] + p["f3"])
                    
                    if p["is_txt"]:
                        st.markdown(f"{raw_data.decode()}")
                    else:
                        st.caption(f"📁 {p['name']}")
                        if "image" in p["type"]: st.image(raw_data)
                        elif "video" in p["type"]: st.video(raw_data)
                        elif "audio" in p["type"] or p["name"].lower().endswith(('.aac', '.m4a', '.wav', '.mp3')):
                            st.audio(raw_data)
                        st.download_button("💾 Aspirer", raw_data, file_name=p["name"], key=f"dl_{p['msg_hash']}")
                except:
                    st.error("🔒 Erreur de fragment")
                
                rem = int(3600 - (time.time() - p["timestamp"]))
                st.markdown(f'<span class="timer-text">🔥 DISPARITION DANS {rem // 60} MIN</span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # =====================================================
    # 2. ZONE D'ENVOI & CAPTURE MÉDIA
    # =====================================================
    st.markdown("---")
    with st.container():
        mode = st.tabs(["💬", "📷", "🎙️", "📂"])
        
        data_to_send, file_name, mime_type, is_text = None, "", "", False

        with mode[0]:
            t_input = st.chat_input("Ton message...")
            if t_input: data_to_send, file_name, mime_type, is_text = t_input.encode(), "txt", "text", True
        with mode[1]:
            cam = st.camera_input("Photo live")
            if cam: data_to_send, file_name, mime_type = cam.getvalue(), "img.jpg", "image/jpeg"
        with mode[2]:
            audio = st.audio_input("Vocal live")
            if audio: data_to_send, file_name, mime_type = audio.getvalue(), "audio.wav", "audio/wav"
        with mode[3]:
            f = st.file_uploader("Fichier", label_visibility="collapsed")
            if f: data_to_send, file_name, mime_type = f.getvalue(), f.name, f.type

        # TRAITEMENT ANTI-BOUCLE
        if data_to_send:
            # Créer un hash unique du message pour éviter les doublons
            msg_hash = hashlib.md5(data_to_send + str(time.time() // 1).encode()).hexdigest()
            
            if msg_hash not in VAULT["SEEN_IDS"]:
                k = Fernet.generate_key()
                box = Fernet(k).encrypt(data_to_send)
                l = len(box)
                
                VAULT["FLUX"][session_id].append({
                    "f1": box[:l//3], "f2": box[l//3:2*l//3], "f3": box[2*l//3:],
                    "k": k, "name": file_name, "type": mime_type, "is_txt": is_text,
                    "timestamp": time.time(), "msg_hash": msg_hash
                })
                VAULT["SEEN_IDS"].add(msg_hash)
                st.rerun()

    # =====================================================
    # 3. CONTRÔLES SOUVERAINS
    # =====================================================
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🧨 DÉTRUIRE TOUT LE TUNNEL", use_container_width=True):
        VAULT["FLUX"][session_id] = []
        st.warning("Tunnel anéanti.")
        st.rerun()

    # Auto-refresh lent (8s) pour stabilité
    time.sleep(8)
    st.rerun()

else:
    st.markdown("""
    <div style="text-align: center; margin-top: 100px; opacity: 0.5;">
        <h2>Veuillez entrer la clé pour manifester le flux.</h2>
        <p>Les données sont éclatées et chiffrées en mémoire vive.</p>
    </div>
    """, unsafe_allow_html=True)
