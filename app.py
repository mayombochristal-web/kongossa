import streamlit as st
import time
import uuid
from datetime import datetime

# ==========================================================
# 1. CONFIGURATION (DOIT ÊTRE EN PREMIER !)
# ==========================================================
st.set_page_config(page_title="FREE-KONGOSSA V13", page_icon="🇬🇦", layout="centered")

# ==========================================================
# 2. CŒUR QUANTIQUE TST (MÉMOIRE PARTAGÉE)
# ==========================================================
@st.cache_resource
def ghost_tunnel():
    """Simule l'intrication de particules via le cache global"""
    return {"FLUX": [], "PRESENCE": {}, "REACTIONS": {}}

DB = ghost_tunnel()

# ==========================================================
# 3. DESIGN & STYLES
# ==========================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: #050505; color: white; }
    
    .signal-card {
        background: #111; padding: 18px; border-radius: 20px 20px 20px 2px;
        margin-bottom: 25px; border: 1px solid #222; position: relative;
    }
    .signal-title { color: #00ffaa; font-weight: 900; text-transform: uppercase; font-size: 1em; margin-bottom: 8px; }
    
    .reaction-bar {
        position: absolute; bottom: -12px; left: 15px;
        display: flex; gap: 4px; background: #00ffaa;
        padding: 2px 10px; border-radius: 15px; z-index: 10;
    }
    .pill { color: black; font-size: 0.8em; font-weight: bold; }
    
    /* Caméra Plein Écran Miroir */
    [data-testid="stCameraInput"] > div { transform: scaleX(-1); border: 2px solid #00ffaa !important; border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# 4. INITIALISATION & PRÉSENCE
# ==========================================================
if "uid" not in st.session_state:
    st.session_state.uid = f"Z-{str(uuid.uuid4())[:4]}"

st.title("🇬🇦 GEN Z GABON V13")
st.caption("PROTOCOLE TST : ÉTATS FANTÔMES")

# Mise à jour présence
DB["PRESENCE"][st.session_state.uid] = time.time()
active_users = [u for u, t in DB["PRESENCE"].items() if time.time() - t < 15]
st.info(f"🟢 {len(active_users)} Signaux actifs dans le tunnel")

# ==========================================================
# 5. FIL DES SIGNAUX
# ==========================================================
for msg in reversed(DB["FLUX"][-20:]): 
    st.markdown('<div class="signal-card">', unsafe_allow_html=True)
    
    if msg['title']:
        st.markdown(f'<div class="signal-title">{msg["title"]}</div>', unsafe_allow_html=True)
    
    st.write(msg['content'])
    
    # Emojis Angle Gauche
    reacts = DB["REACTIONS"].get(msg['id'], [])
    if reacts:
        st.markdown(f'<div class="reaction-bar"><span class="pill">{"".join(reacts)}</span></div>', unsafe_allow_html=True)
    
    # Boutons réactions
    cols = st.columns(7)
    emojis = ["❤️", "😂", "🔥", "✊", "😮"]
    for i, emo in enumerate(emojis):
        if cols[i].button(emo, key=f"re_{msg['id']}_{i}"):
            DB["REACTIONS"].setdefault(msg['id'], []).append(emo)
            st.rerun()

    with st.expander("💬 Discussions"):
        st.caption("Fil de discussion sécurisé TST...")
    
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================================
# 6. ZONE D'ÉMISSION
# ==========================================================
st.markdown("---")
with st.container():
    st.subheader("➕ Émettre un Signal")
    new_title = st.text_input("Thème du Signal (Titre)")
    
    t1, t2, t3 = st.tabs(["💬 Texte", "📸 Photo/Vidéo", "🎙️ Vocal"])
    
    with t1:
        txt = st.text_area("Message...")
        if st.button("DIFFUSER", use_container_width=True):
            if txt:
                DB["FLUX"].append({
                    "id": str(uuid.uuid4()),
                    "title": new_title,
                    "content": txt,
                    "ts": time.time()
                })
                st.rerun()

    with t2:
        st.camera_input("Shoot (Mode TikTok)")
    with t3:
        st.audio_input("Vocal")

# Refresh automatique toutes les 5 secondes
time.sleep(5)
st.rerun()
