import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import random

# =====================================================
# ARCHITECTURE AVEC SYSTÈME DE LEURES
# =====================================================
@st.cache_resource
def initialiser_systeme_triadique():
    return {"FLUX": {}}

SYSTEME = initialiser_systeme_triadique()

def generer_identifiant_temporel(code_base):
    if not code_base: return None
    grain_de_sel = datetime.datetime.now().strftime("%Y-%m-%d-%H")
    return hashlib.sha256(f"{code_base}-{grain_de_sel}".encode()).hexdigest()[:12].upper()

# --- GÉNÉRATEUR DE PERSONNAGES FICTIFS (Leures) ---
def generer_leures_horaires():
    """Crée des discussions fantômes pour noyer les vrais flux."""
    prenoms = ["Moussa", "Fatou", "Yannick", "Leila", "Marc", "Aminata", "Christian", "Béatrice"]
    sujets = ["Le prix du manioc", "Le match de demain", "Recette de cuisine", "Rapport de stage", "Photos de vacances"]
    
    # On génère 5 faux IDs de session par heure
    for i in range(5):
        faux_secret = f"FAKE_KEY_{i}_{datetime.datetime.now().hour}"
        faux_id = generer_identifiant_temporel(faux_secret)
        
        if faux_id not in SYSTEME["FLUX"] or not SYSTEME["FLUX"][faux_id]:
            SYSTEME["FLUX"][faux_id] = [{
                "fragments": (b"x", b"y", b"z"),
                "key": Fernet.generate_key(),
                "name": f"{random.choice(sujets)}.pdf",
                "type": "application/pdf",
                "time": f"{random.randint(0,23)}:{random.randint(10,59)}",
                "is_text": False,
                "is_decoy": True # Marqueur interne
            }]

# On lance la génération de leures à chaque rafraîchissement
generer_leures_horaires()

# =====================================================
# INTERFACE SOUVERAINE
# =====================================================
st.set_page_config(page_title="FREE-KONGOSSA", page_icon="✊")

# CSS pour différencier les bulles
st.markdown("""
    <style>
    .message-bubble { padding: 15px; border-radius: 15px; background-color: #1E1E26; margin-bottom: 10px; border-left: 5px solid #00FFAA; }
    .decoy-bubble { border-left: 5px solid #555; opacity: 0.7; }
    </style>
""", unsafe_allow_html=True)

st.title("✊ FREE-KONGOSSA : Leure Intégré")

code_racine = st.text_input("🔑 CLÉ DE LIAISON", type="password").strip().upper()
id_session = generer_identifiant_temporel(code_racine)

if id_session:
    if id_session not in SYSTEME["FLUX"]:
        SYSTEME["FLUX"][id_session] = []

    # Zone d'envoi (simplifiée pour l'exemple)
    msg = st.text_input("Envoyer un message sécurisé")
    if msg and st.button("🚀 Diffuser"):
        cle = Fernet.generate_key()
        chiffre = Fernet(cle).encrypt(msg.encode())
        t = len(chiffre)
        SYSTEME["FLUX"][id_session].append({
            "fragments": (chiffre[:t//3], chiffre[t//3:2*t//3], chiffre[2*t//3:]),
            "key": cle, "time": datetime.datetime.now().strftime("%H:%M"), "is_text": True, "is_decoy": False
        })
        st.success("Posté dans le tunnel !")

    st.markdown("---")
    
    # Affichage du flux
    posts = SYSTEME["FLUX"][id_session]
    for post in reversed(posts):
        st.markdown(f'<div class="message-bubble"><b>ID de session actif : {id_session}</b><br>', unsafe_allow_html=True)
        if post.get("is_text"):
            try:
                data = Fernet(post["key"]).decrypt(post["fragments"][0]+post["fragments"][1]+post["fragments"][2])
                st.write(data.decode())
            except: st.error("Déchiffrement impossible")
        st.markdown(f'</div>', unsafe_allow_html=True)
else:
    st.info("Entrez votre clé. Pendant ce temps, le système génère des leures pour vous couvrir...")
