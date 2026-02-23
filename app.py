import streamlit as st
from cryptography.fernet import Fernet
import hashlib, time, uuid

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="GEN Z GABON FREE-KONGOSSA",
    page_icon="🇬🇦",
    layout="centered"
)

st.title("🇬🇦 GEN Z GABON")
st.caption("FREE-KONGOSSA — Réseau Fantôme Temps Réel")

# =====================================================
# 👻 GHOST CORE GLOBAL
# =====================================================

@st.cache_resource
def ghost():
    return {
        "BUS": [],
        "PRESENCE": {},
        "REACTIONS": {},
        "COMMENTS": {},
        "REGISTRY": set()
    }

G = ghost()

# =====================================================
# ENGINE
# =====================================================

class Engine:

    def tunnel(self, code):
        return hashlib.sha256(code.encode()).hexdigest()[:12]

    def encrypt(self, data):
        k = Fernet.generate_key()
        enc = Fernet(k).encrypt(data)
        L = len(enc)
        return k,[enc[:L//3],enc[L//3:2*L//3],enc[2*L//3:]]

    def emit(self, src, dst, data, name, typ, is_txt):

        sig = hashlib.md5(data+str(time.time()).encode()).hexdigest()
        if sig in G["REGISTRY"]:
            return

        k,f = self.encrypt(data)

        G["BUS"].append({
            "id":str(uuid.uuid4()),
            "src":src,
            "dst":dst,
            "k":k,
            "frags":f,
            "name":name,
            "type":typ,
            "is_txt":is_txt,
            "ts":time.time()
        })

        G["REGISTRY"].add(sig)

engine = Engine()

# =====================================================
# SESSION SHADOW
# =====================================================

if "msgs" not in st.session_state:
    st.session_state.msgs=[]

if "known" not in st.session_state:
    st.session_state.known=set()

if "typing" not in st.session_state:
    st.session_state.typing=False

# =====================================================
# PRESENCE HEARTBEAT
# =====================================================

def update_presence(me):
    G["PRESENCE"][me]=time.time()

def online_users():
    now=time.time()
    return [u for u,t in G["PRESENCE"].items() if now-t<5]

# =====================================================
# SYNC LOOP (MODE FANTÔME)
# =====================================================

def sync(me):
    for m in G["BUS"]:
        if m["id"] in st.session_state.known:
            continue
        if m["src"]==me or m["dst"]==me:
            st.session_state.msgs.append(m)
            st.session_state.known.add(m["id"])

# =====================================================
# AUTH
# =====================================================

if "auth" not in st.session_state:
    st.session_state.auth=False

if not st.session_state.auth:

    code=st.text_input("🔑 Code Tunnel",type="password")
    target=st.text_input("🎯 Tunnel destinataire")

    if st.button("Entrer"):
        if code:
            st.session_state.me=engine.tunnel(code)
            st.session_state.target=engine.tunnel(target) if target else engine.tunnel(code)
            st.session_state.auth=True
            st.rerun()

else:

    me=st.session_state.me
    target=st.session_state.target

    update_presence(me)
    sync(me)

    # =====================================================
    # PRESENCE UI
    # =====================================================

    online=online_users()
    st.caption(f"🟢 En ligne : {len(online)} tunnel(s)")

    # =====================================================
    # FEED
    # =====================================================

    for msg in reversed(st.session_state.msgs):

        with st.container():

            try:
                raw=Fernet(msg["k"]).decrypt(b"".join(msg["frags"]))

                direction="⬅️" if msg["dst"]==me else "➡️"
                st.caption(f"{direction} {msg['src']}")

                if msg["is_txt"]:
                    st.write(raw.decode())
                else:
                    if "image" in msg["type"]:
                        st.image(raw)
                    elif "video" in msg["type"]:
                        st.video(raw)
                    elif "audio" in msg["type"]:
                        st.audio(raw)

            except:
                st.error("Signal fantôme perdu")

            # ================= REACTIONS =================

            emojis=["❤️","😂","🔥","😮","✊","👍"]
            cols=st.columns(len(emojis))

            for i,e in enumerate(emojis):
                if cols[i].button(e,key=f"{msg['id']}{i}"):
                    G["REACTIONS"].setdefault(msg["id"],[]).append(e)
                    st.rerun()

            reacts=G["REACTIONS"].get(msg["id"],[])
            if reacts:
                st.write(" ".join(reacts[-6:]))

            # ================= COMMENTS =================

            with st.expander(
                f"💬 Discussions ({len(G['COMMENTS'].get(msg['id'],[]))})"
            ):
                for c in G["COMMENTS"].get(msg["id"],[]):
                    st.write("🗨️",c)

                new=st.text_input("Répondre...",key=f"c{msg['id']}")
                if st.button("Envoyer",key=f"s{msg['id']}"):
                    if new:
                        G["COMMENTS"].setdefault(msg["id"],[]).append(new)
                        st.rerun()

    # =====================================================
    # COMPOSER FUTUR
    # =====================================================

    tabs=st.tabs(["💬","📸","🎙️"])

    with tabs[0]:
        txt=st.chat_input("Écrire un kongossa...")
        if txt:
            engine.emit(me,target,txt.encode(),"txt","text",True)
            st.rerun()

    with tabs[1]:
        file=st.file_uploader("Image/Vidéo")
        if file:
            engine.emit(me,target,file.getvalue(),file.name,file.type,False)
            st.rerun()

    with tabs[2]:
        audio=st.audio_input("Vocal")
        if audio:
            engine.emit(me,target,audio.getvalue(),"voice.wav","audio/wav",False)
            st.rerun()

    # =====================================================
    # HEARTBEAT TEMPS RÉEL
    # =====================================================

    time.sleep(1)
    st.rerun()