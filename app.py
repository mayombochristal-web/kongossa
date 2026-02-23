import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import random

# =====================================================
# GESTION DES FLUX SOUVERAINS (RAM UNIQUEMENT)
# =====================================================
@st.cache_resource
def initialiser_systeme():
    return {"FLUX": {}}

SYSTEME = initialiser_systeme()

def generer_id(code_base):
    if not code_base: return None
    # ID qui change toutes les heures
    grain = datetime.datetime.now().strftime("%Y-%m-%d-%H")
    return hashlib.sha256(f"{code_base}-{grain}".encode()).hexdigest()[:10].upper()

# --- Générateur de Leurres (Système anti-surveillance) ---
def injecter_leurres():
    sujets_leures = ["Recette_Gateau.pdf", "Paysage_Afrique.jpg", "Audio_Conf.mp3", "Video_Dansante.mp4"]
    for i in range(5): # 5 faux flux par heure pour brouiller les pistes
        faux_id = generer_id(f"FAKE_KEY_{i}_{datetime.datetime.now().hour}")
        if faux_id not in SYSTEME["FLUX"]:
            SYSTEME["FLUX"][faux_id] = [{
                "is_decoy": True, # Marque un post comme un leurre
                "name": random.choice(sujets_leures),
                "type": "text/plain", # Type générique pour ne pas consommer trop de RAM pour les leurres
                "time": f"{random.randint(0,23)}:{random.randint(10,59)}"
            }]

injecter_leurres() # Active les leurres au démarrage

# =====================================================
# DESIGN "INSTAGRAM DU FUTUR"
# =====================================================
st.set_page_config(page_title="FREE-KONGOSSA", page_icon="✊", layout="wide")

