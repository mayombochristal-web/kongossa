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
        # Initialisation sécurisée des structures de données en RAM
        if "vault" not in st.session_state:
            st.session_state.vault = {
                "FLUX": {}, 
                "HISTORY": set(), 
                "PRESENCE": {},
                "COMMENTS": {} # Stockage des commentaires par ID de message
            }
        self.storage = st.session_state.vault

    def get_session_id(self, key):
        if not key: return None
        # Cycle horaire TST pour la rotation des clés
        grain = datetime.datetime.now().strftime("%Y-%m-%d-%H")
        return hashlib.sha256(f"{key}-{grain}".encode()).hexdigest()[:12].upper()

    def push_signal(self, session_id, content, fname, mtype, is_txt):
        # Hash unique pour bloquer les doublons (Audio/Vidéo)
        sig_hash = hashlib.md5(content + fname.encode()).hexdigest()
        
        if sig_hash not in self.storage["HISTORY"]:
            k = Fernet.generate_key()
            f = Fernet(k)
            enc = f.encrypt(content)
            l = len(enc)
            
            msg_id = f"msg_{int(time.time()*1000)}"
            payload = {
                "id": msg_id,
                "f1": enc[:l//3], "f2": enc[l//3:2*l//3], "f3": enc[2*l//3:],
                "k": k, "name": fname, "type": mtype, "is_txt": is_txt,
                "ts": time.time(), "hash": sig_hash, "reactions": []
            }
            
            if session_id not in self.storage["FLUX"]: self.storage["FLUX"][session_id] = []
            self.storage["FLUX"][session_id].append(payload)
            self.storage["HISTORY"].add(sig_hash)
            return True
        return False

    def add_comment(self, msg_id, comment_txt):
        if msg_id not in self.storage["COMMENTS"]:
            self.storage["COMMENTS"][msg_id] = []
        self.storage["COMMENTS"][msg_id].append({
            "txt": comment_txt,
            "ts": datetime.datetime.now().strftime("%H:%M")
        })

# =====================================================
# CLASSE INTERFACE : EXPERIENCE UTILISATEUR (UX)
# =====================================================
class GenZInterface:
    @staticmethod
    def apply_ui_styles():
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
            * { font-family: 'Outfit', sans-serif; }
            .stApp { background: #050505; color: #ffffff; }
            
            /* Bulles de conversation */
            .chat-card {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 20px; padding: 15px; margin-bottom: 15px;
                border-left: 4px solid #00FFAA; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            }
            
            /* Commentaires */
            .comment-box {
                background: rgba(0, 255, 170, 0.05);
                border-radius: 10px; padding: 8px; margin-top: 5px;
                font-size: 0.85em; border-left: 2px solid #00FFAA;
            }
            
            .tst-badge {
                background: #ff4b4b; color: white; padding: 2px 8px;
                border-radius: 10px; font-size: 0.65em; font-weight: bold;
            }
            
            .logo-text {
                font-size: 2.2em; font-weight: 900; text-align: center;
                background: linear-gradient(90deg, #00FFAA, #00D4FF);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                margin-bottom: 0px;
            }
            </style>
        """, unsafe_allow_html=True)

# =====================================================
# LANCEUR DE L'APPLICATION
# =====================================================
vault = TSTVault()
GenZInterface.apply_ui_styles()

# Logo et Titre
st.markdown('<div><p style="text-align:center; font-size:40px;">🇬🇦</p></div>', unsafe_allow_html=True)
st.markdown('<h1 class="logo-text">GEN Z GABON FREE-KONGOSSA</h1>', unsafe_allow_html=True)
st.caption("<center>Souveraineté Thermodynamique • Éphémère • Incraquable</center>", unsafe_allow_html=True)

# Accès
with st.sidebar:
    st.image("https://img.icons8.com/nolan/96/security-shield.png", width=80)
    key_input = st.text_input("🔑 CLÉ DU TUNNEL", type="password").strip().upper()
    sid = vault.get_session_id(key_input)

if sid:
    # 1. NETTOYAGE TST (Efface les messages de +1h)
    vault.storage["FLUX"][sid] = [p for p in vault.storage["FLUX"].get(sid, []) if (time.time() - p["ts"]) < 3600]

    # 2. AFFICHAGE DU FLUX (LES RÉCENTS EN BAS)
    st.markdown("---")
    for i, p in enumerate(vault.storage["FLUX"].get(sid, [])):
        try:
            raw = Fernet(p["k"]).decrypt(p["f1"] + p["f2"] + p["f3"])
            with st.container():
                st.markdown('<div class="chat-card">', unsafe_allow_html=True)
                
                # Header du message
                rem = int(3600 - (time.time() - p["ts"]))
                st.markdown(f'<span class="tst-badge">🔥 {rem//60}m</span>', unsafe_allow_html=True)
                
                # Contenu
                if p["is_txt"]: st.markdown(f"### {raw.decode()}")
                else:
                    st.write(f"📁 {p['name']}")
                    if "image" in p["type"]: st.image(raw)
                    elif "video" in p["type"]: st.video(raw)
                    elif "audio" in p["type"]: st.audio(raw)
                
                # --- SYSTÈME DE RÉACTIONS (Emojis interactifs) ---
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                with col_r1: 
                    if st.button(f"❤️", key=f"heart_{p['id']}"): vault.add_comment(p['id'], "❤️")
                with col_r2:
                    if st.button(f"😂", key=f"lol_{p['id']}"): vault.add_comment(p['id'], "😂")
                with col_r3:
                    if st.button(f"🔥", key=f"fire_{p['id']}"): vault.add_comment(p['id'], "🔥")
                with col_r4:
                    if st.button(f"✊", key=f"pow_{p['id']}"): vault.add_comment(p['id'], "✊")

                # --- ZONE DE COMMENTAIRES ---
                comments = vault.storage["COMMENTS"].get(p['id'], [])
                for c in comments:
                    st.markdown(f'<div class="comment-box"><b>💬 {c["ts"]} :</b> {c["txt"]}</div>', unsafe_allow_html=True)
                
                with st.expander("Ajouter un commentaire"):
                    c_input = st.text_input("Ton Kongossa sur ce post...", key=f"in_{p['id']}")
                    if st.button("Envoyer", key=f"btn_{p['id']}"):
                        vault.add_comment(p['id'], c_input)
                        st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)
        except: st.error("Rupture de signal TST")

    # 3. ZONE D'ENVOI (FIXÉE EN BAS PAR LE REFRESH)
    st.markdown("---")
    tabs = st.tabs(["💬 Tchat", "📸 Photo", "🎥 Vidéo", "🎙️ Vocal", "📂 Fichier"])
    
    with tabs[0]:
        t_msg = st.chat_input("Écris ton Kongossa...")
        if t_msg: 
            vault.push_signal(sid, t_msg.encode(), "txt", "text", True)
            st.rerun()
    with tabs[1]:
        pic = st.camera_input("Prendre une photo")
        if pic:
            vault.push_signal(sid, pic.getvalue(), "capture.jpg", "image/jpeg", False)
            st.rerun()
    with tabs[2]:
        vid = st.file_uploader("🎥 Envoyer une Vidéo (Bouton Rouge)", type=["mp4", "mov"])
        if vid and st.button("🚀 DIFFUSER VIDÉO"):
            vault.push_signal(sid, vid.getvalue(), vid.name, vid.type, False)
            st.rerun()
    with tabs[3]:
        vox = st.audio_input("Enregistrer un Vocal")
        if vox:
            vault.push_signal(sid, vox.getvalue(), "vocal.wav", "audio/wav", False)
            st.rerun()
    with tabs[4]:
        doc = st.file_uploader("Document", type=None)
        if doc:
            vault.push_signal(sid, doc.getvalue(), doc.name, doc.type, False)
            st.rerun()

    # --- CONTROLE SOUVERAIN ---
    if st.button("🧨 DETRUIRE TOUT LE TUNNEL"):
        vault.storage["FLUX"][sid] = []
        st.rerun()

    time.sleep(10)
    st.rerun()
else:
    st.warning("👋 Entrez la clé souveraine pour débloquer GEN Z GABON.")
