import streamlit as st
import base64, uuid, hashlib, time
from cryptography.fernet import Fernet
from datetime import datetime
import plotly.graph_objects as go

# =====================================================
# LOGIQUE TST (M, C, D) APPLIQUÉE À LA RÉSISTANCE
# =====================================================
def calculate_resistance_invariant(session):
    now_ts = datetime.utcnow().timestamp()
    # M (Mémoire) : Temps avant auto-dissipation des traces
    M = (session["expires"] - now_ts) / 300 
    # C (Cohérence) : Intégrité des 3 fragments réunis
    C = 1.0 if session["fragments_received"] == 3 else 0.3
    # D (Dissipation) : Risque de compromission (baisse l'indice si trop d'essais)
    D = session.get("failed_attempts", 0) * 0.2
    
    return max(0.0, (M * C) - D)

def draw_resistance_radar(chi):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = chi,
        title = {'text': "Indice de Liberté (χ)", 'font': {'size': 20}},
        gauge = {
            'axis': {'range': [0, 1]},
            'bar': {'color': "#367588"}, # Bleu profond (Sagesse)
            'steps': [
                {'range': [0, 0.3], 'color': "#820000"}, # Danger / Censure
                {'range': [0.3, 0.7], 'color': "#f4d03f"}, # Vigilance
                {'range': [0.7, 1], 'color': "#2ecc71"}], # Libre / Cohérent
            'threshold': {'line': {'color': "white", 'width': 4}, 'value': 0.1}
        }))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="#1a1a1a", font={'color': "white"})
    return fig

# =====================================================
# CONFIGURATION UI
# =====================================================
st.set_page_config("FREE-KONGOSSA", layout="wide", page_icon="✊")

# Custom CSS pour une ambiance "Résistance"
st.markdown("""
    <style>
    .stApp { background-color: #1a1a1a; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 20px; border: 1px solid #2ecc71; background-color: transparent; color: white; }
    .stButton>button:hover { background-color: #2ecc71; color: black; }
    </style>
    """, unsafe_allow_html=True)

st.title("✊ FREE-KONGOSSA")
st.markdown("*L'information est un droit, la TST est notre bouclier.*")

if 'KONGOSSA_VAULT' not in st.session_state:
    st.session_state.KONGOSSA_VAULT = {}

tabs = st.tabs(["📤 Alerte (Émetteur)", "📥 Vérité (Récepteur)"])

# =====================================================
# 📤 MODULE ÉMETTEUR : FRAGMENTATION TRIADIQUE
# =====================================================
with tabs[0]:
    st.subheader("🛡️ Fragmenter une Information")
    label = st.text_input("Sujet de l'alerte", "Urgent")
    files = st.file_uploader("Preuves (Photos, PDF, Logs)", accept_multiple_files=True)
    
    if files and st.button("🚀 Diffuser les Fragments"):
        token = str(uuid.uuid4())[:6].upper()
        key = Fernet.generate_key()
        f_key = Fernet(key)
        
        # Fragmentation physique du fichier de preuves
        all_data = b""
        for f in files: all_data += f.getvalue()
        
        # Chiffrement TST
        encrypted_data = f_key.encrypt(all_data)
        
        # Division en 3 Fragments (M, C, D)
        l = len(encrypted_data)
        p = l // 3
        
        st.session_state.KONGOSSA_VAULT[token] = {
            "key": key,
            "M": encrypted_data[:p],
            "C": encrypted_data[p:p*2],
            "D": encrypted_data[p*2:],
            "expires": datetime.utcnow().timestamp() + 300, # 5 minutes de vie
            "fragments_received": 0,
            "failed_attempts": 0
        }
        
        st.success(f"FLUX ACTIF. Code de ralliement : {token}")
        st.info("Distribuez les 3 ondes ci-dessous par 3 canaux différents (SMS, WhatsApp, Signal).")
        
        c1, c2, c3 = st.columns(3)
        c1.download_button("📦 Onde MÉMOIRE", st.session_state.KONGOSSA_VAULT[token]["M"], f"M_{token}.tst")
        c2.download_button("📦 Onde COHÉRENCE", st.session_state.KONGOSSA_VAULT[token]["C"], f"C_{token}.tst")
        c3.download_button("📦 Onde DISSIPATION", st.session_state.KONGOSSA_VAULT[token]["D"], f"D_{token}.tst")

# =====================================================
# 📥 MODULE RÉCEPTEUR : RECONSTITUTION SOUVERAINE
# =====================================================
with tabs[1]:
    st.subheader("🔓 Reconstituer la Vérité")
    input_token = st.text_input("Code de ralliement")
    
    col_up, col_status = st.columns([1, 1])
    
    with col_up:
        frag_m = st.file_uploader("Importer Onde M", type="tst")
        frag_c = st.file_uploader("Importer Onde C", type="tst")
        frag_d = st.file_uploader("Importer Onde D", type="tst")
        
    if input_token in st.session_state.KONGOSSA_VAULT:
        sess = st.session_state.KONGOSSA_VAULT[input_token]
        
        # Mise à jour de la cohérence
        received = 0
        if frag_m: received += 1
        if frag_c: received += 1
        if frag_d: received += 1
        st.session_state.KONGOSSA_VAULT[input_token]["fragments_received"] = received
        
        chi = calculate_resistance_invariant(sess)
        
        with col_status:
            st.plotly_chart(draw_resistance_radar(chi), use_container_width=True)
            
        if chi > 0.6 and received == 3:
            st.balloons()
            st.success("SYMÉTRIE RÉTABLIE : Information décodée.")
            
            # Reconstitution physique des données
            full_data = frag_m.getvalue() + frag_c.getvalue() + frag_d.getvalue()
            decrypted = Fernet(sess["key"]).decrypt(full_data)
            
            st.download_button("⬇️ TÉLÉCHARGER LA VÉRITÉ", decrypted, "VERITE_GABON.zip")
        elif received > 0:
            st.warning(f"Fragments collectés : {received}/3. La Triade est incomplète.")
    else:
        if input_token: st.error("Code inconnu ou supprimé par le système de sécurité.")

st.markdown("---")
st.caption("© 2026 - FREE-KONGOSSA : Technologie TST pour la liberté du peuple.")
