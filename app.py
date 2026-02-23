import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time

# =====================================================
# CŒUR DU SYSTÈME : FLUX INSTANTANÉ
# =====================================================
if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()

@st.cache_resource
def initialiser_systeme():
    return {"FLUX": {}}

SYSTEME = initialiser_systeme()

def generer_id(code_base):
    if not code_base: return None
    grain = datetime.datetime.now().strftime("%Y-%m-%d-%H")
    return hashlib.sha256(f"{code_base}-{grain}".encode()).hexdigest()[:10].upper()

# =====================================================
# DESIGN "INSTAGRAM DU FUTUR" (SANS BORDURES)
# =====================================================
st.set_page_config(page_title="FREE-KONGOSSA", page_icon="✊", layout="centered")

st.markdown("""
    <style>
    /* Suppression des marges inutiles */
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    
    /* Bulles de message modernes */
    .stChatMessage { background-color: #1A1C23; border-radius: 15px; border: none; margin-bottom: 10px; }
    
    /* Zone d'entrée de texte flottante style mobile */
    .fixed-bottom {
        position: fixed; bottom: 0; left: 0; right: 0; 
        background: #0E1117; padding: 10px; z-index: 1000;
        border-top: 1px solid #333;
    }
    
    /* Suppression des coins Streamlit par défaut */
    div[data-testid="stExpander"] { border: none !important; background: transparent !important; }
    .stAlert { border-radius: 10px; border: none; }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# INTERFACE PRINCIPALE
# =====================================================

# 1. Accès (Minimaliste)
code_racine = st.text_input("🔑 CLÉ", type="password", placeholder="Votre secret commun...").strip().upper()
id_session = generer_id(code_racine)

if id_session:
    if id_session not in SYSTEME["FLUX"]: SYSTEME["FLUX"][id_session] = []

    # 2. Fil d'actualité automatique
    st.write(f"### ✨ Fil Souverain")
    
    # Zone de contenu dynamique
    placeholder = st.empty()
    
    with placeholder.container():
        posts = SYSTEME["FLUX"][id_session]
        if not posts:
            st.write("✨ Tunnel prêt. Partagez un secret.")
        else:
            for i, p in enumerate(reversed(posts)):
                # Style Chat Message Streamlit (Très fluide)
                with st.chat_message("user" if i%2==0 else "assistant", avatar="✊"):
                    st.caption(f"{p['time']}")
                    try:
                        # Déchiffrement Triadique
                        complet = p["frag"][0] + p["frag"][1] + p["frag"][2]
                        data = Fernet(p["key"]).decrypt(complet)
                        
                        if p["text"]:
                            st.markdown(data.decode())
                        else:
                            if "image" in p["type"]: st.image(data)
                            elif "video" in p["type"]: st.video(data)
                            elif "audio" in p["type"] or p["name"].endswith(('.aac', '.m4a')): 
                                st.audio(data)
                            st.download_button(f"📥 {p['name']}", data, file_name=p["name"], key=f"dl_{i}")
                    except:
                        st.error("Signal perdu ou clé incorrecte.")

    # 3. Zone de Publication (Ludique & Rapide)
    st.markdown("---")
    with st.expander("➕ PUBLIER MAINTENANT", expanded=True):
        col_type, col_act = st.columns([2, 1])
        with col_type:
            mode = st.radio("Format", ["Texte", "Média"], horizontal=True, label_visibility="collapsed")
        
        contenu, nom_f, mime_f, is_text = None, "", "", False
        
        if mode == "Texte":
            msg = st.chat_input("Écris ton message...") # Barre style WhatsApp
            if msg: contenu, nom_f, mime_f, is_text = msg.encode(), "Msg.txt", "text/plain", True
        else:
            f = st.file_uploader("Photo, Vidéo, Audio (AAC inclus)", type=None)
            if f: contenu, nom_f, mime_f, is_text = f.getvalue(), f.name, f.type, False

        if contenu:
            # Chiffrement et Fragmentation
            cle = Fernet.generate_key()
            chiffre = Fernet(cle).encrypt(contenu)
            t = len(chiffre)
            SYSTEME["FLUX"][id_session].append({
                "frag": (chiffre[:t//3], chiffre[t//3:2*t//3], chiffre[2*t//3:]),
                "key": cle, "name": nom_f, "type": mime_f, "text": is_text,
                "time": datetime.datetime.now().strftime("%H:%M")
            })
            st.rerun()

    # --- AUTO-REFRESH (Le secret de la fluidité) ---
    # Cette ligne fait que l'app vérifie les nouveaux messages toutes les 5 secondes
    time.sleep(5)
    st.rerun()

else:
    st.info("👋 Entrez votre secret pour ouvrir le tunnel.")
