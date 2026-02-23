import streamlit as st
import websocket
import threading
import json
import uuid
import time
from datetime import datetime
from cryptography.fernet import Fernet

# ==========================================================
# CONFIGURATION & DESIGN GABON SOUVERAIN
# ==========================================================
st.set_page_config(page_title="GEN Z GABON — FREE-KONGOSSA", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: #000; color: white; }
    
    /* Carte de signal style Facebook/Journal */
    .card {
        background: #0d0d0d; padding: 18px; border-radius: 20px;
        margin-bottom: 25px; border: 1px solid #1f1f1f; position: relative;
    }
    .signal-title { color: #00ffaa; font-weight: 900; text-transform: uppercase; font-size: 1.1em; margin-bottom: 10px; }
    
    /* Réactions Micro-Pills (Angle Gauche) */
    .reaction-pill-box {
        position: absolute; bottom: -12px; left: 15px;
        display: flex; gap: 4px; background: #00ffaa;
        padding: 2px 8px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }
    .pill-item { color: black; font-size: 0.75em; font-weight: bold; }
    
    /* Caméra Plein Écran Miroir */
    [data-testid="stCameraInput"] > div { transform: scaleX(-1); border: 2px solid #00ffaa !important; border-radius: 15px; }
    
    .comment-bubble { background: #1a1a1a; padding: 8px; border-radius: 10px; margin: 5px 0; border-left: 3px solid #00ffaa; font-size: 0.9em; }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# TTU-MC3 Δk/k & TST ENGINE
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
    k, dk = st.session_state.latency_k, st.session_state.delta_k
    return max(0.1, min(abs(dk / k) if k != 0 else 1.0, 1.5))

# ==========================================================
# LISTENER THREAD
# ==========================================================
def listener(ws):
    while True:
        try:
            start = time.time()
            msg = ws.recv()
            latency = time.time() - start
            
            # Mise à jour Δk/k
            st.session_state.delta_k = latency - st.session_state.latency_k
            st.session_state.latency_k = (st.session_state.latency_k + latency) / 2
            
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
# CONNEXION AU TUNNEL
# ==========================================================
def connect_tunnel(code):
    ratio = get_ttu_ratio()
    # REMPLACE PAR TON URL DE SERVEUR WEBSOCKET (Render/Heroku)
    url = "wss://ton-serveur-realtime.onrender.com" 
    try:
        ws = websocket.create_connection(url, timeout=10 * ratio)
        ws.send(json.dumps({"type": "join", "tunnel": code}))
        threading.Thread(target=listener, args=(ws,), daemon=True).start()
        st.session_state.ws, st.session_state.tunnel = ws, code
        return True
    except: return False

# ==========================================================
# INTERFACE PRINCIPALE
# ==========================================================
st.title("🇬🇦 FREE-KONGOSSA V13")

if not st.session_state.tunnel:
    t_input = st.text_input("🔑 CODE DU TUNNEL", placeholder="EX: LIBREVILLE2024").upper()
    if st.button("ACTIVER LE SIGNAL", use_container_width=True):
        if connect_tunnel(t_input): st.rerun()
        else: st.error("Échec de connexion au serveur distant.")
else:
    # Status Bar
    st.caption(f"🟢 TUNNEL: {st.session_state.tunnel} | 👥 {st.session_state.users} ONLINE | Δk/k: {get_ttu_ratio():.3f}")

    # --- FIL DES SIGNAUX ---
    for m in reversed(st.session_state.messages[-15:]):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        if m.get("title"): st.markdown(f'<div class="signal-title">{m["title"]}</div>', unsafe_allow_html=True)
        
        st.write(m['content'])
        
        # Micro-Pills Réactions
        if m.get("reacts"):
            st.markdown(f'<div class="reaction-pill-box"><span class="pill-item">{"".join(m["reacts"])}</span></div>', unsafe_allow_html=True)
            
        # Barre de réaction & commentaires discrète
        cols = st.columns(6)
        for i, emo in enumerate(["❤️", "😂", "🔥", "✊", "😮"]):
            if cols[i].button(emo, key=f"re_{m.get('id', uuid.uuid4())}_{i}"):
                # Logique de réaction locale/serveur à ajouter si besoin
                pass

        with st.expander("💬 Discussions"):
            st.caption("Onglet commentaires prêt.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ZONE DE CRÉATION (MODE STUDIO) ---
    st.markdown("---")
    with st.expander("➕ ÉMETTRE UN SIGNAL", expanded=True):
        title = st.text_input("Titre de la publication")
        mode = st.tabs(["💬 Texte", "📸 Caméra", "🎥 Vidéo"])
        
        with mode[0]:
            txt = st.text_area("Message...")
            if st.button("Diffuser"):
                payload = {"type":"message", "user":st.session_state.uid, "content":txt, "title":title, "time":datetime.now().strftime("%H:%M")}
                st.session_state.ws.send(json.dumps(payload))
                st.session_state.messages.append(payload)
                st.rerun()
        with mode[1]:
            cam = st.camera_input("Shoot !")
            if cam: st.success("Photo capturée (Prête pour diffusion)")
        with mode[2]:
            st.file_uploader("Upload Vidéo", type=["mp4","mov"])

    if st.button("🧨 QUITTER LE TUNNEL"):
        if st.session_state.ws: st.session_state.ws.close()
        st.session_state.tunnel = None
        st.rerun()

    time.sleep(5 * get_ttu_ratio())
    st.rerun()
