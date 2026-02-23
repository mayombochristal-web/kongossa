import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time

# =====================================================
# ARCHITECTURE TST (OBJET & RAM)
# =====================================================
class TSTEngine:
    def __init__(self):
        if "vault" not in st.session_state:
            st.session_state.vault = {"FLUX": {}, "HISTORY": set(), "REACTIONS": {}}
        self.db = st.session_state.vault

    def derive_id(self, key):
        return hashlib.sha256(key.encode()).hexdigest()[:12].upper() if key else None

    def broadcast(self, sid, content, fname, mtype, is_txt):
        sig_hash = hashlib.md5(content + fname.encode()).hexdigest()
        if sig_hash not in self.db["HISTORY"]:
            k = Fernet.generate_key()
            enc = Fernet(k).encrypt(content)
            msg_id = f"sig_{int(time.time()*1000)}"
            payload = {
                "id": msg_id, "k": k, "ts": time.time(), "is_txt": is_txt,
                "name": fname, "type": mtype,
                "frags": [enc[:len(enc)//3], enc[len(enc)//3:2*len(enc)//3], enc[2*len(enc)//3:]]
            }
            if sid not in self.db["FLUX"]: self.db["FLUX"][sid] = []
            self.db["FLUX"][sid].append(payload)
            self.db["HISTORY"].add(sig_hash)
            return True
        return False

# =====================================================
# DESIGN UX : MICRO-INTERACTIONS
# =====================================================
class KongossaUI:
    @staticmethod
    def apply_styles():
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
            * { font-family: 'Outfit', sans-serif; }
            .stApp { background: #000; color: white; }
            
            /* Bulle de Signal Compacte */
            .signal-card {
                background: #111; border-radius: 15px 15px 15px 2px;
                padding: 12px; margin-bottom: 22px;
                border: 1px solid #222; position: relative; width: fit-content; max-width: 85%;
            }
            
            /* Micro-Reactions Horizontales */
            .mini-react-bar {
                position: absolute; bottom: -10px; left: 8px;
                display: flex; gap: 2px; background: #00ffaa;
                padding: 1px 5px; border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.5); z-index: 5;
            }
            .mini-react-item { color: #000; font-size: 0.75em; font-weight: bold; }
            
            /* Caméra TikTok Style */
            [data-testid="stCameraInput"] { width: 100% !important; }
            [data-testid="stCameraInput"] > div { transform: scaleX(-1); border: 2px solid #00ffaa; }
            
            /* Boutons Réactions sous signal */
            .react-trigger-btn { font-size: 0.8em !important; opacity: 0.6; }
            .react-trigger-btn:hover { opacity: 1; }
            </style>
        """, unsafe_allow_html=True)

# =====================================================
# LOGIQUE APP
# =====================================================
tst = TSTEngine()
KongossaUI.apply_styles()

if "auth" not in st.session_state: st.session_state.auth = False

# --- HEADER SOUVERAIN ---
st.markdown('<h2 style="text-align:center; color:#00FFAA; margin-bottom:0;">🇬🇦 GEN Z GABON</h2>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; font-size:0.7em; letter-spacing:2px; opacity:0.6;">FREE-KONGOSSA TST</p>', unsafe_allow_html=True)

if not st.session_state.auth:
    key = st.text_input("🔑 CLÉ DU TUNNEL", type="password").strip().upper()
    if st.button("ENTRER", use_container_width=True):
        if key:
            st.session_state.sid = tst.derive_id(key)
            st.session_state.auth = True
            st.rerun()
else:
    sid = st.session_state.sid
    
    # Auto-Clean
    tst.db["FLUX"][sid] = [p for p in tst.db["FLUX"].get(sid, []) if (time.time() - p["ts"]) < 3600]

    # --- FIL DE CONVERSATION ---
    for p in tst.db["FLUX"].get(sid, []):
        with st.container():
            st.markdown('<div class="signal-card">', unsafe_allow_html=True)
            try:
                raw = Fernet(p["k"]).decrypt(b"".join(p["frags"]))
                
                if p["is_txt"]: st.write(f"**{raw.decode()}**")
                else:
                    if "image" in p["type"]: st.image(raw, use_container_width=True)
                    elif "video" in p["type"]: st.video(raw)
                    elif "audio" in p["type"]: st.audio(raw)

                # Micro-Réactions dans l'angle
                reacts = tst.db.get("REACTIONS", {}).get(p['id'], [])
                if reacts:
                    react_html = "".join([f'<span class="mini-react-item">{e}</span>' for e in reacts[:6]])
                    st.markdown(f'<div class="mini-react-bar">{react_html}</div>', unsafe_allow_html=True)
                
                # Barre de réaction horizontale ultra-discrète
                cols = st.columns(7)
                for idx, emo in enumerate(["❤️", "😂", "🔥", "✊", "😮"]):
                    if cols[idx].button(emo, key=f"re_{p['id']}_{idx}"):
                        tst.db.setdefault("REACTIONS", {}).setdefault(p['id'], []).append(emo)
                        st.rerun()
            except: st.error("Signal perdu")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- ZONE DE CAPTURE "MODE STUDIO" ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("➕ CRÉER UN SIGNAL (Tiktok Style)", expanded=False):
        mode = st.radio("Format", ["💬 Message", "📸 Photo/Vidéo", "🎙️ Vocal"], horizontal=True)
        
        if mode == "💬 Message":
            txt = st.text_input("Ton Kongossa...")
            if st.button("Envoyer"):
                tst.broadcast(sid, txt.encode(), "txt", "text", True)
                st.rerun()
        
        elif mode == "📸 Photo/Vidéo":
            st.caption("Aperçu Miroir Plein Écran")
            cam = st.camera_input("Shoot !")
            if cam:
                tst.broadcast(sid, cam.getvalue(), "shot.jpg", "image/jpeg", False)
                st.rerun()
            
            st.markdown("---")
            vid = st.file_uploader("Ou charge une Vidéo", type=["mp4", "mov"])
            if vid and st.button("Diffuser Vidéo"):
                tst.broadcast(sid, vid.getvalue(), vid.name, vid.type, False)
                st.rerun()
        
        elif mode == "🎙️ Vocal":
            vox = st.audio_input("Enregistrer")
            if vox:
                tst.broadcast(sid, vox.getvalue(), "vocal.wav", "audio/wav", False)
                st.rerun()

    if st.button("🧨 QUITTER", use_container_width=True):
        st.session_state.auth = False
        st.rerun()
