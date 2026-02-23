import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# CLASSE CŒUR : THERMODYNAMIQUE SOUVERAINE (TST)
# =====================================================
class TSTVault:
    def __init__(self):
        if "vault_data" not in st.session_state:
            st.session_state.vault_data = {"FLUX": {}, "HISTORY": set(), "PRESENCE": {}}
        self.data = st.session_state.vault_data

    def get_session_id(self, key):
        if not key: return None
        grain = datetime.datetime.now().strftime("%Y-%m-%d-%H")
        return hashlib.sha256(f"{key}-{grain}".encode()).hexdigest()[:12].upper()

    def push_signal(self, session_id, content, fname, mtype, is_txt):
        # Sécurité anti-doublon par Hash de contenu
        signal_hash = hashlib.md5(content + fname.encode()).hexdigest()
        
        if signal_hash not in self.data["HISTORY"]:
            k = Fernet.generate_key()
            f = Fernet(k)
            enc = f.encrypt(content)
            l = len(enc)
            
            payload = {
                "f1": enc[:l//3], "f2": enc[l//3:2*l//3], "f3": enc[2*l//3:],
                "k": k, "name": fname, "type": mtype, "is_txt": is_txt,
                "ts": time.time(), "hash": signal_hash
            }
            
            if session_id not in self.data["FLUX"]: self.data["FLUX"][session_id] = []
            self.data["FLUX"][session_id].append(payload)
            self.data["HISTORY"].add(signal_hash)
            return True
        return False

    def clean_expired(self, session_id):
        if session_id in self.data["FLUX"]:
            self.data["FLUX"][session_id] = [p for p in self.data["FLUX"][session_id] if (time.time() - p["ts"]) < 3600]

# =====================================================
# CLASSE INTERFACE : GEN-Z GABON UI
# =====================================================
class GenZInterface:
    @staticmethod
    def apply_styles():
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
            * { font-family: 'Outfit', sans-serif; }
            .stApp { background: #000; color: #fff; }
            .bubble { 
                background: rgba(255,255,255,0.05); border-radius: 20px; 
                padding: 15px; margin: 10px 0; border: 1px solid #00ffaa33;
            }
            .tst-meta { font-size: 0.7em; color: #00ffaa; font-weight: bold; }
            .video-full { width: 100%; border-radius: 15px; border: 2px solid #ff4b4b; }
            </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def render_message(p, idx):
        try:
            raw = Fernet(p["k"]).decrypt(p["f1"] + p["f2"] + p["f3"])
            with st.container():
                st.markdown('<div class="bubble">', unsafe_allow_html=True)
                if p["is_txt"]: st.markdown(f"**{raw.decode()}**")
                else:
                    if "image" in p["type"]: st.image(raw)
                    elif "video" in p["type"]: st.video(raw)
                    elif "audio" in p["type"]: st.audio(raw)
                
                rem = int(3600 - (time.time() - p["ts"]))
                st.markdown(f'<span class="tst-meta">⏳ TST EXP: {rem//60}m | ❤️ 😂 🔥</span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        except: st.error("Signal TST corrompu")

# =====================================================
# EXECUTION PRINCIPALE
# =====================================================
vault = TSTVault()
ui = GenZInterface()
ui.apply_styles()

st.markdown('<h1 style="text-align:center; color:#00ffaa;">GEN-Z GABON</h1>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔐 Accès")
    key = st.text_input("CLÉ SOUVERAINE", type="password").upper()
    sid = vault.get_session_id(key)

if sid:
    vault.clean_expired(sid)
    
    # --- AFFICHAGE FLUX (RÉCENTS EN BAS) ---
    chat_box = st.container()
    for i, post in enumerate(vault.data["FLUX"].get(sid, [])):
        ui.render_message(post, i)

    st.markdown("---")
    
    # --- ZONE D'ACTION (POO) ---
    cols = st.tabs(["💬 Tchat", "📷 Photo", "🎥 Vidéo", "🎙️ Vocal"])
    
    with cols[0]:
        txt = st.chat_input("Kongossa...")
        if txt: 
            vault.push_signal(sid, txt.encode(), "txt", "text", True)
            st.rerun()

    with cols[1]:
        st.subheader("📸 Mode Appareil Photo")
        img_capture = st.camera_input("Capture Photo", key="photo_mode")
        if img_capture:
            vault.push_signal(sid, img_capture.getvalue(), "capture.jpg", "image/jpeg", False)
            st.rerun()

    with cols[2]:
        st.subheader("🎥 Mode Caméra Vidéo")
        # Utilisation du widget uploader pour la vidéo haute qualité
        video_file = st.file_uploader("Enregistre ou charge ta vidéo", type=['mp4', 'mov', 'avi'], key="video_mode")
        if video_file:
            if st.button("🚀 DIFFUSER VIDÉO SOUVERAINE"):
                vault.push_signal(sid, video_file.getvalue(), video_file.name, video_file.type, False)
                st.rerun()

    with cols[3]:
        st.subheader("🎙️ Mode Vocal")
        audio_file = st.audio_input("Enregistrer un audio")
        if audio_file:
            # Le hash MD5 dans push_signal empêchera la multiplication ici
            success = vault.push_signal(sid, audio_file.getvalue(), "vocal.wav", "audio/wav", False)
            if success: st.rerun()

    # Refresh pour le temps réel
    time.sleep(10)
    st.rerun()
else:
    st.warning("En attente du code de déchiffrement...")
