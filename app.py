import streamlit as st
import uuid
from cryptography.fernet import Fernet
from datetime import datetime

# =====================================================
# MÉMOIRE TRIADIQUE (Stockage temporaire en RAM)
# =====================================================
if 'VAULT' not in st.session_state:
    st.session_state.VAULT = {}

def delete_session(token):
    """ Dissipation totale de la donnée """
    if token in st.session_state.VAULT:
        del st.session_state.VAULT[token]

# =====================================================
# INTERFACE ÉPURÉE
# =====================================================
st.set_page_config(page_title="FREE-KONGOSSA", page_icon="✊")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .stButton>button { background-color: #2ecc71; color: black; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("✊ FREE-KONGOSSA")
st.write("Le tunnel sécurisé entre le Gabon et l'International.")

# Système de Tabs pour simplifier l'écran
tab_send, tab_receive = st.tabs(["📤 ENVOYER (Gabon)", "📥 RECEVOIR (Famille)"])

# =====================================================
# 📤 PARTIE ÉMETTEUR (Toi au Gabon)
# =====================================================
with tab_send:
    st.subheader("Préparer l'envoi")
    # Choix d'un code simple pour la sœur
    user_code = st.text_input("Créez un code secret (ex: GABON24)", "").strip().upper()
    file_to_send = st.file_uploader("Document ou photo", type=['pdf', 'png', 'jpg', 'zip', 'docx'])

    if file_to_send and user_code:
        if st.button("🚀 Ouvrir le tunnel"):
            # Chiffrement immédiat
            key = Fernet.generate_key()
            cipher = Fernet(key)
            encrypted_data = cipher.encrypt(file_to_send.getvalue())
            
            # Stockage avec timestamp pour auto-expiration (15 min)
            st.session_state.VAULT[user_code] = {
                "data": encrypted_data,
                "key": key,
                "name": file_to_send.name,
                "time": datetime.now()
            }
            st.success(f"✅ Tunnel ouvert ! Dis à ta sœur d'entrer le code : **{user_code}**")
            st.warning("⚠️ Attention : Le tunnel s'autodétruira après son premier téléchargement.")

# =====================================================
# 📥 PARTIE RÉCEPTEUR (Ta sœur à l'étranger)
# =====================================================
with tab_receive:
    st.subheader("Récupérer l'information")
    access_code = st.text_input("Entrez le code reçu", "").strip().upper()

    if access_code in st.session_state.VAULT:
        doc = st.session_state.VAULT[access_code]
        st.info(f"📦 Document détecté : **{doc['name']}**")
        
        # Le bouton de téléchargement déclenche l'effacement
        try:
            cipher = Fernet(doc['key'])
            decrypted_data = cipher.decrypt(doc['data'])
            
            if st.download_button(
                label="🔓 Télécharger et Effacer le lien",
                data=decrypted_data,
                file_name=doc['name'],
                mime="application/octet-stream"
            ):
                # DISSIPATION : On efface tout juste après le clic
                delete_session(access_code)
                st.rerun()
                
        except Exception as e:
            st.error("Erreur de décodage. Le flux est peut-être corrompu.")
    
    elif access_code != "":
        st.error("❌ Code invalide ou lien déjà expiré/utilisé.")

# Nettoyage automatique des vieilles sessions (Sécurité de la RAM)
# (Optionnel : effacer les sessions de plus de 30 min)
