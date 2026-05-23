import streamlit as st
from supabase import create_client
import pandas as pd
import time
from datetime import datetime, timedelta, timezone
import uuid
import hashlib
import hmac
import base64
from cryptography.fernet import Fernet
from PIL import Image
import io
import logging
import functools
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import numpy as np
import socket

# =====================================================
# CONFIGURATION LOGGING
# =====================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =====================================================
# CONSTANTES
# =====================================================
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 Mo
CIRCUIT_BREAKER_COOLDOWN = 60

# =====================================================
# INTÉGRATION TTU‑MC³
# =====================================================

def soliton_signature_from_key(shared_key: str):
    """Génère les paramètres (ω₀, σ, μ, γ) d'un soliton à partir d'une clé K."""
    h = hashlib.sha256(shared_key.encode()).digest()
    w0 = 0.5 + (int.from_bytes(h[0:4], 'big') / 2**32) * 2.5
    sigma = (int.from_bytes(h[4:8], 'big') / 2**32) * 2.0
    mu = (int.from_bytes(h[8:12], 'big') / 2**32) * 0.05
    gamma = (int.from_bytes(h[12:16], 'big') / 2**32) * 0.2
    return w0, sigma, mu, gamma

def get_user_stability_bonus(user_id, supabase_client):
    """Calcule un bonus de minage (KC) basé sur la stabilité moyenne des tunnels de l'utilisateur."""
    try:
        members = supabase_client.table("tunnel_members").select("tunnel_id").eq("user_id", user_id).execute()
        if not members.data:
            return 5
        total_J = 0.0
        count = 0
        for m in members.data:
            tunnel_id = m["tunnel_id"]
            tunnel = supabase_client.table("tunnels").select("k_hash").eq("id", tunnel_id).execute()
            if tunnel.data and tunnel.data[0].get("k_hash"):
                key_hash = tunnel.data[0]["k_hash"]
                # Approximation de J à partir du hash
                J = 0.192 + (int(key_hash[20:24], 16) / 2**32 - 0.5) * 0.05
                total_J += J
                count += 1
        if count == 0:
            return 5
        avg_J = total_J / count
        stability = max(0.0, 1.0 - abs(avg_J - 0.192) / 0.05)
        bonus = int(5 + stability * 15)
        return bonus
    except Exception:
        return 5

def get_reputation(user_id, supabase_client):
    bonus = get_user_stability_bonus(user_id, supabase_client)
    stability = (bonus - 5) / 15.0
    if stability > 0.8:
        return "⭐ Soliton Platine"
    elif stability > 0.5:
        return "🌟 Soliton Or"
    else:
        return "⚡ Soliton Argent"

