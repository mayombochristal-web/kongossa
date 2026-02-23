import streamlit as st
import time
import uuid
from datetime import datetime

# ==========================================================
# CŒUR QUANTIQUE TST (MÉMOIRE PARTAGÉE)
# ==========================================================
@st.cache_resource
def ghost_tunnel():
    """Simule l'intrication de particules pour la comm instantanée"""
    return {"FLUX": [], "PRESENCE": {}, "REACTIONS": {}}

DB = ghost_tunnel()

# ==========================================================
# DESIGN SOUVERAIN (UX GABONAISE)
# ==========================================================
st.set_page_config(page_title="FREE-KONGOSSA TST", page_icon="🇬🇦")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    .stApp { background: #050505; color: white; }
    
    /* Bulle de Signal */
    .signal-card {
        background: #111; padding: 15px; border-radius: 18px 18px 18px 2px;
        margin-bottom: 20px; border: 1px solid #222; position: relative;
    }
    .signal-title { color: #00ffaa; font-weight: 900; text-transform: uppercase; font-size: 0.9em; margin-bottom: 5px; }
    
    /* Réactions Micro-Pills Angle Gauche */
    .reaction-bar {
        position: absolute; bottom: -10px; left: 10px;
        display: flex; gap: 3px; background: #00ffaa;
        padding: 2px 8px; border-radius: 10px; z-index: 10;
    }
    .pill { color: black; font-size: 0.7em; font-weight: bold; }
    
    /* Caméra TikTok Style */
    [data-testid="stCameraInput"] > div { transform: scaleX(-1); border: 2px solid #00ffaa !important; border-radius: 15px; }
    
    .comment-box { background: #1a1a1a; padding: 8px; border-radius: 10px; margin-top: 5px; font-size: 0.85em; border-left: 2px solid #00ffaa; }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# LOGIQUE TTU-MC3 (ZÉRO LATENCE)
# ==========================================================
if "uid" not in st.session_state:
    st.session_state.uid = f"Z-{str(uuid.uuid4())[:4]}"

st.title("🇬🇦 GEN Z GABON V13")
st.caption("SYSTÈME TST : ÉTATS FANTÔMES DES BITS (INTÉGRÉ)")

# --- BARRE DE PRÉSENCE ---
DB["PRESENCE"][st.session_state.uid] = time.time()
active_users = [u for u, t in DB["PRESENCE"].items() if time.time() - t < 10]
st.info(f"🟢 {len(active_users)} Signaux actifs dans le tunnel")

# --- LE FIL DES SIGNAUX ---
for msg in reversed(DB["FLUX"][-15:]): # Limite à 15 pour la fluidité
    st.markdown('<div class="signal-card">', unsafe_allow_html=True)
    
    if msg['title']:
        st.markdown(f'<div class="signal-title">{msg["title"]}</div>', unsafe_allow_html=True)
    
    st.write(msg['content'])
    
    # Affichage des Emojis (Angle Gauche)
    reacts = DB["REACTIONS"].get(msg['id'], [])
    if reacts:
        st.markdown(f'<div class="reaction-bar"><span class="pill">{"".join(reacts)}</span></div>', unsafe_allow_html=True)
    
    # Barre d'action horizontale
    c1, c2, c3, c4, c5, _ = st.columns([1,1,1,1,1,4])
    for i, emo in enumerate(["❤️", "😂", "🔥", "✊", "😮"]):
        if [c1, c2, c3, c4, c5][i].button(emo, key=f"re_{msg['id']}_{i}"):
            DB["REACTIONS"].setdefault(msg['id'], []).append(emo)
            st.rerun()

    # Onglet Discussion Messenger-Style
    with st.expander(f"💬 Discussions"):
        st.markdown(f'<div class="comment-box">Discussion ouverte pour le signal {msg["id"][:4]}...</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================================
# ZONE DE CAPTURE (STUDIO RAPIDE)
# ==========================================================
st.markdown("<br><br>", unsafe_allow_html=True)
with st.container():
    st.subheader("➕ Émettre un Signal")
    new_title = st.text_input("Titre du Signal", placeholder="Ex: Info Libreville...")
    
    tab_txt, tab_cam, tab_vox = st.tabs(["💬 Texte", "📸 Photo/Vidéo", "🎙️ Vocal"])
    
    with tab_txt:
        new_msg = st.text_area("Ton Kongossa...", height=100)
        if st.button("DIFFUSER", use_container_width=True):
            if new_msg:
                DB["FLUX"].append({
                    "id": str(uuid.uuid4()),
                    "user": st.session_state.uid,
                    "title": new_title,
                    "content": new_msg,
                    "time": datetime.now().strftime("%H:%M")
                })
                st.rerun()

    with tab_cam:
        st.caption("Capture instantanée TikTok Style")
        photo = st.camera_input("Shoot")
        if photo:
            st.success("Signal Visuel prêt (Simulé)")

    with tab_vox:
        vox = st.audio_input("Vocal")
        if vox:
            st.success("Signal Vocal capturé")

# ==========================================================
# TST AUTO-REFRESH (ÉTAT FANTÔME)
# ==========================================================
time.sleep(3) # Fréquence de rafraîchissement optimale
st.rerun()
