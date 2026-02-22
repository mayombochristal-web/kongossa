import streamlit as st
import base64, uuid, hashlib
from cryptography.fernet import Fernet
from datetime import datetime
import plotly.graph_objects as go

# =====================================================
# VERROU DE SYMÉTRIE : Empêche la clé de changer au refresh
# =====================================================
@st.cache_resource
def get_persistent_key(token):
    # Cette fonction garde la même clé pour un token donné
    return Fernet.generate_key()

def reconstruct_payload(uploaded_files):
    # Tri automatique 1, 2, 3 pour éviter l'erreur de déchiffrement
    sorted_files = sorted(uploaded_files, key=lambda x: x.name)
    return b"".join([f.getvalue() for f in sorted_files])

# =====================================================
# INTERFACE
# =====================================================
st.set_page_config("FREE-KONGOSSA", layout="wide")
st.title("✊ FREE-KONGOSSA (Stable Version)")

if 'KONGOSSA_VAULT' not in st.session_state:
    st.session_state.KONGOSSA_VAULT = {}

tab_emit, tab_recv = st.tabs(["📤 DIFFUSION", "📥 RÉCEPTION"])

with tab_emit:
    st.write("Étape 1 : Choisissez vos fichiers")
    files = st.file_uploader("Preuves", accept_multiple_files=True)
    
    # On utilise un ID de session fixe pour cette page
    if 'session_token' not in st.session_state:
        st.session_state.session_token = str(uuid.uuid4())[:6].upper()
    
    token = st.session_state.session_token
    
    if files:
        # LA CLÉ NE CHANGERA PLUS, même après téléchargement
        static_key = get_persistent_key(token)
        f_key = Fernet(static_key)
        
        full_bytes = b"".join([f.getvalue() for f in files])
        encrypted = f_key.encrypt(full_bytes)
        
        p = len(encrypted) // 3
        # Stockage en mémoire
        st.session_state.KONGOSSA_VAULT[token] = {
            "key": static_key,
            "M": encrypted[:p],
            "C": encrypted[p:p*2],
            "D": encrypted[p*2:]
        }
        
        st.success(f"⚡ CLÉ FIXE : {token}")
        st.info("Vous pouvez maintenant télécharger les 3 ondes sans que la clé ne change.")
        
        c1, c2, c3 = st.columns(3)
        c1.download_button("📦 Onde M", st.session_state.KONGOSSA_VAULT[token]["M"], f"1_M_{token}.tst")
        c2.download_button("📦 Onde C", st.session_state.KONGOSSA_VAULT[token]["C"], f"2_C_{token}.tst")
        c3.download_button("📦 Onde D", st.session_state.KONGOSSA_VAULT[token]["D"], f"3_D_{token}.tst")

with tab_recv:
    st.subheader("Fusionner les Ondes")
    code_input = st.text_input("Code Secret")
    uploaded_frags = st.file_uploader("Déposez les 3 fichiers ici", accept_multiple_files=True)
    
    if code_input in st.session_state.KONGOSSA_VAULT:
        sess = st.session_state.KONGOSSA_VAULT[code_input]
        if len(uploaded_frags) == 3:
            try:
                # Réassemblage et déchiffrement avec la clé persistante
                raw_data = reconstruct_payload(uploaded_frags)
                decrypted = Fernet(sess["key"]).decrypt(raw_data)
                st.success("🔓 SYMÉTRIE RÉTABLIE !")
                st.download_button("⬇️ Ouvrir le fichier final", decrypted, "VÉRITÉ_GABON.zip")
            except Exception as e:
                st.error(f"Erreur de cohérence : {e}")
