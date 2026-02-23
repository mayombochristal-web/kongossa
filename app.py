import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib
import time
import random
import base64

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="GEN-Z GABON",
    page_icon="🇬🇦",
    layout="centered"
)

# =====================================================
# LOGO
# =====================================================
def get_logo(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

LOGO = get_logo("logo.png")

# =====================================================
# VAULT GLOBAL (RAM ONLY)
# =====================================================
@st.cache_resource
def init_vault():
    return {
        "FLUX": {},        # messages par tunnel
        "PRESENCE": {},    # utilisateurs actifs
        "SEEN_IDS": set()  # anti duplication
    }

VAULT = init_vault()

# =====================================================
# UTILITAIRES
# =====================================================
def secure_id(secret: str):
    if not secret:
        return None
    raw = f"{secret}-{datetime.datetime.now():%Y-%m-%d-%H}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12].upper()

def encrypt_payload(data: bytes):
    key = Fernet.generate_key()
    cipher = Fernet(key)

    encrypted = cipher.encrypt(data)
    l = len(encrypted)

    return {
        "f1": encrypted[:l//3],
        "f2": encrypted[l//3:2*l//3],
        "f3": encrypted[2*l//3:],
        "k": key
    }

def decrypt_payload(p):
    raw = p["f1"] + p["f2"] + p["f3"]
    return Fernet(p["k"]).decrypt(raw)

# =====================================================
# STYLE
# =====================================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg,#050505,#081c15);
    color:white;
}

.post {
    background: rgba(255,255,255,0.05);
    padding:18px;
    border-radius:20px;
    margin-bottom:15px;
    border:1px solid rgba(255,255,255,0.1);
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# HEADER
# =====================================================
if LOGO:
    st.image(f"data:image/png;base64,{LOGO}", width=120)

st.title("🇬🇦 GEN-Z GABON")
st.caption("Tunnel social éphémère chiffré")

# =====================================================
# LOGIN
# =====================================================
secret = st.text_input(
    "🔑 CLÉ DU TUNNEL",
    type="password"
).strip().upper()

session_id = secure_id(secret)

# =====================================================
# SESSION ACTIVE
# =====================================================
if session_id:

    # Token utilisateur unique
    if "token" not in st.session_state:
        st.session_state.token = random.randint(1000, 9999)

    user_presence = f"{session_id}-{st.session_state.token}"

    # présence
    VAULT["PRESENCE"][user_presence] = time.time()

    # nettoyage présence (15s)
    now = time.time()
    for k, t in list(VAULT["PRESENCE"].items()):
        if now - t > 15:
            VAULT["PRESENCE"].pop(k)

    # init flux
    if session_id not in VAULT["FLUX"]:
        VAULT["FLUX"][session_id] = []

    # nettoyage messages (>1h)
    VAULT["FLUX"][session_id] = [
        m for m in VAULT["FLUX"][session_id]
        if now - m["time_obj"] < 3600
    ]

    # présence autres
    peers = [
        k for k in VAULT["PRESENCE"]
        if k.startswith(session_id) and k != user_presence
    ]

    if peers:
        st.success("● SIGNAL ACTIF — autre utilisateur connecté")

    # =================================================
    # FEED
    # =================================================
    st.subheader("🌟 Flux")

    posts = list(reversed(VAULT["FLUX"][session_id]))

    if not posts:
        st.info("Tunnel vide.")
    else:
        for i, p in enumerate(posts):

            msg_id = p["id"]
            if msg_id in VAULT["SEEN_IDS"]:
                continue

            VAULT["SEEN_IDS"].add(msg_id)

            st.markdown('<div class="post">', unsafe_allow_html=True)
            st.caption(p["time"])

            try:
                data = decrypt_payload(p)

                if p["is_txt"]:
                    st.write(data.decode())
                else:
                    if "image" in p["type"]:
                        st.image(data)
                    elif "video" in p["type"]:
                        st.video(data)
                    elif "audio" in p["type"]:
                        st.audio(data)
                    else:
                        st.download_button(
                            "Télécharger",
                            data,
                            file_name=p["name"],
                            key=f"dl{i}"
                        )
            except:
                st.error("Erreur déchiffrement")

            st.markdown('</div>', unsafe_allow_html=True)

    # =================================================
    # ENVOI
    # =================================================
    st.divider()

    mode = st.radio("Publier", ["Texte", "Média"], horizontal=True)

    content = None
    name = ""
    mtype = ""
    is_txt = False

    if mode == "Texte":
        msg = st.chat_input("Message...")
        if msg:
            content = msg.encode()
            is_txt = True
            name = "txt"
            mtype = "text"

    else:
        f = st.file_uploader("Upload média")
        if f:
            content = f.getvalue()
            name = f.name
            mtype = f.type or "application/octet-stream"

    # =================================================
    # POST
    # =================================================
    if content:

        enc = encrypt_payload(content)

        message_id = hashlib.sha256(
            content + str(time.time()).encode()
        ).hexdigest()

        VAULT["FLUX"][session_id].append({
            **enc,
            "id": message_id,
            "name": name,
            "type": mtype,
            "is_txt": is_txt,
            "time": datetime.datetime.now().strftime("%H:%M"),
            "time_obj": time.time()
        })

        st.balloons()
        st.rerun()

    # refresh doux (SAFE STREAMLIT)
    st.experimental_rerun()

else:
    st.warning("Entre une clé pour ouvrir le tunnel.")