# =====================================================
# DÉCORATEURS DE ROBUSTESSE
# =====================================================
def safe_run(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Erreur dans {func.__name__}: {e}", exc_info=True)
            st.error("🌋 Une erreur inattendue s'est produite. Veuillez réessayer.")
            st.session_state.last_error = str(e)
            return None
    return wrapper

def retry(max_attempts=3, delay=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    wait = delay * (2 ** attempt)
                    logger.warning(f"Tentative {attempt+1} échouée pour {func.__name__}, nouvel essai dans {wait}s")
                    time.sleep(wait)
            return None
        return wrapper
    return decorator

# =====================================================
# FONCTIONS DE CHIFFREMENT (tunnels)
# =====================================================
def get_fernet_from_key(secret: str):
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)

def encrypt_text(plaintext: str) -> str:
    if "current_k" not in st.session_state:
        raise ValueError("🔐 Aucune clé K active en session")
    fernet = get_fernet_from_key(st.session_state.current_k)
    return fernet.encrypt(plaintext.encode()).decode()

def decrypt_text(ciphertext: str) -> str:
    if "current_k" not in st.session_state:
        raise ValueError("🔐 Aucune clé K active en session")
    fernet = get_fernet_from_key(st.session_state.current_k)
    return fernet.decrypt(ciphertext.encode()).decode()

# =====================================================
# CONFIGURATION STREAMLIT
# =====================================================
st.set_page_config(
    page_title="GEN-Z GABON • SOCIAL NETWORK",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# INITIALISATION SUPABASE AVEC TEST DNS
# =====================================================
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"].strip()
        key = st.secrets["SUPABASE_KEY"].strip()
    except KeyError as e:
        st.error(f"🔴 Clé manquante dans les secrets : {e}")
        st.stop()
    except Exception as e:
        st.error(f"🔴 Erreur de lecture des secrets : {e}")
        st.stop()

    if not url.startswith("https://"):
        st.error("❌ L'URL Supabase doit commencer par https://")
        st.stop()

    # Test DNS explicite
    hostname = url.replace("https://", "").split("/")[0]
    try:
        ip = socket.gethostbyname(hostname)
        logger.info(f"DNS OK : {hostname} -> {ip}")
    except Exception as dns_err:
        st.error(f"🌐 Le serveur ne peut pas résoudre {hostname}.")
        st.error(f"Détail : {dns_err}")
        st.info("Vérifiez votre connexion réseau ou contactez le support de votre hébergeur.")
        st.stop()

    try:
        client = create_client(url, key)
        # Test rapide de connexion
        client.table("profiles").select("id").limit(1).execute()
        return client
    except Exception as e:
        st.error(f"🚨 Impossible de se connecter à Supabase : {e}")
        st.stop()

supabase = init_supabase()

@st.cache_resource
def get_fernet_global():
    key = st.secrets.get("fernet_key")
    if not key:
        st.error("🔴 Clé Fernet manquante dans les secrets. Ajoutez 'fernet_key'.")
        st.stop()
    return Fernet(key.encode())

fernet_global = get_fernet_global()

def encrypt_text_global(plain_text: str) -> str:
    if not plain_text:
        return ""
    encrypted = fernet_global.encrypt(plain_text.encode())
    return base64.b64encode(encrypted).decode()

def decrypt_text_global(encrypted_b64: str) -> str:
    if not encrypted_b64:
        return ""
    try:
        encrypted = base64.b64decode(encrypted_b64)
        return fernet_global.decrypt(encrypted).decode()
    except Exception:
        return "🔐 Message illisible (erreur de clé)"

# =====================================================
# FONCTIONS ADMIN & AUTH
# =====================================================
def hash_string(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def verify_admin_code(email: str, code: str) -> bool:
    try:
        admin_email_hash = st.secrets["admin"]["email_hash"]
        admin_code_hash = st.secrets["admin"]["password_hash"]
        return hmac.compare_digest(hash_string(email), admin_email_hash) and \
               hmac.compare_digest(hash_string(code), admin_code_hash)
    except KeyError:
        return False

def parse_iso_date(date_str: str) -> datetime:
    if date_str.endswith('Z'):
        date_str = date_str.replace('Z', '+00:00')
    return datetime.fromisoformat(date_str)

# =====================================================
# AUTHENTIFICATION
# =====================================================
@safe_run
def login_signup():
    st.title("🌍 Bienvenue sur le réseau social GEN-Z")
    tab1, tab2 = st.tabs(["Se connecter", "Créer un compte"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button("Connexion")
            if submitted:
                try:
                    res = supabase.auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )
                    st.session_state["user"] = res.user
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur de connexion : {e}")

    with tab2:
        with st.form("signup_form"):
            new_email = st.text_input("Email")
            new_password = st.text_input("Mot de passe", type="password")
            username = st.text_input("Nom d'utilisateur (unique)")
            admin_code = st.text_input("Code administrateur (si vous en avez un)", type="password")
            submitted = st.form_submit_button("Créer mon compte")
            if submitted:
                if not new_email or not new_password or not username:
                    st.error("Tous les champs sont obligatoires.")
                    return
                try:
                    role = "admin" if verify_admin_code(new_email, admin_code) else "user"
                    res = supabase.auth.sign_up({
                        "email": new_email,
                        "password": new_password,
                        "options": {
                            "data": {
                                "username": username,
                                "role": role
                            }
                        }
                    })
                    user = res.user
                    if not user:
                        st.error("La création du compte a échoué.")
                        return
                    st.success("Compte créé avec succès ! Connectez-vous.")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de l'inscription : {e}")

def logout():
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()

if "user" not in st.session_state:
    login_signup()
    st.stop()

user = st.session_state["user"]

# =====================================================
# PROFIL UTILISATEUR
# =====================================================
@st.cache_data(ttl=60)
def get_profile(user_id):
    res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None

profile = get_profile(user.id)
if profile is None:
    st.warning("Chargement du profil...")
    time.sleep(1)
    st.cache_data.clear()
    profile = get_profile(user.id)
    if profile is None:
        st.error("Impossible de charger votre profil.")
        logout()

def is_admin():
    return profile and profile.get("role") == "admin"

# =====================================================
# NAVIGATION
# =====================================================
st.sidebar.image("https://via.placeholder.com/150x50?text=GEN-Z", width=150)
st.sidebar.write(f"Connecté en tant que : **{profile['username']}**")
if is_admin():
    st.sidebar.markdown("🔑 **Administrateur**")
st.sidebar.write(f"ID : {user.id[:8]}...")

menu_options = ["🌐 Feed", "👤 Mon Profil", "✉️ Messages", "🏪 Marketplace", "💰 Wallet", "💰 Acheter KC", "⚙️ Paramètres"]
if is_admin():
    menu_options.append("🛡️ Admin")
menu = st.sidebar.radio("Navigation", menu_options)

if st.sidebar.button("🚪 Déconnexion"):
    logout()

# =====================================================
# FONCTIONS D'ACCÈS SUPABASE AVEC RETRY
# =====================================================
@retry(max_attempts=3, delay=1)
def supabase_insert(table, data):
    return supabase.table(table).insert(data).execute()

@retry(max_attempts=3, delay=1)
def supabase_update(table, data, match_column, match_value):
    return supabase.table(table).update(data).eq(match_column, match_value).execute()

@retry(max_attempts=3, delay=1)
def supabase_delete(table, conditions):
    query = supabase.table(table).delete()
    for col, val in conditions.items():
        query = query.eq(col, val)
    return query.execute()

@retry(max_attempts=3, delay=1)
def supabase_rpc(rpc_name, params):
    return supabase.rpc(rpc_name, params).execute()

# Circuit breaker
if "supabase_failures" not in st.session_state:
    st.session_state.supabase_failures = 0
    st.session_state.first_failure_time = None

def safe_supabase_call(func, *args, **kwargs):
    now = time.time()
    if st.session_state.supabase_failures >= 5:
        if st.session_state.first_failure_time and (now - st.session_state.first_failure_time) > CIRCUIT_BREAKER_COOLDOWN:
            st.session_state.supabase_failures = 0
            st.session_state.first_failure_time = None
            logger.info("Circuit breaker reset after cooldown.")
        else:
            st.warning("⚠️ Service temporairement indisponible. Réduction des fonctionnalités.")
            return None
    try:
        result = func(*args, **kwargs)
        st.session_state.supabase_failures = 0
        st.session_state.first_failure_time = None
        return result
    except Exception as e:
        st.session_state.supabase_failures += 1
        if st.session_state.first_failure_time is None:
            st.session_state.first_failure_time = time.time()
        logger.error(f"Erreur Supabase: {e}")
        if st.session_state.supabase_failures >= 5:
            st.warning("⚠️ Trop d'erreurs consécutives. Mode dégradé activé.")
        raise e

def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    try:
        res = supabase.storage.from_(bucket).create_signed_url(path, expires_in)
        return res['signedURL']
    except Exception:
        return None

# =====================================================
# FONCTIONS DU FEED
# =====================================================
def upload_optimized_media(file):
    if file.size > MAX_FILE_SIZE:
        st.error(f"Fichier trop volumineux (max {MAX_FILE_SIZE//1024//1024} Mo).")
        return None, None
    try:
        if file.type.startswith("image/"):
            img = Image.open(file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buffer = io.BytesIO()
            quality = 85 if file.size < 1024*1024 else 70
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            file_data = buffer.getvalue()
            content_type = "image/jpeg"
            file_name = f"{uuid.uuid4()}.jpg"
        else:
            file_data = file.getvalue()
            content_type = file.type
            ext = file.name.split(".")[-1]
            file_name = f"{uuid.uuid4()}.{ext}"
        path = f"{user.id}/{file_name}"
        supabase.storage.from_("media").upload(
            path=path,
            file=file_data,
            file_options={"content-type": content_type}
        )
        return path, content_type
    except Exception as e:
        st.error(f"Erreur upload : {e}")
        return None, None

def get_signed_media_url(path: str) -> str:
    if not path:
        return None
    try:
        res = supabase.storage.from_("media").create_signed_url(path, 3600)
        return res['signedURL']
    except Exception:
        return None

@st.cache_data(ttl=300)
def get_cached_media_url(path):
    return get_signed_media_url(path)

def delete_post_and_media(post_id, media_path):
    try:
        if media_path:
            supabase.storage.from_("media").remove([media_path])
        safe_supabase_call(supabase_delete, "posts", {"id": post_id})
        st.toast("🚀 Publication retirée avec succès", icon="🗑️")
        return True
    except Exception as e:
        st.error(f"Erreur suppression : {e}")
        return False

def toggle_like(post_id, user_id):
    check = supabase.table("likes").select("*").eq("post_id", post_id).eq("user_id", user_id).execute()
    if check.data:
        safe_supabase_call(supabase_delete, "likes", {"post_id": post_id, "user_id": user_id})
        return "retiré"
    else:
        safe_supabase_call(supabase_insert, "likes", {"post_id": post_id, "user_id": user_id})
        return "ajouté"

def add_comment(post_id, user_id, text):
    if text.strip():
        safe_supabase_call(supabase_insert, "comments", {"post_id": post_id, "user_id": user_id, "text": text})
        return True
    return False

def process_tip(post_id, sender_id, receiver_id, amount, emoji):
    try:
        safe_supabase_call(supabase_rpc, 'process_tip', {
            'p_post_id': post_id,
            'p_sender_id': sender_id,
            'p_receiver_id': receiver_id,
            'p_amount': amount,
            'p_emoji': emoji
        })
        return True, None
    except Exception as e:
        return False, str(e)

# =====================================================
# PAGE FEED
# =====================================================
@safe_run
def feed_page():
    st.header("🌐 Fil d'actualité")
    if "post_draft" not in st.session_state:
        st.session_state.post_draft = ""

    st.markdown("""
        <style>
        .trending-title { font-size: 1.5rem; font-weight: 600; background: linear-gradient(45deg, #ff9d00, #ff4b4b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; }
        .stats-line { display: flex; gap: 15px; color: #8b949e; font-size: 13px; margin: 8px 0; }
        </style>
    """, unsafe_allow_html=True)

    # Tendances
    st.markdown('<p class="trending-title">🔥 Tendances</p>', unsafe_allow_html=True)
    try:
        tips_24h = supabase.table("tips") \
            .select("post_id, amount") \
            .gte("created_at", (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()) \
            .execute()
        if tips_24h.data:
            tip_sums = {}
            for tip in tips_24h.data:
                tip_sums[tip['post_id']] = tip_sums.get(tip['post_id'], 0) + tip['amount']
            post_ids = list(tip_sums.keys())
            trending_posts = supabase.table("posts") \
                .select("id, user_id, text, media_path, profiles!inner(username, profile_pic)") \
                .in_("id", post_ids) \
                .execute()
            if trending_posts.data:
                trending_posts.data.sort(key=lambda p: tip_sums[p['id']], reverse=True)
                cols = st.columns(min(len(trending_posts.data), 4))
                for i, post in enumerate(trending_posts.data[:4]):
                    with cols[i]:
                        with st.container(border=True):
                            if post.get("media_path"):
                                media_url = get_signed_media_url(post["media_path"])
                                if media_url:
                                    st.image(media_url, use_container_width=True)
                            st.markdown(f"**{post['profiles']['username']}**")
                            st.caption(f"🔥 {tip_sums[post['id']]} KC")
    except Exception:
        st.warning("Tendances indisponibles")
    st.divider()

    # Publication rapide
    with st.container(border=True):
        col_av, col_input = st.columns([1, 5])
        with col_av:
            avatar = profile.get("profile_pic")
            st.image(avatar if avatar else "https://via.placeholder.com/40", width=40)
        with col_input:
            post_text = st.text_area("", value=st.session_state.post_draft, placeholder="Exprimez-vous...", label_visibility="collapsed", key="post_input", height=70)
        c1, c2 = st.columns([1,1])
        with c1:
            uploaded_file = st.file_uploader("📷", type=["png","jpg","jpeg","mp4","mov","mp3","wav"], label_visibility="collapsed", key="media_upload")
        with c2:
            if st.button("🚀 Propulser", use_container_width=True, type="primary"):
                if post_text or uploaded_file:
                    with st.spinner("..."):
                        try:
                            media_path, media_type = None, None
                            if uploaded_file:
                                media_path, media_type = upload_optimized_media(uploaded_file)
                                if media_path is None:
                                    st.stop()
                            supabase.table("posts").insert({
                                "user_id": user.id,
                                "text": post_text if post_text else None,
                                "media_path": media_path,
                                "media_type": media_type,
                                "created_at": datetime.now(timezone.utc).isoformat()
                            }).execute()
                            st.session_state.post_draft = ""
                            st.balloons()
                            st.toast("✨ Posté !")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")
                else:
                    st.warning("Écris ou ajoute un média")

    # Chargement du flux
    if "avg_load_time" not in st.session_state:
        st.session_state.avg_load_time = 0.2
    start_time = time.time()
    with st.spinner("🌊 Chargement..."):
        try:
            POST_LIMIT = 10 if st.session_state.avg_load_time > 1.0 else 30
            posts = supabase.table("posts").select(
                "*, profiles!inner(username, profile_pic)"
            ).order("created_at", desc=True).limit(POST_LIMIT).execute()
        except Exception:
            st.error("Impossible de charger le fil")
            return
    load_time = time.time() - start_time
    st.session_state.avg_load_time = 0.9 * st.session_state.avg_load_time + 0.1 * load_time

    if not posts.data:
        st.info("🌙 Le fil est calme... Sois le premier à propulser !")
        return

    for post in posts.data:
        with st.container(border=True):
            col_avatar, col_header = st.columns([1,8])
            with col_avatar:
                avatar = post["profiles"].get("profile_pic")
                st.image(avatar if avatar else "https://via.placeholder.com/40", width=40)
            with col_header:
                st.markdown(f"**{post['profiles']['username']}**  ·  {post['created_at'][:10]}")
            if post.get("text"):
                st.markdown(f"### {post['text']}")
            if post.get("media_path"):
                media_url = get_cached_media_url(post["media_path"])
                if media_url:
                    if "image" in str(post.get("media_type","")):
                        st.image(media_url, use_container_width=True)
                    elif "video" in str(post.get("media_type","")):
                        st.video(media_url)
                    elif "audio" in str(post.get("media_type","")):
                        st.audio(media_url)
            likes = supabase.table("likes").select("*", count="exact").eq("post_id", post["id"]).execute().count
            comments = supabase.table("comments").select("*", count="exact").eq("post_id", post["id"]).execute().count
            tips = supabase.table("tips").select("*", count="exact").eq("post_id", post["id"]).execute().count
            st.markdown(f"""
            <div class="stats-line">
                <span>❤️ {likes}</span>
                <span>💬 {comments}</span>
                <span>🔥 {tips}</span>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"❤️ {likes}", key=f"like_{post['id']}", use_container_width=True):
                action = toggle_like(post['id'], user.id)
                st.toast(f"❤️ Like {action}")
                time.sleep(0.3)
                st.rerun()

            with st.expander("💬 Réagir avec KC", expanded=False, key=f"exp_{post['id']}"):
                col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                with col_e1:
                    if st.button("🔥 10", key=f"tip10_{post['id']}", use_container_width=True):
                        success, error = process_tip(post['id'], user.id, post['user_id'], 10, '🔥')
                        if success:
                            st.toast("🔥 +10 KC !")
                            st.rerun()
                        else:
                            st.error(f"Erreur : {error}")
                with col_e2:
                    if st.button("💎 50", key=f"tip50_{post['id']}", use_container_width=True):
                        success, error = process_tip(post['id'], user.id, post['user_id'], 50, '💎')
                        if success:
                            st.toast("💎 +50 KC !")
                            st.rerun()
                with col_e3:
                    if st.button("👑 100", key=f"tip100_{post['id']}", use_container_width=True):
                        success, error = process_tip(post['id'], user.id, post['user_id'], 100, '👑')
                        if success:
                            st.balloons()
                            st.toast("👑 +100 KC !")
                            st.rerun()
                with col_e4:
                    with st.popover("💬", help="Voir commentaires"):
                        comments_data = supabase.table("comments").select("*, profiles(username)").eq("post_id", post["id"]).order("created_at").execute()
                        for c in comments_data.data:
                            st.markdown(f"**{c['profiles']['username']}** : {c['text']}")
                        new_comment = st.text_input("", placeholder="Commenter...", key=f"com_{post['id']}")
                        if st.button("Envoyer", key=f"send_{post['id']}"):
                            if add_comment(post['id'], user.id, new_comment):
                                st.rerun()
            if post["user_id"] == user.id or is_admin():
                if st.button("🗑️ Supprimer", key=f"del_{post['id']}", type="secondary"):
                    if delete_post_and_media(post["id"], post.get("media_path")):
                        time.sleep(0.5)
                        st.rerun()

# =====================================================
# PAGE PROFIL (avec badge TTU)
# =====================================================
@safe_run
def profile_page():
    st.header("👤 Mon Profil Souverain")
    st.markdown("""
        <style>
        .badge { display: inline-block; background: linear-gradient(45deg, #ff9d00, #ff4b4b); color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; margin-right: 8px; }
        </style>
    """, unsafe_allow_html=True)
    try:
        profile_data = supabase.table("profiles").select("*").eq("id", user.id).single().execute()
        profile = profile_data.data
    except Exception:
        st.error("Impossible de charger votre profil.")
        return
    col_avatar, col_info = st.columns([1,3])
    with col_avatar:
        avatar = profile.get("profile_pic")
        st.image(avatar if avatar else "https://via.placeholder.com/120x120?text=Avatar", width=120)
    with col_info:
        st.title(f"@{profile['username']}")
        rep = get_reputation(user.id, supabase)
        st.markdown(f"<span class='badge'>{rep}</span>", unsafe_allow_html=True)
        badges = []
        if profile.get("role") == "admin":
            badges.append("🛡️ Administrateur")
        if badges:
            st.markdown(" ".join([f'<span class="badge">{b}</span>' for b in badges]), unsafe_allow_html=True)
        st.markdown(f"📍 **{profile.get('location', 'Localisation non définie')}**")
        st.markdown(f"*{profile.get('bio', 'Aucune bio.')}*")
        if profile.get("created_at"):
            st.caption(f"📅 Membre depuis le {profile['created_at'][:10]}")
    st.divider()
    tab_stats, tab_activity, tab_tunnels, tab_edit, tab_vault = st.tabs(["📊 Statistiques","📋 Activité","🚇 Mes Tunnels","⚙️ Modifier","🔐 Coffre TTU"])
    with tab_stats:
        st.subheader("📊 Statistiques Globales")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            try:
                posts_count = supabase.table("posts").select("*", count="exact").eq("user_id", user.id).execute().count
            except:
                posts_count = 0
            st.metric("Publications", posts_count)
        with col2:
            try:
                followers = supabase.table("follows").select("*", count="exact").eq("followed", user.id).execute().count
            except:
                followers = 0
            st.metric("Abonnés", followers)
        with col3:
            try:
                following = supabase.table("follows").select("*", count="exact").eq("follower", user.id).execute().count
            except:
                following = 0
            st.metric("Abonnements", following)
        with col4:
            try:
                likes_received = supabase.table("likes").select("*", count="exact").eq("post_id", supabase.table("posts").select("id").eq("user_id", user.id).execute().data).execute().count
            except:
                likes_received = 0
            st.metric("Likes reçus", likes_received)
        st.divider()
        st.subheader("💰 Portefeuille KC")
        try:
            wallet = supabase.table("wallets").select("*").eq("user_id", user.id).single().execute()
            if wallet.data:
                col_w1, col_w2, col_w3 = st.columns(3)
                col_w1.metric("Solde KC", f"{wallet.data['kongo_balance']:,.0f}")
                col_w2.metric("Total miné", f"{wallet.data['total_mined']:,.0f}")
                if wallet.data.get('last_reward_at'):
                    last = parse_iso_date(wallet.data['last_reward_at'])
                    next_reward = last + timedelta(days=1)
                    time_left = next_reward - datetime.now(timezone.utc)
                    hours = int(time_left.total_seconds() // 3600)
                    col_w3.metric("Prochain minage", f"{hours}h")
        except Exception:
            st.info("Portefeuille en cours d'initialisation")
        st.subheader("🚇 Activité TTU-MC³")
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            try:
                messages_count = supabase.table("messages").select("*", count="exact").eq("sender", user.id).execute().count
            except:
                messages_count = 0
            st.metric("Messages envoyés", messages_count)
        with col_t2:
            try:
                tunnels_member = supabase.table("tunnel_members").select("*", count="exact").eq("user_id", user.id).execute().count
            except:
                tunnels_member = 0
            st.metric("Tunnels rejoints", tunnels_member)
        with col_t3:
            try:
                tunnels_created = supabase.table("tunnels").select("*", count="exact").eq("creator_id", user.id).execute().count
            except:
                tunnels_created = 0
            st.metric("Tunnels créés", tunnels_created)

    with tab_activity:
        st.subheader("📋 Activité Récente")
        try:
            last_posts = supabase.table("posts").select("text, created_at, media_type").eq("user_id", user.id).order("created_at", desc=True).limit(5).execute()
            if last_posts.data:
                st.write("**📝 Dernières publications**")
                for p in last_posts.data:
                    media_icon = "📷" if "image" in str(p.get("media_type","")) else "🎬" if "video" in str(p.get("media_type","")) else "📄"
                    st.caption(f"{media_icon} {p['text'][:50]}... - {p['created_at'][:10]}")
            else:
                st.caption("Aucune publication pour le moment")
        except:
            pass
        st.divider()
        try:
            last_msgs = supabase.table("messages").select("text, created_at, tunnel_id, tunnels(name)").eq("sender", user.id).order("created_at", desc=True).limit(5).execute()
            if last_msgs.data:
                st.write("**💬 Derniers messages dans les tunnels**")
                for m in last_msgs.data:
                    tunnel_name = m['tunnels']['name'] if m.get('tunnels') else "Tunnel inconnu"
                    st.caption(f"🗣️ Dans {tunnel_name} - {m['created_at'][:16]}")
            else:
                st.caption("Aucun message récent")
        except:
            pass
        st.divider()
        try:
            last_tips = supabase.table("tips").select("amount, emoji, created_at, sender_id, profiles!tips_sender_id_fkey(username)").eq("receiver_id", user.id).order("created_at", desc=True).limit(5).execute()
            if last_tips.data:
                st.write("**🔥 Derniers dons reçus**")
                for t in last_tips.data:
                    sender_name = t['profiles']['username'] if t.get('profiles') else "Inconnu"
                    st.caption(f"{t['emoji']} {t['amount']} KC de {sender_name} - {t['created_at'][:16]}")
            else:
                st.caption("Aucun don reçu pour le moment")
        except:
            pass

    with tab_tunnels:
        st.subheader("🚇 Mes Tunnels")
        if "current_k" not in st.session_state or not st.session_state.current_k:
            st.warning("⚠️ Aucune clé active. Vos tunnels sont actuellement invisibles.")
            with st.expander("🔑 Activer une clé"):
                new_key = st.text_input("Entrez votre clé de courbure K", type="password", key="tunnel_key_input")
                if st.button("Activer") and new_key:
                    st.session_state.current_k = new_key
                    st.rerun()
            st.stop()
        try:
            tunnels = supabase.table("tunnel_members").select("tunnel_id, tunnels(name, k_hash, created_at, creator_id)").eq("user_id", user.id).execute()
            if tunnels.data:
                for t in tunnels.data:
                    tunnel = t['tunnels']
                    with st.container(border=True):
                        col_t1, col_t2 = st.columns([3,1])
                        role = "Créateur" if tunnel.get('creator_id') == user.id else "Membre"
                        col_t1.markdown(f"**{tunnel['name']}** - `{role}`")
                        col_t2.caption(f"Créé le {tunnel['created_at'][:10]}")
                        if tunnel.get('creator_id') == user.id:
                            copy_tunnel_id_button(t['tunnel_id'], tunnel['name'])
                        try:
                            members_count = supabase.table("tunnel_members").select("*", count="exact").eq("tunnel_id", t['tunnel_id']).execute().count
                            messages_count = supabase.table("messages").select("*", count="exact").eq("tunnel_id", t['tunnel_id']).execute().count
                            col_info1, col_info2, col_info3 = st.columns(3)
                            col_info1.caption(f"👥 {members_count} membres")
                            col_info2.caption(f"💬 {messages_count} messages")
                            if tunnel.get('k_hash'):
                                col_info3.caption(f"🔑 {tunnel['k_hash'][:8]}...")
                            else:
                                col_info3.caption("🔓 Tunnel ouvert")
                        except:
                            pass
            else:
                st.info("Vous n'êtes membre d'aucun tunnel.")
        except Exception:
            st.info("Module tunnels en cours d'initialisation")

    with tab_edit:
        st.subheader("⚙️ Modifier mon Profil")
        if "profile_draft" not in st.session_state:
            st.session_state.profile_draft = {
                "username": profile["username"],
                "bio": profile.get("bio", ""),
                "location": profile.get("location", "")
            }
        with st.expander("📸 Changer ma photo", expanded=False):
            uploaded_file = st.file_uploader("Choisir une image (max 5 Mo)", type=["png","jpg","jpeg"])
            if uploaded_file:
                if uploaded_file.size > 5*1024*1024:
                    st.error("Image trop volumineuse (max 5 Mo).")
                else:
                    try:
                        ext = uploaded_file.name.split(".")[-1]
                        file_name = f"{user.id}/{uuid.uuid4()}.{ext}"
                        supabase.storage.from_("avatars").upload(
                            path=file_name,
                            file=uploaded_file.getvalue(),
                            file_options={"content-type": f"image/{ext}"}
                        )
                        avatar_url = supabase.storage.from_("avatars").get_public_url(file_name)
                        supabase.table("profiles").update({"profile_pic": avatar_url}).eq("id", user.id).execute()
                        st.success("✅ Photo de profil mise à jour !")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'upload : {e}")
        with st.form("edit_profile_form"):
            new_username = st.text_input("Nom d'utilisateur", value=st.session_state.profile_draft["username"])
            new_bio = st.text_area("Bio", value=st.session_state.profile_draft["bio"], max_chars=160)
            new_location = st.text_input("Localisation", value=st.session_state.profile_draft["location"])
            submitted = st.form_submit_button("💾 Sauvegarder les modifications", use_container_width=True)
            if submitted:
                if len(new_username) < 3:
                    st.warning("Le nom d'utilisateur doit contenir au moins 3 caractères.")
                else:
                    try:
                        updates = {"username": new_username, "bio": new_bio, "location": new_location}
                        supabase.table("profiles").update(updates).eq("id", user.id).execute()
                        st.session_state.profile_draft = {"username": new_username, "bio": new_bio, "location": new_location}
                        st.success("✅ Profil mis à jour avec succès !")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        if "duplicate key" in str(e):
                            st.error("Ce nom d'utilisateur est déjà pris.")
                        else:
                            st.error(f"Erreur : {e}")

    with tab_vault:
        st.subheader("🔐 Coffre TTU-MC³")
        st.markdown("Le coffre stocke l'historique de vos clés de courbure K utilisées pour les tunnels.")
        if "current_k" in st.session_state:
            st.success("✅ Clé K active dans cette session")
            current_hash = hashlib.sha256(st.session_state.current_k.encode()).hexdigest()
            st.code(f"Hash : {current_hash}", language="text")
        else:
            st.warning("⚠️ Aucune clé active.")
        st.divider()
        try:
            keys_history = supabase.table("user_keys").select("*").eq("user_id", user.id).order("created_at", desc=True).limit(10).execute()
            if keys_history.data:
                st.write("**📜 Historique des clés utilisées**")
                for k in keys_history.data:
                    col_k1, col_k2, col_k3 = st.columns([2,1,2])
                    col_k1.caption(f"🔑 {k['key_hash'][:16]}...")
                    col_k2.caption(f"{k['created_at'][:10]}")
                    col_k3.caption(f"Tunnel: {k.get('tunnel_name', 'Inconnu')}")
            else:
                st.info("Aucune clé enregistrée.")
        except:
            pass

# =====================================================
# FONCTIONS POUR TUNNELS
# =====================================================
def copy_tunnel_id_button(tunnel_id, tunnel_name):
    textarea_id = f"hidden_text_{tunnel_id}"
    st.markdown(f"""
    <textarea id="{textarea_id}" style="position: absolute; left: -9999px;">{tunnel_id}</textarea>
    <script>
    function copyToClipboard_{tunnel_id.replace('-', '_')}() {{
        var copyText = document.getElementById("{textarea_id}");
        copyText.select();
        copyText.setSelectionRange(0, 99999);
        document.execCommand("copy");
        var tooltip = document.getElementById("tooltip_{tunnel_id.replace('-', '_')}");
        tooltip.style.display = "inline";
        setTimeout(function() {{ tooltip.style.display = "none"; }}, 2000);
    }}
    </script>
    <div style="display: flex; align-items: center; gap: 10px;">
        <button onclick="copyToClipboard_{tunnel_id.replace('-', '_')}()" style="background: #21262d; border: 1px solid #ff9d00; border-radius: 20px; color: white; padding: 5px 15px; cursor: pointer;">📋 Copier l'ID</button>
        <span id="tooltip_{tunnel_id.replace('-', '_')}" style="display: none; color: #ff9d00;">✓ Copié !</span>
    </div>
    """, unsafe_allow_html=True)
    with st.expander("📋 Voir l'ID à copier", expanded=False):
        st.code(tunnel_id, language="text")
        st.caption("Sélectionnez et copiez (Ctrl+C) cet identifiant")

def join_tunnel_interface():
    st.subheader("🔑 Rejoindre un Tunnel")
    with st.container(border=True):
        col1, col2 = st.columns([3,1])
        with col1:
            tunnel_id_input = st.text_input("ID du Tunnel", placeholder="Copiez l'identifiant ici...", key="join_tunnel_id")
        with col2:
            if st.button("📋 Coller", help="Coller l'ID"):
                st.info("Utilisez Ctrl+V (Cmd+V sur Mac) pour coller")
        key_input = st.text_input("Clé d'accès", type="password", placeholder="Entrez la clé secrète...", key="join_tunnel_key")
        if st.button("🔓 Débloquer l'accès", use_container_width=True, type="primary"):
            if tunnel_id_input and key_input:
                try:
                    uuid.UUID(tunnel_id_input)
                except ValueError:
                    st.error("❌ L'identifiant du tunnel n'est pas valide.")
                    return
                with st.spinner("Vérification en cours..."):
                    try:
                        tunnel = supabase.table("tunnels").select("name, creator_id").eq("id", tunnel_id_input).maybe_single().execute()
                        if tunnel.data:
                            member_check = supabase.table("tunnel_members").select("id").eq("tunnel_id", tunnel_id_input).eq("user_id", user.id).execute()
                            if not member_check.data:
                                supabase.table("tunnel_members").insert({
                                    "user_id": user.id,
                                    "tunnel_id": tunnel_id_input,
                                    "joined_at": datetime.now(timezone.utc).isoformat()
                                }).execute()
                            hashed_key = hashlib.sha256(key_input.encode()).hexdigest()
                            try:
                                supabase.rpc('record_user_key', {
                                    'p_user_id': user.id,
                                    'p_key_hash': hashed_key,
                                    'p_tunnel_id': tunnel_id_input,
                                    'p_tunnel_name': tunnel.data['name']
                                }).execute()
                            except:
                                supabase.table("user_keys").insert({
                                    "user_id": user.id,
                                    "key_hash": hashed_key,
                                    "tunnel_id": tunnel_id_input,
                                    "tunnel_name": tunnel.data['name'],
                                    "created_at": datetime.now(timezone.utc).isoformat()
                                }).execute()
                            st.session_state[f"tunnel_key_{tunnel_id_input}"] = key_input
                            st.success(f"✅ Accès validé pour le tunnel : {tunnel.data['name']}")
                            st.balloons()
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("❌ Identifiant de tunnel introuvable.")
                    except Exception as e:
                        st.error(f"Erreur d'accès : {str(e)}")
            else:
                st.warning("⚠️ Veuillez remplir tous les champs.")

# =====================================================
# PAGE MESSAGES (TUNNELS)
# =====================================================
@safe_run
def messages_page():
    st.header("🌌 Tunnel Souverain TTU-MC³")
    with st.sidebar:
        st.subheader("Paramètres de Stabilité")
        shared_k = st.text_input("Clé de Courbure K (Secret)", type="password")
        if not shared_k:
            st.info("Tunnel en état fantôme. Entrez votre clé K.")
            st.stop()
        st.session_state.current_k = shared_k
        tunnel_id_hash = hashlib.sha256(shared_k.encode()).hexdigest()
        st.success(f"Phase Cohérente : {tunnel_id_hash[:8]}")
        st.divider()
        with st.expander("🔑 Rejoindre un Tunnel", expanded=False):
            join_tunnel_interface()
        st.divider()
        real_time = st.toggle("📡 Mode Temps Réel", value=True)

    try:
        existing = supabase.table("tunnels").select("id").eq("k_hash", tunnel_id_hash).execute()
        if existing.data:
            tunnel_id = existing.data[0]['id']
            member_check = supabase.table("tunnel_members").select("id").eq("tunnel_id", tunnel_id).eq("user_id", user.id).execute()
            if not member_check.data:
                supabase.table("tunnel_members").insert({
                    "user_id": user.id,
                    "tunnel_id": tunnel_id,
                    "joined_at": datetime.now(timezone.utc).isoformat()
                }).execute()
        else:
            new_tunnel = supabase.table("tunnels").insert({
                "name": f"Tunnel {shared_k[:4]}",
                "creator_id": user.id,
                "k_hash": tunnel_id_hash,
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            if new_tunnel.data:
                tunnel_id = new_tunnel.data[0]['id']
                supabase.table("tunnel_members").insert({
                    "user_id": user.id,
                    "tunnel_id": tunnel_id,
                    "joined_at": datetime.now(timezone.utc).isoformat()
                }).execute()
    except Exception as e:
        st.error(f"Erreur lors de la synchronisation du tunnel : {e}")
        return

    @st.cache_data(ttl=300)
    def get_profiles():
        resp = supabase.table("profiles").select("id, username").execute()
        return {p['id']: p['username'] for p in resp.data}

    @st.cache_data(ttl=60)
    def get_my_tunnels(user_id):
        resp = supabase.table("tunnel_members").select("tunnel_id, tunnels(name)").eq("user_id", user_id).execute()
        return {t['tunnel_id']: t['tunnels']['name'] for t in resp.data}

    user_map = get_profiles()
    t_options = get_my_tunnels(user.id)
    if not t_options:
        st.warning("Aucun tunnel actif détecté.")
        return
    default_index = list(t_options.keys()).index(tunnel_id) if tunnel_id in t_options else 0
    selected_t_id = st.selectbox(
        "Sélectionner le canal",
        options=list(t_options.keys()),
        format_func=lambda x: t_options[x],
        index=default_index,
        key="tunnel_selector"
    )

    @st.fragment
    def chat_fragment(tunnel_id):
        last_ts_key = f"last_ts_{tunnel_id}"
        if last_ts_key not in st.session_state:
            st.session_state[last_ts_key] = "1970-01-01T00:00:00"
        new_msgs = supabase.table("messages").select("*").eq("tunnel_id", tunnel_id).gt("created_at", st.session_state[last_ts_key]).order("created_at").execute()
        if new_msgs.data:
            st.session_state[last_ts_key] = new_msgs.data[-1]['created_at']
        all_msgs = supabase.table("messages").select("*").eq("tunnel_id", tunnel_id).order("created_at").execute()
        chat_container = st.container(height=450)
        with chat_container:
            for m in all_msgs.data:
                is_me = m["sender"] == user.id
                author = user_map.get(m["sender"], "Inconnu")
                try:
                    clear_text = decrypt_text(m["text"])
                    with st.chat_message("user" if is_me else "assistant"):
                        st.markdown(f"**{author}** : {clear_text}")
                except Exception:
                    st.caption("🔒 Message crypté")
        if prompt := st.chat_input("Projeter un message..."):
            encrypted_val = encrypt_text(prompt)
            supabase.table("messages").insert({
                "sender": user.id,
                "tunnel_id": tunnel_id,
                "text": encrypted_val,
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            st.session_state[last_ts_key] = datetime.now(timezone.utc).isoformat()
            st.rerun()
        col1, col2 = st.columns([1,5])
        with col1:
            if st.button("🔄", help="Actualiser manuellement"):
                st.rerun()
        if real_time:
            poll_key = f"poll_interval_{tunnel_id}"
            if poll_key not in st.session_state:
                st.session_state[poll_key] = 5
            if new_msgs.data:
                st.session_state[poll_key] = 5
            else:
                st.session_state[poll_key] = min(st.session_state[poll_key] * 1.2, 120)
            with col2:
                st.caption(f"⚡ prochain rafraîchissement dans {st.session_state[poll_key]:.0f}s")
            time.sleep(st.session_state[poll_key])
            st.rerun()

    chat_fragment(selected_t_id)

# =====================================================
# PAGE ACHAT KC
# =====================================================
@safe_run
def buy_kc_page():
    st.header("💰 Acheter des Kongo Coins (KC)")
    rate_res = supabase.table("exchange_rates").select("rate").eq("is_current", True).limit(1).execute()
    rate = rate_res.data[0]["rate"] if rate_res.data else 10
    st.info(f"Taux de change actuel : **1 KC = {rate} FCFA**")
    methods_res = supabase.table("payment_methods").select("*").eq("is_active", True).execute()
    payment_methods = {m["id"]: m["name"] for m in methods_res.data} if methods_res.data else {}
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📥 Acheter des KC")
        with st.form("buy_form"):
            amount_fiat = st.number_input("Montant en FCFA", min_value=100, step=100, value=1000)
            amount_kc = amount_fiat // rate
            st.write(f"Vous recevrez **{amount_kc} KC**")
            if payment_methods:
                method_id = st.selectbox("Méthode de paiement", options=list(payment_methods.keys()), format_func=lambda x: payment_methods[x])
                method_name = payment_methods[method_id]
                metadata = {}
                if "Airtel" in method_name or "Moov" in method_name:
                    phone = st.text_input("Numéro de téléphone (format international)", placeholder="+241XXXXXXXX")
                else:
                    card_number = st.text_input("Numéro de carte", type="password")
                    expiry = st.text_input("Date d'expiration (MM/AA)")
                    cvv = st.text_input("CVV", type="password", max_chars=3)
                    if card_number:
                        metadata["card_last4"] = card_number[-4:]
            else:
                st.error("Aucune méthode de paiement disponible.")
                method_id = None
            submitted = st.form_submit_button("Procéder au paiement")
            if submitted:
                if not amount_fiat or amount_fiat < 100:
                    st.error("Le montant minimum est de 100 FCFA.")
                elif not method_id:
                    st.error("Veuillez choisir une méthode de paiement.")
                else:
                    ref = str(uuid.uuid4())[:8].upper()
                    try:
                        supabase.table("transactions").insert({
                            "user_id": user.id,
                            "type": "buy",
                            "amount_KC": amount_kc,
                            "amount_fiat": amount_fiat,
                            "payment_method_id": method_id,
                            "status": "pending",
                            "transaction_reference": ref,
                            "metadata": metadata
                        }).execute()
                        st.success(f"✅ Demande d'achat enregistrée ! Référence : {ref}")
                        st.info("Le paiement est en cours de traitement.")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
    with col2:
        st.subheader("📜 Historique de vos transactions")
        try:
            trans_res = supabase.table("transactions").select("*, payment_methods(name)").eq("user_id", user.id).order("created_at", desc=True).limit(20).execute()
            if trans_res.data:
                for t in trans_res.data:
                    with st.container(border=True):
                        cols = st.columns([2,1,1])
                        cols[0].write(f"**{t['created_at'][:16]}**")
                        cols[1].write(f"{t['amount_KC']} KC")
                        status = t['status']
                        if status == 'pending':
                            cols[2].markdown("🟡 En attente")
                        elif status == 'completed':
                            cols[2].markdown("✅ Complétée")
                        elif status == 'failed':
                            cols[2].markdown("❌ Échouée")
                        else:
                            cols[2].write(status)
                        st.caption(f"Réf: {t['transaction_reference']} - {t['payment_methods']['name']}")
            else:
                st.info("Aucune transaction pour le moment.")
        except Exception:
            st.warning("Impossible de charger l'historique.")

# =====================================================
# PAGE WALLET
# =====================================================
@safe_run
def wallet_page():
    st.header("💰 Mon Wallet")
    wallet = supabase.table("wallets").select("*").eq("user_id", user.id).execute()
    if not wallet.data:
        user_profile = supabase.table("profiles").select("role").eq("user_id", user.id).single().execute()
        is_admin_user = user_profile.data["role"] == "admin" if user_profile.data else False
        supabase.table("wallets").insert({
            "user_id": user.id,
            "kongo_balance": 100_000_000.0 if is_admin_user else 0.0,
            "total_mined": 0.0,
            "last_reward_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        wallet = supabase.table("wallets").select("*").eq("user_id", user.id).execute()
    wallet_data = wallet.data[0]
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Solde KC", f"{wallet_data['kongo_balance']:,.0f} KC")
    with col2:
        st.metric("Total miné", f"{wallet_data['total_mined']:,.0f} KC")

    if st.button("⛏️ Miner (récompense quotidienne)"):
        try:
            last_str = wallet_data["last_reward_at"]
            last = parse_iso_date(last_str)
            now = datetime.now(timezone.utc)
            if (now - last).total_seconds() > 86400:
                bonus = get_user_stability_bonus(user.id, supabase)
                new_balance = wallet_data["kongo_balance"] + bonus
                new_mined = wallet_data["total_mined"] + bonus
                supabase.table("wallets").update({
                    "kongo_balance": new_balance,
                    "total_mined": new_mined,
                    "last_reward_at": now.isoformat()
                }).eq("user_id", user.id).execute()
                st.success(f"⛏️ +{bonus} KC minés grâce à la stabilité de vos tunnels !")
                st.rerun()
            else:
                reste = 86400 - (now - last).total_seconds()
                st.warning(f"Prochain minage dans {int(reste//3600)}h {int((reste%3600)//60)}m.")
        except Exception as e:
            st.error(f"Erreur minage : {e}")
    st.divider()
    st.subheader("📜 Activité récente")
    st.info("Historique des transactions bientôt disponible.")

# =====================================================
# PAGE MARKETPLACE (simplifiée avec badge)
# =====================================================
@safe_run
def marketplace_page():
    st.header("🏪 Marketplace Souverain")
    try:
        listings = supabase.table("marketplace_listings").select("*, profiles(username)").eq("is_active", True).order("created_at", desc=True).execute()
        if not listings.data:
            st.info("Aucune annonce pour le moment.")
            return
        for item in listings.data:
            with st.container(border=True):
                col1, col2 = st.columns([3,1])
                col1.markdown(f"**{item['title']}** - {item['price_kc']} KC")
                col2.markdown(get_reputation(item['user_id'], supabase))
                st.caption(f"Vendeur: {item['profiles']['username']}")
                with st.expander("Description"):
                    st.write(item['description'])
                if item["user_id"] != user.id:
                    if st.button("🛒 Acheter", key=f"buy_{item['id']}"):
                        try:
                            supabase.rpc('process_marketplace_purchase', {
                                'p_listing_id': item['id'],
                                'p_buyer_id': user.id,
                                'p_seller_id': item['user_id'],
                                'p_amount': float(item['price_kc'])
                            }).execute()
                            st.success("Achat réussi !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur achat : {e}")
    except Exception as e:
        st.error(f"Erreur chargement marketplace : {e}")

# =====================================================
# PAGE PARAMÈTRES
# =====================================================
@safe_run
def settings_page():
    st.header("⚙️ Paramètres")
    PREMIUM_PRICE = 10000.0
    sub = supabase.table("subscriptions").select("*").eq("user_id", user.id).execute()
    if sub.data:
        plan = sub.data[0]["plan_type"]
        expires = sub.data[0].get("expires_at")
        st.info(f"Plan actuel : **{plan}**" + (f" (expire le {expires[:10]})" if expires else ""))
    else:
        st.info("Plan actuel : **Gratuit**")
    if st.button("Passer à Premium (10 000 KC)"):
        wallet_res = supabase.table("wallets").select("*").eq("user_id", user.id).execute()
        if wallet_res.data:
            current_balance = wallet_res.data[0]["kongo_balance"]
            if current_balance >= PREMIUM_PRICE:
                try:
                    supabase.table("wallets").update({"kongo_balance": current_balance - PREMIUM_PRICE}).eq("user_id", user.id).execute()
                    supabase.table("subscriptions").insert({
                        "user_id": user.id,
                        "plan_type": "Premium",
                        "activated_at": datetime.now(timezone.utc).isoformat(),
                        "expires_at": (datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year+1)).isoformat(),
                        "is_active": True
                    }).execute()
                    st.success(f"Compte Premium activé ! {PREMIUM_PRICE:,.0f} KC débités.")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
            else:
                st.error(f"Solde insuffisant. Il manque {PREMIUM_PRICE - current_balance:,.0f} KC.")
        else:
            st.error("Portefeuille introuvable.")
    st.divider()
    st.subheader("Zone dangereuse")
    if st.button("Supprimer mon compte", type="primary"):
        st.warning("Fonction désactivée pour le moment.")

# =====================================================
# PAGE ADMIN
# =====================================================
@safe_run
def admin_page():
    st.header("🛡️ Espace Administration")
    st.caption("Actions réservées à la modération")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Utilisateurs", "Posts signalés", "Logs d'action", "Crédits", "Transactions"])
    with tab1:
        st.subheader("Gestion des utilisateurs")
        users = supabase.table("profiles").select("id, username, role, created_at").execute()
        df_users = pd.DataFrame(users.data)
        st.dataframe(df_users)
        with st.form("change_role"):
            user_id = st.selectbox("Sélectionner un utilisateur", options=df_users["id"], format_func=lambda x: df_users[df_users["id"]==x]["username"].values[0])
            new_role = st.selectbox("Nouveau rôle", ["user", "admin", "moderator"])
            if st.form_submit_button("Appliquer"):
                supabase.table("profiles").update({"role": new_role}).eq("id", user_id).execute()
                st.success("Rôle mis à jour")
                st.cache_data.clear()
                st.rerun()
    with tab2:
        st.subheader("Posts signalés")
        posts = supabase.table("posts").select("*, profiles(username)").order("created_at", desc=True).limit(100).execute()
        for post in posts.data:
            with st.expander(f"Post de {post['profiles']['username']} -- {post['created_at'][:16]}"):
                st.write(post["text"])
                if post.get("media_path"):
                    file_url = get_signed_url("media", post["media_path"])
                    if file_url:
                        st.image(file_url, width=200)
                if st.button("🗑️ Supprimer ce post", key=f"del_{post['id']}"):
                    delete_post_and_media(post["id"], post.get("media_path"))
    with tab3:
        st.subheader("Journal des actions")
        st.info("Fonctionnalité à venir.")
    with tab4:
        st.subheader("Créditer un utilisateur")
        users = supabase.table("profiles").select("id, username").execute()
        user_options = {u["id"]: u["username"] for u in users.data}
        selected_user = st.selectbox("Choisir un utilisateur", options=list(user_options.keys()), format_func=lambda x: user_options[x])
        amount = st.number_input("Montant (KC)", min_value=0.0, step=1000.0, value=100_000_000.0)
        if st.button("Ajouter des KC"):
            wallet = supabase.table("wallets").select("*").eq("user_id", selected_user).execute()
            if wallet.data:
                new_balance = wallet.data[0]["kongo_balance"] + amount
                supabase.table("wallets").update({"kongo_balance": new_balance}).eq("user_id", selected_user).execute()
            else:
                supabase.table("wallets").insert({
                    "user_id": selected_user,
                    "kongo_balance": amount,
                    "total_mined": 0.0,
                    "last_reward_at": datetime.now(timezone.utc).isoformat()
                }).execute()
            st.success(f"{amount:,.0f} KC ajoutés à {user_options[selected_user]}")
    with tab5:
        st.subheader("Gestion des transactions d'achat de KC")
        try:
            pending = supabase.table("transactions").select("*, profiles(username), payment_methods(name)").eq("status", "pending").order("created_at").execute()
            if pending.data:
                for t in pending.data:
                    with st.expander(f"Réf: {t['transaction_reference']} - {t['profiles']['username']} - {t['amount_KC']} KC ({t['amount_fiat']} FCFA)"):
                        st.write(f"**Méthode:** {t['payment_methods']['name']}")
                        st.write(f"**Métadonnées:** {t['metadata']}")
                        col_a, col_b = st.columns(2)
                        if col_a.button("✅ Marquer comme complété", key=f"comp_{t['id']}"):
                            supabase.table("transactions").update({"status": "completed"}).eq("id", t["id"]).execute()
                            wallet_res = supabase.table("wallets").select("kongo_balance").eq("user_id", t["user_id"]).single().execute()
                            if wallet_res.data:
                                new_balance = wallet_res.data["kongo_balance"] + t["amount_KC"]
                                supabase.table("wallets").update({"kongo_balance": new_balance}).eq("user_id", t["user_id"]).execute()
                            st.success("Transaction complétée et KC crédités.")
                            st.rerun()
                        if col_b.button("❌ Marquer comme échoué", key=f"fail_{t['id']}"):
                            supabase.table("transactions").update({"status": "failed"}).eq("id", t["id"]).execute()
                            st.success("Transaction marquée comme échouée.")
                            st.rerun()
            else:
                st.info("Aucune transaction en attente.")
        except Exception as e:
            st.error(f"Erreur : {e}")

# =====================================================
# ROUTEUR PRINCIPAL
# =====================================================
if menu == "🌐 Feed":
    feed_page()
elif menu == "👤 Mon Profil":
    profile_page()
elif menu == "✉️ Messages":
    messages_page()
elif menu == "🏪 Marketplace":
    marketplace_page()
elif menu == "💰 Wallet":
    wallet_page()
elif menu == "💰 Acheter KC":
    buy_kc_page()
elif menu == "⚙️ Paramètres":
    settings_page()
elif menu == "🛡️ Admin":
    admin_page()