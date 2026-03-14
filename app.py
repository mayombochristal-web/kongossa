import streamlit as st
from supabase import create_client
import pandas as pd
import time
from datetime import datetime, timedelta
import uuid
import hashlib
import hmac
import base64
from cryptography.fernet import Fernet
import cv2
import numpy as np
from PIL import Image, ImageFilter
import io
import random

# =====================================================
# CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="GEN-Z GABON • SOCIAL NETWORK",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# INITIALISATION SUPABASE & FERNET
# =====================================================
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

@st.cache_resource
def get_fernet():
    key = st.secrets.get("fernet_key")
    if not key:
        st.error("🔴 Clé Fernet manquante dans les secrets. Ajoutez 'fernet_key'.")
        st.stop()
    return Fernet(key.encode())

fernet = get_fernet()

# =====================================================
# INITIALISATION DES CADEAUX (à exécuter une fois)
# =====================================================
def init_gift_definitions():
    """Insère les 10 cadeaux thématiques dans la table gift_definitions si elle est vide."""
    gifts = [
        {"name": "Atome d'Ogooué", "emoji": "💧", "kc_cost": 50, "animation_type": "particle", "ttu_impact": 0.1},
        {"name": "Masque Punu", "emoji": "🎭", "kc_cost": 100, "animation_type": "full_screen", "ttu_impact": 0.2},
        {"name": "Torche d'Ozavigui", "emoji": "🔥", "kc_cost": 75, "animation_type": "particle", "ttu_impact": 0.15},
        {"name": "Pierre de Mbigou", "emoji": "🪨", "kc_cost": 120, "animation_type": "wave", "ttu_impact": 0.25},
        {"name": "Danse du Ndjembè", "emoji": "💃", "kc_cost": 150, "animation_type": "full_screen", "ttu_impact": 0.3},
        {"name": "Tambour de l'Unité", "emoji": "🥁", "kc_cost": 80, "animation_type": "wave", "ttu_impact": 0.15},
        {"name": "Émeraude de l'Ivindo", "emoji": "💎", "kc_cost": 200, "animation_type": "full_screen", "ttu_impact": 0.4},
        {"name": "Vol du Perroquet Gris", "emoji": "🦜", "kc_cost": 90, "animation_type": "particle", "ttu_impact": 0.2},
        {"name": "Lion du Mayombé", "emoji": "🦁", "kc_cost": 300, "animation_type": "full_screen", "ttu_impact": 0.5},
        {"name": "Porte de l'Oracle", "emoji": "⛩️", "kc_cost": 500, "animation_type": "full_screen", "ttu_impact": 1.0}
    ]
    for g in gifts:
        existing = supabase.table("gift_definitions").select("id").eq("name", g["name"]).execute()
        if not existing.data:
            supabase.table("gift_definitions").insert(g).execute()

init_gift_definitions()

# =====================================================
# FONCTIONS DE CHIFFREMENT / DÉCHIFFREMENT AVEC SEL DYNAMIQUE
# =====================================================
def get_user_specific_fernet(sender_id: str):
    base_key = st.secrets["fernet_key"].encode()
    salt = hashlib.sha256(sender_id.encode()).digest()
    derived = hashlib.sha256(base_key + salt).digest()[:32]
    derived_key = base64.urlsafe_b64encode(derived)
    return Fernet(derived_key)

def encrypt_private_message(plain_text: str, sender_id: str) -> str:
    if not plain_text:
        return ""
    user_fernet = get_user_specific_fernet(sender_id)
    encrypted = user_fernet.encrypt(plain_text.encode())
    return base64.b64encode(encrypted).decode()

def decrypt_private_message(encrypted_b64: str, sender_id: str) -> str:
    if not encrypted_b64:
        return ""
    try:
        user_fernet = get_user_specific_fernet(sender_id)
        encrypted = base64.b64decode(encrypted_b64)
        return user_fernet.decrypt(encrypted).decode()
    except Exception:
        return "🔒 [Message illisible -- clé invalide]"

# =====================================================
# FONCTIONS DE HASH (admin)
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

# =====================================================
# GESTION DE L'AUTHENTIFICATION
# =====================================================
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
                    # Mise à jour last_seen
                    supabase.table("profiles").update({"last_seen": datetime.now().isoformat()}).eq("id", res.user.id).execute()
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
                    res = supabase.auth.sign_up({
                        "email": new_email,
                        "password": new_password
                    })
                    user = res.user
                    if not user:
                        st.error("La création du compte a échoué.")
                        return

                    role = "admin" if verify_admin_code(new_email, admin_code) else "user"

                    profile_data = {
                        "id": user.id,
                        "username": username,
                        "bio": "",
                        "location": "",
                        "profile_pic": "",
                        "role": role,
                        "created_at": datetime.now().isoformat(),
                        "last_seen": datetime.now().isoformat(),
                        "donation_level": 0,
                        "total_donations": 0
                    }
                    supabase.table("profiles").insert(profile_data).execute()

                    # Création du wallet avec bonus admin
                    initial_balance = 100_000_000.0 if role == "admin" else 0.0
                    supabase.table("wallets").insert({
                        "user_id": user.id,
                        "kongo_balance": initial_balance,
                        "total_mined": 0.0,
                        "last_reward_at": datetime.now().isoformat()
                    }).execute()

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

# Mise à jour de la présence (last_seen)
supabase.table("profiles").update({"last_seen": datetime.now().isoformat()}).eq("id", user.id).execute()

# =====================================================
# CHARGEMENT DU PROFIL
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
        st.error("Impossible de charger votre profil. Veuillez réessayer.")
        logout()

def is_admin():
    return profile and profile.get("role") == "admin"

# =====================================================
# FONCTIONS POUR LES UTILISATEURS EN LIGNE
# =====================================================
def get_online_users(threshold_minutes=5):
    cutoff = (datetime.now() - timedelta(minutes=threshold_minutes)).isoformat()
    res = supabase.table("profiles").select("id, username, profile_pic").gte("last_seen", cutoff).execute()
    return res.data if res.data else []

