import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random

# =====================================================
# SYSTÈME DE PRÉSENCE ET FLUX
# =====================================================
if "user_id" not in st.session_state:
    st.session_state.user_id = f"USER-{random.randint(100, 999)}"

@st.cache_resource
def initialiser_systeme():
    return {
        "FLUX": {},
        "PRESENCE": {} # Stocke l'heure de dernière activité par ID_SESSION
    }

SYSTEME = initialiser_systeme()

def generer_id(code_base):
    if not code_base: return None
    grain = datetime.datetime.now().strftime("%Y-%m-%d-%H")
    return hashlib.sha256(f"{code_base}-{grain}".encode()).hexdigest()[:10].upper()

# =====================================================
# INTERFACE "INSTA-FUTUR" (CSS AVANCÉ)
# =====================================================
st.set_page_config(page_title="FREE-KONGOSSA", page_icon="✊", layout="centered")

st.markdown("""
    <style>
    /* Fond dégradé animé */
    .stApp {
        background: radial-gradient(circle at top right, #1e2a44, #0e1117);
    }
    
    /* Indicateur de présence */
    .presence-dot {
        height: 12px; width: 12px; background-color: #00ffa0;
        border-radius: 50%; display: inline-block;
        box-shadow: 0 0 10px #00ffa0; margin-right: 10px;
    }
    
    /* Cartes Glassmorphism */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
    }
    
    /* Suppression des éléments Streamlit lourds */
    header, footer {visibility: hidden;}
    .stChatInput { border-radius: 30px !important; }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# LOGIQUE DE CONNEXION
# =====================================================
st.title("✊ FREE-KONGOSSA")
code_racine = st.text_input("🔑 CLÉ QUANTIQUE", type="password", placeholder="Votre secret...").strip().upper()
id_session = generer_id(code_racine)

if id_session:
    # Mise à jour de la présence
    SYSTEME["PRESENCE"][f"{id_session}-{st.session_state.user_id}"] = time.time()
    
    if id_session not in SYSTEME["FLUX"]: SYSTEME["FLUX"][id_session] = []

    # --- BARRE D'ÉTAT (Présence de la sœur) ---
    # On regarde si un autre utilisateur est actif sur cet ID depuis moins de 30s
    autres_actifs = [uid for uid, t in SYSTEME["PRESENCE"].items() 
                     if uid.startswith(id_session) and uid != f"{id_session}-{st.session_state.user_id}" 
                     and (time.time() - t) < 30]
    
    if autres_actifs:
        st.markdown(f'<div><span class="presence-dot"></span><b>Signal détecté : Ta sœur est en ligne</b></div>', unsafe_allow_html=True)
    else:
        st.caption("☁️ Seul dans le tunnel (en attente du signal distant...)")

    st.markdown("---")

    # --- FIL D'ACTUALITÉ DYNAMIQUE ---
    placeholder = st.empty()
    with placeholder.container():
        posts = SYSTEME["FLUX"][id_session]
        for i, p in enumerate(reversed(posts)):
            with st.container():
                # Design Glassmorphism pour chaque post
                st.markdown(f'<div class="glass-card">', unsafe_allow_html=True)
                st.caption(f"⏱️ {p['time']}")
                
                try:
                    data = Fernet(p["key"]).decrypt(p["frag"][0]+p["frag"][1]+p["frag"][2])
                    if p["text"]:
                        st.markdown(f"### {data.decode()}")
                    else:
                        st.write(f"📁 **{p['name']}**")
                        if "image" in p["type"]: st.image(data)
                        elif "video" in p["type"]: st.video(data)
                        elif "audio" in p["type"] or p["name"].endswith(('.aac', '.m4a')):
                            st.audio(data)
                        st.download_button("💾 Récupérer", data, file_name=p["name"], key=f"dl_{i}")
                except:
                    st.error("Signal corrompu.")
                st.markdown('</div>', unsafe_allow_html=True)

    # --- ZONE DE CRÉATION RAPIDE ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("✨ PARTAGER UNE STORY", expanded=False):
        mode = st.tabs(["💬 Texte", "📸 Média"])
        
        with mode[0]:
            msg = st.chat_input("Écris ton secret...")
            if msg:
                cle = Fernet.generate_key()
                chiffre = Fernet(cle).encrypt(msg.encode())
                t = len(chiffre)
                SYSTEME["FLUX"][id_session].append({
                    "frag": (chiffre[:t//3], chiffre[t//3:2*t//3], chiffre[2*t//3:]),
                    "key": cle, "name": "Msg.txt", "type": "text/plain", "text": True,
                    "time": datetime.datetime.now().strftime("%H:%M")
                })
                st.rerun()
        
        with mode[1]:
            f = st.file_uploader("Prends une photo/vidéo ou charge un audio", type=None)
            if f and st.button("🚀 Diffuser le média"):
                cle = Fernet.generate_key()
                chiffre = Fernet(cle).encrypt(f.getvalue())
                t = len(chiffre)
                SYSTEME["FLUX"][id_session].append({
                    "frag": (chiffre[:t//3], chiffre[t//3:2*t//3], chiffre[2*t//3:]),
                    "key": cle, "name": f.name, "type": f.type, "text": False,
                    "time": datetime.datetime.now().strftime("%H:%M")
                })
                st.balloons()
                st.rerun()

    # Rafraîchissement automatique toutes les 7 secondes
    time.sleep(7)
    st.rerun()

else:
    # Écran de veille futuriste
    st.markdown("""
    <div style="text-align: center; margin-top: 100px;">
        <h1 style="font-size: 3em; color: #00ffa0;">SOUVERAINETÉ</h1>
        <p style="font-size: 1.5em; opacity: 0.6;">Le tunnel est scellé. Entrez la clé pour manifester le flux.</p>
    </div>
    """, unsafe_allow_html=True)
