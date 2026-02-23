import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# CONFIGURATION & MÉMOIRE (RAM SÉCURISÉE)
# =====================================================
st.set_page_config(page_title="GEN-Z GABON", page_icon="🇬🇦", layout="centered")

@st.cache_resource
def init_vault():
    """Initialise le dictionnaire partagé avec toutes les clés nécessaires."""
    return {
        "FLUX": {},           # Messages par session_id
        "PRESENCE": {},       # Présence des utilisateurs
        "HISTORY": set(),     # IDs des messages déjà vus (pour éviter les doublons)
        "SEEN_IDS": set(),    # (Optionnel) pour d'autres vérifications
    }

VAULT = init_vault()

def secure_id(key):
    """Génère un identifiant de session sécurisé à partir de la clé."""
    if not key:
        return None
    h = f"{key}-{datetime.datetime.now().strftime('%Y-%m-%d-%H')}"
    return hashlib.sha256(h.encode()).hexdigest()[:12].upper()

# =====================================================
# DESIGN DARK MODE (GLASSMORPHISM)
# =====================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background-color: #000000; color: #ffffff; }
    
    .chat-bubble {
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(12px);
        border-radius: 22px;
        padding: 18px;
        margin: 12px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        width: fit-content;
        max-width: 88%;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    
    .timer { color: #ff4b2b; font-size: 0.75em; font-weight: bold; margin-top: 8px; display: block; }
    .status-active { color: #00ffaa; font-size: 0.85em; text-align: center; font-weight: 600; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# LOGIQUE D'ACCÈS
# =====================================================
st.markdown('<h1 style="text-align:center; color:#00ffaa; font-weight:900; letter-spacing:-1px;">GEN-Z GABON</h1>', unsafe_allow_html=True)

with st.expander("🔑 CLÉ DU TUNNEL", expanded=True):
    secret_key = st.text_input("SECRET", type="password", label_visibility="collapsed").strip().upper()

session_id = secure_id(secret_key)

if session_id:
    # Gestion de la présence de l'utilisateur
    if "u_token" not in st.session_state:
        st.session_state.u_token = random.randint(100, 999)
    
    presence_key = f"{session_id}-{st.session_state.u_token}"
    VAULT["PRESENCE"][presence_key] = time.time()
    
    # Nettoyage des présences expirées (plus de 20 secondes)
    current_time = time.time()
    expired = [k for k, t in VAULT["PRESENCE"].items() if current_time - t > 20]
    for k in expired:
        VAULT["PRESENCE"].pop(k, None)
    
    # Initialisation du flux pour cette session si nécessaire
    if session_id not in VAULT["FLUX"]:
        VAULT["FLUX"][session_id] = []

    # Affichage du statut de connexion
    others = [k for k in VAULT["PRESENCE"].keys() if k.startswith(session_id) and k != presence_key]
    if others:
        st.markdown(f'<div class="status-active">● SIGNAL ACTIF : {len(others)} autre(s) connecté(s)</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-active">● EN ATTENTE...</div>', unsafe_allow_html=True)

    # =====================================================
    # 1. FIL DE DISCUSSION (FLUX CHRONOLOGIQUE)
    # =====================================================
    # Nettoyage des messages de plus de 60 minutes
    VAULT["FLUX"][session_id] = [p for p in VAULT["FLUX"][session_id] if (time.time() - p["ts"]) < 3600]
    
    st.markdown("---")
    chat_container = st.container()
    with chat_container:
        posts = VAULT["FLUX"][session_id]
        if not posts:
            st.caption("<center>Aucun message. Le tunnel est vide.</center>", unsafe_allow_html=True)
        else:
            for i, p in enumerate(posts):
                st.markdown('<div class="chat-bubble">', unsafe_allow_html=True)
                try:
                    # Reconstruction triadique sécurisée
                    k_obj = p.get("k")
                    fragments = p.get("f1", b"") + p.get("f2", b"") + p.get("f3", b"")
                    
                    if k_obj and fragments:
                        data = Fernet(k_obj).decrypt(fragments)
                        
                        if p.get("is_txt"):
                            st.markdown(f"{data.decode()}")
                        else:
                            st.caption(f"📁 {p['name']}")
                            if "image" in p["type"]:
                                st.image(data)
                            elif "video" in p["type"]:
                                st.video(data)
                            elif "audio" in p["type"] or p["name"].lower().endswith(('.aac', '.m4a', '.wav', '.mp3')):
                                st.audio(data)
                            else:
                                # Fichier binaire générique
                                st.download_button("💾 Télécharger", data, file_name=p["name"], key=f"dl_{i}_{p['ts']}")
                except Exception as e:
                    st.error(f"🔒 Fragment illisible : {str(e)}")
                
                # Affichage du temps restant avant auto-destruction
                rem = int(3600 - (time.time() - p["ts"]))
                st.markdown(f'<span class="timer">🔥 AUTO-DESTRUCT : {rem // 60} min</span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # =====================================================
    # 2. CAPTURE & ENVOI (ANTI-BOUCLE)
    # =====================================================
    st.markdown("---")
    with st.container():
        mode = st.tabs(["💬 Texte", "📸 Photo", "🎙️ Audio", "📂 Fichier"])
        
        raw_to_send = None
        f_name = ""
        m_type = ""
        is_txt = False

        with mode[0]:
            t_in = st.chat_input("Message...")
            if t_in:
                raw_to_send = t_in.encode()
                f_name = "txt"
                m_type = "text/plain"
                is_txt = True

        with mode[1]:
            cam = st.camera_input("Prendre une photo")
            if cam:
                raw_to_send = cam.getvalue()
                f_name = "photo.jpg"
                m_type = "image/jpeg"

        with mode[2]:
            mic = st.audio_input("Enregistrer un message vocal")
            if mic:
                raw_to_send = mic.getvalue()
                f_name = "audio.wav"
                m_type = "audio/wav"

        with mode[3]:
            upl = st.file_uploader("Choisir un fichier", label_visibility="collapsed")
            if upl:
                raw_to_send = upl.getvalue()
                f_name = upl.name
                m_type = upl.type or "application/octet-stream"

        # Envoi du message si des données sont présentes
        if raw_to_send:
            # Génération d'un identifiant unique pour éviter les doublons
            msg_id = hashlib.md5(raw_to_send + str(round(time.time(), 1)).encode()).hexdigest()
            
            # Vérification des doublons
            if msg_id not in VAULT["HISTORY"]:
                # Chiffrement triadique
                key = Fernet.generate_key()
                cipher = Fernet(key)
                encrypted = cipher.encrypt(raw_to_send)
                l = len(encrypted)
                
                # Découpage en trois fragments
                fragment1 = encrypted[:l//3]
                fragment2 = encrypted[l//3:2*l//3]
                fragment3 = encrypted[2*l//3:]
                
                # Ajout au flux
                VAULT["FLUX"][session_id].append({
                    "f1": fragment1,
                    "f2": fragment2,
                    "f3": fragment3,
                    "k": key,
                    "name": f_name,
                    "type": m_type,
                    "is_txt": is_txt,
                    "ts": time.time(),
                    "msg_id": msg_id
                })
                VAULT["HISTORY"].add(msg_id)
                st.rerun()
            else:
                st.warning("Ce message a déjà été envoyé récemment.")

    # =====================================================
    # 3. CONTRÔLE DE DESTRUCTION
    # =====================================================
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🧨 DISPERSER TOUT LE TUNNEL", use_container_width=True):
        VAULT["FLUX"][session_id] = []
        st.rerun()

    # =====================================================
    # 4. RAFRAÎCHISSEMENT AUTOMATIQUE (optionnel)
    # =====================================================
    # Pour éviter de surcharger le serveur, on utilise un rafraîchissement toutes les 10 secondes
    # mais seulement si l'utilisateur est actif. On peut aussi utiliser st.empty() et des mises à jour partielles.
    # Ici, on utilise un placeholder pour éviter un rerun inconditionnel.
    placeholder = st.empty()
    time.sleep(10)
    st.rerun()

else:
    st.info("🔐 Entrez la clé secrète pour manifester la GEN-Z GABON.")