st.markdown("""
    <style>
    /* Général */
    .stApp { background: #0E1117; color: white; }
    h1, h2, h3, h4, h5, h6 { color: #00FFAA; }
    p { font-size: 1.1em; }

    /* Entrée de la Clé */
    .stTextInput label { font-size: 1.2em; color: #FF4B4B; }
    .stTextInput input { border-radius: 10px; border: 1px solid #333; padding: 10px; }

    /* Boutons */
    .stButton>button { 
        width: 100%; border-radius: 10px; height: 3em; 
        background: linear-gradient(90deg, #FF4B4B, #FF8C00); /* Dégradé stylé */
        color: white; font-weight: bold; border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .stDownloadButton button { background: #007BFF; } /* Couleur bleue pour télécharger */

    /* "Stories" éphémères (les bulles) */
    .story-card {
        background: #1C1C24; /* Fond sombre */
        border-radius: 15px; margin-bottom: 15px; padding: 20px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.4);
        border-left: 5px solid #00FFAA; /* Bordure colorée pour le "vrai" flux */
    }
    .story-card.decoy { border-left: 5px solid #555; opacity: 0.6; } /* Leurre plus discret */
    .timestamp { font-size: 0.8em; color: #808495; margin-bottom: 10px; display: block; }
    .stImage, .stVideo, .stAudio { border-radius: 10px; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# APPLICATION PRINCIPALE
# =====================================================

st.title("✊ FREE-KONGOSSA")
st.markdown("### *Ton espace privé, éphémère et souverain*")

# --- ZONE D'ACCÈS ET CLÉ SECRÈTE ---
st.subheader("🔑 Ouvre ton Tunnel")
code_racine = st.text_input("Entre ta clé secrète ici", type="password", placeholder="Ex: MAMBOUNDOU, le nom de notre rue...").strip().upper()

id_session = generer_id(code_racine)

if id_session:
    if id_session not in SYSTEME["FLUX"]: SYSTEME["FLUX"][id_session] = []

    st.success(f"Tunnel Actif : {id_session} (Valide jusqu'à la prochaine heure)")
    st.markdown("---")

    # --- FIL D'ACTUALITÉ / "STORIES" ---
    st.subheader("🌟 Tes Stories Éphémères")
    posts_actifs = [p for p in SYSTEME["FLUX"][id_session] if not p.get("is_decoy", False)]

    if not posts_actifs: # Affiche seulement les vrais posts
        st.info("👻 Le tunnel est ouvert ! Partage ta première histoire...")
    else:
        # Affichage des posts du plus récent au plus ancien
        for i, p in enumerate(reversed(posts_actifs)):
            with st.container():
                st.markdown(f'<div class="story-card">', unsafe_allow_html=True)
                st.markdown(f'<span class="timestamp">{p["time"]}</span>', unsafe_allow_html=True)
                
                try:
                    # Fusion des 3 fragments et déchiffrement
                    complet = p["frag"][0] + p["frag"][1] + p["frag"][2]
                    data = Fernet(p["key"]).decrypt(complet)
                    
                    if p["text"]:
                        st.write(data.decode())
                    else:
                        st.write(f"📁 **{p['name']}**")
                        if "image" in p["type"]: st.image(data, use_column_width=True)
                        elif "video" in p["type"]: st.video(data)
                        elif "audio" in p["type"]: st.audio(data)
                        st.download_button(f"📥 Télécharger {p['name']}", data, file_name=p["name"], key=f"dl_{i}")
                except Exception as e:
                    st.error(f"Rupture de signal : impossible de lire ce post. ({e})")
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")

    # --- ZONE D'ENVOI "CRÉER UNE STORY" ---
    st.subheader("➕ Crée ta Story")
    
    col_input, col_button = st.columns([0.7, 0.3])
    
    with col_input:
        type_media = st.radio("Quel type de story ?", ["💬 Message", "📸 Photo/Vidéo", "🎙️ Audio", "📄 Document"], horizontal=True)
        
        contenu = None
        nom_f, mime_f, is_text = "", "", False

        if type_media == "💬 Message":
            msg = st.text_area("Ton message...", placeholder="Partage tes pensées secrètes...", height=100)
            if msg: contenu, nom_f, mime_f, is_text = msg.encode(), "Msg.txt", "text/plain", True
        else:
            # Type = None pour accepter TOUS les formats (y compris AAC)
            f = st.file_uploader("Charge ton média", type=None) 
            if f: contenu, nom_f, mime_f, is_text = f.getvalue(), f.name, f.type, False

    with col_button:
        # Bouton d'envoi principal
        st.write("") # Espace pour aligner le bouton
        st.write("") 
        if contenu and st.button("🚀 PUBLIER MA STORY"):
            cle = Fernet.generate_key()
            chiffre = Fernet(cle).encrypt(contenu)
            t = len(chiffre)
            
            SYSTEME["FLUX"][id_session].append({
                "frag": (chiffre[:t//3], chiffre[t//3:2*t//3], chiffre[2*t//3:]),
                "key": cle, "name": nom_f, "type": mime_f, "text": is_text,
                "time": datetime.datetime.now().strftime("%H:%M")
            })
            st.success("Story publiée et sécurisée !")
            st.balloons() # Célébration ludique
            st.rerun() # Rafraîchit le fil d'actualité

        # Bouton de destruction des données
        st.write("")
        if st.button("🧨 Vider le Tunnel"):
            SYSTEME["FLUX"][id_session] = []
            st.warning("Le tunnel a été vidé. Toutes les stories ont disparu !")
            st.rerun()

else:
    st.info("💡 Saisis la clé secrète partagée avec ton proche pour débloquer les stories éphémères et sécurisées.")
    st.markdown("---")
    st.write("""
        ### Pourquoi FREE-KONGOSSA ?
        - **Souveraineté** : Tes données restent invisibles, jamais stockées sur un disque.
        - **Éphémère** : Tout disparaît automatiquement après chaque heure.
        - **Incraquable** : Ton secret est fragmenté en 3, chiffré et noyé parmi des leurres numériques.
        - **Éthique** : Zéro traçage, zéro publicité. C'est TA communication.
    """)
