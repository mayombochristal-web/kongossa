# =====================================================
# GEN Z GABON — FREE KONGOSSA V9
# TST MAXIMUM COMPUTE MODE
# TTU-MC3 ARCHITECTURE
# =====================================================

import streamlit as st
from cryptography.fernet import Fernet
import hashlib, time, uuid, base64

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="GEN Z GABON FREE-KONGOSSA",
    layout="centered"
)

# =====================================================
# TTU FIELD (GLOBAL COMPUTE LAYER)
# =====================================================

@st.cache_resource
def TTU_FIELD():
    return {
        "EVENT_BUS": [],
        "INDEX": {},
        "CLOCK": time.time()
    }

FIELD = TTU_FIELD()

# =====================================================
# TST GHOST CORE
# =====================================================

if "GHOST" not in st.session_state:
    st.session_state.GHOST = {
        "FEED": {},
        "COMMENTS": {},
        "KNOWN": set(),
        "LOCAL_CACHE": []
    }

GHOST = st.session_state.GHOST

# =====================================================
# TTU ENGINE
# =====================================================

class TTU:

    @staticmethod
    def tunnel(code):
        return hashlib.sha256(code.encode()).hexdigest()[:12]

    @staticmethod
    def encrypt(data):
        k = Fernet.generate_key()
        enc = Fernet(k).encrypt(data)
        L=len(enc)
        return k,[enc[:L//3],enc[L//3:2*L//3],enc[2*L//3:]]

    @staticmethod
    def decrypt(k,f):
        return Fernet(k).decrypt(b"".join(f))

ENGINE = TTU()

# =====================================================
# HEADER + LOGO
# =====================================================

def load_logo():
    try:
        with open("logo_free_kongossa.png","rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""

logo=load_logo()

if logo:
    st.markdown(
        f"<center><img src='data:image/png;base64,{logo}' width=150></center>",
        unsafe_allow_html=True
    )

st.markdown(
"<h3 style='text-align:center;color:#00ffaa'>GEN Z GABON — FREE KONGOSSA</h3>",
unsafe_allow_html=True
)

# =====================================================
# AUTH
# =====================================================

if "auth" not in st.session_state:
    st.session_state.auth=False

if not st.session_state.auth:

    code=st.text_input("Code Tunnel",type="password")

    if st.button("Connexion"):
        if code:
            st.session_state.sid=ENGINE.tunnel(code)
            st.session_state.auth=True
            st.rerun()

    st.stop()

sid=st.session_state.sid

# =====================================================
# EVENT EMITTER
# =====================================================

def emit(data,name,typ,is_txt):

    k,f=ENGINE.encrypt(data)

    evt={
        "id":str(uuid.uuid4()),
        "sid":sid,
        "k":k,
        "frags":f,
        "name":name,
        "type":typ,
        "is_txt":is_txt,
        "ts":time.time()
    }

    FIELD["EVENT_BUS"].append(evt)

# =====================================================
# SYNC ENGINE (TST MAX)
# =====================================================

def sync():

    for e in FIELD["EVENT_BUS"]:
        if e["id"] in GHOST["KNOWN"]:
            continue

        GHOST["KNOWN"].add(e["id"])
        GHOST["LOCAL_CACHE"].append(e)

sync()

# =====================================================
# FEED (DIFFERENTIAL PROJECTION)
# =====================================================

for msg in reversed(GHOST["LOCAL_CACHE"]):

    with st.container():

        try:
            raw=ENGINE.decrypt(msg["k"],msg["frags"])

            if msg["is_txt"]:
                st.write(raw.decode())
            else:
                if "image" in msg["type"]:
                    st.image(raw,use_container_width=True)
                elif "video" in msg["type"]:
                    st.video(raw)
                elif "audio" in msg["type"]:
                    st.audio(raw)

        except:
            st.warning("Signal fantôme invalide")

        # COMMENTS
        coms=GHOST["COMMENTS"].get(msg["id"],[])

        with st.expander(f"Discussions ({len(coms)})"):

            for c in coms:
                st.write("•",c)

            new=st.text_input(
                "Répondre",
                key=f"c{msg['id']}"
            )

            if st.button("Envoyer",key=f"s{msg['id']}"):
                GHOST["COMMENTS"].setdefault(msg["id"],[]).append(new)
                st.rerun()

# =====================================================
# COMPOSER
# =====================================================

st.markdown("---")

tabs=st.tabs(["Texte","Media","Vocal"])

with tabs[0]:
    txt=st.text_area("Message")
    if st.button("Diffuser Texte"):
        emit(txt.encode(),"txt","text",True)
        st.rerun()

with tabs[1]:
    file=st.file_uploader("Image / Video")
    if file and st.button("Envoyer Media"):
        emit(file.getvalue(),file.name,file.type,False)
        st.rerun()

with tabs[2]:
    audio=st.audio_input("Vocal")
    if audio:
        emit(audio.getvalue(),"voice.wav","audio/wav",False)
        st.rerun()

# =====================================================
# TST CLOCK (MAX PERFORMANCE)
# =====================================================

if time.time()-FIELD["CLOCK"]>6:
    FIELD["CLOCK"]=time.time()
    st.rerun()