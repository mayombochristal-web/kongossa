import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time

# =====================================================
# CLASSE CŒUR : LOGIQUE TST (TITRES & COMMENTAIRES)
# =====================================================
class TSTEngine:
    def __init__(self):
        if "vault" not in st.session_state:
            st.session_state.vault = {
                "FLUX": {}, "HISTORY": set(), 
                "REACTIONS": {}, "COMMENTS": {}
            }
        self.db = st.session_state.vault

    def derive_id(self, key):
        return hashlib.sha256(key.encode()).hexdigest()[:12].upper() if key else None

    def broadcast(self, sid, content, fname, mtype, is_txt, title=""):
        sig_hash = hashlib.md5(content + fname.encode() + title.encode()).hexdigest()
        if sig_hash not in self.db["HISTORY"]:
            k = Fernet.generate_key()
            enc = Fernet(k).encrypt(content)
            msg_id = f"sig_{int(time.time()*1000)}"
            payload = {
                "id": msg_id, "k": k, "ts": time.time(), "is_txt": is_txt,
                "name": fname, "type": mtype, "title": title,
                "frags": [enc[:len(enc)//3], enc[len(enc)//3:2*len(enc)//3], enc[2*len(enc)//3:]]
            }
            if sid not in self.db["FLUX"]: self.db["FLUX"][sid] = []
            self.db["FLUX"][sid].append(payload)
            self.db["HISTORY"].add(sig_hash)
            return True
        return False

    def add_comment(self, msg_id, comment_text):
        if msg_id not in self.db["COMMENTS"]:
            self.db["COMMENTS"][msg_id] = []
        self.db["COMMENTS"][msg_id].append({
            "text": comment_text,
            "ts": datetime.datetime.now().strftime("%H:%M")
        })

# =====================================================
# DESIGN : INTERFACE SOUVERAINE ÉPURÉE
# =====================================================
class KongossaUI:
    @staticmethod
    def apply_styles():
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
            * { font-family: 'Outfit', sans-serif; }
            .stApp { background: #000; color: white; }
            
            /* Titre du Signal (Style Facebook/Journal) */
            .signal-title {
                color: #00FFAA; font-weight: 900; font-size: 1.1em;
                margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;
            }
            
            .signal-card {
                background: #0f0f0f; border-radius: 15px;
                padding: 15px; margin-bottom: 25px;
                border: 1px solid #1a1a1a; position: relative;
            }
            
            /* Micro-Reactions Angle Gauche */
            .mini-react-bar {
                position: absolute; bottom: -8px; left: 12px;
                display: flex; gap: 3px; background: #00ffaa;
                padding: 1px 6px; border-radius: 10px; z-index: 5;
            }
            .mini-react-item { color: #000; font-size: 0.7em; font-weight: bold; }
            
            /* Zone Commentaire Style Fil de Discussion */
            .comment-bubble {
                background: #1a1a1a; border-radius: 10px;
                padding: 8px; margin: 5px 0; font-size: 0.85em;
                border-left: 2px solid #00FFAA;
            }
            </style>
        """, unsafe_allow_html=True)

# =====================================================
# EXÉCUTION
# =====================================================
tst = TSTEngine()
KongossaUI.apply_styles()

if "auth" not in st.session_state: st.session_state.auth = False

st.markdown('<h2 style="text-align:center; color:#00FFAA; margin-bottom:0;">🇬🇦 GEN Z GABON</h2>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; font-size:0.7em; letter-spacing:3px; opacity:0.6;">FREE-KONGOSSA : SYSTÈME DÉCENTRALISÉ</p>', unsafe_allow_html=True)

if not st.session_state.auth:
    key = st.text_input("🔑 ACCÈS AU TUNNEL", type="password").strip().upper()
    if st.button("AUTHENTIFICATION", use_container_width=True):
        if key:
            st.session_state.sid = tst.derive_id(key)
            st.session_state.auth = True
            st.rerun()
else:
    sid = st.session_state.sid
    
    # 🔄 Bouton Refresh Manuel (Évite de faire ramer)
    if st.button("🔄 Actualiser le Flux"): st.rerun()

    # --- FIL DES SIGNAUX ---
    signals = tst.db["FLUX"].get(sid, [])
    for p in reversed(signals): # Plus récent en haut pour le style "Fil d'actualité"
        with st.container():
            st.markdown('<div class="signal-card">', unsafe_allow_html=True)
            try:
                # Affichage du Titre de la publication
                if p.get("title"):
                    st.markdown(f'<div class="signal-title">{p["title"]}</div>', unsafe_allow_html=True)
                
                raw = Fernet(p["k"]).decrypt(b"".join(p["frags"]))
                
                if p["is_txt"]: st.write(raw.decode())
                else:
                    if "image" in p["type"]: st.image(raw, use_container_width=True)
                    elif "video" in p["type"]: st.video(raw)
                    elif "audio" in p["type"]: st.audio(raw)

                # Réactions discrètes
                reacts = tst.db.get("REACTIONS", {}).get(p['id'], [])
                if reacts:
                    st.markdown(f'<div class="mini-react-bar">{"".join([f"<span class=\'mini-react-item\'>{e}</span>" for e in reacts[:5]])}</div>', unsafe_allow_html=True)
                
                # --- ACTIONS (Réagir & Commenter) ---
                st.markdown("<br>", unsafe_allow_html=True)
                c1, c2, c3, c4, c5, _ = st.columns([1,1,1,1,1,4])
                for i, e in enumerate(["❤️", "😂", "🔥", "✊", "😮"]):
                    if c1.button(e, key=f"re_{p['id']}_{i}") if i==0 else c2.button(e, key=f"re_{p['id']}_{i}") if i==1 else c3.button(e, key=f"re_{p['id']}_{i}") if i==2 else c4.button(e, key=f"re_{p['id']}_{i}") if i==3 else c5.button(e, key=f"re_{p['id']}_{i}"):
                        tst.db.setdefault("REACTIONS", {}).setdefault(p['id'], []).append(e)
                        st.rerun()

                # --- ONGLET COMMENTAIRES ---
                with st.expander(f"💬 Discussions ({len(tst.db['COMMENTS'].get(p['id'], []))})"):
                    # Affichage des commentaires existants
                    for comm in tst.db["COMMENTS"].get(p['id'], []):
                        st.markdown(f'<div class="comment-bubble"><b>{comm["ts"]}</b> : {comm["text"]}</div>', unsafe_allow_html=True)
                    
                    # Nouveau commentaire
                    new_comm = st.text_input("Votre avis...", key=f"in_comm_{p['id']}")
                    if st.button("Commenter", key=f"btn_comm_{p['id']}"):
                        if new_comm:
                            tst.add_comment(p['id'], new_comm)
                            st.rerun()

            except: st.error("Signal TST expiré ou corrompu")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- ZONE DE CRÉATION (MODE STUDIO) ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("➕ ÉMETTRE UN NOUVEAU SIGNAL", expanded=True):
        # Onglet Titre (Point demandé)
        post_title = st.text_input("Titre du Signal (Optionnel)", placeholder="Ex: Alerte Kongossa...")
        
        mode = st.tabs(["💬 Texte", "📸 Photo/Vidéo", "🎙️ Vocal"])
        
        with mode[0]:
            txt = st.text_area("Contenu du message")
            if st.button("Diffuser Texte"):
                tst.broadcast(sid, txt.encode(), "txt", "text", True, title=post_title)
                st.rerun()
        
        with mode[1]:
            media_choice = st.radio("Source", ["Appareil Photo (Miroir)", "Fichier Vidéo"])
            if "Photo" in media_choice:
                cam = st.camera_input("Capture")
                if cam:
                    tst.broadcast(sid, cam.getvalue(), "shot.jpg", "image/jpeg", False, title=post_title)
                    st.rerun()
            else:
                vid = st.file_uploader("Fichier MP4/MOV", type=["mp4", "mov"])
                if vid and st.button("Diffuser Vidéo"):
                    tst.broadcast(sid, vid.getvalue(), vid.name, vid.type, False, title=post_title)
                    st.rerun()
        
        with mode[2]:
            vox = st.audio_input("Microphone")
            if vox:
                tst.broadcast(sid, vox.getvalue(), "vocal.wav", "audio/wav", False, title=post_title)
                st.rerun()

    if st.button("🧨 QUITTER LE TUNNEL", use_container_width=True):
        st.session_state.auth = False
        st.rerun()
