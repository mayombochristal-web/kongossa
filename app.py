# =====================================================
# GEN Z GABON — FREE KONGOSSA V10
# TTU-MC3 × TST MAXIMUM STABLE
# =====================================================

import streamlit as st
from cryptography.fernet import Fernet
import hashlib, time, uuid, json, asyncio, threading
import websockets
import base64

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="GEN Z GABON FREE-KONGOSSA",
    layout="centered"
)

SERVER_URI = "ws://localhost:8765"

# =====================================================
# TTU FIELD GLOBAL
# =====================================================

@st.cache_resource
def FIELD():
    return {
        "EVENTS": [],
        "INDEX": set(),     # anti-duplication absolue
        "USERS": {}
    }

FIELD = FIELD()

# =====================================================
# SESSION GHOST (TST)
# =====================================================

if "GHOST" not in st.session_state:
    st.session_state.GHOST = {
        "LOCAL": [],
        "KNOWN": set(),
        "CONNECTED": False,
        "SID": None
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
# LOGO
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
        sid=ENGINE.tunnel(code)
        GHOST["SID"]=sid
        st.session_state.auth=True
        st.rerun()

    st.stop()

SID = GHOST["SID"]

# =====================================================
# WEBSOCKET CLIENT (TTU SYNC)
# =====================================================

async def ws_listener():

    async with websockets.connect(SERVER_URI) as ws:

        GHOST["CONNECTED"]=True

        # announce presence
        await ws.send(json.dumps({
            "type":"presence",
            "sid":SID,
            "time":time.time()
        }))

        async for message in ws:

            evt=json.loads(message)

            sig=evt["hash"]

            # ANTI DUPLICATION ABSOLUE
            if sig in FIELD["INDEX"]:
                continue

            FIELD["INDEX"].add(sig)
            FIELD["EVENTS"].append(evt)

def start_ws():
    loop=asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_listener())

if not GHOST["CONNECTED"]:
    threading.Thread(target=start_ws,daemon=True).start()

# =====================================================
# EMIT EVENT
# =====================================================

async def send_event(evt):

    async with websockets.connect(SERVER_URI) as ws:
        await ws.send(json.dumps(evt))

def emit(data,name,typ,is_txt):

    k,f=ENGINE.encrypt(data)

    payload={
        "id":str(uuid.uuid4()),
        "sid":SID,
        "k":base64.b64encode(k).decode(),
        "frags":[base64.b64encode(x).decode() for x in f],
        "name":name,
        "type":typ,
        "is_txt":is_txt,
        "ts":time.time()
    }

    payload["hash"]=hashlib.sha256(
        json.dumps(payload).encode()
    ).hexdigest()

    asyncio.run(send_event(payload))

# =====================================================
# SYNC LOCAL FEED
# =====================================================

new_signal=False

for e in FIELD["EVENTS"]:

    if e["id"] in GHOST["KNOWN"]:
        continue

    if e["sid"]==SID:
        new_signal=True
        GHOST["KNOWN"].add(e["id"])
        GHOST["LOCAL"].append(e)

# =====================================================
# PRESENCE COUNT
# =====================================================

FIELD["USERS"][SID]=time.time()

online=[
u for u,t in FIELD["USERS"].items()
if time.time()-t<10
]

st.caption(f"🟢 {len(online)} utilisateur(s) dans ce tunnel")

# =====================================================
# SIGNAL NOUVEAU MESSAGE
# =====================================================

if new_signal:
    st.success("Nouveau signal reçu")

# =====================================================
# FEED
# =====================================================

for msg in reversed(GHOST["LOCAL"]):

    try:
        k=base64.b64decode(msg["k"])
        frags=[base64.b64decode(x) for x in msg["frags"]]

        raw=ENGINE.decrypt(k,frags)

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
        st.warning("Signal corrompu")

# =====================================================
# COMPOSER
# =====================================================

st.markdown("---")

tabs=st.tabs(["Texte","Media","Vocal"])

with tabs[0]:
    txt=st.text_area("Message")
    if st.button("Envoyer Texte"):
        emit(txt.encode(),"txt","text",True)

with tabs[1]:
    file=st.file_uploader("Image / Video")
    if file and st.button("Envoyer Media"):
        emit(file.getvalue(),file.name,file.type,False)

with tabs[2]:
    audio=st.audio_input("Vocal")
    if audio:
        emit(audio.getvalue(),"voice.wav","audio/wav",False)

# =====================================================
# TST CLOCK
# =====================================================

time.sleep(3)
st.rerun()