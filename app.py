# ==========================================================
# GEN Z GABON — FREE KONGOSSA V13
# TTU-MC3 Δk/k Adaptive Tunnel Engine
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
    page_title="GEN Z GABON FREE-KONGOSSA",
    layout="wide"
)

SERVER_URL = "wss://TON-SERVER.onrender.com"

# ==========================================================
# SESSION INIT
# ==========================================================

def init():
    ss = st.session_state

    if "uid" not in ss:
        ss.uid = str(uuid.uuid4())[:6]

    if "messages" not in ss:
        ss.messages = []

    if "ws" not in ss:
        ss.ws = None

    if "tunnel" not in ss:
        ss.tunnel = None

    if "users" not in ss:
        ss.users = 1

    # TTU variables
    if "latency_k" not in ss:
        ss.latency_k = 1.0

    if "delta_k" not in ss:
        ss.delta_k = 0.1


init()

# ==========================================================
# TTU Δk/k ENGINE
# ==========================================================

def ttu_ratio():

    k = st.session_state.latency_k
    dk = st.session_state.delta_k

    ratio = abs(dk / k)

    # bornes de stabilité
    ratio = max(0.2, min(ratio, 2.0))

    return ratio


# ==========================================================
# LISTENER THREAD
# ==========================================================

def listener(ws):

    while True:
        try:
            start = time.time()

            msg = ws.recv()

            latency = time.time() - start

            # mise à jour TTU
            old_k = st.session_state.latency_k
            st.session_state.delta_k = latency - old_k
            st.session_state.latency_k = (old_k + latency) / 2

            data = json.loads(msg)

            if data.get("type") == "presence":
                st.session_state.users = data["count"]
                continue

            if data not in st.session_state.messages:
                st.session_state.messages.append(data)

        except:
            break


# ==========================================================
# CONNECT WITH Δk/k ADAPTATION
# ==========================================================

def connect_tunnel(tunnel):

    ratio = ttu_ratio()

    retries = int(3 * ratio)

    for _ in range(retries):

        try:
            ws = websocket.WebSocket()
            ws.connect(SERVER_URL, timeout=5)

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
            st.session_state.tunnel = tunnel

            return True

        except:
            time.sleep(0.6 * ratio)

    return False


# ==========================================================
# UI
# ==========================================================

st.title("GEN Z GABON — FREE-KONGOSSA")

tunnel_input = st.text_input("Code Tunnel").upper()

if st.button("Ouvrir Flux") and tunnel_input:

    ok = connect_tunnel(tunnel_input)

    if ok:
        st.success("Flux ouvert via Δk/k ⚡")
    else:
        st.error("Impossible d’ouvrir le tunnel")


# ==========================================================
# STATUS
# ==========================================================

if st.session_state.tunnel:

    ratio_display = round(ttu_ratio(), 3)

    st.info(
        f"TUNNEL : {st.session_state.tunnel} | "
        f"👥 {st.session_state.users} utilisateurs | "
        f"Δk/k = {ratio_display}"
    )

# ==========================================================
# SEND MESSAGE
# ==========================================================

if st.session_state.ws:

    col1, col2 = st.columns([6,1])

    with col1:
        msg = st.text_input("Message")

    with col2:
        send = st.button("Envoyer")

    if send and msg:

        payload = {
            "type":"message",
            "user":st.session_state.uid,
            "content":msg,
            "time":datetime.now().strftime("%H:%M:%S")
        }

        st.session_state.messages.append(payload)

        try:
            st.session_state.ws.send(json.dumps(payload))
        except:
            st.warning("Connexion instable")


# ==========================================================
# DISPLAY CHAT
# ==========================================================

st.markdown("---")

for m in reversed(st.session_state.messages):

    align = "right" if m["user"] == st.session_state.uid else "left"

    st.markdown(f"""
    <div style="
    text-align:{align};
    background:#101010;
    padding:10px;
    margin:6px;
    border-radius:12px;">
    <b>{m['user']}</b><br>
    {m['content']}<br>
    <small>{m['time']}</small>
    </div>
    """, unsafe_allow_html=True)

# ==========================================================
# TST GHOST REFRESH
# ==========================================================

time.sleep(1)
st.rerun()