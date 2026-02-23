import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# 1. MOTEUR TST : OPTIMISÉ ET STABLE
# =====================================================
class TSTEngine:
    def __init__(self):
        if "vault" not in st.session_state:
            st.session_state.vault = {
                "FLUX": {}, "HISTORY": set(), "REACTIONS": {}
            }
        self.db = st.session_state.vault

    def derive_stable_id(self, key):
        """Amélioration 4 : ID stable pour éviter la perte de messages chaque heure"""
        if not key: return None
        return hashlib.sha256(key.encode()).hexdigest()[:12].upper()

    def broadcast_signal(self, sid, content, fname, mtype, is_txt):
        """Amélioration 6 : Gestion du feedback d'envoi"""
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
# 2. UI & UX : DESIGN MOBILE-FIRST & FLUIDE
# =====================================================
class KongossaUI:
    @staticmethod
    def apply_styles():
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
            * { font-family: 'Outfit', sans-serif; }
            .stApp { background: #050505; color: white; }
            
            /* Amélioration 7 & 9 : Bulles et Animations */
            .signal-card {
                background: rgba(255, 255, 255, 0.04);
                border-radius: 20px; padding: 18px; margin-bottom: 20px;
                border: 1px solid rgba(0, 255, 170, 0.1);
                transition: transform 0.3s ease;
            }
            .signal-card:hover { transform: translateY(-2px); border-color: #00FFAA; }
            
            /* Amélioration 2 : Reactions en Pills */
            .pill-container { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }
            .react-pill {
                background: rgba(0, 255, 170, 0.15); border: 1px solid #00FFAA;
                border-radius: 12px; padding: 2px 8px; font-size: 0.8em;
            }
            
            /* Amélioration 3 & 10 : Timer et Miroir */
            .timer-critical { color: #ff4b4b; font-weight: 900; animation: blink 1s infinite; }
            @keyframes blink { 0% {opacity:1;} 50% {opacity:0.5;} 100% {opacity:1;} }
            
            [data-testid="stCameraInput"] > div { transform: scaleX(-1); border-radius: 15px; }
            </style>
        """, unsafe_allow_html=True)

# =====================================================
# 3. LOGIQUE APPLICATIVE
# =====================================================
tst = TSTEngine()
ui = KongossaUI()
ui.apply_styles()

if "auth" not in st.session_state: st.session_state.auth = False

# --- ENTÊTE ---
st.markdown('<h1 style="text-align:center; color:#00FFAA; margin-bottom:0;">🇬🇦 GEN Z GABON</h1>', unsafe_allow_html=True)
st.caption("<center><b>FREE-KONGOSSA : Le Tunnel de Maintenance Sociale</b></center>", unsafe_allow_html=True)

# --- PHASE D'ACCUEIL ---
if not st.session_state.auth:
    with st.container():
        st.markdown("<br>", unsafe_allow_html=True)
        key = st.text_input("🔑 CLÉ SOUVERAINE", type="password", placeholder="Entrez le secret partagé...").strip().upper()
        if st.button("ACTIVER LE SIGNAL TST", use_container_width=True):
            if key:
                st.session_state.sid = tst.derive_stable_id(key)
                st.session_state.auth = True
                st.rerun()
else:
    sid = st.session_state.sid
    
    # Amélioration 1 : Remplacement du timer agressif par un bouton de rafraîchissement manuel pro
    col_nav, col_refresh = st.columns([0.8, 0.2])
    if col_refresh.button("🔄", help="Synchroniser les signaux"):
        st.rerun()
    if col_nav.button("🧨 Quitter le tunnel"):
        # Amélioration 11 : Confirmation de sortie simple
        st.session_state.auth = False
        st.rerun()

    # --- FLUX DES SIGNAUX (AMÉLIORÉ) ---
    signals = tst.db["FLUX"].get(sid, [])
    # Nettoyage (Amélioration 3)
    valid_signals = [p for p in signals if (time.time() - p["ts"]) < 3600]
    tst.db["FLUX"][sid] = valid_signals

    for p in reversed(valid_signals):
        with st.container():
            st.markdown('<div class="signal-card">', unsafe_allow_html=True)
            try:
                # Décryptage
                f = Fernet(p["k"])
                raw = f.decrypt(p["frags"][0] + p["frags"][1] + p["frags"][2])
                
                # Timer Dynamique (Amélioration 3)
                rem = int(3600 - (time.time() - p["ts"]))
                timer_class = "timer-critical" if rem < 300 else ""
                st.markdown(f'<span class="{timer_class}">⏳ Expire dans {rem//60} min</span>', unsafe_allow_html=True)
                
                # Amélioration 12 : Rendu factorisé
                if p["is_txt"]: st.markdown(f"### {raw.decode()}")
                else:
                    if "image" in p["type"]: st.image(raw, use_container_width=True)
                    elif "video" in p["type"]: st.video(raw)
                    elif "audio" in p["type"]: st.audio(raw)

                # Amélioration 2 : Réactions Inline (sans expander)
                r_cols = st.columns(6)
                for idx, emo in enumerate(["❤️", "😂", "🔥", "✊", "😮"]):
                    if r_cols[idx].button(emo, key=f"re_{p['id']}_{idx}"):
                        tst.db.setdefault("REACTIONS", {}).setdefault(p['id'], []).append(emo)
                        st.rerun()
                
                # Affichage des Pills
                reacts = tst.db.get("REACTIONS", {}).get(p['id'], [])
                if reacts:
                    st.markdown('<div class="pill-container">' + 
                                "".join([f'<span class="react-pill">{e}</span>' for e in set(reacts)]) + 
                                '</div>', unsafe_allow_html=True)

            except Exception as e:
                st.error(f"⚠️ Signal brouillé : {str(e)}") # Amélioration 8
            st.markdown('</div>', unsafe_allow_html=True)

    # --- ZONE D'ENVOI (Amélioration 5 & 6) ---
    st.markdown("---")
    mode = st.selectbox("📥 NOUVEAU SIGNAL", ["💬 Texte", "📸 Photo", "🎥 Vidéo", "🎙️ Vocal"])

    if mode == "💬 Texte":
        txt = st.chat_input("Partage ton Kongossa...")
        if txt:
            with st.spinner("Cryptage TST..."):
                tst.broadcast_signal(sid, txt.encode(), "txt", "text", True)
                st.rerun()

    elif mode == "📸 Photo":
        cam = st.camera_input("Aperçu Miroir Actif")
        if cam:
            with st.spinner("Envoi du cliché..."):
                tst.broadcast_signal(sid, cam.getvalue(), "img.jpg", "image/jpeg", False)
                st.success("Signal Photo Expédié !")
                time.sleep(1)
                st.rerun()

    elif mode == "🎥 Vidéo":
        vid = st.file_uploader("Sélectionne ton clip (MP4/MOV)", type=["mp4", "mov"])
        if vid: # Amélioration 5 : Envoi direct ou bouton unique
            if st.button("🚀 DIFFUSER LA VIDÉO", use_container_width=True):
                with st.spinner("Injection thermodynamique..."):
                    tst.broadcast_signal(sid, vid.getvalue(), vid.name, vid.type, False)
                    st.rerun()

    elif mode == "🎙️ Vocal":
        vox = st.audio_input("Enregistre ton signal sonore")
        if vox:
            if tst.broadcast_signal(sid, vox.getvalue(), "vocal.wav", "audio/wav", False):
                st.rerun()