# =====================================================
# FONCTIONS D'ABONNEMENT (FOLLOW)
# =====================================================
def follow_user(follower_id, followed_id):
    try:
        supabase.table("follows").insert({
            "follower": follower_id,
            "followed": followed_id
        }).execute()
        return True
    except Exception:
        return False

def unfollow_user(follower_id, followed_id):
    supabase.table("follows").delete().eq("follower", follower_id).eq("followed", followed_id).execute()
    return True

def is_following(follower_id, followed_id):
    res = supabase.table("follows").select("*").eq("follower", follower_id).eq("followed", followed_id).execute()
    return len(res.data) > 0

# =====================================================
# FONCTIONS POUR LE PARTAGE DE POST
# =====================================================
def share_post(original_post_id, sharer_id, comment=""):
    orig = supabase.table("posts").select("*, profiles!inner(username)").eq("id", original_post_id).single().execute()
    if not orig.data:
        return False
    original = orig.data
    share_text = f"🔁 Partage de @{original['profiles']['username']} :\n\n{original['text']}"
    if comment:
        share_text = f"{comment}\n\n{share_text}"
    post_data = {
        "user_id": sharer_id,
        "text": share_text,
        "media_path": None,
        "media_type": None,
        "shared_post_id": original_post_id,
        "created_at": datetime.now().isoformat()
    }
    supabase.table("posts").insert(post_data).execute()
    return True

# =====================================================
# FONCTIONS TTU : GÉNÉRATION DES COUCHES SPECTRALES
# =====================================================
def generate_ttu_layers(media_bytes):
    try:
        with open("temp_media", "wb") as f:
            f.write(media_bytes)
        cap = cv2.VideoCapture("temp_media")
        ret, frame = cap.read()
        cap.release()
        if ret:
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        else:
            img = Image.open(io.BytesIO(media_bytes))
        img.thumbnail((64, 64))
        img_blur = img.filter(ImageFilter.GaussianBlur(radius=2))
        buffer = io.BytesIO()
        img_blur.save(buffer, format="JPEG", quality=30)
        thumb_bytes = buffer.getvalue()
        spectral_density = float(np.var(np.array(img)) / 1000.0)
        return thumb_bytes, spectral_density
    except Exception as e:
        print(f"Erreur TTU : {e}")
        return None, 1.0

# =====================================================
# FONCTIONS POUR LES STREAMS ET CADEAUX (avec combo et jauge)
# =====================================================
def create_stream(title, description, video_file):
    user_id = user.id
    stream_id = str(uuid.uuid4())
    file_ext = video_file.name.split(".")[-1]
    file_name = f"streams/{user_id}/{stream_id}.{file_ext}"
    supabase.storage.from_("streams").upload(
        path=file_name,
        file=video_file.getvalue(),
        file_options={"content-type": video_file.type}
    )
    thumb_bytes, spectral_density = generate_ttu_layers(video_file.getvalue())
    thumb_name = f"streams/{user_id}/{stream_id}_thumb.jpg"
    supabase.storage.from_("streams").upload(
        path=thumb_name,
        file=thumb_bytes,
        file_options={"content-type": "image/jpeg"}
    )
    thumb_url = supabase.storage.from_("streams").get_public_url(thumb_name)
    supabase.table("ttu_streams").insert({
        "id": stream_id,
        "user_id": user_id,
        "title": title,
        "description": description,
        "stream_key": str(uuid.uuid4()),
        "current_viewer_count": 0,
        "resonance_score": 0.0,
        "stability_gauge": 0.0,
        "phi_m_core_url": thumb_url,
        "video_url": supabase.storage.from_("streams").get_public_url(file_name),
        "is_active": True,
        "created_at": datetime.now().isoformat()
    }).execute()
    return stream_id

def check_and_trigger_combo(stream_id, gift_id, sender_id):
    cutoff = (datetime.now() - timedelta(seconds=10)).isoformat()
    recent = supabase.table("stream_gifts").select("*").eq("stream_id", stream_id).eq("gift_id", gift_id).gte("created_at", cutoff).execute()
    if len(recent.data) >= 3:
        viewers = get_online_users(threshold_minutes=2)
        for v in viewers:
            wallet = supabase.table("wallets").select("*").eq("user_id", v["id"]).execute()
            if wallet.data:
                new_bal = wallet.data[0]["kongo_balance"] + 10
                supabase.table("wallets").update({"kongo_balance": new_bal}).eq("user_id", v["id"]).execute()
        supabase.table("stream_chat").insert({
            "stream_id": stream_id,
            "user_id": None,
            "message": "🎉 COMBO TRIADIQUE ! Une pluie de 10 KC pour tous les viewers !",
            "created_at": datetime.now().isoformat()
        }).execute()
        return True
    return False

def send_gift(stream_id, gift_id):
    gift = supabase.table("gift_definitions").select("*").eq("id", gift_id).single().execute()
    if not gift.data:
        st.error("Cadeau inconnu.")
        return False
    gift = gift.data
    cost = gift["kc_cost"]
    wallet = supabase.table("wallets").select("*").eq("user_id", user.id).execute()
    if not wallet.data or wallet.data[0]["kongo_balance"] < cost:
        st.error("Solde insuffisant.")
        return False
    new_balance = wallet.data[0]["kongo_balance"] - cost
    supabase.table("wallets").update({"kongo_balance": new_balance}).eq("user_id", user.id).execute()
    supabase.table("stream_gifts").insert({
        "stream_id": stream_id,
        "sender_id": user.id,
        "gift_id": gift_id,
        "combo_count": 1,
        "created_at": datetime.now().isoformat()
    }).execute()
    profile = supabase.table("profiles").select("total_donations, donation_level").eq("id", user.id).single().execute()
    new_total = profile.data["total_donations"] + cost
    new_level = int(new_total / 1000)
    supabase.table("profiles").update({
        "total_donations": new_total,
        "donation_level": new_level
    }).eq("id", user.id).execute()
    stream = supabase.table("ttu_streams").select("stability_gauge").eq("id", stream_id).single().execute()
    new_gauge = min(100, stream.data["stability_gauge"] + gift["ttu_impact"] * 10)
    supabase.table("ttu_streams").update({"stability_gauge": new_gauge}).eq("id", stream_id).execute()
    check_and_trigger_combo(stream_id, gift_id, user.id)
    if gift["animation_type"] == "full_screen":
        st.balloons()
    elif gift["animation_type"] == "particle":
        st.snow()
    elif gift["animation_type"] == "wave":
        st.toast("🌊 Effet de vague !")
    return True

