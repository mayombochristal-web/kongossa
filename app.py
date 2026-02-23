# ============================================================
# GEN Z GABON FREE-KONGOSSA — V12 FINAL
# TTU-MC3 × TST SOCIAL ENGINE
# STREAMLIT CLOUD SAFE
# ============================================================

import streamlit as st
import uuid
import hashlib
import time
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="GEN Z GABON FREE-KONGOSSA",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# TTU-MC3 CORE
# ============================================================

class TTUCore:

    def energy(self, users, messages):
        return round(0.6*users + 0.3*messages + 0.1*(users*messages), 2)

ttu = TTUCore()

# ============================================================
# SESSION INIT
# ============================================================

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]

if "tunnel" not in st.session_state:
    st.session_state.tunnel = None

if "messages" not in st.session_state:
    st.session_state.messages = {}

if "pending_file" not in st.session_state:
    st.session_state.pending_file = None

# ============================================================
# STYLE TST (MODE FANTÔME)
# ============================================================

st.markdown("""
<style>

html, body, [class*="css"] {
    background:#050505;
    color:white;
    font-family:system-ui;
}

.tst-card{
    background:#0f0f0f;
    padding:14px;
    border-radius:14px;
    margin-bottom:10px;
    border:1px solid #1f1f1f;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================

col1, col2 = st.columns([1,6])

with col1:
    logo = st.file_uploader(
        "logo",
        type=["png","jpg","jpeg"],
        label_visibility="collapsed"
    )
    if logo:
        st.image(logo, width=90)

with col2:
    st.title("GEN Z GABON FREE-KONGOSSA")
    st.caption("TTU-MC3 × TST — Mode Fantôme Permanent")

# ============================================================
# TUNNEL
# ============================================================

def hash_tunnel(code):
    return hashlib.sha256(code.encode()).hexdigest()[:16]

code = st.text_input(
    "Code tunnel",
    placeholder="LIBREVILLE2030"
)

if code:
    st.session_state.tunnel = hash_tunnel(code)

# ============================================================
# MAIN SYSTEM
# ============================================================

if st.session_state.tunnel:

    tunnel = st.session_state.tunnel

    if tunnel not in st.session_state.messages:
        st.session_state.messages[tunnel] = []

    st.success(f"Tunnel actif : {tunnel}")

    # ========================================================
    # ONGLET FIXES (POSITION STABLE)
    # ========================================================

    tab_text, tab_file = st.tabs(["💬 Messages", "📎 Fichiers"])

    # ========================================================
    # TAB 1 — MESSAGE TEXTE
    # ========================================================

    with tab_text:

        with st.form("text_form", clear_on_submit=True):
            msg = st.text_input("Message fantôme")
            send_text = st.form_submit_button("Envoyer")

            if send_text and msg.strip():

                st.session_state.messages[tunnel].append({
                    "type":"text",
                    "user":st.session_state.user_id,
                    "content":msg,
                    "time":datetime.now().strftime("%H:%M:%S")
                })

    # ========================================================
    # TAB 2 — FICHIERS
    # ========================================================

    with tab_file:

        uploaded = st.file_uploader(
            "Importer photo, vidéo ou fichier",
            type=None
        )

        # Upload terminé → stocker
        if uploaded:
            st.session_state.pending_file = uploaded
            st.success("Fichier prêt à envoyer ✅")

        # Bouton apparaît seulement après upload
        if st.session_state.pending_file:

            if st.button("Envoyer le fichier"):

                file = st.session_state.pending_file

                st.session_state.messages[tunnel].append({
                    "type":"file",
                    "user":st.session_state.user_id,
                    "content":file,
                    "filename":file.name,
                    "time":datetime.now().strftime("%H:%M:%S")
                })

                st.session_state.pending_file = None
                st.rerun()

    # ========================================================
    # FLUX GLOBAL
    # ========================================================

    st.markdown("### Flux TST Synchronisé")

    for m in reversed(st.session_state.messages[tunnel][-40:]):

        if m["type"] == "text":

            st.markdown(f"""
            <div class="tst-card">
            <b>{m["user"]}</b><br>
            {m["content"]}
            <div style="font-size:11px;color:#888">
            {m["time"]}
            </div>
            </div>
            """, unsafe_allow_html=True)

        elif m["type"] == "file":

            st.markdown(f"""
            <div class="tst-card">
            <b>{m["user"]}</b><br>
            📎 {m["filename"]}
            <div style="font-size:11px;color:#888">
            {m["time"]}
            </div>
            </div>
            """, unsafe_allow_html=True)

            file = m["content"]

            if file.type.startswith("image"):
                st.image(file)

            elif file.type.startswith("video"):
                st.video(file)

            else:
                st.download_button(
                    "Télécharger",
                    file,
                    file_name=file.name
                )

    # ========================================================
    # TTU ENERGY
    # ========================================================

    energy = ttu.energy(
        1,
        len(st.session_state.messages[tunnel])
    )

    st.caption(f"Energie système TTU-MC3 : {energy}")

# ============================================================
# REFRESH DOUX (ANTI BUG STREAMLIT)
# ============================================================

time.sleep(1.2)
st.rerun()