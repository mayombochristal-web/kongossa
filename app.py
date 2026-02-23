import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# CLASSE TST : GESTION DES SIGNAUX ET RÉACTIONS
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
        grain = datetime.datetime.now().strftime("%Y-%m-%d-%H")
        return hashlib.sha256(f"{key}-{grain}".encode()).hexdigest()[:12].upper()

    def send_signal(self, sid, content, fname, mtype, is_txt):
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

    def add_reaction(self, msg_id, emoji):
        if msg_id not in self.db["REACTIONS"]:
            self.db["REACTIONS"][msg_id] = []
        self.db["REACTIONS"][msg_id].append(emoji)

# =====================================================
# CLASSE UI : DESIGN ET ERGONOMIE PHOTO
# =====================================================
class KongossaUI:
    @staticmethod
    def apply_custom_css():
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;700;900&display=swap');
            * { font-family: 'Outfit', sans-serif; }
            .stApp { background: #050505; color: white; }
            
            /* Bulles de tchat avec réactions superposées */
            .signal-card {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 25px 25px 25px 5px;
                padding: 20px; margin-bottom: 25px;
                border: 1px solid rgba(0, 255, 170, 0.15);
                position: relative;
            }
            .reaction-pill {
                position: absolute; bottom: -12px; left: 20px;
                background: #1a1a1a; border: 1px solid #00ffaa;
                border-radius: 15px; padding: 2px 8px; font-size: 0.9em;
                display: flex; gap: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);
            }
            .tst-timer { color: #ff4b4b; font-size: 0.75em; font-weight: bold; }
            
            /* Style Caméra Miroir */
            [data-testid="stCameraInput"] > div {
                transform: scaleX(-1); /* Effet miroir pour l'utilisateur */
                border: 3px solid #00ffaa !important; border-radius: 20px;
            }
            </style>
        """, unsafe_allow_html=True)

# =====================================================
# LOGIQUE PRINCIPALE
# =====================================================
tst = TSTEngine()
ui = KongossaUI()
ui.apply_custom_css()

if "auth" not in st.session_state: st.session_state.auth = False

# --- HEADER ---
st.markdown('<p style="text-align:center; font-size:45px;">🇬🇦</p>', unsafe_allow_html=True)
st.markdown('<h1 style="text-align:center; background: linear-gradient(90deg, #00FFAA, #00D4FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight:900;">GEN Z GABON</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; font-weight:bold; letter-spacing:2px; margin-top:-20px;">FREE-KONGOSSA</p>', unsafe_allow_html=True)

# --- ACCUEIL ---
if not st.session_state.auth:
    with st.container():
        st.markdown("<br><br>", unsafe_allow_html=True)
        key = st.text_input("🔑 CLÉ DU TUNNEL", type="password", placeholder="Entre ton secret...").strip().upper()
        if st.button("ACTIVER LE SIGNAL", use_container_width=True):
            if key:
                st.session_state.sid = tst.derive_id(key)
                st.session_state.auth = True
                st.rerun()

# --- ESPACE KONGOSSA ---
else:
    sid = st.session_state.sid
    
    # Auto-nettoyage (1h)
    tst.db["FLUX"][sid] = [p for p in tst.db["FLUX"].get(sid, []) if (time.time() - p["ts"]) < 3600]

    # Affichage des Signaux
    for p in tst.db["FLUX"].get(sid, []):
        with st.container():
            st.markdown('<div class="signal-card">', unsafe_allow_html=True)
            try:
                # Décryptage TST
                f = Fernet(p["k"])
                raw = f.decrypt(p["frags"][0] + p["frags"][1] + p["frags"][2])
                
                rem = int(3600 - (time.time() - p["ts"]))
                st.markdown(f'<span class="tst-timer">⌛ {rem//60} MIN AVANT ÉVAPORATION</span>', unsafe_allow_html=True)
                
                if p["is_txt"]: st.markdown(f"### {raw.decode()}")
                else:
                    if "image" in p["type"]: st.image(raw, use_container_width=True)
                    elif "video" in p["type"]: st.video(raw)
                    elif "audio" in p["type"]: st.audio(raw)

                # --- RÉACTIONS SUPERPOSÉES ---
                reactions = tst.db["REACTIONS"].get(p['id'], [])
                if reactions:
                    react_str = "".join(reactions[:5]) # Affiche les 5 premières
                    if len(reactions) > 5: react_str += f" +{len(reactions)-5}"
                    st.markdown(f'<div class="reaction-pill">{react_str}</div>', unsafe_allow_html=True)

                # Menu de réaction (simulant l'appui long)
                with st.expander("Réagir au signal"):
                    r_cols = st.columns(5)
                    for idx, emo in enumerate(["❤️", "😂", "🔥", "✊", "😮"]):
                        if r_cols[idx].button(emo, key=f"re_{idx}_{p['id']}"):
                            tst.add_reaction(p['id'], emo)
                            st.rerun()
            except: st.error("Rupture de signal")
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    # --- ZONE D'ENVOI SÉLECTIVE (ANTI-RAM) ---
    st.subheader("➕ NOUVEAU SIGNAL")
    choice = st.selectbox("Choisis ton mode", ["💬 Tchat", "📸 Photo (Miroir)", "🎥 Vidéo", "🎙️ Vocal"], label_visibility="collapsed")

    if choice == "💬 Tchat":
        txt = st.chat_input("Écris ici...")
        if txt: 
            tst.send_signal(sid, txt.encode(), "txt", "text", True)
            st.rerun()

    elif choice == "📸 Photo (Miroir)":
        st.info("💡 L'effet miroir est activé pour t'aider à mieux cadrer ton Kongossa.")
        photo = st.camera_input("Prendre la photo")
        if photo:
            tst.send_signal(sid, photo.getvalue(), "shot.jpg", "image/jpeg", False)
            st.success("Signal photo envoyé !")
            time.sleep(1)
            st.rerun()

    elif choice == "🎥 Vidéo":
        vid = st.file_uploader("Enregistre et charge ta vidéo", type=["mp4", "mov"])
        if vid and st.button("🚀 DIFFUSER LA VIDÉO"):
            tst.send_signal(sid, vid.getvalue(), vid.name, vid.type, False)
            st.rerun()

    elif choice == "🎙️ Vocal":
        vox = st.audio_input("Enregistre ton vocal")
        if vox:
            if tst.send_signal(sid, vox.getvalue(), "vocal.wav", "audio/wav", False):
                st.rerun()

    if st.button("🧨 FERMER LE TUNNEL"):
        st.session_state.auth = False
        st.rerun()

    time.sleep(8)
    st.rerun()
