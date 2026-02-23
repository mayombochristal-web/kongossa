# ==========================================================
# GEN Z GABON FREE-KONGOSSA — V12 STABLE EDITION
# TTU-MC3 × TST × STREAMLIT CLOUD SAFE
# ==========================================================

import streamlit as st
import uuid
import hashlib
import time
from datetime import datetime

# ==========================================================
# CONFIGURATION SAFE
# ==========================================================

st.set_page_config(
    page_title="GEN Z GABON FREE-KONGOSSA",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================================
# SESSION INIT (ANTI-CRASH)
# ==========================================================

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]

if "tunnel_id" not in st.session_state:
    st.session_state.tunnel_id = None

if "storage" not in st.session_state:
    st.session_state.storage = {}

if "seen_hash" not in st.session_state:
    st.session_state.seen_hash = set()

# ==========================================================
# STYLE TST MODE FANTÔME
# ==========================================================

st.markdown("""
<style>
html, body, [class*="css"] {
    background-color:#050505;
    color:#EAEAEA;
    font-family:system-ui;
}

.block-container {
    padding-top: 1rem;
}

.tst-card {
    background:#0f0f0f;
    padding:16px;
    border-radius:14px;
    margin-bottom:12px;
    border:1px solid #1f1f1f;
}

.meta {
    font-size:11px;
    color:#888;
}

.tunnel-box {
    background:#111;
    padding:20px;
    border-radius:12px;
}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# TTU CORE ENERGY
# ==========================================================

class TTUEngine:
    def compute(self, users, messages):
        return round((0.6*users + 0.3*messages + 0.1*(users*messages)),2)

ttu = TTUEngine()

# ==========================================================
# HEADER
# ==========================================================

col1, col2 = st.columns([1,6])

with col1:
    logo = st.file_uploader("Logo", type=["png","jpg","jpeg"], label_visibility="collapsed")
    if logo:
        st.image(logo, width=90)

with col2:
    st.title("GEN Z GABON FREE-KONGOSSA")
    st.caption("TTU-MC3 × TST — Mode Fantôme Permanent")

# ==========================================================
# CREATION / REJOINDRE TUNNEL
# ==========================================================

def hash_tunnel(code):
    return hashlib.sha256(code.encode()).hexdigest()[:16]

st.markdown("### Tunnel Sécurisé")

code = st.text_input("Entrer ou créer un code tunnel")

if code:
    st.session_state.tunnel_id = hash_tunnel(code)

if st.session_state.tunnel_id:

    tunnel = st.session_state.tunnel_id

    if tunnel not in st.session_state.storage:
        st.session_state.storage[tunnel] = []

    st.success(f"Tunnel actif : {tunnel}")

    # ======================================================
    # ONGLET STRUCTURE
    # ======================================================

    tab_text, tab_media = st.tabs(["Message Texte", "Importer Fichier"])

    # ---------------------------
    # 1️⃣ MESSAGE TEXTE
    # ---------------------------

    with tab_text:

        with st.form("text_form", clear_on_submit=True):
            text_msg = st.text_area("Votre message")
            send_text = st.form_submit_button("Envoyer")

            if send_text and text_msg.strip():

                msg_id = hashlib.sha256(text_msg.encode()).hexdigest()

                if msg_id not in st.session_state.seen_hash:
                    st.session_state.seen_hash.add(msg_id)

                    st.session_state.storage[tunnel].append({
                        "type":"text",
                        "user":st.session_state.user_id,
                        "content":text_msg,
                        "time":datetime.now().strftime("%H:%M:%S")
                    })

                    st.rerun()

    # ---------------------------
    # 2️⃣ IMPORT MEDIA
    # ---------------------------

    with tab_media:

        uploaded = st.file_uploader(
            "Importer image, vidéo, audio ou document",
            type=None
        )

        if uploaded:

            st.info("Fichier prêt à être envoyé")

            if st.button("Envoyer Fichier"):

                file_hash = hashlib.sha256(uploaded.getvalue()).hexdigest()

                if file_hash not in st.session_state.seen_hash:
                    st.session_state.seen_hash.add(file_hash)

                    st.session_state.storage[tunnel].append({
                        "type":"file",
                        "user":st.session_state.user_id,
                        "filename":uploaded.name,
                        "filetype":uploaded.type,
                        "data":uploaded.getvalue(),
                        "time":datetime.now().strftime("%H:%M:%S")
                    })

                    st.rerun()

    # ======================================================
    # AFFICHAGE FLUX
    # ======================================================

    st.markdown("### Flux du Tunnel")

    container = st.container()

    with container:

        for item in reversed(st.session_state.storage[tunnel][-50:]):

            st.markdown('<div class="tst-card">', unsafe_allow_html=True)

            st.write(f"Utilisateur : {item['user']}")

            if item["type"] == "text":
                st.write(item["content"])

            if item["type"] == "file":

                if "image" in item["filetype"]:
                    st.image(item["data"], use_container_width=True)

                elif "video" in item["filetype"]:
                    st.video(item["data"])

                elif "audio" in item["filetype"]:
                    st.audio(item["data"])

                else:
                    st.download_button(
                        "Télécharger",
                        item["data"],
                        file_name=item["filename"]
                    )

            st.markdown(f'<div class="meta">{item["time"]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ======================================================
    # ENERGIE TTU
    # ======================================================

    energy = ttu.compute(
        1,
        len(st.session_state.storage[tunnel])
    )

    st.caption(f"Energie Système TTU-MC3 : {energy}")

# ==========================================================
# REFRESH DOUX STABLE
# ==========================================================

time.sleep(1.2)
st.rerun()