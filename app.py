import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# MOTEUR TST : SOUVERAINETÉ ET RÉACTIONS
# =====================================================
class TSTEngine:
    def __init__(self):
        if "vault" not in st.session_state:
            st.session_state.vault = {
                "FLUX": {}, "HISTORY": set(), "REACTIONS": {}
            }
        self.db = st.session_state.vault

    def derive_id(self, key):
        if not key: return None
        return hashlib.sha256(key.encode()).hexdigest()[:12].upper()

    def broadcast(self, sid, content, fname, mtype, is_txt):
        sig_hash = hashlib.md5(content + fname.encode()).hexdigest()
        if sig_hash not in self.db["HISTORY"]:
            k = Fernet.generate_key()
            enc = Fernet(k).encrypt(content)
            msg_id = f"sig_{int(time.time()*1000)}"
            payload = {
                "id": msg_id, "k": k, "ts": time.time(), "is_txt": is_txt,
                "name": fname, "type": mtype, "hash": sig_hash,
                "frags": [enc[:len(enc)//3], enc[len(enc)//3:2*len(enc)//3], enc[2*len(enc)//3:]]
            }
            if sid not in self.db["FLUX"]: self.db["FLUX"][sid] = []
            self.db["FLUX"][sid].append(payload)
            self.db["HISTORY"].add(sig_hash)
            return True
        return False

# =====================================================
# UI DESIGN : PLEIN ÉCRAN ET RÉACTIONS D'ANGLE
# =====================================================
class KongossaUI:
    @staticmethod
    def apply_styles():
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
            * { font-family: 'Outfit', sans-serif; }
            .stApp { background: #050505; color: white; }
            
            /* Bulle de Signal */
            .signal-card {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 20px 20px 20px 5px;
                padding: 15px; margin-bottom: 30px;
                border: 1px solid rgba(0, 255, 170, 0.1);
                position: relative;
                width: 100%;
            }
            
            /* Emojis dans l'angle gauche bas */
            .reaction-stack {
                position: absolute;
                bottom: -15px;
                left: 10px;
                display: flex;
                gap: 3px;
                background: #0a0a0a;
                padding: 3px 8px;
                border-radius: 20px;
                border: 1px solid #00ffaa;
                box-shadow: 0 4px 10px rgba(0,0,0,0.8);
                z-index: 10;
            }
            
            /* Caméra Plein Écran Miroir */
            [data-testid="stCameraInput"] {
                width: 100% !important;
            }
            [data-testid="stCameraInput"] > div {
                transform: scaleX(-1);
                border: 2px solid #00ffaa !important;
                border-radius: 15px;
            }
            
            /* Alignement horizontal des boutons emojis */
            .emoji-bar {
                display: flex;
                justify-content: flex-start;
                gap: 10px;
                margin-top: 10px;
            }
            </style>
        """, unsafe_allow_html=True)

# =====================================================
# APP LOGIC
# =====================================================
tst = TSTEngine()
ui = KongossaUI()
ui.apply_styles()

if "auth" not in st.session_state: st.session_state.auth = False

st.markdown('<h1 style="text-align:center; color:#00FFAA; margin-bottom:0;">🇬🇦 GEN Z GABON</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; font-weight:900; letter-spacing:3px;">FREE-KONGOSSA</p>', unsafe_allow_html=True)

if not st.session_state.auth:
    st.markdown("<br>", unsafe_allow_html=True)
    key = st.text_input("🔑 CLÉ DU TUNNEL", type="password", placeholder="CODE SECRET...").strip().upper()
    if st.button("ACTIVER LE SIGNAL", use_container_width=True):
        if key:
            st.session_state.sid = tst.derive_id(key)
            st.session_state.auth = True
            st.rerun()
else:
    sid = st.session_state.sid
    
    # Nettoyage TST
    tst.db["FLUX"][sid] = [p for p in tst.db["FLUX"].get(sid, []) if (time.time() - p["ts"]) < 3600]

    # --- FLUX DES SIGNAUX ---
    for p in tst.db["FLUX"].get(sid, []):
        with st.container():
            st.markdown('<div class="signal-card">', unsafe_allow_html=True)
            try:
                raw = Fernet(p["k"]).decrypt(p["frags"][0] + p["frags"][1] + p["frags"][2])
                
                # Timer
                rem = int(3600 - (time.time() - p["ts"]))
                st.markdown(f'<small style="color:#ff4b4b;">⌛ {rem//60}m</small>', unsafe_allow_html=True)
                
                if p["is_txt"]: st.markdown(f"### {raw.decode()}")
                else:
                    if "image" in p["type"]: st.image(raw, use_container_width=True)
                    elif "video" in p["type"]: st.video(raw)
                    elif "audio" in p["type"]: st.audio(raw)

                # Affichage des réactions dans l'angle gauche
                reacts = tst.db.get("REACTIONS", {}).get(p['id'], [])
                if reacts:
                    st.markdown(f'<div class="reaction-stack">{"".join(reacts)}</div>', unsafe_allow_html=True)

                # Barre d'emojis horizontale pour réagir
                st.markdown('<div style="margin-top:15px;"></div>', unsafe_allow_html=True)
                emo_cols = st.columns([1,1,1,1,1,5])
                for idx, emo in enumerate(["❤️", "😂", "🔥", "✊", "😮"]):
                    if emo_cols[idx].button(emo, key=f"re_{p['id']}_{idx}"):
                        tst.db.setdefault("REACTIONS", {}).setdefault(p['id'], []).append(emo)
                        st.rerun()

            except: st.error("Rupture de signal")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- ZONE D'ENVOI PLEIN ÉCRAN ---
    st.markdown("---")
    option = st.selectbox("📥 ENVOYER UN SIGNAL", ["💬 Tchat", "📸 Photo Plein Écran", "🎥 Vidéo", "🎙️ Vocal"], label_visibility="collapsed")

    if option == "💬 Tchat":
        msg = st.chat_input("Kongossa...")
        if msg:
            tst.broadcast(sid, msg.encode(), "txt", "text", True)
            st.rerun()

    elif option == "📸 Photo Plein Écran":
        st.info("📷 Mode Miroir Activé - Cadre ton Kongossa en plein écran.")
        photo = st.camera_input("Prendre la photo", key="full_cam")
        if photo:
            with st.spinner("Envoi..."):
                tst.broadcast(sid, photo.getvalue(), "shot.jpg", "image/jpeg", False)
                st.rerun()

    elif option == "🎥 Vidéo":
        vid = st.file_uploader("Fichier Vidéo (MP4/MOV)", type=["mp4", "mov"])
        if vid and st.button("🚀 DIFFUSER VIDÉO", use_container_width=True):
            tst.broadcast(sid, vid.getvalue(), vid.name, vid.type, False)
            st.rerun()

    elif option == "🎙️ Vocal":
        vox = st.audio_input("Signal Vocal")
        if vox:
            if tst.broadcast(sid, vox.getvalue(), "vocal.wav", "audio/wav", False):
                st.rerun()

    if st.button("🧨 QUITTER LE TUNNEL", use_container_width=True):
        st.session_state.auth = False
        st.rerun()
