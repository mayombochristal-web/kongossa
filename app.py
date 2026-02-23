import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# CLASSE CŒUR : TST ENGINE (GESTION RAM)
# =====================================================
class TSTEngine:
    def __init__(self):
        if "tst_vault" not in st.session_state:
            st.session_state.tst_vault = {
                "FLUX": {}, "HISTORY": set(), "PRESENCE": {}, "COMMENTS": {}
            }
        self.db = st.session_state.tst_vault

    def derive_session_id(self, key):
        if not key: return None
        grain = datetime.datetime.now().strftime("%Y-%m-%d-%H")
        return hashlib.sha256(f"{key}-{grain}".encode()).hexdigest()[:12].upper()

    def broadcast(self, sid, content, fname, mtype, is_txt):
        # Hash strict pour bloquer les répétitions infinies
        sig_hash = hashlib.md5(content + fname.encode()).hexdigest()
        if sig_hash not in self.db["HISTORY"]:
            k = Fernet.generate_key()
            enc = Fernet(k).encrypt(content)
            msg_id = f"tst_{int(time.time()*1000)}"
            payload = {
                "id": msg_id, "k": k, "ts": time.time(), "is_txt": is_txt,
                "name": fname, "type": mtype, "hash": sig_hash,
                "fragments": [enc[:len(enc)//3], enc[len(enc)//3:2*len(enc)//3], enc[2*len(enc)//3:]]
            }
            if sid not in self.db["FLUX"]: self.db["FLUX"][sid] = []
            self.db["FLUX"][sid].append(payload)
            self.db["HISTORY"].add(sig_hash)
            return True
        return False

# =====================================================
# INTERFACE SANS SIDEBAR ET SANS RAMAGES
# =====================================================
tst = TSTEngine()

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;700;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: #050505; color: white; }
    .hero-card {
        background: rgba(255, 255, 255, 0.03); border: 1px solid #00FFAA33;
        border-radius: 25px; padding: 25px; text-align: center;
    }
    .chat-bubble {
        background: rgba(255, 255, 255, 0.07); border-radius: 20px;
        padding: 15px; margin-bottom: 15px; border-left: 5px solid #00FFAA;
    }
    .reaction-btn { border-radius: 50% !important; padding: 5px !important; }
    </style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

st.markdown('<h1 style="text-align:center; color:#00FFAA;">🇬🇦 GEN Z GABON</h1>', unsafe_allow_html=True)
st.markdown('<h3 style="text-align:center; color:#00D4FF;">FREE-KONGOSSA</h3>', unsafe_allow_html=True)

# --- ACCUEIL ---
if not st.session_state.authenticated:
    st.markdown("""
    <div class="hero-card">
        <h3>🚨 GUIDE DU KONGOSSA SOUVERAIN</h3>
        <p>1. Entre ta clé. 2. Capture ton signal. 3. Le signal s'évapore en 1h.</p>
    </div>
    """, unsafe_allow_html=True)
    
    secret = st.text_input("🔑 CLÉ SECRÈTE", type="password").strip().upper()
    if st.button("ACTIVER LE TUNNEL", use_container_width=True):
        if secret:
            st.session_state.sid = tst.derive_session_id(secret)
            st.session_state.authenticated = True
            st.rerun()

# --- INTERFACE DE TCHAT ---
else:
    sid = st.session_state.sid
    
    # Nettoyage automatique TST
    tst.db["FLUX"][sid] = [p for p in tst.db["FLUX"].get(sid, []) if (time.time() - p["ts"]) < 3600]

    # Flux de messages
    for p in tst.db["FLUX"].get(sid, []):
        with st.container():
            st.markdown('<div class="chat-bubble">', unsafe_allow_html=True)
            try:
                raw = Fernet(p["k"]).decrypt(p["fragments"][0] + p["fragments"][1] + p["fragments"][2])
                if p["is_txt"]: st.markdown(f"**{raw.decode()}**")
                else:
                    if "image" in p["type"]: st.image(raw)
                    elif "video" in p["type"]: st.video(raw)
                    elif "audio" in p["type"]: st.audio(raw)
                
                # Réactions & Commentaires simplifiés
                cols = st.columns([0.1, 0.1, 0.1, 0.7])
                if cols[0].button("❤️", key=f"h_{p['id']}"): tst.db.setdefault("COMMENTS", {}).setdefault(p['id'], []).append("❤️")
                if cols[1].button("🔥", key=f"f_{p['id']}"): tst.db.setdefault("COMMENTS", {}).setdefault(p['id'], []).append("🔥")
                
                if p['id'] in tst.db.get("COMMENTS", {}):
                    st.caption(" | ".join(tst.db["COMMENTS"][p['id']]))
            except: st.error("Fragment perdu")
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    # --- ZONE DE SIGNAL UNIQUE (POUR ÉVITER LE RAMAGE) ---
    st.subheader("➕ NOUVEAU SIGNAL")
    
    # Le secret pour ne pas faire ramer : un selectbox au lieu de tabs pour les médias lourds
    option = st.selectbox("Type de signal", ["💬 Message", "📸 Photo (Instant)", "🎥 Vidéo (Upload)", "🎙️ Vocal"], label_visibility="collapsed")

    if option == "💬 Message":
        msg = st.chat_input("Raconte...")
        if msg:
            tst.broadcast(sid, msg.encode(), "txt", "text", True)
            st.rerun()

    elif option == "📸 Photo (Instant)":
        # On n'affiche le camera_input QUE si l'option est sélectionnée
        cam = st.camera_input("Sourire pour le Kongossa")
        if cam:
            tst.broadcast(sid, cam.getvalue(), "img.jpg", "image/jpeg", False)
            st.success("Photo capturée ! Change d'option pour envoyer autre chose.")
            # On force un petit délai pour que l'utilisateur voit le succès
            time.sleep(1)
            st.rerun()

    elif option == "🎥 Vidéo (Upload)":
        vid = st.file_uploader("Charge ta vidéo souveraine", type=["mp4", "mov", "avi"])
        if vid:
            if st.button("🚀 DIFFUSER LA VIDÉO"):
                tst.broadcast(sid, vid.getvalue(), vid.name, vid.type, False)
                st.rerun()

    elif option == "🎙️ Vocal":
        vox = st.audio_input("Enregistre ton message")
        if vox:
            # On vérifie le hash avant d'envoyer pour éviter la boucle infinie
            if tst.broadcast(sid, vox.getvalue(), "vocal.wav", "audio/wav", False):
                st.rerun()

    if st.button("🧨 FERMER LE TUNNEL"):
        st.session_state.authenticated = False
        st.rerun()

    time.sleep(10)
    st.rerun()