def get_donor_badge(level):
    if level == 0:
        return ""
    elif level < 5:
        return "⭐"
    elif level < 10:
        return "🌟"
    elif level < 20:
        return "💫"
    else:
        return "👑"

# =====================================================
# FONCTIONS POUR LES ÉMOJIS PREMIUM
# =====================================================
EMOJI_HIERARCHY = {
    "🔥": {"label": "Hype", "cost": 10, "share": 8, "color": "#FF5722"},
    "💎": {"label": "Pépite", "cost": 50, "share": 40, "color": "#4CAF50"},
    "👑": {"label": "Légende", "cost": 100, "share": 80, "color": "#FFC107"}
}

def display_emoji_buttons(post_id, author_id):
    cols = st.columns(len(EMOJI_HIERARCHY))
    for i, (emoji, info) in enumerate(EMOJI_HIERARCHY.items()):
        with cols[i]:
            if st.button(
                f"{emoji} {info['cost']} KC",
                key=f"emoji_{post_id}_{emoji}",
                help=info['label'],
                use_container_width=True
            ):
                process_emoji_payment(post_id, author_id, emoji)

def process_emoji_payment(post_id, author_id, emoji_type):
    cost = EMOJI_HIERARCHY[emoji_type]["cost"]
    share = EMOJI_HIERARCHY[emoji_type]["share"]
    wallet_res = supabase.table("wallets").select("kongo_balance").eq("user_id", user.id).execute()
    if not wallet_res.data:
        st.error("Portefeuille introuvable.")
        return
    wallet = wallet_res.data[0]
    if wallet["kongo_balance"] < cost:
        st.error(f"Solde insuffisant. Il vous manque {cost - wallet['kongo_balance']} KC.")
        return
    try:
        new_bal = wallet["kongo_balance"] - cost
        supabase.table("wallets").update({"kongo_balance": new_bal}).eq("user_id", user.id).execute()
        author_wallet_res = supabase.table("wallets").select("kongo_balance").eq("user_id", author_id).execute()
        if author_wallet_res.data:
            author_wallet = author_wallet_res.data[0]
            new_author_bal = author_wallet["kongo_balance"] + share
            supabase.table("wallets").update({"kongo_balance": new_author_bal}).eq("user_id", author_id).execute()
        supabase.table("reactions").insert({
            "post_id": post_id,
            "user_id": user.id,
            "emoji": emoji_type,
            "cost": cost
        }).execute()
        st.success(f"Réaction {emoji_type} envoyée !")
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.error(f"Erreur lors du traitement de la réaction : {e}")

# =====================================================
# AUTRES FONCTIONS UTILES
# =====================================================
def like_post(post_id):
    try:
        supabase.table("likes").insert({
            "post_id": post_id,
            "user_id": user.id
        }).execute()
        st.success("👍 Like ajouté !")
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.error("Vous avez déjà liké ce post ou une erreur est survenue.")

def add_comment(post_id, text):
    if not text.strip():
        st.warning("Le commentaire ne peut pas être vide.")
        return
    supabase.table("comments").insert({
        "post_id": post_id,
        "user_id": user.id,
        "text": text
    }).execute()
    st.success("💬 Commentaire ajouté")
    time.sleep(0.5)
    st.rerun()

def delete_post(post_id):
    try:
        post = supabase.table("posts").select("media_path").eq("id", post_id).execute()
        if post.data and post.data[0].get("media_path"):
            supabase.storage.from_("media").remove([post.data[0]["media_path"]])
        supabase.table("posts").delete().eq("id", post_id).execute()
        st.success("Post supprimé")
        st.rerun()
    except Exception as e:
        st.error(f"Erreur lors de la suppression : {e}")

def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    try:
        res = supabase.storage.from_(bucket).create_signed_url(path, expires_in)
        return res['signedURL']
    except Exception:
        return None

def get_post_stats(post_id):
    likes_res = supabase.table("likes").select("*", count="exact").eq("post_id", post_id).execute()
    likes_count = likes_res.count if likes_res.count else 0
    comments_res = supabase.table("comments").select("*", count="exact").eq("post_id", post_id).execute()
    comments_count = comments_res.count if comments_res.count else 0
    reactions_res = supabase.table("reactions").select("*", count="exact").eq("post_id", post_id).execute()
    reactions_count = reactions_res.count if reactions_res.count else 0
    return {"likes": likes_count, "comments": comments_count, "reactions": reactions_count}

# =====================================================
# NAVIGATION (SIDEBAR)
# =====================================================
st.sidebar.image("https://via.placeholder.com/150x50?text=GEN-Z", width=150)
badge = get_donor_badge(profile.get("donation_level", 0))
st.sidebar.write(f"Connecté en tant que : **{profile['username']}** {badge}")
if is_admin():
    st.sidebar.markdown("🔑 **Administrateur**")
st.sidebar.write(f"ID : {user.id[:8]}...")

with st.sidebar.expander("🟢 En ligne", expanded=False):
    online = get_online_users()
    if online:
        for u in online[:10]:
            st.write(f"• {u['username']}")
        if len(online) > 10:
            st.write(f"... et {len(online)-10} autres")
    else:
        st.write("Aucun utilisateur en ligne")

menu_options = [
    "🌐 Feed",
    "🎥 TTU Feed",
    "👤 Mon Profil",
    "✉️ Messages",
    "🏪 Marketplace",
    "💰 Wallet",
    "🎥 TTU Live",
    "💬 Panels",
    "⚙️ Paramètres"
]
if is_admin():
    menu_options.append("🛡️ Admin")

