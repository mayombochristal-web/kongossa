import streamlit as st
import websocket
import threading
import json
import uuid
from datetime import datetime

# ===================================================
# CONFIG
# ===================================================

st.set_page_config(layout="wide")

SERVER_URL = "ws://TON_IP_SERVEUR:8765"
# exemple:
# ws://192.168.1.15:8765

# ===================================================
# SESSION
# ===================================================

if "uid" not in st.session_state:
    st.session_state.uid = str(uuid.uuid4())[:6]

if "messages" not in st.session_state:
    st.session_state.messages = []

if "ws" not in st.session_state:
    st.session_state.ws = None

# ===================================================
# WEBSOCKET LISTENER
# ===================================================

def listen(ws):

    while True:
        try:
            msg = ws.recv()
            data = json.loads(msg)

            st.session_state.messages.append(data)

        except:
            break

# ===================================================
# CONNECT
# ===================================================

tunnel = st.text_input("Code tunnel")

if tunnel and st.session_state.ws is None:

    ws = websocket.WebSocket()
    ws.connect(SERVER_URL)

    ws.send(json.dumps({
        "type":"join",
        "tunnel":tunnel
    }))

    thread = threading.Thread(
        target=listen,
        args=(ws,),
        daemon=True
    )
    thread.start()

    st.session_state.ws = ws

    st.success("Connecté au tunnel mondial")

# ===================================================
# SEND MESSAGE
# ===================================================

msg = st.text_input("Message")

if st.button("Envoyer") and msg:

    data = {
        "type":"text",
        "user":st.session_state.uid,
        "content":msg,
        "time":datetime.now().strftime("%H:%M:%S")
    }

    st.session_state.messages.append(data)
    st.session_state.ws.send(json.dumps(data))

# ===================================================
# DISPLAY
# ===================================================

st.markdown("## Conversation")

for m in reversed(st.session_state.messages):

    st.markdown(f"""
    **{m["user"]}** : {m["content"]}
    _{m["time"]}_
    """)