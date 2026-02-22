import streamlit as st
import base64, uuid, time, hashlib
from cryptography.fernet import Fernet
from datetime import datetime
import plotly.graph_objects as go

# ===============================
# RADAR DE DISSIPATION TST
# ===============================
def draw_dissipation_radar(chi):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = chi,
        gauge = {
            'axis': {'range': [0, 1]},
            'bar': {'color': "#00FF00" if chi > 0.4 else "#FF4B4B"},
            'steps': [
                {'range': [0, 0.3], 'color': "gray"},
                {'range': [0.3, 0.7], 'color': "lightgray"}],
            'threshold': {'line': {'color': "red", 'width': 4}, 'value': 0.1}
        }))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="#0e1117", font={'color': "white"})
    return fig

# ===============================
# CONFIGURATION & MÉMOIRE
# ===============================
st.set_page_config("TTU-Sync Global", layout="wide")
st.title("🛡️ TTU-Sync : Tunnel Triadique")

if 'SESSIONS' not in st.session_state:
    st.session_state.SESSIONS = {}

tabs = st.tabs(["📤 Émetteur", "📥 Récepteur"])

# ===============================
# 📤 ÉMETTEUR
# ===============================
with tabs[0]:
    st.subheader("Paramétrage du Flux")
    col_a, col_b = st.columns(2)
    with col_a:
        ma_position = st.text_input("📍 Ma position (ex: Libreville)", "Gabon")
    with col_b:
        position_cible = st.text_input("🎯 Destination (ex: Paris)", "International")
    
    files = st.file_uploader("Fichiers à sécuriser", accept_multiple_files=True)
    
    if files and st.button("🚀 Générer le Code TST"):
        token = str(uuid.uuid4())[:6].upper()
        key = Fernet.generate_key()
        
        payload = []
        for f in files:
            enc = Fernet(key).encrypt(f.getvalue())
            payload.append({"name": f.name, "data": base64.b64encode(enc).decode()})
            
        st.session_state.SESSIONS[token] = {
            "key": key,
            "files": payload,
            "expires": datetime.utcnow().timestamp() + 180, # 3 minutes
            "origin": ma_position,
            "target": position_cible,
            "downloads": 0
        }
        st.success(f"PARTAGEZ CE CODE : **{token}**")
        st.warning(f"Le tunnel entre {ma_position} et {position_cible} est ouvert pour 180s.")

# ===============================
# 📥 RÉCEPTEUR
# ===============================
with tabs[1]:
    st.subheader("Récupération du Flux")
    code_entree = st.text_input("Entrez le code secret")
    ta_position = st.text_input("📍 Confirmez votre position actuelle", "International")
    
    if code_entree in st.session_state.SESSIONS:
        sess = st.session_state.SESSIONS[code_entree]
        
        # CALCUL TST EN DIRECT
        now_ts = datetime.utcnow().timestamp()
        M = (sess["expires"] - now_ts) / 180  # Mémoire (Temps)
        C = 1.0 if ta_position.lower() in sess["target"].lower() else 0.5 # Cohérence Géo
        D = sess["downloads"] * 0.6 # Dissipation (Usage)
        chi = max(0.0, (M * C) - D)
        
        st.plotly_chart(draw_dissipation_radar(chi), use_container_width=True)
        
        if chi > 0.1:
            st.info(f"Flux détecté en provenance de : {sess['origin']}")
            f_key = sess["key"]
            for f in sess["files"]:
                dec = Fernet(f_key).decrypt(base64.b64decode(f["data"]))
                if st.download_button(f"⬇️ Récupérer {f['name']}", data=dec, file_name=f["name"]):
                    st.session_state.SESSIONS[code_entree]["downloads"] += 1
                    st.rerun()
        else:
            st.error("🚨 Rupture de Symétrie : Le lien est expiré ou corrompu.")