menu = st.sidebar.radio("Navigation", menu_options)
if st.sidebar.button("🚪 Déconnexion"):
    logout()

# =====================================================
# PAGE : FEED CLASSIQUE (avec émojis améliorés)
# =====================================================
def feed_page():
    st.header("🌐 Fil d'actualité")

    with st.expander("✍️ Créer un post", expanded=False):
        with st.form("new_post"):
            post_text = st.text_area("Quoi de neuf ?")
            media_file = st.file_uploader("Image / Vidéo / Audio", type=["png", "jpg", "jpeg", "mp4", "mp3", "wav"])
            submitted = st.form_submit_button("Publier")
            if submitted and (post_text or media_file):
                if media_file and media_file.size > 50 * 1024 * 1024:
                    st.error("Le fichier est trop volumineux (max 50 Mo).")
                    st.stop()
                try:
                    media_path = None
                    media_type = None
                    ttu_thumb = None
                    spectral_density = 1.0
                    if media_file:
                        ext = media_file.name.split(".")[-1]
                        file_name = f"posts/{user.id}/{uuid.uuid4()}.{ext}"
                        if ext.lower() in ["mp3", "wav"]:
                            content_type = "audio/mpeg" if ext == "mp3" else "audio/wav"
                        elif ext.lower() in ["mp4"]:
                            content_type = "video/mp4"
                        else:
                            content_type = f"image/{ext}"
                        supabase.storage.from_("media").upload(
                            path=file_name,
                            file=media_file.getvalue(),
                            file_options={"content-type": content_type}
                        )
                        media_path = file_name
                        media_type = content_type
                        thumb_bytes, spectral_density = generate_ttu_layers(media_file.getvalue())
                        if thumb_bytes:
                            thumb_name = f"ttu/{user.id}/{uuid.uuid4()}_thumb.jpg"
                            supabase.storage.from_("media").upload(
                                path=thumb_name,
                                file=thumb_bytes,
                                file_options={"content-type": "image/jpeg"}
                            )
                            ttu_thumb = thumb_name
                    post_data = {
                        "user_id": user.id,
                        "text": post_text,
                        "media_path": media_path,
                        "media_type": media_type,
                        "created_at": datetime.now().isoformat(),
                        "is_spectral": ttu_thumb is not None,
                        "streaming_mode": "standard"
                    }
                    post_res = supabase.table("posts").insert(post_data).execute()
                    post_id = post_res.data[0]["id"]
                    if ttu_thumb:
                        supabase.table("ttu_spectral_metadata").insert({
                            "post_id": post_id,
                            "low_freq_thumb_url": ttu_thumb,
                            "spectral_density": spectral_density,
                            "coherence_vectors": {},
                            "dissipation_rate": 0.05,
                            "entropy_limit": 0.95
                        }).execute()
                    st.success("Post publié !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de la publication : {e}")

    posts = supabase.table("v_triadic_feed").select("*").order("created_at", desc=True).limit(50).execute()
    if not posts.data:
        st.info("Aucun post pour le moment. Sois le premier à poster !")
        return

    for post in posts.data:
        with st.container():
            col1, col2 = st.columns([1, 20])
            with col1:
                prof = supabase.table("profiles").select("username, profile_pic, donation_level").eq("id", post["user_id"]).single().execute()
                pic = prof.data.get("profile_pic") if prof.data else None
                if pic:
                    st.image(pic, width=40)
                else:
                    st.image("https://via.placeholder.com/40", width=40)
            with col2:
                username = prof.data["username"] if prof.data else "inconnu"
                badge = get_donor_badge(prof.data.get("donation_level", 0)) if prof.data else ""
                st.markdown(f"**{username}** {badge} · {post['created_at'][:10]}")
                st.write(post["text"])

                if post.get("media_path"):
                    file_url = get_signed_url("media", post["media_path"])
                    if file_url:
                        if post.get("media_type") and "image" in post["media_type"]:
                            st.image(file_url, use_container_width=True)
                        elif post.get("media_type") and "video" in post["media_type"]:
                            st.video(file_url)
                        elif post.get("media_type") and "audio" in post["media_type"]:
                            st.audio(file_url)

                stats = get_post_stats(post["id"])
                st.markdown(f"❤️ {stats['likes']} | 💬 {stats['comments']} | 🔥 {stats['reactions']}")

                col_a, col_b, col_c, col_d, col_e, col_f = st.columns([1,1,1,1,1,1])
                with col_a:
                    if st.button("❤️", key=f"like_{post['id']}"):
                        like_post(post["id"])
                with col_b:
                    with st.popover("💬"):
                        comments = supabase.table("comments").select("*, profiles(username)").eq("post_id", post["id"]).order("created_at").execute()
                        for c in comments.data:
                            st.markdown(f"**{c['profiles']['username']}** : {c['text']}")
                        new_comment = st.text_input("Votre commentaire", key=f"input_{post['id']}")
                        if st.button("Envoyer", key=f"send_{post['id']}"):
                            add_comment(post["id"], new_comment)
                with col_c:
                    display_emoji_buttons(post["id"], post["user_id"])
                with col_f:
                    if st.button("🔁 Partager", key=f"share_{post['id']}"):
                        comment = st.text_input("Ajouter un commentaire (optionnel)", key=f"share_comment_{post['id']}")
                        if st.button("Confirmer le partage", key=f"share_confirm_{post['id']}"):
                            if share_post(post["id"], user.id, comment):
                                st.success("Post partagé !")
                                st.rerun()
                if post["user_id"] == user.id or is_admin():
                    if st.button("🗑️ Supprimer", key=f"del_{post['id']}"):
                        delete_post(post["id"])
                st.divider()

