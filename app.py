import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# CLASSE CŒUR : LOGIQUE TST & SOUVERAINETÉ
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
        # Cycle de Derime : calcul de l'entropie horaire
        grain = datetime.datetime.now().strftime("%Y-%m-%d-%H")
        return hashlib.sha256(f"{key}-{grain}".encode()).hexdigest()[:12].upper()

    def broadcast(self, sid, content, fname, mtype, is_txt):
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
# CLASSE UI : INTERFACE INTERACTIVE
# =====================================================
class KongossaUI:
    @staticmethod
    def inject_glassmorphism():
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;700;900&display=swap');
            * { font-family: 'Outfit', sans-serif; }
            .stApp { background: #050505; color: white; }
            
            /* Accueil Interactif */
            .hero-card {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(0, 255, 170, 0.2);
                border-radius: 25px; padding: 30px; text-align: center;
                margin-top: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }
            .step-box {
                background: rgba(0, 255, 170, 0.05);
                border-radius: 15px; padding: 15px; margin: 10px 0;
                border-left: 4px solid #00FFAA; text-align: left;
            }
            .chat-bubble {
                background: rgba(255, 255, 255, 0.07);
                border-radius: 20px; padding: 20px; margin-bottom: 20px;
                border: 1px solid rgba(255,255,255,0.1);
            }
            .tst-timer { color: #ff4b4b; font-weight: bold; font-size: 0.8em; }
            .comment-area { background: rgba(0,0,0,0.3); border-radius: 10px; padding: 10px; margin-top: 10px; }
            </style>
        """, unsafe_allow_html=True)

# =====================================================
# MAIN APP
# =====================================================
tst = TSTEngine()
ui = KongossaUI()
ui.inject_glassmorphism()

# --- ETAT DE LA SESSION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- LOGO & TITRE ---
st.markdown('<p style="text-align:center; font-size:50px; margin-bottom:0;">🇬🇦</p>', unsafe_allow_html=True)
st.markdown('<h1 style="text-align:center; background: linear-gradient(90deg, #00FFAA, #00D4FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight:900; font-size:2.5em;">GEN Z GABON FREE-KONGOSSA</h1>', unsafe_allow_html=True)

# =====================================================
# PHASE 1 : ACCUEIL INTERACTIF (LANDING)
# =====================================================
if not st.session_state.authenticated:
    st.markdown("""
    <div class="hero-card">
        <h2>Bienvenue dans le Tunnel Souverain ⚡</h2>
        <p>Ici, le Kongossa est un art protégé par la Thermodynamique (TST).</p>
        <div class="step-box"><b>1. La Clé :</b> Utilise un mot secret connu de vous seuls.</div>
        <div class="step-box"><b>2. L'Éphémère :</b> Tes messages s'évaporent en 60 min.</div>
        <div class="step-box"><b>3. La Sécurité :</b> Chaque donnée est éclatée en 3 fragments.</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("<br>", unsafe_allow_html=True)
    secret = st.text_input("🔑 Entre ton code secret pour activer le tunnel", type="password", help="Ce code génère ton ID de session unique.").strip().upper()
    
    if st.button("🚀 ACTIVER LE KONGOSSA", use_container_width=True):
        if secret:
            st.session_state.sid = tst.derive_session_id(secret)
            st.session_state.authenticated = True
            st.balloons()
            st.rerun()
        else:
            st.error("Il faut une clé pour entrer dans le tunnel.")

# =====================================================
# PHASE 2 : INTERFACE DE TCHAT (APRES AUTH)
# =====================================================
else:
    sid = st.session_state.sid
    
    # Présence active
    if "u_token" not in st.session_state: st.session_state.u_token = random.randint(100, 999)
    tst.db["PRESENCE"][f"{sid}-{st.session_state.u_token}"] = time.time()
    
    # Stats
    active = [k for k, v in tst.db["PRESENCE"].items() if k.startswith(sid) and (time.time() - v) < 20]
    st.markdown(f"<center><small>🟢 SIGNAL ACTIF : {len(active)} Unités dans le tunnel</small></center>", unsafe_allow_html=True)

    # Bouton de sortie
    if st.button("🔓 Quitter le tunnel"):
        st.session_state.authenticated = False
        st.rerun()

    st.markdown("---")

    # --- FLUX DE MESSAGES ---
    tst.db["FLUX"][sid] = [p for p in tst.db["FLUX"].get(sid, []) if (time.time() - p["ts"]) < 3600]
    
    for i, p in enumerate(tst.db["FLUX"].get(sid, [])):
        with st.container():
            st.markdown('<div class="chat-bubble">', unsafe_allow_html=True)
            try:
                # Reconstruction TST
                f = Fernet(p["k"])
                raw = f.decrypt(p["fragments"][0] + p["fragments"][1] + p["fragments"][2])
                
                rem = int(3600 - (time.time() - p["ts"]))
                st.markdown(f'<span class="tst-timer">⏳ DISSIPATION : {rem//60}m</span>', unsafe_allow_html=True)
                
                if p["is_txt"]: st.markdown(f"### {raw.decode()}")
                else:
                    st.caption(f"📁 {p['name']}")
                    if "image" in p["type"]: st.image(raw)
                    elif "video" in p["type"]: st.video(raw)
                    elif "audio" in p["type"]: st.audio(raw)

                # --- REACTIONS & COMMENTAIRES ---
                r_col1, r_col2, r_col3 = st.columns(3)
                with r_col1:
                    if st.button("❤️", key=f"h_{p['id']}"): 
                        if p['id'] not in tst.db["COMMENTS"]: tst.db["COMMENTS"][p['id']] = []
                        tst.db["COMMENTS"][p['id']].append("❤️")
                with r_col2:
                    if st.button("😂", key=f"l_{p['id']}"):
                        if p['id'] not in tst.db["COMMENTS"]: tst.db["COMMENTS"][p['id']] = []
                        tst.db["COMMENTS"][p['id']].append("😂")
                with r_col3:
                    if st.button("✊", key=f"p_{p['id']}"):
                        if p['id'] not in tst.db["COMMENTS"]: tst.db["COMMENTS"][p['id']] = []
                        tst.db["COMMENTS"][p['id']].append("✊")

                # Affichage commentaires
                if p['id'] in tst.db["COMMENTS"]:
                    st.markdown('<div class="comment-area">', unsafe_allow_html=True)
                    for c in tst.db["COMMENTS"][p['id']]:
                        st.markdown(f"💬 {c}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Input commentaire
                c_in = st.text_input("Commenter...", key=f"in_{p['id']}")
                if st.button("Publier", key=f"pub_{p['id']}"):
                    if p['id'] not in tst.db["COMMENTS"]: tst.db["COMMENTS"][p['id']] = []
                    tst.db["COMMENTS"][p['id']].append(c_in)
                    st.rerun()
                    
            except: st.error("🔒 Fragment TST perdu")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- ZONE D'ENVOI (EN BAS) ---
    st.markdown("---")
    st.subheader("➕ Nouveau Signal")
    tabs = st.tabs(["💬 Tchat", "📸 Photo", "🎥 Vidéo", "🎙️ Vocal"])
    
    with tabs[0]:
        t_in = st.chat_input("Raconte ton Kongossa...")
        if t_in: 
            tst.broadcast(sid, t_in.encode(), "txt", "text", True)
            st.rerun()
    with tabs[1]:
        cam = st.camera_input("📸 Photo")
        if cam: 
            tst.broadcast(sid, cam.getvalue(), "img.jpg", "image/jpeg", False)
            st.rerun()
    with tabs[2]:
        vid = st.file_uploader("🎥 Vidéo (MP4/MOV)", type=["mp4", "mov"])
        if vid and st.button("🚀 Diffuser Vidéo"):
            tst.broadcast(sid, vid.getvalue(), vid.name, vid.type, False)
            st.rerun()
    with tabs[3]:
        vox = st.audio_input("🎙️ Message Vocal")
        if vox:
            tst.broadcast(sid, vox.getvalue(), "vocal.wav", "audio/wav", False)
            st.rerun()

    # Refresh
    time.sleep(8)
    st.rerun()
