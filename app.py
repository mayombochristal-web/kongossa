# ==========================================================
# GEN Z GABON — FREE-KONGOSSA V12
# TST ENGINE + MULTI TUNNELS + REALTIME SAFE
# ==========================================================

import streamlit as st
import websocket
import threading
import json
import uuid
import time
from datetime import datetime

# ==========================================================
# CONFIG
# ==========================================================

st.set_page_config(
    page_title="GEN Z GABON — FREE-KONGOSSA",
    layout="wide"
)

# 🔴 METTRE TON URL RENDER ICI
SERVER_URL = "wss://TON-SERVER.onrender.com"

# ==========================================================
# SESSION INIT
# ==========================================================

if "uid" not in st.session_state:
    st.session_state.uid = str(uuid.uuid4())[:6]

if "messages" not in st.session_state:
    st.session_state.messages = []

if "ws" not in st.session_state:
    st.session_state.ws = None

if "connected_tunnel" not in st.session_state:
    st.session_state.connected_tunnel = None

if "users_count" not in st.session_state:
    st.session_state.users_count = 1


# ==========================================================
# WEBSOCKET LISTENER (TST LOOP)
# ==========================================================

def listener(ws):

    while True:
        try:
            msg = ws.recv()
            data = json.loads(msg)

            # présence tunnel
            if data.get("type") == "presence":
                st.session_state.users_count = data["count"]
                continue

            # anti duplication TST
            if data not in st.session_state.messages:
                st.session_state.messages.append(data)

        except:
            break


# ==========================================================
# CONNECT TUNNEL
# ==========================================================

st.title("🇬🇦 GEN Z GABON — FREE-KONGOSSA")

tunnel = st.text_input(
    "🔐 Code Tunnel",
    placeholder="Ex: LIBREVILLE"
).upper()

connect = st.button("Connexion Tunnel")

if connect and tunnel:

    try:
        ws = websocket.WebSocket()
        ws.connect(SERVER_URL)

        ws.send(json.dumps({
            "type": "join",
            "tunnel": tunnel
        }))

        thread = threading.Thread(
            target=listener,
            args=(ws,),
            daemon=True
        )
        thread.start()

        st.session_state.ws = ws
        st.session_state.connected_tunnel = tunnel
        st.success("Tunnel synchronisé 🌐")

    except Exception as e:
        st.error("Connexion impossible au serveur realtime")


# ==========================================================
# STATUS BAR
# ==========================================================

if st.session_state.connected_tunnel:

    st.info(
        f"Tunnel : {st.session_state.connected_tunnel} | "
        f"👥 {st.session_state.users_count} utilisateur(s) connecté(s)"
    )

# ==========================================================
# ENVOI MESSAGE
# ==========================================================

if st.session_state.ws:

    col1, col2 = st.columns([6,1])

    with col1:
        msg = st.text_input("Message")

    with col2:
        send = st.button("Envoyer")

    if send and msg:

        payload = {
            "type": "message",
            "user": st.session_state.uid,
            "content": msg,
            "time": datetime.now().strftime("%H:%M:%S")
        }

        # local instant (TST ghost)
        st.session_state.messages.append(payload)

        try:
            st.session_state.ws.send(json.dumps(payload))
        except:
            st.warning("Message non envoyé")

# ==========================================================
# AFFICHAGE CONVERSATION
# ==========================================================

st.markdown("---")
st.subheader("Flux du Tunnel")

for m in reversed(st.session_state.messages):

    align = "right" if m["user"] == st.session_state.uid else "left"

    st.markdown(
        f"""
        <div style="
        text-align:{align};
        padding:10px;
        margin:6px;
        background:#111;
        border-radius:12px;">
        <b>{m['user']}</b><br>
        {m['content']}<br>
        <small>{m['time']}</small>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================================
# AUTO REFRESH TST (pseudo temps réel Streamlit)
# ==========================================================

time.sleep(1)
st.rerun()