# =====================================================
# PAGE : TTU FEED (MODE TIKTOK VERTICAL)
# =====================================================
def ttu_feed_page():
    st.header("🎥 TTU Feed - Swipe vertical")
    posts = supabase.table("v_triadic_feed").select("*").order("created_at", desc=True).execute()
    if not posts.data:
        st.info("Aucun post disponible.")
        return

    if "ttu_feed_index" not in st.session_state:
        st.session_state.ttu_feed_index = 0
    index = st.session_state.ttu_feed_index
    total = len(posts.data)

    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        if st.button("⬆️", disabled=(index == 0)):
            st.session_state.ttu_feed_index -= 1
            st.rerun()
    with col2:
        st.write(f"Post {index+1} / {total}")
    with col3:
        if st.button("⬇️", disabled=(index == total-1)):
            st.session_state.ttu_feed_index += 1
            st.rerun()

    post = posts.data[index]
    with st.container():
        prof = supabase.table("profiles").select("username, profile_pic, donation_level").eq("id", post["user_id"]).single().execute()
        username = prof.data["username"] if prof.data else "inconnu"
        badge = get_donor_badge(prof.data.get("donation_level", 0)) if prof.data else ""
        st.markdown(f"**{username}** {badge}")
        st.write(post["text"])

        if post.get("media_path"):
            file_url = get_signed_url("media", post["media_path"])
            if file_url:
                if post.get("media_type") and "image" in post["media_type"]:
                    st.image(file_url, use_container_width=True)
                elif post.get("media_type") and "video" in post["media_type"]:
                    st.video(file_url)
                elif post.get("media_type") and "audio" in post["media_type"]:
                    st.audio(file_url)

        stats = get_post_stats(post["id"])
        st.markdown(f"❤️ {stats['likes']} | 💬 {stats['comments']} | 🔥 {stats['reactions']}")

        col_a, col_b, col_c, col_d, col_e = st.columns(5)
        with col_a:
            if st.button("❤️", key=f"like_{post['id']}"):
                like_post(post["id"])
        with col_b:
            if st.button("💬", key=f"comment_{post['id']}"):
                st.session_state[f"show_comment_{post['id']}"] = True
        with col_c:
            display_emoji_buttons(post["id"], post["user_id"])
        with col_d:
            if st.button("🔁 Partager", key=f"share_{post['id']}"):
                st.session_state[f"show_share_{post['id']}"] = True

        if st.session_state.get(f"show_comment_{post['id']}", False):
            comments = supabase.table("comments").select("*, profiles(username)").eq("post_id", post["id"]).order("created_at").execute()
            for c in comments.data:
                st.markdown(f"**{c['profiles']['username']}** : {c['text']}")
            new_comment = st.text_input("Votre commentaire", key=f"input_{post['id']}")
            if st.button("Envoyer", key=f"send_{post['id']}"):
                add_comment(post["id"], new_comment)
                st.session_state[f"show_comment_{post['id']}"] = False
                st.rerun()

        if st.session_state.get(f"show_share_{post['id']}", False):
            comment = st.text_input("Ajouter un commentaire (optionnel)", key=f"share_comment_{post['id']}")
            if st.button("Confirmer le partage", key=f"share_confirm_{post['id']}"):
                if share_post(post["id"], user.id, comment):
                    st.success("Post partagé !")
                    st.session_state[f"show_share_{post['id']}"] = False
                    st.rerun()

        if post["user_id"] == user.id or is_admin():
            if st.button("🗑️ Supprimer", key=f"del_{post['id']}"):
                delete_post(post["id"])

# =====================================================
# PAGE : PROFIL (et profil public)
# =====================================================
def profile_page(profile_user_id=None):
    if profile_user_id is None or profile_user_id == user.id:
        st.header("👤 Mon Profil")
        with st.expander("Changer ma photo de profil", expanded=False):
            uploaded_file = st.file_uploader("Choisir une image", type=["png", "jpg", "jpeg"])
            if uploaded_file:
                if uploaded_file.size > 5 * 1024 * 1024:
                    st.error("Image trop volumineuse (max 5 Mo).")
                    st.stop()
                try:
                    ext = uploaded_file.name.split(".")[-1]
                    file_name = f"avatars/{user.id}/{uuid.uuid4()}.{ext}"
                    supabase.storage.from_("avatars").upload(
                        path=file_name,
                        file=uploaded_file.getvalue(),
                        file_options={"content-type": f"image/{ext}"}
                    )
                    public_url = supabase.storage.from_("avatars").get_public_url(file_name)
                    supabase.table("profiles").update({"profile_pic": public_url}).eq("id", user.id).execute()
                    st.success("Photo de profil mise à jour")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de l'upload : {e}")

        with st.form("edit_profile"):
            username = st.text_input("Nom d'utilisateur", value=profile["username"])
            bio = st.text_area("Bio", value=profile.get("bio", ""))
            location = st.text_input("Localisation", value=profile.get("location", ""))
            if st.form_submit_button("Mettre à jour"):
                supabase.table("profiles").update({
                    "username": username,
                    "bio": bio,
                    "location": location
                }).eq("id", user.id).execute()
                st.success("Profil mis à jour")
                st.cache_data.clear()
                st.rerun()

        st.subheader("Mes statistiques")
        post_count = supabase.table("posts").select("*", count="exact").eq("user_id", user.id).execute()
        st.metric("Posts publiés", post_count.count)
        followers = supabase.table("follows").select("*", count="exact").eq("followed", user.id).execute()
        following = supabase.table("follows").select("*", count="exact").eq("follower", user.id).execute()
        col1, col2 = st.columns(2)
        col1.metric("Abonnés", followers.count)
        col2.metric("Abonnements", following.count)
        st.metric("Niveau donateur", profile.get("donation_level", 0))
        st.metric("Total KC donnés", profile.get("total_donations", 0))
    else:
        prof = supabase.table("profiles").select("*").eq("id", profile_user_id).single().execute()
        if not prof.data:
            st.error("Utilisateur introuvable.")
            return
        p = prof.data
        st.header(f"👤 Profil de {p['username']} {get_donor_badge(p.get('donation_level',0))}")
        col1, col2 = st.columns([1, 3])
        with col1:
            if p.get("profile_pic"):
                st.image(p["profile_pic"], width=100)
            else:
                st.image("https://via.placeholder.com/100", width=100)
        with col2:
            st.write(f"**Bio :** {p.get('bio', '')}")
            st.write(f"**Localisation :** {p.get('location', '')}")
            st.write(f"Membre depuis : {p['created_at'][:10]}")
            st.write(f"Niveau donateur : {p.get('donation_level',0)}")
            if is_following(user.id, profile_user_id):
                if st.button("Ne plus suivre"):
                    unfollow_user(user.id, profile_user_id)
                    st.rerun()
            else:
                if st.button("Suivre"):
                    follow_user(user.id, profile_user_id)
                    st.rerun()

        st.subheader("Posts récents")
        posts = supabase.table("posts").select("*").eq("user_id", profile_user_id).order("created_at", desc=True).limit(20).execute()
        for post in posts.data:
            st.write(f"**{post['created_at'][:10]}** : {post['text'][:100]}...")

