import streamlit as st
import websocket
import threading
import json
import uuid
import time
from datetime import datetime

# ==========================================================
# CONFIGURATION & DESIGN SOUVERAIN
# ==========================================================
st.set_page_config(page_title="GEN Z GABON — FREE-KONGOSSA", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: #000; color: white; }
    .card {
        background: #0d0d0d; padding: 15px; border-radius: 18px;
        margin-bottom: 15px; border: 1px solid #1f1f1f; position: relative;
    }
    .msg-user { color: #00ffaa; font-weight: 900; font-size: 0.8em; }
    .msg-time { opacity: 0.4; font-size: 0.7em; float: right; }
    /* Miroir Caméra TikTok Style */
    [data-testid="stCameraInput"] > div { transform: scaleX(-1); border: 2px solid #00ffaa !important; border-radius: 15px; }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# TTU-MC3 Δk/k ADAPTIVE ENGINE
# ==========================================================
def init_session():
    if "uid" not in st.session_state: st.session_state.uid = f"Z-{str(uuid.uuid4())[:4]}"
    if "messages" not in st.session_state: st.session_state.messages = []
    if "ws" not in st.session_state: st.session_state.ws = None
    if "tunnel" not in st.session_state: st.session_state.tunnel = None
    if "users" not in st.session_state: st.session_state.users = 1
    if "latency_k" not in st.session_state: st.session_state.latency_k = 0.5
    if "delta_k" not in st.session_state: st.session_state.delta_k = 0.05

init_session()

def get_ttu_ratio():
    k = st.session_state.latency_k
    dk = st.session_state.delta_k
    ratio = abs(dk / k) if k != 0 else 1.0
    return max(0.1, min(ratio, 1.5))

# ==========================================================
# LISTENER (THREAD SÉCURISÉ)
# ==========================================================
def listener(ws):
    while True:
        try:
            start_time = time.time()
            msg = ws.recv()
            latency = time.time() - start_time
            
            # Mise à jour TTU Δk/k
            old_k = st.session_state.latency_k
            st.session_state.delta_k = latency - old_k
            st.session_state.latency_k = (old_k + latency) / 2
            
            data = json.loads(msg)
            if data.get("type") == "presence":
                st.session_state.users = data["count"]
            else:
                st.session_state.messages.append(data)
                st.rerun()
        except:
            st.session_state.ws = None
            break

# ==========================================================
# TUNNEL CONNECTION
# ==========================================================
def connect_tunnel(tunnel_code):
    ratio = get_ttu_ratio()
    server_url = "wss://ton-serveur-realtime.onrender.com" # REMPLACER PAR TON URL RENDER
    
    try:
        ws = websocket.create_connection(server_url, timeout=10)
        ws.send(json.dumps({"type": "join", "tunnel": tunnel_code}))
        
        thread = threading.Thread(target=listener, args=(ws,), daemon=True)
        thread.start()
        
        st.session_state.ws = ws
        st.session_state.tunnel = tunnel_code
        return True
    except Exception as e:
        return False

# ==========================================================
# UI INTERFACE
# ==========================================================
st.title("🇬🇦 FREE-KONGOSSA V13")

if not st.session_state.tunnel:
    t_input = st.text_input("CODE DU TUNNEL SECRÉTAIRE", placeholder="Ex: GABON241").upper()
    if st.button("OUVRIR LE FLUX TST", use_container_width=True):
        if connect_tunnel(t_input):
            st.success("Tunnel Δk/k Synchronisé")
            st.rerun()
        else:
            st.error("Échec de la connexion au serveur distant.")
else:
    # Header Info
    ratio = get_ttu_ratio()
    st.caption(f"🟢 TUNNEL: {st.session_state.tunnel} | 👥 {st.session_state.users} ONLINE | Δk/k: {ratio:.3f}")
    
    # Message Input
    with st.container():
        m_col1, m_col2 = st.columns([5,1])
        with m_col1:
            new_msg = st.text_input("Raconte le Kongossa...", key="input_msg")
        with m_col2:
            if st.button("🚀") and new_msg:
                payload = {
                    "type": "message",
                    "user": st.session_state.uid,
                    "content": new_msg,
                    "time": datetime.now().strftime("%H:%M")
                }
                try:
                    st.session_state.ws.send(json.dumps(payload))
                    st.session_state.messages.append(payload)
                except:
                    st.error("Lien perdu. Reconnexion...")

    # Feed
    st.markdown("---")
    for m in reversed(st.session_state.messages[-20:]):
        is_me = m["user"] == st.session_state.uid
        align = "margin-left: auto; border-right: 3px solid #00ffaa;" if is_me else "margin-right: auto; border-left: 3px solid #555;"
        
        st.markdown(f"""
        <div class="card" style="width: 80%; {align}">
            <span class="msg-user">{m['user']}</span>
            <span class="msg-time">{m['time']}</span><br>
            <div style="padding-top:5px;">{m['content']}</div>
        </div>
        """, unsafe_allow_html=True)

    if st.button("🧨 QUITTER"):
        if st.session_state.ws: st.session_state.ws.close()
        st.session_state.tunnel = None
        st.rerun()

    time.sleep(get_ttu_ratio() * 5) # Adaptative Ghost Refresh
    st.rerun()
