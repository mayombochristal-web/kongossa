import streamlit as st
from cryptography.fernet import Fernet
import hashlib, time, datetime, random

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="KONGOSSA v2", page_icon="🇬🇦", layout="centered")

# =====================================================
# GLOBAL SERVER MEMORY (SIMULATED BACKEND)
# =====================================================
@st.cache_resource
def server():
    return {
        "USERS": {},
        "ROOMS": {},
        "REACTIONS": {},
        "COMMENTS": {},
        "PRESENCE": {}
    }

DB = server()

# =====================================================
# CORE ENGINE
# =====================================================
class KongossaCore:

    # ---------- AUTH ----------
    def login(self, key):
        sid = hashlib.sha256(key.encode()).hexdigest()[:12]
        DB["USERS"].setdefault(sid, {})
        DB["ROOMS"].setdefault(sid, [])
        return sid

    # ---------- PRESENCE ----------
    def heartbeat(self, sid, token):
        DB["PRESENCE"][f"{sid}:{token}"] = time.time()

    def online_users(self, sid):
        now = time.time()
        return [
            k for k,v in DB["PRESENCE"].items()
            if k.startswith(sid) and now-v < 20
        ]

    # ---------- POST ----------
    def post(self, sid, data, name, mtype, is_txt, title):

        key = Fernet.generate_key()
        enc = Fernet(key).encrypt(data)

        L=len(enc)

        msg={
            "id": hashlib.md5(enc).hexdigest(),
            "k":key,
            "frags":[enc[:L//3],enc[L//3:2*L//3],enc[2*L//3:]],
            "title":title,
            "type":mtype,
            "name":name,
            "is_txt":is_txt,
            "ts":time.time()
        }

        DB["ROOMS"][sid].append(msg)

    # ---------- CLEANUP ----------
    def cleanup(self,sid):
        now=time.time()
        DB["ROOMS"][sid]=[
            m for m in DB["ROOMS"][sid]
            if now-m["ts"]<3600
        ]

    # ---------- REACTION ----------
    def react(self,msg_id,emoji):
        DB["REACTIONS"].setdefault(msg_id,[]).append(emoji)

    # ---------- COMMENT ----------
    def comment(self,msg_id,text):
        DB["COMMENTS"].setdefault(msg_id,[]).append({
            "t":text,
            "ts":datetime.datetime.now().strftime("%H:%M")
        })

core = KongossaCore()

# =====================================================
# STYLE
# =====================================================
st.markdown("""
<style>
.stApp{background:#000;color:white}
.card{
 background:#111;
 padding:15px;
 border-radius:14px;
 margin-bottom:20px;
 border:1px solid #222;
}
.title{color:#00ffaa;font-weight:900}
.comment{background:#1a1a1a;padding:6px;border-radius:8px;margin:4px}
</style>
""",unsafe_allow_html=True)

# =====================================================
# LOGIN
# =====================================================
st.title("🇬🇦 KONGOSSA v2")

if "sid" not in st.session_state:
    key=st.text_input("🔑 Clé du tunnel",type="password")
    if st.button("Entrer") and key:
        st.session_state.sid=core.login(key.upper())
        st.session_state.token=random.randint(1000,9999)
        st.rerun()

else:

    sid=st.session_state.sid

    # presence
    core.heartbeat(sid,st.session_state.token)

    online=len(core.online_users(sid))
    if online>1:
        st.success(f"🟢 {online} personnes dans le tunnel")

    core.cleanup(sid)

# =====================================================
# FEED
# =====================================================
    for p in reversed(DB["ROOMS"][sid]):

        st.markdown('<div class="card">',unsafe_allow_html=True)

        if p["title"]:
            st.markdown(f'<div class="title">{p["title"]}</div>',unsafe_allow_html=True)

        try:
            raw=Fernet(p["k"]).decrypt(b"".join(p["frags"]))

            if p["is_txt"]:
                st.write(raw.decode())
            else:
                if "image" in p["type"]:
                    st.image(raw)
                elif "audio" in p["type"]:
                    st.audio(raw)
                elif "video" in p["type"]:
                    st.video(raw)

        except:
            st.error("Signal expiré")

        # reactions
        reacts=DB["REACTIONS"].get(p["id"],[])
        cols=st.columns(5)
        emojis=["❤️","😂","🔥","😮","✊"]

        for i,e in enumerate(emojis):
            if cols[i].button(e,key=f"{p['id']}{i}"):
                core.react(p["id"],e)
                st.rerun()

        if reacts:
            st.caption(" ".join(reacts[-10:]))

        # comments
        with st.expander("💬 discussions"):
            for c in DB["COMMENTS"].get(p["id"],[]):
                st.markdown(f'<div class="comment"><b>{c["ts"]}</b> {c["t"]}</div>',unsafe_allow_html=True)

            new=st.text_input("Commenter",key=f"c{p['id']}")
            if st.button("Envoyer",key=f"s{p['id']}"):
                core.comment(p["id"],new)
                st.rerun()

        st.markdown("</div>",unsafe_allow_html=True)

# =====================================================
# CREATE POST
# =====================================================
    st.divider()
    st.subheader("➕ Nouveau signal")

    title=st.text_input("Titre")

    tab1,tab2,tab3=st.tabs(["💬 Texte","📸 Média","🎙️ Vocal"])

    with tab1:
        txt=st.text_area("Message")
        if st.button("Publier texte"):
            core.post(sid,txt.encode(),"txt","text",True,title)
            st.rerun()

    with tab2:
        f=st.file_uploader("Image/Vidéo")
        if f and st.button("Publier média"):
            core.post(sid,f.getvalue(),f.name,f.type,False,title)
            st.rerun()

    with tab3:
        audio=st.audio_input("Parler")
        if audio:
            core.post(sid,audio.getvalue(),"vocal.wav","audio/wav",False,title)
            st.rerun()

# =====================================================
# LIVE LOOP
# =====================================================
    time.sleep(8)
    st.rerun()