# =====================================================
# PAGE : MESSAGES (inchangée)
# =====================================================
def messages_page():
    st.header("✉️ Messagerie privée (chiffrée de bout en bout)")
    sent = supabase.table("messages").select("recipient").eq("sender", user.id).execute()
    received = supabase.table("messages").select("sender").eq("recipient", user.id).execute()
    contact_ids = set()
    for msg in sent.data:
        contact_ids.add(msg["recipient"])
    for msg in received.data:
        contact_ids.add(msg["sender"])

    if not contact_ids:
        st.info("Aucune conversation pour l'instant.")
        return

    contacts = supabase.table("profiles").select("id, username").in_("id", list(contact_ids)).execute()
    contact_dict = {c["id"]: c["username"] for c in contacts.data}
    selected_contact = st.selectbox(
        "Choisir un contact",
        options=list(contact_dict.keys()),
        format_func=lambda x: contact_dict[x]
    )
    if selected_contact:
        st.subheader(f"Discussion avec {contact_dict[selected_contact]} (messages chiffrés)")
        messages = supabase.table("messages").select("*").or_(
            f"and(sender.eq.{user.id},recipient.eq.{selected_contact}),"
            f"and(sender.eq.{selected_contact},recipient.eq.{user.id})"
        ).order("created_at").limit(100).execute()
        for msg in messages.data:
            decrypted_text = decrypt_private_message(msg.get("text", ""), msg["sender"])
            if msg["sender"] == user.id:
                st.markdown(
                    f"<div style='text-align: right; background-color: #dcf8c6; padding: 8px; border-radius: 10px; margin:5px;'>"
                    f"<b>Vous</b> : {decrypted_text}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='text-align: left; background-color: #f1f0f0; padding: 8px; border-radius: 10px; margin:5px;'>"
                    f"<b>{contact_dict[selected_contact]}</b> : {decrypted_text}</div>",
                    unsafe_allow_html=True
                )
        with st.form("new_message"):
            msg_text = st.text_area("Votre message")
            if st.form_submit_button("Envoyer (chiffré)"):
                if msg_text.strip():
                    encrypted_b64 = encrypt_private_message(msg_text, user.id)
                    supabase.table("messages").insert({
                        "sender": user.id,
                        "recipient": selected_contact,
                        "text": encrypted_b64,
                        "created_at": datetime.now().isoformat()
                    }).execute()
                    st.success("Message envoyé (chiffré)")
                    st.rerun()
                else:
                    st.warning("Le message ne peut pas être vide.")

# =====================================================
# PAGE : MARKETPLACE (inchangée)
# =====================================================
def marketplace_page():
    st.header("🏪 Marketplace")
    with st.expander("➕ Ajouter une annonce"):
        with st.form("new_listing"):
            title = st.text_input("Titre")
            description = st.text_area("Description")
            price = st.number_input("Prix (KC)", min_value=0.0, step=0.1)
            media = st.file_uploader("Image du produit", type=["png", "jpg", "jpeg"])
            submitted = st.form_submit_button("Publier l'annonce")
            if submitted and title:
                if media and media.size > 5 * 1024 * 1024:
                    st.error("Image trop volumineuse (max 5 Mo).")
                    st.stop()
                try:
                    media_url = None
                    if media:
                        file_name = f"marketplace/{user.id}/{uuid.uuid4()}.jpg"
                        supabase.storage.from_("marketplace").upload(
                            path=file_name,
                            file=media.getvalue(),
                            file_options={"content-type": media.type}
                        )
                        media_url = supabase.storage.from_("marketplace").get_public_url(file_name)
                    supabase.table("marketplace_listings").insert({
                        "user_id": user.id,
                        "title": title,
                        "description": description,
                        "price_kc": price,
                        "media_url": media_url,
                        "media_type": "image",
                        "created_at": datetime.now().isoformat(),
                        "is_active": True,
                        "status": "Disponible",
                        "sales_count": 0
                    }).execute()
                    st.success("Annonce ajoutée et disponible !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de la publication : {e}")

    st.subheader("Annonces récentes")
    listings = supabase.table("marketplace_listings").select(
        "*, profiles!inner(username)"
    ).eq("is_active", True).order("created_at", desc=True).execute()
    if not listings.data:
        st.info("Aucune annonce pour le moment.")
        return

    cols = st.columns(3)
    for i, listing in enumerate(listings.data):
        with cols[i % 3]:
            status = listing.get("status", "Disponible")
            color = "green" if status == "Disponible" else "red"
            st.markdown(f"### {listing['title']}")
            st.markdown(f":{color}[**[{status}]**]")
            if listing.get("media_url"):
                st.image(listing["media_url"], use_container_width=True)
            st.write(listing["description"][:100] + "..." if len(listing["description"]) > 100 else listing["description"])
            st.write(f"💰 **{listing['price_kc']:,.0f} KC**")
            st.caption(f"Vendeur : {listing['profiles']['username']}")
            if listing["user_id"] != user.id:
                if status == "Disponible":
                    if st.button(f"🛒 Acheter ({listing['price_kc']} KC)", key=f"buy_{listing['id']}"):
                        current_listing = supabase.table("marketplace_listings").select("status").eq("id", listing["id"]).single().execute()
                        if current_listing.data and current_listing.data["status"] != "Disponible":
                            st.error("Cette annonce n'est plus disponible.")
                            st.rerun()
                        wallet_res = supabase.table("wallets").select("*").eq("user_id", user.id).execute()
                        if wallet_res.data:
                            buyer_wallet = wallet_res.data[0]
                            if buyer_wallet["kongo_balance"] >= listing["price_kc"]:
                                try:
                                    new_buyer_balance = buyer_wallet["kongo_balance"] - listing["price_kc"]
                                    supabase.table("wallets").update({"kongo_balance": new_buyer_balance}).eq("user_id", user.id).execute()
                                    vendeur_wallet_res = supabase.table("wallets").select("kongo_balance").eq("user_id", listing["user_id"]).execute()
                                    if vendeur_wallet_res.data:
                                        new_seller_balance = vendeur_wallet_res.data[0]["kongo_balance"] + listing["price_kc"]
                                        supabase.table("wallets").update({"kongo_balance": new_seller_balance}).eq("user_id", listing["user_id"]).execute()
                                    new_sales_count = listing.get("sales_count", 0) + 1
                                    supabase.table("marketplace_listings").update({
                                        "status": "Vendu",
                                        "sales_count": new_sales_count
                                    }).eq("id", listing["id"]).execute()
                                    msg_text = f"🚨 ACHAT : Je suis intéressé par '{listing['title']}'. Le paiement de {listing['price_kc']} KC a été transféré sur votre compte."
                                    encrypted_msg = encrypt_private_message(msg_text, user.id)
                                    supabase.table("messages").insert({
                                        "sender": user.id,
                                        "recipient": listing["user_id"],
                                        "text": encrypted_msg,
                                        "created_at": datetime.now().isoformat()
                                    }).execute()
                                    st.success("✅ Transaction terminée ! Le vendeur a été notifié.")
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur transactionnelle : {e}")
                            else:
                                st.error("Solde KC insuffisant.")
                        else:
                            st.error("Portefeuille introuvable.")
                else:
                    st.button("❌ Déjà Vendu", disabled=True, key=f"sold_{listing['id']}")
            else:
                st.info(f"📊 {listing.get('sales_count', 0)} client(s) sur cette annonce")

