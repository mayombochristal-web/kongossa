import streamlit as st
import base64, uuid, time, json, hashlib
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import qrcode
from io import BytesIO

# =====================================================
# MOTEUR TST : CALCUL DE L'INVARIANT DE CONNEXION
# =====================================================
def calculate_tst_stability(session):
    now_ts = datetime.utcnow().timestamp()
    # M (Mémoire) : Temps de vie restant du lien
    M = (session["expires"] - now_ts) / 120 
    # C (Cohérence) : Intégrité du tunnel (Simulée par le token)
    C = 1.0 if session["status"] == "Active" else 0.0
    # D (Dissipation) : Usure du lien (plus on télécharge, plus il s'efface)
    D = session.get("downloads", 0) * 0.4
    
    return max(0.0, M * C - D)

# =====================================================
# INTERFACE SÉCURISÉE
# =====================================================
st.set_page_config("TTU-Sync 2030", layout="wide")
st.title("🔗 TTU-Sync : Partage Triadique Global")

if 'SESSIONS' not in st.session_state:
    st.session_state.SESSIONS = {}

tabs = st.tabs(["📤 Émetteur (Gabon)", "📥 Récepteur (International)"])

with tabs[0]:
    st.subheader("Générer un Flux Sécurisé")
    uploaded_files = st.file_uploader("Fichiers à envoyer", accept_multiple_files=True)
    
    if uploaded_files and st.button("🚀 Lancer le Flux TST"):
        token = str(uuid.uuid4())[:8] # Token court pour faciliter le partage
        key = Fernet.generate_key()
        
        # Chiffrement et préparation
        payload = []
        for f in uploaded_files:
            encrypted = Fernet(key).encrypt(f.getvalue())
            payload.append({"name": f.name, "data": base64.b64encode(encrypted).decode()})
            
        st.session_state.SESSIONS[token] = {
            "key": key,
            "files": payload,
            "expires": datetime.utcnow().timestamp() + 120,
            "status": "Active",
            "downloads": 0
        }
        
        link = f"https://ttu-sync-2030.streamlit.app/?token={token}"
        st.success(f"✅ Flux établi ! Envoie ce code à ta sœur : **{token}**")
        st.info("Le lien se dissipera automatiquement après 120s ou après téléchargement.")

with tabs[1]:
    st.subheader("Récupérer le Flux")
    query_token = st.text_input("Entrez le code de session", value=st.query_params.get("token", ""))
    
    if query_token in st.session_state.SESSIONS:
        sess = st.session_state.SESSIONS[query_token]
        chi = calculate_tst_stability(sess)
        
        if chi > 0:
            st.write(f"🌐 **Stabilité du tunnel Gabon-International :** {chi:.2f}")
            st.progress(chi)
            
            f_key = sess["key"]
            for f in sess["files"]:
                decrypted_data = Fernet(f_key).decrypt(base64.b64decode(f["data"]))
                if st.download_button(f"⬇️ Télécharger {f['name']}", data=decrypted_data, file_name=f["name"]):
                    st.session_state.SESSIONS[query_token]["downloads"] += 1
                    st.rerun()
        else:
            st.error("🚨 Rupture de Symétrie : Le lien s'est dissipé (Temps expiré ou déjà utilisé).")
