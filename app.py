import streamlit as st
import base64
import uuid
import hashlib
import time
from cryptography.fernet import Fernet
from datetime import datetime
import plotly.graph_objects as go
import qrcode
from io import BytesIO

# ===============================
# Fonctions de dérivation de clé
# ===============================
def derive_key_from_token(token: str) -> bytes:
    """Transforme un token (6 caractères) en clé Fernet valide (32 octets base64)."""
    # On utilise SHA256 pour obtenir 32 octets, puis on encode en base64 (Fernet exige ce format)
    key = hashlib.sha256(token.encode()).digest()
    return base64.urlsafe_b64encode(key)

def reconstruct_payload(uploaded_files):
    """Trie les fragments par nom de fichier (inchangé)."""
    sorted_files = sorted(uploaded_files, key=lambda x: x.name)
    combined_data = b"".join([f.getvalue() for f in sorted_files])
    return combined_data

# ===============================
# Interface
# ===============================
st.set_page_config("FREE-KONGOSSA", layout="wide", page_icon="✊")

st.markdown("""
    <style>
    .stApp { background-color: #101214; color: #e0e0e0; }
    .status-box { padding: 15px; border-radius: 10px; border: 1px solid #2ecc71; background-color: #1a1c1e; }
    </style>
    """, unsafe_allow_html=True)

st.title("✊ FREE-KONGOSSA")
st.subheader("Protocole de Transmission en Zone de Censure")

tabs = st.tabs(["📤 DIFFUSION (Émetteur)", "📥 RÉCEPTION (Peuple)"])

# ===============================
# 📤 ÉMETTEUR
# ===============================
with tabs[0]:
    st.info("🛠️ **Prérequis de Diffusion :** Activez votre **Point d'accès Mobile** ou **Bluetooth** si le réseau internet est instable. Cela permet aux personnes proches de capter vos ondes localement.")
    
    files = st.file_uploader("Preuves à fragmenter", accept_multiple_files=True)
    if files and st.button("🚀 Lancer la Brisure de Symétrie"):
        # Génération d'un token de 6 caractères
        token = str(uuid.uuid4())[:6].upper()
        # Clé dérivée du token (plus besoin de stockage)
        key = derive_key_from_token(token)
        
        full_bytes = b"".join([f.getvalue() for f in files])
        encrypted = Fernet(key).encrypt(full_bytes)
        
        # Division
        p = len(encrypted) // 3
        m_part = encrypted[:p]
        c_part = encrypted[p:p*2]
        d_part = encrypted[p*2:]
        
        st.success(f"⚡ CODE DE RALLIEMENT : {token}")
        
        # Génération d'un QR code pour le token
        qr = qrcode.make(token)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        buf.seek(0)
        st.image(buf, caption="Scannez ce QR pour obtenir le code", width=150)
        
        c1, c2, c3 = st.columns(3)
        c1.download_button("📦 Onde MÉMOIRE", m_part, f"1_M_{token}.tst")
        c2.download_button("📦 Onde COHÉRENCE", c_part, f"2_C_{token}.tst")
        c3.download_button("📦 Onde DISSIPATION", d_part, f"3_D_{token}.tst")
        
        st.markdown("---")
        st.markdown("**🔁 Instructions pour l’émetteur :** transmettez ces trois fichiers à votre contact par **Bluetooth**, **Wi‑Fi Direct** ou tout autre moyen. Le code de ralliement doit être communiqué séparément (oral, SMS, papier).")

# ===============================
# 📥 RÉCEPTEUR
# ===============================
with tabs[1]:
    st.markdown("""
    ### 📡 Mode d'emploi Résilience :
    1. **Internet coupé ?** Demandez à l'émetteur de vous envoyer les 3 fichiers via **Bluetooth** ou **Partage de proximité**.
    2. **Localisation :** Assurez-vous que votre **capteur Wi-Fi est actif** (même sans internet) pour stabiliser la réception.
    """)
    
    code = st.text_input("Code de Ralliement (6 caractères)").strip().upper()
    fragments = st.file_uploader("Déposez les 3 fragments (ordre indifférent)", accept_multiple_files=True)
    
    if code and len(fragments) == 3:
        try:
            # Recalcul de la clé à partir du code saisi
            key = derive_key_from_token(code)
            data_fusion = reconstruct_payload(fragments)
            f = Fernet(key)
            final_file = f.decrypt(data_fusion)
            
            st.balloons()
            st.success("🔓 VÉRITÉ RESTAURÉE : La Triade a fusionné avec succès.")
            st.download_button("💾 Ouvrir le Dossier Libéré", final_file, "SOUVERAINETE_GABON.zip")
        except Exception as e:
            st.error(f"🚨 ÉCHEC DE FUSION : {str(e)}")
    elif len(fragments) > 0:
        st.warning(f"Collecte en cours : {len(fragments)}/3 fragments détectés.")