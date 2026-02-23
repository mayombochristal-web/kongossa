import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# SYSTÈME DE GESTION (RAM & ÉPHÉMÈRE)
# =====================================================
@st.cache_resource
def init_vault():
    # FLUX stocke les messages, PRESENCE les utilisateurs en ligne
    return {"FLUX": {}, "PRESENCE": {}}

VAULT = init_vault()

def secure_id(key):
    if not key: return None
    # L'identifiant change toutes les heures pour rompre le traçage
    h = f"{key}-{datetime.datetime.now().strftime('%Y-%m-%d-%H')}"
    return hashlib.sha256(h.encode()).hexdigest()[:12].upper()

# =====================================================
# DESIGN FUTURISTE GABONAIS (CSS)
# =====================================================
st.set_page_config(page_title="GEN-Z GABON", page_icon="🇬🇦", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: radial-gradient(circle at top, #0f2027, #203a43, #2c5364); }
    
    /* Cartes Glassmorphism */
    .post-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        border-radius: 25px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    
    /* Timer de destruction */
    .timer-badge {
        background: linear-gradient(90deg, #ff4b2b, #ff416c);
        color: white; padding: 4px 12px; border-radius: 20px;
        font-size: 0.7em; font-weight: bold; float: right;
    }
    
    .online-indicator {
        color: #00ffaa; font-size: 0.8em; font-weight: bold;
        text-shadow: 0 0 10px #00ffaa;
    }
    
    .app-header {
        text-align: center; font-weight: 900; font-size: 3em;
        background: linear-gradient(to right, #00ffaa, #00d4ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# INTERFACE D'ACCÈS
# =====================================================
st.markdown('<h1 class="app-header">GEN-Z GABON</h1>', unsafe_allow_html=True)
st.caption("<center>Souveraineté. Éphémérité. Liberté.</center>", unsafe_allow_html=True)

secret_key = st.text_input("🔑 CLÉ DU TUNNEL", type="password", placeholder="Secret partagé...").strip().upper()
session_id = secure_id(secret_key)

if session_id:
    # Présence temps réel
    if "u_token" not in st.session_state: st.session_state.u_token = random.randint(100, 999)
    current_time = time.time()
    VAULT["PRESENCE"][f"{session_id}-{st.session_state.u_token}"] = current_time
    
    if session_id not in VAULT["FLUX"]: VAULT["FLUX"][session_id] = []

    # Vérification présence de l'autre
    peers = [k for k, v in VAULT["PRESENCE"].items() if k.startswith(session_id) and (current_time - v) < 20]
    if len(peers) > 1:
        st.markdown('<p class="online-indicator">🟢 SIGNAL ACTIF : TA SŒUR EST DANS LE TUNNEL</p>', unsafe_allow_html=True)

    # =====================================================
    # CRÉATION MULTIMÉDIA (CAPTURE LIVE)
    # =====================================================
    st.markdown("### ⚡ Diffuser un signal")
    tabs = st.tabs(["💬 Texte", "📷 Caméra", "🎙️ Micro", "📂 Fichier"])
    
    content, name, m_type, is_txt = None, "", "", False

    with tabs[0]:
        msg = st.chat_input("Un Kongossa ?")
        if msg: content, name, m_type, is_txt = msg.encode(), "txt", "text", True

    with tabs[1]:
        photo = st.camera_input("Capture instantanée")
        if photo: content, name, m_type = photo.getvalue(), "live.jpg", "image/jpeg"

    with tabs[2]:
        vocal = st.audio_input("Mémo vocal souverain")
        if vocal: content, name, m_type = vocal.getvalue(), "vocal.wav", "audio/wav"

    with tabs[3]:
        doc = st.file_uploader("Tout document", type=None)
        if doc: content, name, m_type = doc.getvalue(), doc.name, doc.type

    if content:
        # Sécurisation Triadique
        key = Fernet.generate_key()
        f = Fernet(key)
        encrypted_data = f.encrypt(content)
        size = len(encrypted_data)
        
        VAULT["FLUX"][session_id].append({
            "f1": encrypted_data[:size//3], 
            "f2": encrypted_data[size//3:2*size//3], 
            "f3": encrypted_data[2*size//3:],
            "k": key, "name": name, "type": m_type, "is_txt": is_txt,
            "timestamp": time.time(), # Pour le compte à rebours
            "expiry": 3600 # Durée de vie : 1 heure (3600 sec)
        })
        st.balloons()
        st.rerun()

    # =====================================================
    # FLUX DYNAMIQUE & AUTO-DESTRUCT
    # =====================================================
    st.markdown("---")
    st.subheader("🌐 Tunnel Temporel")
    
    feed = st.empty()
    with feed.container():
        # Filtrage des messages expirés
        active_posts = [p for p in VAULT["FLUX"][session_id] if (time.time() - p["timestamp"]) < p["expiry"]]
        VAULT["FLUX"][session_id] = active_posts # Nettoyage mémoire
        
        if not active_posts:
            st.info("Le tunnel est vide. Les messages précédents ont été désintégrés.")
        else:
            for i, p in enumerate(reversed(active_posts)):
                # Calcul du temps restant
                temps_restant = int(p["expiry"] - (time.time() - p["timestamp"]))
                minutes = temps_restant // 60
                
                st.markdown(f'''
                    <div class="post-card">
                        <span class="timer-badge">⏳ AUTO-DESTRUCT : {minutes}m</span>
                        <p style="font-size:0.8em; opacity:0.6;">Signal émis à {datetime.datetime.fromtimestamp(p["timestamp"]).strftime("%H:%M")}</p>
                ''', unsafe_allow_html=True)
                
                try:
                    # Reconstruction
                    decrypted = Fernet(p["k"]).decrypt(p["f1"] + p["f2"] + p["f3"])
                    
                    if p["is_txt"]:
                        st.markdown(f"### {decrypted.decode()}")
                    else:
                        st.write(f"📎 {p['name']}")
                        if "image" in p["type"]: st.image(decrypted)
                        elif "video" in p["type"]: st.video(decrypted)
                        elif "audio" in p["type"] or p["name"].endswith(('.aac', '.m4a', '.wav')):
                            st.audio(decrypted)
                        st.download_button("💾 Aspirer", decrypted, file_name=p["name"], key=f"dl_{i}")
                except:
                    st.error("Rupture de signal.")
                
                st.markdown('</div>', unsafe_allow_html=True)

    # Rafraîchissement automatique toutes les 10 secondes
    time.sleep(10)
    st.rerun()

else:
    st.markdown("""
    <div style="text-align: center; margin-top: 100px; color: #00ffaa; opacity: 0.7;">
        <h3>En attente de la clé de déchiffrement...</h3>
        <p>Tunnel sécurisé par protocole Triadique.</p>
    </div>
    """, unsafe_allow_html=True)
