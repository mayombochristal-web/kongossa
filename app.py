import streamlit as st
from cryptography.fernet import Fernet
import hashlib, time, datetime, random

# =====================================================
# CONFIGURATION ET STYLE SOUVERAIN
# =====================================================
st.set_page_config(page_title="GEN Z GABON v2", page_icon="🇬🇦", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: #000; color: white; }
    
    /* Carte de signal style "Fil d'actualité" */
    .card {
        background: #0d0d0d;
        padding: 20px;
        border-radius: 18px;
        margin-bottom: 25px;
        border: 1px solid #1f1f1f;
        position: relative;
    }
    .title-banner {
        color: #00ffaa;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-size: 1.1em;
        margin-bottom: 10px;
        border-bottom: 1px solid #00ffaa33;
        padding-bottom: 5px;
    }
    
    /* Réactions discrètes dans l'angle */
    .reaction-pill-box {
        position: absolute;
        bottom: -12px;
        left: 15px;
        display: flex;
        gap: 4px;
        background: #00ffaa;
        padding: 2px 8px;
        border-radius: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }
    .pill-item { color: black; font-size: 0.75em; font-weight: bold; }
    
    /* Miroir pour la caméra */
    [data-testid="stCameraInput"] > div {
        transform: scaleX(-1);
        border: 2px solid #00ffaa !important;
        border-radius: 15px;
    }
    
    .comment-bubble {
        background: #1a1a1a;
        padding: 8px 12px;
        border-radius: 12px;
        margin: 6px 0;
        font-size: 0.9em;
        border-left: 3px solid #00ffaa;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# MÉMOIRE SERVEUR (CACHE)
# =====================================================
@st.cache_resource
def server():
    return {
        "ROOMS": {},
        "REACTIONS": {},
        "COMMENTS": {},
        "PRESENCE": {}
    }

DB = server()

# =====================================================
# CŒUR LOGIQUE (POO)
# =====================================================
class KongossaCore:
    def login(self, key):
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    def post(self, sid, data, name, mtype, is_txt, title):
        key = Fernet.generate_key()
        enc = Fernet(key).encrypt(data)
        L = len(enc)
        msg_id = hashlib.md5(enc).hexdigest()
        
        msg = {
            "id": msg_id,
            "k": key,
            "frags": [enc[:L//3], enc[L//3:2*L//3], enc[2*L//3:]],
            "title": title,
            "type": mtype,
            "ts": time.time(),
            "is_txt": is_txt
        }
        DB["ROOMS"].setdefault(sid, []).append(msg)

    def cleanup(self, sid):
        now = time.time()
        if sid in DB["ROOMS"]:
            DB["ROOMS"][sid] = [m for m in DB["ROOMS"][sid] if now - m["ts"] < 3600]

core = KongossaCore()

# =====================================================
# INTERFACE UTILISATEUR
# =====================================================
st.markdown('<h1 style="text-align:center; color:#00ffaa;">🇬🇦 GEN Z GABON</h1>', unsafe_allow_html=True)
st.caption("<center>SOUVERAINETÉ NUMÉRIQUE • FREE-KONGOSSA</center>", unsafe_allow_html=True)

if "sid" not in st.session_state:
    with st.container():
        st.write("---")
        key = st.text_input("🔑 Entrez la clé souveraine", type="password")
        if st.button("ACTIVER LE TUNNEL", use_container_width=True) and key:
            st.session_state.sid = core.login(key.upper())
            st.session_state.token = random.randint(1000, 9999)
            st.rerun()
else:
    sid = st.session_state.sid
    core.cleanup(sid)

    # --- FEED (FIL D'ACTUALITÉ) ---
    for p in reversed(DB["ROOMS"].get(sid, [])):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        if p["title"]:
            st.markdown(f'<div class="title-banner">{p["title"]}</div>', unsafe_allow_html=True)

        try:
            raw = Fernet(p["k"]).decrypt(b"".join(p["frags"]))
            if p["is_txt"]:
                st.markdown(f"### {raw.decode()}")
            else:
                if "image" in p["type"]: st.image(raw, use_container_width=True)
                elif "audio" in p["type"]: st.audio(raw)
                elif "video" in p["type"]: st.video(raw)
        except:
            st.error("Signal TST corrompu")

        # Micro-Réactions (Pills)
        reacts = DB["REACTIONS"].get(p["id"], [])
        if reacts:
            unique_reacts = "".join(list(set(reacts))[:5])
            st.markdown(f'<div class="reaction-pill-box"><span class="pill-item">{unique_reacts} {len(reacts)}</span></div>', unsafe_allow_html=True)

        # Barre d'action horizontale
        st.markdown("<br>", unsafe_allow_html=True)
        cols = st.columns(6)
        emojis = ["❤️", "😂", "🔥", "✊", "😮"]
        for i, e in enumerate(emojis):
            if cols[i].button(e, key=f"re_{p['id']}_{i}"):
                DB["REACTIONS"].setdefault(p["id"], []).append(e)
                st.rerun()

        # Système de commentaires
        with st.expander(f"💬 Discussions ({len(DB['COMMENTS'].get(p['id'], []))})"):
            for c in DB["COMMENTS"].get(p["id"], []):
                st.markdown(f'<div class="comment-bubble"><b>{c["ts"]}</b> : {c["t"]}</div>', unsafe_allow_html=True)
            
            c_input = st.text_input("Ajouter un avis...", key=f"in_{p['id']}")
            if st.button("Envoyer", key=f"btn_{p['id']}"):
                DB["COMMENTS"].setdefault(p["id"], []).append({
                    "t": c_input, "ts": datetime.datetime.now().strftime("%H:%M")
                })
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ZONE DE CRÉATION ---
    st.write("---")
    st.subheader("➕ Émettre un Signal")
    new_title = st.text_input("Thème du signal (Titre Facebook style)")
    
    t1, t2, t3 = st.tabs(["💬 Texte", "📸 Caméra", "🎙️ Vocal"])
    
    with t1:
        txt = st.text_area("Votre message...")
        if st.button("Diffuser Texte", use_container_width=True):
            core.post(sid, txt.encode(), "txt", "text", True, new_title)
            st.rerun()
    with t2:
        cam = st.camera_input("Prise de vue miroir")
        if cam:
            core.post(sid, cam.getvalue(), "img.jpg", "image/jpeg", False, new_title)
            st.rerun()
    with t3:
        vox = st.audio_input("Enregistrement vocal")
        if vox:
            core.post(sid, vox.getvalue(), "vocal.wav", "audio/wav", False, new_title)
            st.rerun()

    if st.button("🧨 QUITTER LE TUNNEL"):
        del st.session_state.sid
        st.rerun()

    # Boucle de rafraîchissement intelligente
    time.sleep(10)
    st.rerun()