# =====================================================
# PAGE : WALLET (inchangée)
# =====================================================
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
            "last_reward_at": datetime.now().isoformat()
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
            if last_str.endswith("Z"):
                last_str = last_str.replace("Z", "+00:00")
            last = datetime.fromisoformat(last_str)
            now = datetime.now()
            delta = now - last
            if delta.total_seconds() > 86400:
                new_balance = wallet_data["kongo_balance"] + 10
                new_mined = wallet_data["total_mined"] + 10
                supabase.table("wallets").update({
                    "kongo_balance": new_balance,
                    "total_mined": new_mined,
                    "last_reward_at": now.isoformat()
                }).eq("user_id", user.id).execute()
                st.success("+10 KC minés !")
                st.rerun()
            else:
                reste = 86400 - delta.total_seconds()
                st.warning(f"Prochain minage dans {int(reste//3600)}h {int((reste%3600)//60)}m.")
        except Exception as e:
            st.error(f"Erreur lors du minage : {e}")
    st.divider()
    st.subheader("📜 Activité récente")
    st.info("L'historique détaillé des transactions Marketplace sera bientôt disponible.")

# =====================================================
# PAGE : TTU LIVE (avec cadeaux et jauge)
# =====================================================
def ttu_live_page():
    st.header("🎥 TTU Live - Streams en direct")
    tab1, tab2 = st.tabs(["📺 Voir les streams", "🎬 Créer un stream"])

    with tab1:
        streams = supabase.table("ttu_streams").select("*, profiles!inner(username, profile_pic, donation_level)").eq("is_active", True).order("created_at", desc=True).execute()
        if not streams.data:
            st.info("Aucun stream en cours.")
        else:
            for stream in streams.data:
                with st.expander(f"{stream['title']} par {stream['profiles']['username']} {get_donor_badge(stream['profiles']['donation_level'])}"):
                    st.write(stream.get('description', ''))
                    gauge = stream.get('stability_gauge', 0.0)
                    st.progress(gauge/100, text=f"Stabilité du flux : {gauge:.1f}%")
                    if gauge >= 100:
                        st.success("✨ MODE TTU-VISION ACTIVÉ ! L'image devient spectrale.")
                    if stream.get('video_url'):
                        st.video(stream['video_url'])
                    else:
                        st.warning("Flux non disponible")
                    st.metric("Résonance", f"{stream['resonance_score']:.2f}")

                    st.subheader("Envoyer un cadeau")
                    gifts = supabase.table("gift_definitions").select("*").execute()
                    if gifts.data:
                        cols = st.columns(5)
                        for i, gift in enumerate(gifts.data):
                            with cols[i % 5]:
                                if st.button(f"{gift['emoji']} {gift['name']}\n({gift['kc_cost']} KC)", key=f"gift_{stream['id']}_{gift['id']}"):
                                    if send_gift(stream['id'], gift['id']):
                                        st.success(f"Cadeau {gift['name']} envoyé !")
                                        st.rerun()

                    st.subheader("Chat en direct")
                    chat_msgs = supabase.table("stream_chat").select("*, profiles(username, donation_level)").eq("stream_id", stream['id']).order("created_at").limit(50).execute()
                    for msg in chat_msgs.data:
                        badge = get_donor_badge(msg['profiles']['donation_level'])
                        st.text(f"{msg['profiles']['username']} {badge}: {msg['message']}")
                    new_msg = st.text_input("Votre message", key=f"chat_{stream['id']}")
                    if st.button("Envoyer", key=f"send_chat_{stream['id']}"):
                        supabase.table("stream_chat").insert({
                            "stream_id": stream['id'],
                            "user_id": user.id,
                            "message": new_msg,
                            "created_at": datetime.now().isoformat()
                        }).execute()
                        st.rerun()

    with tab2:
        with st.form("create_stream"):
            title = st.text_input("Titre du stream")
            description = st.text_area("Description")
            video_file = st.file_uploader("Vidéo (fichier)", type=["mp4", "mov", "avi"])
            if st.form_submit_button("Lancer le stream"):
                if title and video_file:
                    stream_id = create_stream(title, description, video_file)
                    st.success(f"Stream créé avec succès ! ID: {stream_id}")
                    st.rerun()
                else:
                    st.error("Veuillez remplir tous les champs.")

