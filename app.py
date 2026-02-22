import streamlit as st
from cryptography.fernet import Fernet
import time

# =====================================================
# MÉMOIRE COMMUNE (Le tunnel entre le Gabon et l'International)
# =====================================================
@st.cache_resource
def get_global_vault():
    """Cette fonction crée un coffre-fort unique partagé par tous les utilisateurs"""
    return {}

VAULT = get_global_vault()

# =====================================================
# INTERFACE
# =====================================================
st.set_page_config(page_title="FREE-KONGOSSA", page_icon="✊")
st.title("✊ FREE-KONGOSSA : Tunnel WIDA")

# Utilisation d'un code secret pour relier les deux mondes
code = st.text_input("🔑 Entrez le CODE SECRET (ex: WIDA)", "").strip().upper()

tab1, tab2 = st.tabs(["📤 Émetteur (Gabon)", "📥 Récepteur (Famille)"])

with tab1:
    st.subheader("Envoyer une preuve")
    img = st.file_uploader("Choisissez la photo/document", type=['png', 'jpg', 'jpeg', 'pdf'])
    if img and code:
        if st.button("🚀 Ouvrir le tunnel vers l'International"):
            # Chiffrement
            cle = Fernet.generate_key()
            donnees_chiffrees = Fernet(cle).encrypt(img.getvalue())
            
            # Stockage dans le coffre GLOBAL (visible par la sœur)
            VAULT[code] = {
                "data": donnees_chiffrees,
                "key": cle,
                "nom": img.name,
                "status": "ACTIF"
            }
            st.success(f"✅ Tunnel WIDA établi ! Dites à votre sœur d'entrer le code : {code}")

with tab2:
    st.subheader("Récupérer la vérité")
    if code in VAULT:
        item = VAULT[code]
        st.info(f"📦 Document détecté : {item['nom']}")
        
        if st.button("🔓 Afficher et Détruire"):
            try:
                # Déchiffrement
                image_brute = Fernet(item['key']).decrypt(item['data'])
                st.image(image_brute)
                
                # DISSIPATION IMMÉDIATE (Le lien s'efface pour tout le monde)
                del VAULT[code]
                st.warning("⚠️ Information dissipée du serveur mondial.")
            except Exception as e:
                st.error("Erreur de synchronisation du flux.")
    else:
        if code:
            st.write("⏳ En attente de l'ouverture du tunnel ou code déjà utilisé...")
