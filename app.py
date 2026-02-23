import streamlit as st
from cryptography.fernet import Fernet
import hashlib
import time
import threading
from collections import deque

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="KONGOSSA V4",
    page_icon="🇬🇦",
    layout="centered"
)

# =====================================================
# SESSION STORE (STABLE)
# =====================================================

def init_state():
    defaults = {
        "messages": [],
        "registry": set(),
        "event_queue": deque(),
        "engine_started": False
    }

    for k,v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# =====================================================
# REALTIME ENGINE (NO RERUN)
# =====================================================

def realtime_engine():

    while True:
        time.sleep(0.6)

        # simulation sync réseau
        if st.session_state.event_queue:
            continue

# démarre UNE SEULE FOIS
if not st.session_state.engine_started:
    threading.Thread(
        target=realtime_engine,
        daemon=True
    ).start()

    st.session_state.engine_started = True

# =====================================================
# CORE ENGINE
# =====================================================

class KongossaEngine:

    @staticmethod
    def emit(content, fname, mtype, is_txt):

        key = Fernet.generate_key()
        enc = Fernet(key).encrypt(content)

        msg_id = hashlib.md5(enc).hexdigest()

        event = {
            "id": msg_id,
            "k": key,
            "type": mtype,
            "name": fname,
            "is_txt": is_txt,
            "frags":[
                enc[:len(enc)//3],
                enc[len(enc)//3:2*len(enc)//3],
                enc[2*len(enc)//3:]
            ]
        }

        st.session_state.event_queue.append(event)

# =====================================================
# SAFE SYNC (NO DOM BREAK)
# =====================================================

def sync_events():

    new_events = []

    while st.session_state.event_queue:
        ev = st.session_state.event_queue.popleft()

        if ev["id"] not in st.session_state.registry:
            st.session_state.registry.add(ev["id"])
            new_events.append(ev)

    if new_events:
        st.session_state.messages.extend(new_events)

sync_events()

# =====================================================
# UI STYLE
# =====================================================

st.markdown("""
<style>
.stApp { background:black;color:white }
.card{
background:#111;
padding:15px;
border-radius:14px;
margin-bottom:18px;
border:1px solid #222;
}
</style>
""", unsafe_allow_html=True)

st.title("🇬🇦 KONGOSSA V4 — TEMPS RÉEL ABSOLU")

# =====================================================
# RENDER (IMMUTABLE)
# =====================================================

def render_message(msg):

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)

        raw = Fernet(msg["k"]).decrypt(b"".join(msg["frags"]))

        if msg["is_txt"]:
            st.write(raw.decode())

        elif "image" in msg["type"]:
            st.image(raw, use_container_width=True)

        elif "video" in msg["type"]:
            st.video(raw)

        elif "audio" in msg["type"]:
            st.audio(raw)

        st.markdown('</div>', unsafe_allow_html=True)

# affichage stable
for m in reversed(st.session_state.messages):
    render_message(m)

# =====================================================
# EMITTER (UNCHANGED UX)
# =====================================================

tabs = st.tabs(["💬 Texte","📸 Média","🎙️ Vocal"])

with tabs[0]:
    txt = st.chat_input("Kongossa...")
    if txt:
        KongossaEngine.emit(txt.encode(),"txt","text",True)

with tabs[1]:
    file = st.file_uploader("Image / Vidéo")
    if file:
        KongossaEngine.emit(
            file.getvalue(),
            file.name,
            file.type,
            False
        )

with tabs[2]:
    audio = st.audio_input("Parler")
    if audio:
        KongossaEngine.emit(
            audio.getvalue(),
            "voice.wav",
            "audio/wav",
            False
        )

# =====================================================
# AUTO REFRESH INVISIBLE (SAFE)
# =====================================================

st.empty()
time.sleep(1.2)
st.rerun()