# =====================================================
# PAGE : PANELS (inchangée)
# =====================================================
def panels_page():
    st.header("💬 Panels de discussion")
    tab1, tab2 = st.tabs(["📋 Panels actifs", "➕ Créer un panel"])

    with tab1:
        panels = supabase.table("ttu_panels").select("*, profiles(username)").order("created_at", desc=True).execute()
        if not panels.data:
            st.info("Aucun panel pour l'instant.")
        else:
            for panel in panels.data:
                with st.expander(f"{panel['title']} (créé par {panel['profiles']['username']})"):
                    stability = panel.get('current_stability', 1.0)
                    entropy = panel.get('entropy_level', 0.0)
                    st.progress(stability, text=f"Stabilité : {stability:.2f}")
                    st.caption(f"Entropie : {entropy:.2f}")
                    msgs = supabase.table("messages").select("*, profiles(username, donation_level)").eq("panel_id", panel['id']).order("created_at").limit(50).execute()
                    for msg in msgs.data:
                        badge = get_donor_badge(msg['profiles']['donation_level'])
                        st.markdown(f"**{msg['profiles']['username']}** {badge} : {msg['text']}")
                    new_msg = st.text_input("Votre message", key=f"panel_msg_{panel['id']}")
                    if st.button("Envoyer", key=f"panel_send_{panel['id']}"):
                        supabase.table("messages").insert({
                            "sender": user.id,
                            "recipient": None,
                            "text": new_msg,
                            "panel_id": panel['id'],
                            "created_at": datetime.now().isoformat()
                        }).execute()
                        st.rerun()

    with tab2:
        with st.form("new_panel"):
            title = st.text_input("Titre du panel")
            if st.form_submit_button("Créer"):
                supabase.table("ttu_panels").insert({
                    "title": title,
                    "creator_id": user.id,
                    "current_stability": 1.0,
                    "entropy_level": 0.0,
                    "is_live": True,
                    "created_at": datetime.now().isoformat()
                }).execute()
                st.success("Panel créé !")
                st.rerun()

# =====================================================
# PAGE : PARAMÈTRES (inchangée)
# =====================================================
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
            wallet_data = wallet_res.data[0]
            current_balance = wallet_data["kongo_balance"]
            if current_balance >= PREMIUM_PRICE:
                try:
                    new_balance = current_balance - PREMIUM_PRICE
                    supabase.table("wallets").update({
                        "kongo_balance": new_balance
                    }).eq("user_id", user.id).execute()
                    supabase.table("subscriptions").insert({
                        "user_id": user.id,
                        "plan_type": "Premium",
                        "activated_at": datetime.now().isoformat(),
                        "expires_at": (datetime.now().replace(year=datetime.now().year+1)).isoformat(),
                        "is_active": True
                    }).execute()
                    st.success(f"Compte Premium activé ! {PREMIUM_PRICE:,.0f} KC ont été débités.")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de la transaction : {e}")
            else:
                st.error(f"Solde insuffisant. Il vous manque {PREMIUM_PRICE - current_balance:,.0f} KC.")
        else:
            st.error("Portefeuille introuvable. Veuillez d'abord initialiser votre Wallet.")
    st.divider()
    st.subheader("Zone dangereuse")
    if st.button("Supprimer mon compte", type="primary"):
        st.warning("Fonction désactivée pour le moment.")

# =====================================================
# PAGE : ADMIN (inchangée)
# =====================================================
def admin_page():
    st.header("🛡️ Espace Administration")
    st.caption("Actions réservées à la modération -- utilisez‑les avec discernement.")
    tab1, tab2, tab3, tab4 = st.tabs(["Utilisateurs", "Posts signalés", "Logs d'action", "Crédits"])

    with tab1:
        st.subheader("Gestion des utilisateurs")
        users = supabase.table("profiles").select("id, username, role, created_at").execute()
        df_users = pd.DataFrame(users.data)
        st.dataframe(df_users)
        with st.form("change_role"):
            user_id = st.selectbox(
                "Sélectionner un utilisateur",
                options=df_users["id"],
                format_func=lambda x: df_users[df_users["id"] == x]["username"].values[0]
            )
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
                    delete_post(post["id"])

    with tab3:
        st.subheader("Journal des actions")
        st.info("Fonctionnalité à venir : traçabilité des actions d'administration.")

    with tab4:
        st.subheader("Créditer un utilisateur")
        users = supabase.table("profiles").select("id, username").execute()
        user_options = {u["id"]: u["username"] for u in users.data}
        selected_user = st.selectbox(
            "Choisir un utilisateur",
            options=list(user_options.keys()),
            format_func=lambda x: user_options[x]
        )
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
                    "last_reward_at": datetime.now().isoformat()
                }).execute()
            st.success(f"{amount:,.0f} KC ajoutés à {user_options[selected_user]}")

# =====================================================
# ROUTEUR PRINCIPAL
# =====================================================
if menu == "🌐 Feed":
    feed_page()
elif menu == "🎥 TTU Feed":
    ttu_feed_page()
elif menu == "👤 Mon Profil":
    profile_page()
elif menu == "✉️ Messages":
    messages_page()
elif menu == "🏪 Marketplace":
    marketplace_page()
elif menu == "💰 Wallet":
    wallet_page()
elif menu == "🎥 TTU Live":
    ttu_live_page()
elif menu == "💬 Panels":
    panels_page()
elif menu == "⚙️ Paramètres":
    settings_page()
elif menu == "🛡️ Admin":
    admin_page()