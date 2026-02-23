import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import random

# =====================================================
# ARCHITECTURE MULTI-FLUX & LEURES
# =====================================================
@st.cache_resource
def initialiser_systeme_triadique():
    return {"FLUX": {}}

SYSTEME = initialiser_systeme_triadique()

def generer_identifiant_temporel(code_base):
    if not code_base: return None
    grain_de_sel = datetime.datetime.now().strftime("%Y-%m-%d-%H")
    return hashlib.sha256(f"{code_base}-{grain_de_sel}".encode()).hexdigest()[:12].upper()

def generer_leures_horaires():
    """Génère du bruit numérique pour saturer le serveur de faux IDs."""
    sujets = ["Rapport_Vente.pdf", "Vacances.jpg", "Note_Vocale.mp3", "Film_Famille.mp4"]
    for i in range(5):
        faux_id = generer_identifiant_temporel(f"FAKE_KEY_{i}_{datetime.datetime.now().hour}")
        if faux_id not in SYSTEME["FLUX"]:
            SYSTEME["FLUX"][faux_id] = [{"is_decoy": True, "name": random.choice(sujets), "time": "14:02"}]

generer_leures_horaires()

# =====================================================
# INTERFACE RÉSEAU SOCIAL
# =====================================================
st.set_page_config(page_title="FREE-KONGOSSA", page_icon="✊", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    .message-bubble { 
        padding: 20px; border-radius: 20px; background-color: #262730; 
        margin-bottom: 15px; border-left: 6px solid #00FFAA;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .time-stamp { color: #808495; font-size: 0.75em; margin-bottom: 10px; display: block; }
    </style>
""", unsafe_allow_html=True)

st.title("✊ FREE-KONGOSSA")
st.caption("Messagerie Sociale Triadique | Souveraineté Totale")

# Saisie de la clé (Ton secret avec Laetitia)
code_racine = st.text_input("🔑 VOTRE CLÉ SECRÈTE PARTAGÉE", type="password").strip().upper()
id_session = generer_identifiant_temporel(code_racine)

if id_session:
    if id_session not in SYSTEME["FLUX"]:
        SYSTEME["FLUX"][id_session] = []

    # --- ZONE DE PUBLICATION MULTIMÉDIA ---
    with st.container():
        st.subheader("➕ Publier dans le tunnel")
        type_post = st.radio("Format :", ["📝 Texte", "📂 Fichier (Vidéo, Audio, Image, PDF)"], horizontal=True)
        
        contenu_final = None
        nom_f, mime_f = "", ""
        is_text = True

        if type_post == "📝 Texte":
            msg = st.text_area("Votre message secret...", placeholder="Écrivez ici...")
            if msg:
                contenu_final, nom_f, mime_f, is_text = msg.encode(), "Texte.txt", "text/plain", True
        else:
            fichier = st.file_uploader("Choisir un média", type=None)
            if fichier:
                contenu_final, nom_f, mime_f, is_text = fichier.getvalue(), fichier.name, fichier.type, False

        if contenu_final and st.button("🚀 DIFFUSER DANS LA TRIADE"):
            cle_fernet = Fernet.generate_key()
            donnees_chiffrees = Fernet(cle_fernet).encrypt(contenu_final)
            
            # Fragmentation
            t = len(donnees_chiffrees)
            p1, p2 = t // 3, (t // 3) * 2
            
            nouveau_post = {
                "fragments": (donnees_chiffrees[:p1], donnees_chiffrees[p1:p2], donnees_chiffrees[p2:]),
                "key": cle_fernet, "name": nom_f, "type": mime_f, "is_text": is_text,
                "time": datetime.datetime.now().strftime("%H:%M"), "is_decoy": False
            }
            SYSTEME["FLUX"][id_session].append(nouveau_post)
            st.success(f"✅ Flux {nom_f} éclaté et diffusé !")

    st.markdown("---")
    
    # --- FIL D'ACTUALITÉ ---
    st.subheader("🌐 Fil du Tunnel")
    posts = SYSTEME["FLUX"][id_session]
    
    if not posts:
        st.info("Le fil est vide. En attente de données...")
    else:
        for i, post in enumerate(reversed(posts)):
            with st.container():
                st.markdown(f'<div class="message-bubble"><span class="time-stamp">{post["time"]}</span>', unsafe_allow_html=True)
                
                try:
                    # Fusion et Déchiffrement
                    complet = post["fragments"][0] + post["fragments"][1] + post["fragments"][2]
                    data = Fernet(post["key"]).decrypt(complet)
                    
                    if post["is_text"]:
                        st.write(data.decode())
                    else:
                        st.write(f"📁 **{post['name']}**")
                        # Affichage intelligent selon le type
                        if "image" in post["type"]: st.image(data)
                        elif "video" in post["type"]: st.video(data)
                        elif "audio" in post["type"]: st.audio(data)
                        
                        st.download_button(f"📥 Récupérer {post['name']}", data, file_name=post["name"], key=f"btn_{i}")
                except Exception as e:
                    st.error("Rupture du flux : clé invalide ou données corrompues.")
                
                st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🧨 TOUT DÉTRUIRE (DISSIPATION)"):
        SYSTEME["FLUX"][id_session] = []
        st.rerun()

else:
    st.info("⚠️ Entrez votre clé pour ouvrir le tunnel. Le système de leures est actif en arrière-plan.")
