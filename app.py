# ============================================================
# GEN Z GABON FREE-KONGOSSA — V11
# TTU-MC3 × TST ENGINE (STREAMLIT SAFE EDITION)
# ============================================================

import streamlit as st
import uuid
import time
import hashlib
import json
from datetime import datetime

# ============================================================
# CONFIG STREAMLIT SAFE
# ============================================================

st.set_page_config(
    page_title="GEN Z GABON FREE-KONGOSSA",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# TTU-MC3 CORE ENGINE
# ============================================================

class TTUCore:
    """
    Architecture inspirée TTU-MC3 :
    - Flux dynamique
    - Etat minimal
    - Synchronisation douce
    """

    def __init__(self):
        self.alpha = 0.6
        self.beta = 0.3
        self.gamma = 0.1

    def compute_energy(self, n_users, n_msgs):
        return (self.alpha*n_users +
                self.beta*n_msgs +
                self.gamma*(n_users*n_msgs))


ttu = TTUCore()

# ============================================================
# SESSION INIT (ANTI CRASH)
# ============================================================

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]

if "tunnel" not in st.session_state:
    st.session_state.tunnel = None

if "messages" not in st.session_state:
    st.session_state.messages = {}

if "ghost_mode" not in st.session_state:
    st.session_state.ghost_mode = True

# ============================================================
# STYLE TST (MODE FANTÔME PERMANENT)
# ============================================================

st.markdown("""
<style>

html, body, [class*="css"] {
    background-color:#050505;
    color:#EAEAEA;
    font-family:system-ui;
}

.block-container{
    padding-top:1rem;
}

.tst-card{
    background:#0d0d0d;
    padding:14px;
    border-radius:14px;
    margin-bottom:10px;
    border:1px solid #1f1f1f;
}

.tunnel-box{
    background:#111;
    padding:20px;
    border-radius:12px;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER + LOGO
# ============================================================

col1, col2 = st.columns([1,6])

with col1:
    logo = st.file_uploader(
        "Logo",
        type=["png","jpg","jpeg"],
        label_visibility="collapsed"
    )
    if logo:
        st.image(logo, width=90)

with col2:
    st.title("GEN Z GABON FREE-KONGOSSA")
    st.caption("TTU-MC3 × TST — Mode Fantôme Permanent")

# ============================================================
# CREATION TUNNEL UTILISATEUR
# ============================================================

st.markdown("### 🔐 Code Tunnel")

code = st.text_input(
    "Créer ou rejoindre un tunnel",
    placeholder="Ex: LIBREVILLE2030"
)

def hash_tunnel(c):
    return hashlib.sha256(c.encode()).hexdigest()[:16]

if code:
    tunnel_id = hash_tunnel(code)
    st.session_state.tunnel = tunnel_id

if st.session_state.tunnel:

    tunnel = st.session_state.tunnel

    if tunnel not in st.session_state.messages:
        st.session_state.messages[tunnel] = []

    st.success(f"Tunnel actif : {tunnel}")

    # ========================================================
    # MESSAGE INPUT
    # ========================================================

    with st.form("msg_form", clear_on_submit=True):
        msg = st.text_input("Message fantôme")
        send = st.form_submit_button("Envoyer")

        if send and msg.strip():

            st.session_state.messages[tunnel].append({
                "id":str(uuid.uuid4()),
                "user":st.session_state.user_id,
                "msg":msg,
                "time":datetime.now().strftime("%H:%M:%S")
            })

    # ========================================================
    # AFFICHAGE FLUX (TST STREAM)
    # ========================================================

    st.markdown("### Flux Synchronisé")

    container = st.container()

    with container:
        for m in reversed(st.session_state.messages[tunnel][-50:]):

            st.markdown(f"""
            <div class="tst-card">
            <b>{m["user"]}</b><br>
            {m["msg"]}
            <div style="font-size:11px;color:#888">
            {m["time"]}
            </div>
            </div>
            """, unsafe_allow_html=True)

    # ========================================================
    # TTU ENERGY DISPLAY
    # ========================================================

    energy = ttu.compute_energy(
        1,
        len(st.session_state.messages[tunnel])
    )

    st.caption(f"Energie TTU-MC3 : {round(energy,2)}")

# ============================================================
# AUTO REFRESH DOUX (ANTI removeChild BUG)
# ============================================================

time.sleep(1.2)
st.rerun()