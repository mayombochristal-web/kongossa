import streamlit as st
import base64, uuid, time, hashlib
from cryptography.fernet import Fernet
from datetime import datetime
import plotly.graph_objects as go
import requests

# ===============================
# UTILS & GÉO-LOCALISATION
# ===============================
def get_client_ip_data():
    """ Simule ou récupère la cohérence géographique via IP """
    try:
        # Utilisation d'une API publique pour la démo
        res = requests.get('https://ipapi.co/json/').json()
        return f"{res.get('city')}, {res.get('country_name')}", res.get('ip')
    except:
        return "Localisation Inconnue", "0.0.0.0"

# ===============================
# RADAR DE DISSIPATION VISUEL
# ===============================
def draw_dissipation_radar(chi):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = chi,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Invariant de Stabilité (χ)", 'font': {'size': 24}},
        gauge = {
            'axis': {'range': [0, 1], 'tickwidth': 1},
            'bar': {'color': "#00FF00" if chi > 0.4 else "#FF4B4B"},
            'bgcolor': "white",
            'borderwidth': 2,
            'steps': [
                {'range': [0, 0.25], 'color': '#ffcccc'},
                {'range': [0.25, 0.5], 'color': '#fff3cd'}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 0.1}
        }))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=50, b=10))
    return fig

# ===============================
# MOTEUR TST AMÉLIORÉ
# ===============================
def calculate_tst_stability(session, current_loc):
    now_ts = datetime.utcnow().timestamp()
    M = (session["expires"] - now_ts) / 120 
    
    # C (Cohérence Géographique) : Si le tunnel est cassé par un tiers
    # On compare la localisation attendue vs actuelle
    C = 1.0 if current_loc == session["origin_loc"] or "International" in session["target"] else 0.8
    
    D = session.get("downloads", 0) * 0.5
    return max(0.0, M * C - D)

# ===============================
# UI STREAMLIT
# ===============================
st.set_page_config("TTU-Sync Global", layout="wide", page_icon="🔗")
st.title("🔗 TTU-Sync : Tunnel Triadique Global")

if 'SESSIONS' not in st.session_state:
    st.session_state.SESSIONS = {}

tabs = st.tabs(["📤 Émetteur (Gabon)", "📥 Récepteur (Sœur/International)"])

loc_label, ip_addr = get_client_ip_data()

with tabs[0]:
    st.subheader("🚀 Initialiser un flux à partir de : " + loc_label)
    uploaded_files = st.file_uploader("Fichiers sensibles", accept_multiple_files=True)
    
    if uploaded_files and st.button("Lancer la Synchronisation"):
        token = str(uuid.uuid4())[:6].upper()
        key = Fernet.generate_key()
        
        payload = []
        for f in uploaded_files:
            encrypted = Fernet(key).encrypt(f.getvalue())
            payload.append({"name": f.name, "data": base64.b64encode(encrypted).decode()})
            
        st.session_state.SESSIONS[token] = {
            "key": key,
            "files": payload,
            "expires": datetime.utcnow().timestamp() + 120,
            "origin_loc": loc_label,
            "target": "International",
            "downloads": 0
        }
        st.success(f"CODE SECRET : {token}")
        st.info("Partagez ce code. Le flux se dissipe dans 120s.")

with tabs[1]:
    st.subheader("📥 Réception & Déchiffrement")
    input_token = st.text_input("Code Secret", placeholder="Ex: A1B2C3")
    
    if input_token in st.session_state.SESSIONS:
        sess = st.session_state.SESSIONS[input_token]
        chi = calculate_tst_stability(sess, loc_label)
        
        col_radar, col_actions = st.columns([1, 1])
        
        with col_radar:
            st.plotly_chart(draw_dissipation_radar(chi), use_container_width=True)
            
        with col_actions:
            if chi > 0.1:
                st.write(f"📍 **Point de sortie :** {loc_label}")
                st.write(f"🛡️ **Niveau de Cohérence :** {'Optimal' if chi > 0.5 else 'Faible'}")
                
                f_key = sess["key"]
                for f in sess["files"]:
                    decrypted = Fernet(f_key).decrypt(base64.b64decode(f["data"]))
                    if st.download_button(f"⬇️ Récupérer {f['name']}", data=decrypted, file_name=f["name"]):
                        st.session_state.SESSIONS[input_token]["downloads"] += 1
                        st.rerun()
            else:
                st.error("🚨 DISSIPATION TOTALE : Le lien a disparu par mesure de sécurité.")
