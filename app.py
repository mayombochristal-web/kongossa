import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import random

# =====================================================
# SYSTÈME DE GESTION DES FLUX
# =====================================================
@st.cache_resource
def initialiser_systeme():
    return {"FLUX": {}}

SYSTEME = initialiser_systeme()

def generer_id(code_base):
    if not code_base: return None
    grain = datetime.datetime.now().strftime("%Y-%m-%d-%H")
    return hashlib.sha256(f"{code_base}-{grain}".encode()).hexdigest()[:10].upper()

# =====================================================
# DESIGN & STYLE LUDIQUE
# =====================================================
st.set_page_config(page_title="FREE-KONGOSSA", page_icon="✊", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; background-color: #ff4b4b; color: white; }
    .chat-bubble {
        background: #262730; padding: 15px; border-radius: 15px;
        margin-bottom: 15px; border-left: 5px solid #00ffa0;
    }
    .decoy { opacity: 0.3; filter: blur(1px); }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# BARRE LATERALE (Configuration)
# =====================================================
with st.sidebar:
    st.title("🔐 Accès")
    code_racine = st.text_input("VOTRE SECRET", type="password").strip().upper()
    id_session = generer_id(code_racine)
    
    if id_session:
        st.success(f"Tunnel Actif : {id_session}")
        if st.button("🧨 TOUT DÉTRUIRE"):
            SYSTEME["FLUX"][id_session] = []
            st.rerun()

# =====================================================
# CORPS DE L'APPLICATION (Colonnes)
# =====================================================
if id_session:
    if id_session not in SYSTEME["FLUX"]: SYSTEME["FLUX"][id_session] = []

    # Division de l'écran : 60% Discussion | 40% Envoi
    col_chat, col_post = st.columns([0.6, 0.4], gap="large")

    # --- COLONNE DROITE : ENVOI LUDIQUE ---
    with col_post:
        st.subheader("📤 Envoyer")
        
        with st.container(border=True):
            option = st.selectbox("Quoi de neuf ?", ["💬 Message", "🖼️ Média (Image/Vidéo)", "🎵 Audio/Vocaux", "📄 Document"])
            
            contenu = None
            nom_f, mime_f, is_text = "", "", False

            if option == "💬 Message":
                msg = st.text_input("Écris ton message ici...")
                if msg: contenu, nom_f, mime_f, is_text = msg.encode(), "Msg.txt", "text/plain", True
            
            elif option == "🖼️ Média (Image/Vidéo)":
                f = st.file_uploader("Prends ou choisis une photo/vidéo", type=['png', 'jpg', 'jpeg', 'mp4', 'mov'])
                if f: contenu, nom_f, mime_f, is_text = f.getvalue(), f.name, f.type, False
                
            elif option == "🎵 Audio/Vocaux":
                f = st.file_uploader("Enregistrement vocal", type=['mp3', 'wav', 'm4a'])
                if f: contenu, nom_f, mime_f, is_text = f.getvalue(), f.name, f.type, False
            
            else:
                f = st.file_uploader("Fichier")
                if f: contenu, nom_f, mime_f, is_text = f.getvalue(), f.name, f.type, False

            if contenu and st.button("🚀 PROPULSER DANS LE TUNNEL"):
                cle = Fernet.generate_key()
                chiffre = Fernet(cle).encrypt(contenu)
                t = len(chiffre)
                
                SYSTEME["FLUX"][id_session].append({
                    "frag": (chiffre[:t//3], chiffre[t//3:2*t//3], chiffre[2*t//3:]),
                    "key": cle, "name": nom_f, "type": mime_f, "text": is_text,
                    "time": datetime.datetime.now().strftime("%H:%M")
                })
                st.balloons() # Petit effet ludique !
                st.rerun()

    # --- COLONNE GAUCHE : FIL D'ACTUALITÉ ---
    with col_chat:
        st.subheader("🌐 Fil Free-Kongossa")
        posts = SYSTEME["FLUX"][id_session]
        
        if not posts:
            st.write("📭 Le tunnel est vide. En attente de signaux...")
        else:
            for i, p in enumerate(reversed(posts)):
                with st.container():
                    st.markdown(f'<div class="chat-bubble">', unsafe_allow_html=True)
                    st.caption(f"🕒 {p['time']}")
                    
                    try:
                        # Reconstitution
                        data = Fernet(p["key"]).decrypt(p["frag"][0]+p["frag"][1]+p["frag"][2])
                        
                        if p["text"]:
                            st.write(f"**Message :** {data.decode()}")
                        else:
                            st.write(f"📁 {p['name']}")
                            if "image" in p["type"]: st.image(data)
                            elif "video" in p["type"]: st.video(data)
                            elif "audio" in p["type"]: st.audio(data)
                            st.download_button("💾 Récupérer", data, file_name=p["name"], key=f"dl_{i}")
                    except:
                        st.error("Erreur de déchiffrement")
                    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("👋 Bienvenue ! Saisis ta clé secrète dans la barre latérale pour ouvrir ton tunnel.")
