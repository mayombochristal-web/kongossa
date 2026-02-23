import streamlit as st
import websocket
import threading
import json
import uuid
import time
from collections import deque

# =============================
# SESSION INIT
# =============================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "registry" not in st.session_state:
    st.session_state.registry = set()

if "media_lock" not in st.session_state:
    st.session_state.media_lock = {}

if "event_queue" not in st.session_state:
    st.session_state.event_queue = deque()

if "connected" not in st.session_state:
    st.session_state.connected = False

# =============================
# WEBSOCKET
# =============================

def on_message(ws, message):
    event = json.loads(message)
    st.session_state.event_queue.append(event)

def connect_ws():
    ws = websocket.WebSocketApp(
        "ws://localhost:8765",
        on_message=on_message
    )

    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()

    st.session_state.ws = ws
    st.session_state.connected = True

if not st.session_state.connected:
    connect_ws()

# =============================
# UTILS
# =============================

def kongossa_time():
    return int(time.time() * 1000)

def create_event(event_type, content):
    return {
        "id": uuid.uuid4().hex,
        "time": kongossa_time(),
        "type": event_type,
        "content": content
    }

def media_once(media_id):
    if media_id in st.session_state.media_lock:
        return False
    st.session_state.media_lock[media_id] = True
    return True

# =============================
# UI
# =============================

st.title("🔥 KONGOSSA v3")

username = st.text_input("Nom", "User")

# =============================
# INPUT TEXTE
# =============================

msg = st.chat_input("Message...")

if msg:
    event = create_event("text", {
        "user": username,
        "text": msg
    })

    st.session_state.ws.send(json.dumps(event))
    st.session_state.event_queue.append(event)

# =============================
# AUDIO UPLOAD
# =============================

audio = st.file_uploader("Audio", type=["mp3","wav"], key="audio")

if audio:
    file_id = uuid.uuid4().hex
    path = f"media/{file_id}.mp3"

    with open(path,"wb") as f:
        f.write(audio.read())

    event = create_event("audio", {
        "user": username,
        "path": path
    })

    st.session_state.ws.send(json.dumps(event))
    st.session_state.event_queue.append(event)

# =============================
# VIDEO UPLOAD
# =============================

video = st.file_uploader("Vidéo", type=["mp4"], key="video")

if video:
    file_id = uuid.uuid4().hex
    path = f"media/{file_id}.mp4"

    with open(path,"wb") as f:
        f.write(video.read())

    event = create_event("video", {
        "user": username,
        "path": path
    })

    st.session_state.ws.send(json.dumps(event))
    st.session_state.event_queue.append(event)

# =============================
# EVENT PROCESSOR
# =============================

def render_event(event):

    if event["id"] in st.session_state.registry:
        return

    st.session_state.registry.add(event["id"])

    content = event["content"]

    with st.chat_message(content["user"]):

        if event["type"] == "text":
            st.write(content["text"])

        elif event["type"] == "audio":
            if media_once(event["id"]):
                st.audio(content["path"])

        elif event["type"] == "video":
            if media_once(event["id"]):
                st.video(content["path"])

# =============================
# DISPLAY LOOP
# =============================

while st.session_state.event_queue:
    ev = st.session_state.event_queue.popleft()
    render_event(ev)