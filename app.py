# =====================================================
# GEN Z GABON — FREE KONGOSSA V8
# TTU-MC3 × TST ARCHITECTURE
# =====================================================

import streamlit as st
from cryptography.fernet import Fernet
import hashlib
import time
import datetime
import base64

# =====================================================
# CONFIG APP
# =====================================================

st.set_page_config(
    page_title="GEN Z GABON FREE-KONGOSSA",
    page_icon="🛰️",
    layout="centered"
)

# =====================================================
# LOAD LOGO (REMPLACE DRAPEAU)
# =====================================================

def load_logo(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""

LOGO = load_logo("logo_free_kongossa.png")

# =====================================================
# VAULT TTU (ETAT FANTÔME PERMANENT)
# =====================================================

if "TST_VAULT" not in st.session_state:
    st.session_state.TST_VAULT = {
        "FLUX": {},
        "COMMENTS": {},
        "REACTIONS": {},
        "HISTORY": set(),
        "LAST_UPDATE": time.time()
    }

DB = st.session_state.TST_VAULT

# =====================================================
# TTU ENGINE
# =====================================================

class TTUEngine:

    @staticmethod
    def tunnel_id(key):
        if not key:
            return None
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    @staticmethod
    def encrypt_triadic(data):
        k = Fernet.generate_key()
        box = Fernet(k).encrypt(data)
        l = len(box)

        return k, [
            box[:l//3],
            box[l//3:2*l//3],
            box[2*l//3:]
        ]

    @staticmethod
    def decrypt_triadic(k, frags):
        return Fernet(k).decrypt(b"".join(frags))


ENGINE = TTUEngine()

# =====================================================
# DESIGN TTU (SANS EMOJIS)
# =====================================================

st.markdown("""
<style>

.stApp{
background:#050505;
color:white;
font-family:Outfit;
}

.title{
text-align:center;
font-size:28px;
font-weight:800;
color:#00ffaa;
}

.card{
background:#0f0f0f;
padding:15px;
margin-bottom:20px;
border-radius:14px;
border:1px solid #1c1c1c;
}

.comment{
background:#1a1a1a;
padding:6px;
margin:4px 0;
border-left:3px solid #00ffaa;
border-radius:6px;
font-size:0.85em;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# HEADER
# =====================================================

if LOGO:
    st.markdown(
        f"<center><img src='data:image/png;base64,{LOGO}' width='140'></center>",
        unsafe_allow_html=True
    )

st.markdown(
    "<div class='title'>GEN Z GABON — FREE KONGOSSA</div>",
    unsafe_allow_html=True
)

# =====================================================
# AUTH TUNNEL
# =====================================================

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:

    key = st.text_input("Code Tunnel", type="password")

    if st.button("Entrer"):
        sid = ENGINE.tunnel_id(key)
        if sid:
            st.session_state.sid = sid
            st.session_state.auth = True
            st.rerun()

    st.stop()

sid = st.session_state.sid

# =====================================================
# INIT TUNNEL
# =====================================================

if sid not in DB["FLUX"]:
    DB["FLUX"][sid] = []

# =====================================================
# FIL TEMPS REEL STABLE (ANTI removeChild)
# =====================================================

signals = DB["FLUX"][sid]

for p in reversed(signals):

    with st.container():

        st.markdown("<div class='card'>", unsafe_allow_html=True)

        try:
            raw = ENGINE.decrypt_triadic(p["k"], p["frags"])

            if p["is_txt"]:
                st.write(raw.decode())
            else:
                if "image" in p["type"]:
                    st.image(raw, use_container_width=True)
                elif "video" in p["type"]:
                    st.video(raw)
                elif "audio" in p["type"]:
                    st.audio(raw)

        except:
            st.warning("Signal expiré")

        # ---------- COMMENTAIRES ----------
        comms = DB["COMMENTS"].get(p["id"], [])

        with st.expander(f"Discussions ({len(comms)})"):

            for c in comms:
                st.markdown(
                    f"<div class='comment'>{c}</div>",
                    unsafe_allow_html=True
                )

            txt = st.text_input(
                "Commenter",
                key=f"comm_{p['id']}"
            )

            if st.button("Envoyer", key=f"btn_{p['id']}"):
                DB["COMMENTS"].setdefault(p["id"], []).append(txt)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# NOUVEAU SIGNAL (CONFIG INCHANGÉE)
# =====================================================

with st.expander("Nouveau Signal", expanded=True):

    title = st.text_input("Titre")

    tabs = st.tabs(["Texte", "Media", "Vocal"])

    # -------- TEXTE
    with tabs[0]:
        txt = st.text_area("Message")

        if st.button("Diffuser Texte"):
            data = txt.encode()

            sig = hashlib.md5(data).hexdigest()

            if sig not in DB["HISTORY"]:
                k, frags = ENGINE.encrypt_triadic(data)

                DB["FLUX"][sid].append({
                    "id": str(time.time()),
                    "k": k,
                    "frags": frags,
                    "is_txt": True,
                    "type": "text",
                    "title": title,
                    "ts": time.time()
                })

                DB["HISTORY"].add(sig)
                st.rerun()

    # -------- MEDIA
    with tabs[1]:
        file = st.file_uploader("Image / Video")

        if file and st.button("Diffuser Media"):
            data = file.getvalue()
            k, frags = ENGINE.encrypt_triadic(data)

            DB["FLUX"][sid].append({
                "id": str(time.time()),
                "k": k,
                "frags": frags,
                "is_txt": False,
                "type": file.type,
                "title": title,
                "ts": time.time()
            })

            st.rerun()

    # -------- VOCAL
    with tabs[2]:
        audio = st.audio_input("Enregistrer")

        if audio:
            data = audio.getvalue()
            k, frags = ENGINE.encrypt_triadic(data)

            DB["FLUX"][sid].append({
                "id": str(time.time()),
                "k": k,
                "frags": frags,
                "is_txt": False,
                "type": "audio/wav",
                "title": title,
                "ts": time.time()
            })

            st.rerun()

# =====================================================
# REFRESH TTU STABLE
# =====================================================

if time.time() - DB["LAST_UPDATE"] > 8:
    DB["LAST_UPDATE"] = time.time()
    st.rerun()