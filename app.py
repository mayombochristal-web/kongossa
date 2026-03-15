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
from PIL import Image 
import io             

def get_fernet_from_key(secret: str) -> Fernet:
    """Dérive une clé Fernet à partir du secret partagé."""
    # Fernet nécessite une clé de 32 bytes en base64
    # On utilise SHA256 pour obtenir 32 bytes, puis base64
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)

def encrypt_text(plaintext: str) -> str:
    """Chiffre un texte avec la clé stockée en session."""
    fernet = get_fernet_from_key(st.session_state.current_k)
    return fernet.encrypt(plaintext.encode()).decode()

def decrypt_text(ciphertext: str) -> str:
    """Déchiffre un texte avec la clé stockée en session."""
    fernet = get_fernet_from_key(st.session_state.current_k)
    return fernet.decrypt(ciphertext.encode()).decode()
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
# FONCTIONS DE CHIFFREMENT / DÉCHIFFREMENT
# =====================================================
def encrypt_text(plain_text: str) -> str:
    if not plain_text:
        return ""
    encrypted = fernet.encrypt(plain_text.encode())
    return base64.b64encode(encrypted).decode()

def decrypt_text(encrypted_b64: str) -> str:
    if not encrypted_b64:
        return ""
    try:
        encrypted = base64.b64decode(encrypted_b64)
        return fernet.decrypt(encrypted).decode()
    except Exception:
        return "🔐 Message illisible (erreur de clé)"

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
                        "created_at": datetime.now().isoformat()
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
# NAVIGATION (SIDEBAR)
# =====================================================
st.sidebar.image("https://via.placeholder.com/150x50?text=GEN-Z", width=150)
st.sidebar.write(f"Connecté en tant que : **{profile['username']}**")
if is_admin():
    st.sidebar.markdown("🔑 **Administrateur**")
st.sidebar.write(f"ID : {user.id[:8]}...")

menu_options = ["🌐 Feed", "👤 Mon Profil", "✉️ Messages", "🏪 Marketplace", "💰 Wallet", "⚙️ Paramètres"]
if is_admin():
    menu_options.append("🛡️ Admin")
menu = st.sidebar.radio("Navigation", menu_options)

if st.sidebar.button("🚪 Déconnexion"):
    logout()

# =====================================================
# FONCTIONS UTILES
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
        # Récupérer le chemin du média pour le supprimer du storage
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

# =====================================================
# FONCTIONS POUR LES STATISTIQUES DES POSTS
# =====================================================
def get_post_stats(post_id):
    # Compte réel des likes (gratuits)
    likes_res = supabase.table("likes").select("*", count="exact").eq("post_id", post_id).execute()
    likes_count = likes_res.count if likes_res.count else 0

    # Compte réel des commentaires
    comments_res = supabase.table("comments").select("*", count="exact").eq("post_id", post_id).execute()
    comments_count = comments_res.count if comments_res.count else 0

    # Compte des réactions premium (emojis payants)
    reactions_res = supabase.table("reactions").select("*", count="exact").eq("post_id", post_id).execute()
    reactions_count = reactions_res.count if reactions_res.count else 0

    return {
        "likes": likes_count,
        "comments": comments_count,
        "reactions": reactions_count
    }

# Hiérarchie des emojis payants
EMOJI_HIERARCHY = {
    "🔥": {"label": "Hype", "cost": 10, "share": 8},      # L'auteur gagne 8 KC
    "💎": {"label": "Pépite", "cost": 50, "share": 40},   # L'auteur gagne 40 KC
    "👑": {"label": "Légende", "cost": 100, "share": 80}  # L'auteur gagne 80 KC
}

def process_emoji_payment(post_id, author_id, emoji_type):
    """Gère le paiement d'une réaction émoji premium."""
    cost = EMOJI_HIERARCHY[emoji_type]["cost"]
    share = EMOJI_HIERARCHY[emoji_type]["share"]

    # Vérifier le solde de l'utilisateur
    wallet_res = supabase.table("wallets").select("kongo_balance").eq("user_id", user.id).execute()
    if not wallet_res.data:
        st.error("Portefeuille introuvable.")
        return
    wallet = wallet_res.data[0]
    if wallet["kongo_balance"] < cost:
        st.error(f"Solde insuffisant. Il vous manque {cost - wallet['kongo_balance']} KC.")
        return

    # Vérifier que l'utilisateur n'a pas déjà réagi avec cet émoji sur ce post (optionnel)
    # On peut autoriser plusieurs réactions de types différents

    try:
        # 1. Débiter l'utilisateur
        new_bal = wallet["kongo_balance"] - cost
        supabase.table("wallets").update({"kongo_balance": new_bal}).eq("user_id", user.id).execute()

        # 2. Créditer l'auteur (80% du coût)
        author_wallet_res = supabase.table("wallets").select("kongo_balance").eq("user_id", author_id).execute()
        if author_wallet_res.data:
            author_wallet = author_wallet_res.data[0]
            new_author_bal = author_wallet["kongo_balance"] + share
            supabase.table("wallets").update({"kongo_balance": new_author_bal}).eq("user_id", author_id).execute()

        # 3. Enregistrer la réaction dans la table reactions
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
# PAGES
# =====================================================
# =====================================================
# FONCTIONS UTILITAIRES POUR LE FEED
# =====================================================
def upload_optimized_media(file):
    """Upload avec compression automatique des images."""
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
    """Génère une URL signée valable 1 heure."""
    if not path:
        return None
    try:
        res = supabase.storage.from_("media").create_signed_url(path, 3600)
        return res['signedURL']
    except Exception as e:
        return None

def delete_post_and_media(post_id, media_path):
    """Supprime proprement le média du storage et le post de la DB."""
    try:
        # 1. Supprimer le fichier physique (API Storage)
        if media_path:
            supabase.storage.from_("media").remove([media_path])
            
        # 2. Supprimer l'entrée en base de données
        supabase.table("posts").delete().eq("id", post_id).execute()
        
        st.toast("🚀 Publication retirée avec succès", icon="🗑️")
        return True
    except Exception as e:
        st.error(f"Erreur lors de la suppression : {e}")
        return False

def toggle_like(post_id, user_id):
    """Toggle like : ajoute ou retire selon l'état actuel."""
    check = supabase.table("likes").select("*").eq("post_id", post_id).eq("user_id", user_id).execute()
    if check.data:
        supabase.table("likes").delete().eq("post_id", post_id).eq("user_id", user_id).execute()
        return "retiré"
    else:
        supabase.table("likes").insert({"post_id": post_id, "user_id": user_id}).execute()
        return "ajouté"

def add_comment(post_id, user_id, text):
    """Ajoute un commentaire."""
    if text.strip():
        supabase.table("comments").insert({
            "post_id": post_id,
            "user_id": user_id,
            "text": text
        }).execute()
        return True
    return False

def process_tip(post_id, sender_id, receiver_id, amount, emoji):
    """Traite un don KC via RPC."""
    try:
        supabase.rpc('process_tip', {
            'p_post_id': post_id,
            'p_sender_id': sender_id,
            'p_receiver_id': receiver_id,
            'p_amount': amount,
            'p_emoji': emoji
        }).execute()
        return True, None
    except Exception as e:
        return False, str(e)

# =====================================================
# PAGE FEED
# =====================================================
def feed_page():
    st.header("🌐 Fil d'actualité")

    # --- CSS PREMIUM COMPACT ---
    st.markdown("""
        <style>
        div[data-testid="stVerticalBlockBorderControl"] {
            background: rgba(22, 27, 34, 0.7) !important;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 157, 0, 0.2) !important;
            border-radius: 12px;
            transition: transform 0.2s;
            margin-bottom: 12px;
            padding: 12px !important;
        }
        div[data-testid="stVerticalBlockBorderControl"]:hover {
            transform: scale(1.01);
            border-color: #ff9d00 !important;
        }
        .stImage > img, .stVideo > video {
            border-radius: 12px;
            max-height: 500px;
            object-fit: cover;
        }
        .stImage > img[alt*="avatar"] {
            border-radius: 50%;
            width: 40px !important;
            height: 40px !important;
            object-fit: cover;
            border: 2px solid #ff9d00;
        }
        .stButton button {
            background: #21262d !important;
            border: none !important;
            border-radius: 20px !important;
            color: #e4e6eb !important;
            font-weight: 600;
            height: 35px !important;
            font-size: 14px !important;
            padding: 0 10px !important;
            margin: 0 !important;
        }
        div.streamlit-expanderHeader {
            background: #21262d !important;
            border-radius: 20px !important;
            color: #e4e6eb !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            padding: 5px 12px !important;
            border: 1px solid #3a3b3c !important;
        }
        div.streamlit-expanderHeader:hover {
            border-color: #ff9d00 !important;
        }
        div.streamlit-expanderContent {
            border: none !important;
            background: transparent !important;
            padding: 8px 0 0 0 !important;
        }
        .stats-line {
            display: flex;
            gap: 15px;
            color: #8b949e;
            font-size: 13px;
            margin: 8px 0;
        }
        .stats-line span {
            display: flex;
            align-items: center;
            gap: 3px;
        }
        .trending-title {
            font-size: 1.5rem;
            font-weight: 600;
            background: linear-gradient(45deg, #ff9d00, #ff4b4b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- SECTION TENDANCES ---
    st.markdown('<p class="trending-title">🔥 Tendances</p>', unsafe_allow_html=True)
    try:
        tips_24h = supabase.table("tips") \
            .select("post_id, amount") \
            .gte("created_at", (datetime.now() - timedelta(days=1)).isoformat()) \
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
    except Exception as e:
        st.warning("Tendances indisponibles")

    st.divider()

    # --- PUBLICATION RAPIDE ---
    with st.container(border=True):
        col_av, col_input = st.columns([1, 5])
        with col_av:
            avatar = profile.get("profile_pic")
            st.image(avatar if avatar else "https://via.placeholder.com/40", width=40)
        with col_input:
            post_text = st.text_area("", placeholder="Exprimez-vous...", label_visibility="collapsed", key="post_input", height=70)

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            uploaded_file = st.file_uploader("📷", type=["png", "jpg", "jpeg", "mp4", "mov", "mp3", "wav"], 
                                            label_visibility="collapsed", key="media_upload")
        with c2:
            if st.button("🚀 Propulser", use_container_width=True, type="primary"):
                if post_text or uploaded_file:
                    with st.spinner("..."):
                        try:
                            media_path, media_type = None, None
                            if uploaded_file:
                                media_path, media_type = upload_optimized_media(uploaded_file)
                            supabase.table("posts").insert({
                                "user_id": user.id,
                                "text": post_text if post_text else None,
                                "media_path": media_path,
                                "media_type": media_type,
                                "created_at": datetime.now().isoformat()
                            }).execute()
                            st.balloons()
                            st.toast("✨ Posté !")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")
                else:
                    st.warning("Écris ou ajoute un média")

    # --- CHARGEMENT DU FLUX ---
    with st.spinner("🌊 Chargement..."):
        try:
            posts = supabase.table("posts").select(
                "*, profiles!inner(username, profile_pic)"
            ).order("created_at", desc=True).limit(30).execute()
        except Exception as e:
            st.error("Impossible de charger le fil")
            return

    if not posts.data:
        st.info("🌙 Le fil est calme... Sois le premier à propulser !")
        return

    # --- AFFICHAGE COMPACT DES POSTS ---
    for post in posts.data:
        with st.container(border=True):
            # Header
            col_avatar, col_header = st.columns([1, 8])
            with col_avatar:
                avatar = post["profiles"].get("profile_pic")
                st.image(avatar if avatar else "https://via.placeholder.com/40", width=40)
            with col_header:
                st.markdown(f"**{post['profiles']['username']}**  ·  {post['created_at'][:10]}")
            
            # Texte
            if post.get("text"):
                st.markdown(f"### {post['text']}")

            # Média
            if post.get("media_path"):
                media_url = get_signed_media_url(post["media_path"])
                if media_url:
                    if "image" in str(post.get("media_type", "")):
                        st.image(media_url, use_container_width=True)
                    elif "video" in str(post.get("media_type", "")):
                        st.video(media_url)
                    elif "audio" in str(post.get("media_type", "")):
                        st.audio(media_url)
                    else:
                        ext = post["media_path"].split(".")[-1].lower()
                        if ext in ['jpg','jpeg','png','webp']:
                            st.image(media_url, use_container_width=True)
                        elif ext in ['mp4','mov','webm']:
                            st.video(media_url)
                        elif ext in ['mp3','wav']:
                            st.audio(media_url)

            # Statistiques
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

            # Bouton like toggle
            if st.button(f"❤️ {likes}", key=f"like_{post['id']}", use_container_width=True):
                action = toggle_like(post['id'], user.id)
                st.toast(f"❤️ Like {action}")
                time.sleep(0.3)
                st.rerun()

            # TIROIR D'ÉMOJIS
            with st.expander("💬 Réagir avec KC", expanded=False):
                col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                with col_e1:
                    if st.button("🔥 10", key=f"tip10_{post['id']}", use_container_width=True):
                        success, error = process_tip(post['id'], user.id, post['user_id'], 10, '🔥')
                        if success:
                            st.toast("🔥 +10 KC !")
                            time.sleep(0.3)
                            st.rerun()
                        else:
                            st.error(f"Erreur : {error}")
                with col_e2:
                    if st.button("💎 50", key=f"tip50_{post['id']}", use_container_width=True):
                        success, error = process_tip(post['id'], user.id, post['user_id'], 50, '💎')
                        if success:
                            st.toast("💎 +50 KC !")
                            time.sleep(0.3)
                            st.rerun()
                        else:
                            st.error(f"Erreur : {error}")
                with col_e3:
                    if st.button("👑 100", key=f"tip100_{post['id']}", use_container_width=True):
                        success, error = process_tip(post['id'], user.id, post['user_id'], 100, '👑')
                        if success:
                            st.balloons()
                            st.toast("👑 +100 KC !")
                            time.sleep(0.3)
                            st.rerun()
                        else:
                            st.error(f"Erreur : {error}")
                with col_e4:
                    with st.popover("💬", help="Voir commentaires"):
                        comments_data = supabase.table("comments").select(
                            "*, profiles(username)"
                        ).eq("post_id", post["id"]).order("created_at").execute()
                        for c in comments_data.data:
                            st.markdown(f"**{c['profiles']['username']}** : {c['text']}")
                        new_comment = st.text_input("", placeholder="Commenter...", key=f"com_{post['id']}")
                        if st.button("Envoyer", key=f"send_{post['id']}"):
                            if add_comment(post['id'], user.id, new_comment):
                                st.rerun()

            # BOUTON SUPPRESSION (propriétaire ou admin)
            if post["user_id"] == user.id or (is_admin() if 'is_admin' in dir() else False):
                if st.button("🗑️ Supprimer", key=f"del_{post['id']}", type="secondary"):
                    if delete_post_and_media(post["id"], post.get("media_path")):
                        time.sleep(0.5)
                        st.rerun()

def profile_page():
    st.header("👤 Mon Profil Souverain")

    # --- CSS PERSONNALISÉ POUR LE PROFIL ---
    st.markdown("""
        <style>
        /* Carte de profil */
        div[data-testid="stVerticalBlockBorderControl"] {
            background: rgba(22, 27, 34, 0.7) !important;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 157, 0, 0.2) !important;
            border-radius: 15px;
            padding: 20px !important;
        }
        /* Avatar */
        .stImage > img[alt*="avatar"] {
            border-radius: 50%;
            border: 3px solid #ff9d00;
            object-fit: cover;
        }
        /* Badges */
        .badge {
            display: inline-block;
            background: linear-gradient(45deg, #ff9d00, #ff4b4b);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
            margin-bottom: 8px;
        }
        /* Statistiques */
        .metric-card {
            background: #21262d;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            border: 1px solid #3a3b3c;
        }
        .metric-value {
            font-size: 24px;
            font-weight: 700;
            color: #ff9d00;
        }
        .metric-label {
            font-size: 12px;
            color: #8b949e;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- RÉCUPÉRATION DU PROFIL ---
    try:
        profile_data = supabase.table("profiles").select("*").eq("id", user.id).single().execute()
        profile = profile_data.data
    except Exception as e:
        st.error("Impossible de charger votre profil.")
        return

    # --- HEADER DU PROFIL ---
    col_avatar, col_info = st.columns([1, 3])
    
    with col_avatar:
        avatar = profile.get("profile_pic")
        if avatar:
            st.image(avatar, width=120)
        else:
            st.image("https://via.placeholder.com/120x120?text=Avatar", width=120)
    
    with col_info:
        st.title(f"@{profile['username']}")
        
        # Badges automatiques
        badges = []
        
        # Badge admin/vérifié
        if profile.get("role") == "admin":
            badges.append("🛡️ Administrateur")
        elif profile.get("role") == "moderator":
            badges.append("⚖️ Modérateur")
        
        # Badge créateur de tunnels
        try:
            tunnels_created = supabase.table("tunnels").select("*", count="exact").eq("creator_id", user.id).execute().count
            if tunnels_created >= 3:
                badges.append("🔑 Architecte des Tunnels")
        except:
            pass
        
        # Badge marchand
        try:
            sales = supabase.table("marketplace_listings").select("*", count="exact").eq("user_id", user.id).gt("sales_count", 0).execute().count
            if sales >= 1:
                badges.append("💰 Marchand Actif")
        except:
            pass
        
        # Badge contributeur
        try:
            posts_count = supabase.table("posts").select("*", count="exact").eq("user_id", user.id).execute().count
            if posts_count >= 10:
                badges.append("📢 Influenceur")
        except:
            pass
        
        # Affichage des badges
        if badges:
            st.markdown(" ".join([f'<span class="badge">{b}</span>' for b in badges]), unsafe_allow_html=True)
        
        # Bio et localisation
        st.markdown(f"📍 **{profile.get('location', 'Localisation non définie')}**")
        st.markdown(f"*{profile.get('bio', 'Aucune bio pour le moment.')}*")
        
        # Date d'inscription
        if profile.get("created_at"):
            st.caption(f"📅 Membre depuis le {profile['created_at'][:10]}")

    st.divider()

    # --- ONGLETS DU PROFIL ---
    tab_stats, tab_activity, tab_tunnels, tab_edit, tab_vault = st.tabs([
        "📊 Statistiques", "📋 Activité", "🚇 Mes Tunnels", "⚙️ Modifier", "🔐 Coffre TTU"
    ])

    # =============================================
    # ONGLET 1 : STATISTIQUES
    # =============================================
    with tab_stats:
        st.subheader("📊 Statistiques Globales")
        
        # Statistiques sociales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            try:
                posts_count = supabase.table("posts").select("*", count="exact").eq("user_id", user.id).execute().count
            except:
                posts_count = 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{posts_count}</div>
                <div class="metric-label">Publications</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            try:
                followers = supabase.table("follows").select("*", count="exact").eq("followed", user.id).execute().count
            except:
                followers = 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{followers}</div>
                <div class="metric-label">Abonnés</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            try:
                following = supabase.table("follows").select("*", count="exact").eq("follower", user.id).execute().count
            except:
                following = 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{following}</div>
                <div class="metric-label">Abonnements</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            try:
                likes_received = supabase.table("likes").select("*", count="exact").eq("post_id", supabase.table("posts").select("id").eq("user_id", user.id).execute().data).execute().count
            except:
                likes_received = 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{likes_received}</div>
                <div class="metric-label">Likes reçus</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Statistiques économiques
        st.subheader("💰 Portefeuille KC")
        
        try:
            wallet = supabase.table("wallets").select("*").eq("user_id", user.id).single().execute()
            if wallet.data:
                col_w1, col_w2, col_w3 = st.columns(3)
                with col_w1:
                    st.metric("Solde KC", f"{wallet.data['kongo_balance']:,.0f}")
                with col_w2:
                    st.metric("Total miné", f"{wallet.data['total_mined']:,.0f}")
                with col_w3:
                    if wallet.data.get('last_reward_at'):
                        last = datetime.fromisoformat(wallet.data['last_reward_at'].replace('Z', '+00:00'))
                        next_reward = last + timedelta(days=1)
                        time_left = next_reward - datetime.now()
                        hours = int(time_left.total_seconds() // 3600)
                        st.metric("Prochain minage", f"{hours}h")
        except Exception as e:
            st.info("Portefeuille en cours d'initialisation")

        # Statistiques TTU
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

    # =============================================
    # ONGLET 2 : ACTIVITÉ RÉCENTE
    # =============================================
    with tab_activity:
        st.subheader("📋 Activité Récente")
        
        # Derniers posts
        try:
            last_posts = supabase.table("posts").select(
                "text, created_at, media_type"
            ).eq("user_id", user.id).order("created_at", desc=True).limit(5).execute()
            
            if last_posts.data:
                st.write("**📝 Dernières publications**")
                for p in last_posts.data:
                    media_icon = "📷" if "image" in str(p.get("media_type", "")) else "🎬" if "video" in str(p.get("media_type", "")) else "📄"
                    st.caption(f"{media_icon} {p['text'][:50]}... - {p['created_at'][:10]}")
            else:
                st.caption("Aucune publication pour le moment")
        except:
            pass

        st.divider()

        # Derniers messages dans les tunnels
        try:
            last_msgs = supabase.table("messages").select(
                "text, created_at, tunnel_id, tunnels(name)"
            ).eq("sender", user.id).order("created_at", desc=True).limit(5).execute()
            
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

        # Dernières transactions (tips reçus)
        try:
            last_tips = supabase.table("tips").select(
                "amount, emoji, created_at, sender_id, profiles!tips_sender_id_fkey(username)"
            ).eq("receiver_id", user.id).order("created_at", desc=True).limit(5).execute()
            
            if last_tips.data:
                st.write("**🔥 Derniers dons reçus**")
                for t in last_tips.data:
                    sender_name = t['profiles']['username'] if t.get('profiles') else "Inconnu"
                    st.caption(f"{t['emoji']} {t['amount']} KC de {sender_name} - {t['created_at'][:16]}")
            else:
                st.caption("Aucun don reçu pour le moment")
        except:
            pass

    # =============================================
    # ONGLET 3 : MES TUNNELS
    # =============================================
    with tab_tunnels:
        st.subheader("🚇 Mes Tunnels")
        
        try:
            tunnels = supabase.table("tunnel_members") \
                .select("tunnel_id, tunnels(name, k_hash, created_at, creator_id)") \
                .eq("user_id", user.id) \
                .execute()
            
            if tunnels.data:
                for t in tunnels.data:
                    tunnel = t['tunnels']
                    with st.container(border=True):
                        col_t1, col_t2 = st.columns([3, 1])
                        
                        # Nom du tunnel et rôle
                        role = "Créateur" if tunnel.get('creator_id') == user.id else "Membre"
                        col_t1.markdown(f"**{tunnel['name']}** - `{role}`")
                        col_t2.caption(f"Créé le {tunnel['created_at'][:10]}")

if tunnel.get('creator_id') == user.id:
                 copy_tunnel_id_button(t['tunnel_id'], tunnel['name'])
                        
                        # Statistiques du tunnel
                        try:
                            members_count = supabase.table("tunnel_members").select("*", count="exact").eq("tunnel_id", t['tunnel_id']).execute().count
                            messages_count = supabase.table("messages").select("*", count="exact").eq("tunnel_id", t['tunnel_id']).execute().count
                            
                            col_info1, col_info2, col_info3 = st.columns(3)
                            col_info1.caption(f"👥 {members_count} membres")
                            col_info2.caption(f"💬 {messages_count} messages")
                            
                            # Hash de la clé (si disponible)
                            if tunnel.get('k_hash'):
                                col_info3.caption(f"🔑 {tunnel['k_hash'][:8]}...")
                            else:
                                col_info3.caption("🔓 Tunnel ouvert")
                        except:
                            pass
            else:
                st.info("Vous n'êtes membre d'aucun tunnel.")
                if st.button("🔍 Explorer les tunnels publics"):
                    st.switch_page("messages_page")  # ou redirection vers la page des tunnels
        except Exception as e:
            st.info("Module tunnels en cours d'initialisation")

    # =============================================
    # ONGLET 4 : MODIFIER LE PROFIL
    # =============================================
    with tab_edit:
        st.subheader("⚙️ Modifier mon Profil")
        
        # Changement d'avatar
        with st.expander("📸 Changer ma photo", expanded=False):
            uploaded_file = st.file_uploader("Choisir une image (max 5 Mo)", type=["png", "jpg", "jpeg"])
            if uploaded_file:
                if uploaded_file.size > 5 * 1024 * 1024:
                    st.error("Image trop volumineuse (max 5 Mo).")
                else:
                    try:
                        # Upload vers le bucket avatars
                        ext = uploaded_file.name.split(".")[-1]
                        file_name = f"{user.id}/{uuid.uuid4()}.{ext}"
                        
                        supabase.storage.from_("avatars").upload(
                            path=file_name,
                            file=uploaded_file.getvalue(),
                            file_options={"content-type": f"image/{ext}"}
                        )
                        
                        # Récupérer l'URL publique
                        avatar_url = supabase.storage.from_("avatars").get_public_url(file_name)
                        
                        # Mettre à jour le profil
                        supabase.table("profiles").update({
                            "profile_pic": avatar_url
                        }).eq("id", user.id).execute()
                        
                        st.success("✅ Photo de profil mise à jour !")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'upload : {e}")

        # Formulaire d'édition du profil
        with st.form("edit_profile_form"):
            new_username = st.text_input("Nom d'utilisateur", value=profile["username"])
            new_bio = st.text_area("Bio", value=profile.get("bio", ""), max_chars=160,
                                  help="160 caractères maximum")
            new_location = st.text_input("Localisation", value=profile.get("location", ""))
            
            submitted = st.form_submit_button("💾 Sauvegarder les modifications", use_container_width=True)
            
            if submitted:
                try:
                    updates = {
                        "username": new_username,
                        "bio": new_bio,
                        "location": new_location
                    }
                    
                    supabase.table("profiles").update(updates).eq("id", user.id).execute()
                    
                    st.success("✅ Profil mis à jour avec succès !")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    if "duplicate key" in str(e):
                        st.error("Ce nom d'utilisateur est déjà pris.")
                    else:
                        st.error(f"Erreur lors de la mise à jour : {e}")

    # =============================================
    # ONGLET 5 : COFFRE TTU (CLÉS)
    # =============================================
    with tab_vault:
        st.subheader("🔐 Coffre TTU-MC³")
        
        st.markdown("""
        Le coffre stocke l'historique de vos clés de courbure K utilisées pour les tunnels.
        Chaque clé est hachée pour des raisons de sécurité.
        """)
        
        # Clé actuelle en session
        if "current_k" in st.session_state:
            st.success("✅ Clé K active dans cette session")
            current_hash = hashlib.sha256(st.session_state.current_k.encode()).hexdigest()
            st.code(f"Hash : {current_hash}", language="text")
        else:
            st.warning("⚠️ Aucune clé active. Vos tunnels sont actuellement invisibles.")
        
        st.divider()
        
        # Historique des clés utilisées (si table user_keys existe)
        try:
            keys_history = supabase.table("user_keys").select("*").eq("user_id", user.id).order("created_at", desc=True).limit(10).execute()
            
            if keys_history.data:
                st.write("**📜 Historique des clés utilisées**")
                for k in keys_history.data:
                    col_k1, col_k2, col_k3 = st.columns([2, 1, 2])
                    col_k1.caption(f"🔑 {k['key_hash'][:16]}...")
                    col_k2.caption(f"{k['created_at'][:10]}")
                    col_k3.caption(f"Tunnel: {k.get('tunnel_name', 'Inconnu')}")
            else:
                st.info("Aucune clé enregistrée. Utilisez un tunnel pour générer une clé.")
        except:
            # Si la table n'existe pas, on ignore
            pass
        
        # Informations sur le chiffrement
        with st.expander("🔒 Comment fonctionne le chiffrement TTU-MC³ ?"):
            st.markdown("""
            - **Clé K** : Votre clé secrète partagée (jamais stockée en clair)
            - **Hachage** : La clé est hachée avec SHA-256 pour identifier les tunnels
            - **Chiffrement** : Les messages sont chiffrés avec Fernet (AES 128)
            - **Déchiffrement** : Impossible sans la clé K exacte
            
            > Le coffre ne stocke que les hashs, jamais les clés elles-mêmes.
            """)

# =====================================================
# INTERFACE POUR REJOINDRE UN TUNNEL
# =====================================================
def join_tunnel_interface():
    """Interface pour rejoindre un tunnel avec une clé."""
    
    st.subheader("🔑 Rejoindre un Tunnel")
    
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            tunnel_id_input = st.text_input("ID du Tunnel", placeholder="Copiez l'identifiant ici...", key="join_tunnel_id")
        with col2:
            # Bouton pour coller depuis le presse-papiers (aide)
            if st.button("📋 Coller", help="Coller l'ID depuis le presse-papiers"):
                # Note: Streamlit ne peut pas accéder directement au presse-papiers,
                # mais on peut utiliser une astuce avec st.markdown
                st.info("Utilisez Ctrl+V (Cmd+V sur Mac) pour coller")
        
        key_input = st.text_input("Clé d'accès", type="password", placeholder="Entrez la clé secrète...", key="join_tunnel_key")
        
        if st.button("🔓 Débloquer l'accès", use_container_width=True, type="primary"):
            if tunnel_id_input and key_input:
                with st.spinner("Vérification en cours..."):
                    try:
                        # 1. Vérifier si le tunnel existe
                        tunnel = supabase.table("tunnels").select("name, creator_id").eq("id", tunnel_id_input).maybe_single().execute()
                        
                        if tunnel.data:
                            # 2. Vérifier que l'utilisateur n'est pas déjà membre
                            member_check = supabase.table("tunnel_members").select("id").eq("tunnel_id", tunnel_id_input).eq("user_id", user.id).execute()
                            
                            if not member_check.data:
                                # 3. Ajouter l'utilisateur comme membre
                                supabase.table("tunnel_members").insert({
                                    "user_id": user.id,
                                    "tunnel_id": tunnel_id_input,
                                    "joined_at": datetime.now().isoformat()
                                }).execute()
                            
                            # 4. Enregistrer la clé pour cet utilisateur
                            hashed_key = hashlib.sha256(key_input.encode()).hexdigest()
                            
                            # Appeler la fonction RPC existante ou insérer directement
                            try:
                                supabase.rpc('record_user_key', {
                                    'p_user_id': user.id,
                                    'p_key_hash': hashed_key,
                                    'p_tunnel_id': tunnel_id_input,
                                    'p_tunnel_name': tunnel.data['name']
                                }).execute()
                            except Exception as rpc_error:
                                # Fallback: insertion directe si la RPC n'existe pas
                                supabase.table("user_keys").insert({
                                    "user_id": user.id,
                                    "key_hash": hashed_key,
                                    "tunnel_id": tunnel_id_input,
                                    "tunnel_name": tunnel.data['name'],
                                    "created_at": datetime.now().isoformat()
                                }).execute()
                            
                            # 5. Stocker la clé en session pour cette session
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
# INTERFACE POUR COPIER L'ID D'UN TUNNEL
# =====================================================
def copy_tunnel_id_button(tunnel_id, tunnel_name):
    """Affiche un bouton pour copier l'ID du tunnel."""
    
    # Générer un ID unique pour le textarea caché
    textarea_id = f"hidden_text_{tunnel_id}"
    
    # Créer un textarea caché avec l'ID
    st.markdown(f"""
    <textarea id="{textarea_id}" style="position: absolute; left: -9999px;">{tunnel_id}</textarea>
    
    <script>
    function copyToClipboard_{tunnel_id.replace('-', '_')}() {{
        var copyText = document.getElementById("{textarea_id}");
        copyText.select();
        copyText.setSelectionRange(0, 99999);
        document.execCommand("copy");
        
        // Afficher une notification
        var tooltip = document.getElementById("tooltip_{tunnel_id.replace('-', '_')}");
        tooltip.style.display = "inline";
        setTimeout(function() {{ tooltip.style.display = "none"; }}, 2000);
    }}
    </script>
    
    <div style="display: flex; align-items: center; gap: 10px;">
        <button onclick="copyToClipboard_{tunnel_id.replace('-', '_')}()" 
                style="background: #21262d; border: 1px solid #ff9d00; border-radius: 20px; 
                       color: white; padding: 5px 15px; cursor: pointer; font-size: 14px;">
            📋 Copier l'ID
        </button>
        <span id="tooltip_{tunnel_id.replace('-', '_')}" style="display: none; color: #ff9d00; font-size: 12px;">
            ✓ Copié !
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # Alternative Streamlit si le JavaScript pose problème
    with st.expander("📋 Voir l'ID à copier", expanded=False):
        st.code(tunnel_id, language="text")
        st.caption("Sélectionnez et copiez (Ctrl+C) cet identifiant")

def messages_page():
    st.header("🌌 Tunnel Souverain TTU-MC³")

    # --- 1. BARRE LATÉRALE : STABILISATION K + CONTRÔLES ---
    with st.sidebar:
        st.subheader("Paramètres de Stabilité")
        shared_k = st.text_input("Clé de Courbure K (Secret)", type="password")
        
        if not shared_k:
            st.info("Tunnel en état fantôme. Entrez votre clé K.")
            st.stop()
            
        # Stockage de la clé en session
        st.session_state.current_k = shared_k
            
        tunnel_id_hash = hashlib.sha256(shared_k.encode()).hexdigest()
        st.success(f"Phase Cohérente : {tunnel_id_hash[:8]}")

        st.divider()
        
        # 🔘 AJOUTER L'INTERFACE POUR REJOINDRE UN TUNNEL ICI
        with st.expander("🔑 Rejoindre un Tunnel", expanded=False):
            join_tunnel_interface()
        
        st.divider()
        
        # 🔘 Toggle pour activer/désactiver le mode temps réel
        real_time = st.toggle("📡 Mode Temps Réel", value=True,
                              help="Actualisation automatique (intervalle adaptatif)")

    # --- 2. RECHERCHE OU CRÉATION DU TUNNEL PAR K_HASH ---
    try:
        existing = supabase.table("tunnels").select("id").eq("k_hash", tunnel_id_hash).execute()
        if existing.data:
            tunnel_id = existing.data[0]['id']
            member_check = supabase.table("tunnel_members").select("id").eq("tunnel_id", tunnel_id).eq("user_id", user.id).execute()
            if not member_check.data:
                supabase.table("tunnel_members").insert({"user_id": user.id, "tunnel_id": tunnel_id}).execute()
        else:
            new_tunnel = supabase.table("tunnels").insert({
                "name": f"Tunnel {shared_k[:4]}", 
                "creator_id": user.id, 
                "k_hash": tunnel_id_hash
            }).execute()
            if new_tunnel.data:
                tunnel_id = new_tunnel.data[0]['id']
                supabase.table("tunnel_members").insert({
                    "user_id": user.id, 
                    "tunnel_id": tunnel_id
                }).execute()
    except Exception as e:
        st.error(f"Erreur lors de la synchronisation du tunnel : {e}")
        return

    # --- 3. DONNÉES MISES EN CACHE ---
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

    # --- 4. SÉLECTION DU CANAL ---
    default_index = list(t_options.keys()).index(tunnel_id) if tunnel_id in t_options else 0
    selected_t_id = st.selectbox(
        "Sélectionner le canal",
        options=list(t_options.keys()),
        format_func=lambda x: t_options[x],
        index=default_index,
        key="tunnel_selector"
    )

    # --- 5. FRAGMENT DE CHAT AUTO-RAFRÎCHISSANT ---
    @st.fragment
    def chat_fragment(tunnel_id, user_map, shared_k, real_time):
        # Initialiser le timestamp du dernier message
        last_ts_key = f"last_ts_{tunnel_id}"
        if last_ts_key not in st.session_state:
            st.session_state[last_ts_key] = "1970-01-01T00:00:00"

        # Récupérer les messages plus récents que le dernier timestamp
        new_msgs = supabase.table("messages") \
            .select("*") \
            .eq("tunnel_id", tunnel_id) \
            .gt("created_at", st.session_state[last_ts_key]) \
            .order("created_at") \
            .execute()

        if new_msgs.data:
            st.session_state[last_ts_key] = new_msgs.data[-1]['created_at']

        # Récupérer tous les messages pour affichage complet
        all_msgs = supabase.table("messages") \
            .select("*") \
            .eq("tunnel_id", tunnel_id) \
            .order("created_at") \
            .execute()

        # Conteneur de chat
        chat_container = st.container(height=450)
        with chat_container:
            for m in all_msgs.data:
                is_me = m["sender"] == user.id
                author = user_map.get(m["sender"], "Inconnu")
                try:
                    clear_text = decrypt_text(m["text"])  # utilise la clé en session
                    with st.chat_message("user" if is_me else "assistant"):
                        st.markdown(f"**{author}** : {clear_text}")
                except Exception:
                    st.caption("🔒 Message crypté")

        # Zone de saisie
        if prompt := st.chat_input("Projeter un message..."):
            encrypted_val = encrypt_text(prompt)
            supabase.table("messages").insert({
                "sender": user.id,
                "tunnel_id": tunnel_id,
                "text": encrypted_val,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            st.session_state[last_ts_key] = datetime.utcnow().isoformat()
            st.rerun()  # relance le fragment immédiatement

        # --- BOUTON MANUEL D'ACTUALISATION ---
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("🔄", help="Actualiser manuellement"):
                st.rerun()

        # --- POLLING AUTOMATIQUE ADAPTATIF (température du tunnel) ---
        if real_time:
            poll_key = f"poll_interval_{tunnel_id}"
            if poll_key not in st.session_state:
                st.session_state[poll_key] = 5  # intervalle initial (secondes)
            
            # Ajustement basé sur l'activité
            if new_msgs.data:
                # Nouveaux messages → on accélère
                st.session_state[poll_key] = 5
            else:
                # Aucun nouveau message → on ralentit progressivement (max 120s)
                st.session_state[poll_key] = min(st.session_state[poll_key] * 1.2, 120)
            
            # Affichage optionnel de l'intervalle
            with col2:
                st.caption(f"⚡ prochain rafraîchissement dans {st.session_state[poll_key]:.0f}s")
            
            # Pause puis rerun du fragment
            time.sleep(st.session_state[poll_key])
            st.rerun()

    # --- 6. APPEL DU FRAGMENT ---
    chat_fragment(selected_t_id, user_map, shared_k, real_time)

# =====================================================
# DESIGN & CSS (SANS BUG)
# =====================================================
def apply_custom_design():
    """Applique le style CSS personnalisé à l'application."""
    st.markdown("""
        <style>
        .stApp { background-color: #0e1117; }
        [data-testid="stMetricValue"] { font-size: 1.6rem !important; color: #ff9d00 !important; }
        .stButton>button { width: 100%; border-radius: 10px; font-weight: 600; }
        div[data-testid="stExpander"] { border-radius: 10px; border: 1px solid #30363d; }
        /* Style pour les cartes d'annonces */
        div[data-testid="column"] > div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] {
            transition: transform 0.2s;
        }
        div[data-testid="column"] > div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"]:hover {
            transform: scale(1.02);
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        </style>
    """, unsafe_allow_html=True)

# =====================================================
# NOTIFICATIONS
# =====================================================
def show_notifications():
    """Affiche les notifications non lues de l'utilisateur."""
    try:
        notifs = supabase.table("notifications").select("*").eq("user_id", user.id).eq("is_read", False).execute()
        if notifs.data:
            with st.expander(f"🔔 Notifications ({len(notifs.data)})", expanded=False):
                for n in notifs.data:
                    col_n1, col_n2 = st.columns([4, 1])
                    col_n1.write(f"**{n['title']}**\n{n['message']}")
                    if col_n2.button("✓", key=f"read_{n['id']}"):
                        supabase.table("notifications").update({"is_read": True}).eq("id", n['id']).execute()
                        st.rerun()
    except Exception as e:
        # En cas d'erreur (ex: table pas encore créée), on ignore silencieusement
        pass

# =====================================================
# PAGE MARKETPLACE (VERSION COMPLÈTE ET CORRIGÉE)
# =====================================================
def marketplace_page():
    apply_custom_design()  # Maintenant défini avant !
    st.header("🏪 Marketplace Souverain")

    # --- SECTION NOTIFICATIONS ---
    show_notifications()

    # --- INITIALISATION DES ÉTATS DE SESSION POUR FILTRES ---
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = "Toutes"
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = {}

    # --- SIDEBAR : FILTRES ET ACTIONS RAPIDES ---
    with st.sidebar:
        st.subheader("🔍 Filtres")
        search = st.text_input("Rechercher un article", value=st.session_state.search_query,
                               key="search_input", placeholder="Nom, description...")
        st.session_state.search_query = search

        # Catégories (soit depuis la base, soit en dur)
        try:
            categories_resp = supabase.table("categories").select("name").execute()
            cat_list = ["Toutes"] + [c["name"] for c in categories_resp.data]
        except:
            cat_list = ["Toutes", "Art", "Technologie", "Services", "Autre"]
        category = st.selectbox("Catégorie", cat_list,
                                index=cat_list.index(st.session_state.selected_category) if st.session_state.selected_category in cat_list else 0)
        st.session_state.selected_category = category

        st.divider()
        st.subheader("💰 Mon Portefeuille")
        try:
            profile = supabase.table("profiles").select("kc_balance").eq("id", user.id).execute()
            balance = profile.data[0]["kc_balance"] if profile.data else 0
            st.metric("Solde KC", f"{balance:,.0f}")
        except Exception:
            st.metric("Solde KC", "N/A")

        if st.button("📥 Recharger", use_container_width=True):
            st.info("Fonctionnalité à venir")

    # --- DASHBOARD VENDEUR ---
    with st.expander("📊 Mon Dashboard Vendeur", expanded=False):
        my_listings = supabase.table("marketplace_listings").select("*").eq("user_id", user.id).execute()
        if my_listings.data:
            df = pd.DataFrame(my_listings.data)
            total_sales = df['sales_count'].sum() if 'sales_count' in df.columns else 0
            total_revenue = (df['sales_count'] * df['price_kc']).sum() if 'sales_count' in df.columns else 0
            avg_price = df['price_kc'].mean()
            col_d1, col_d2, col_d3, col_d4 = st.columns(4)
            col_d1.metric("📦 Ventes", f"{total_sales}")
            col_d2.metric("💰 Revenus", f"{total_revenue:,.0f} KC")
            col_d3.metric("📈 Prix moyen", f"{avg_price:,.0f} KC")
            col_d4.metric("🏷️ Articles", f"{len(df)}")

            if total_sales > 0:
                st.subheader("Performances des ventes")
                df_sorted = df.sort_values('sales_count', ascending=False).head(10)
                st.bar_chart(df_sorted.set_index('title')['sales_count'])
            else:
                st.info("Aucune vente enregistrée pour le moment.")
        else:
            st.info("Publiez votre premier article pour voir vos stats.")

    # --- PUBLIER UNE ANNONCE ---
    with st.expander("➕ Publier une annonce"):
        with st.form("new_listing_form", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                title = st.text_input("Nom de l'article *", max_chars=100)
                price = st.number_input("Prix (KC) *", min_value=0.0, step=10.0)
                category = st.selectbox("Catégorie", cat_list[1:] if len(cat_list)>1 else ["Général"])
            with col_f2:
                condition = st.selectbox("État", ["Neuf", "Comme neuf", "Bon état", "État correct"])
                stock = st.number_input("Quantité", min_value=1, value=1, step=1)
                img = st.file_uploader("Image (optionnelle)", type=["jpg", "jpeg", "png"])
            description = st.text_area("Description *", height=100)

            if st.form_submit_button("🚀 Lancer la vente", use_container_width=True):
                if not title or not description or price <= 0:
                    st.error("Veuillez remplir tous les champs obligatoires (*).")
                else:
                    media_url = None
                    if img is not None:
                        # Upload vers Supabase Storage
                        file_ext = img.name.split(".")[-1]
                        file_name = f"{uuid.uuid4()}.{file_ext}"
                        try:
                            supabase.storage.from_("marketplace").upload(file_name, img.getvalue(),
                                                                          {"content-type": img.type})
                            media_url = supabase.storage.from_("marketplace").get_public_url(file_name)
                        except Exception as e:
                            st.warning(f"L'image n'a pas pu être uploadée : {e}")

                    try:
                        supabase.table("marketplace_listings").insert({
                            "user_id": user.id,
                            "title": title,
                            "description": description,
                            "price_kc": price,
                            "category": category,
                            "condition": condition,
                            "stock": stock,
                            "media_url": media_url,
                            "is_active": True,
                            "created_at": datetime.utcnow().isoformat()
                        }).execute()
                        st.success("✅ Annonce publiée avec succès !")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la publication : {e}")

    st.divider()

    # --- REQUÊTE DES ANNONCES AVEC FILTRES ---
    query = supabase.table("marketplace_listings").select("*, profiles(username)").eq("is_active", True)
    if st.session_state.search_query:
        query = query.ilike("title", f"%{st.session_state.search_query}%")
    if st.session_state.selected_category != "Toutes":
        query = query.eq("category", st.session_state.selected_category)
    listings = query.order("created_at", desc=True).execute()

    if not listings.data:
        st.info("😕 Aucune annonce ne correspond à vos critères.")
        return

    # --- AFFICHAGE DES ANNONCES EN GRILLE ---
    st.subheader(f"📌 Annonces disponibles ({len(listings.data)})")
    cols = st.columns(3)
    for idx, item in enumerate(listings.data):
        with cols[idx % 3]:
            with st.container(border=True):
                # Image
                if item.get("media_url"):
                    st.image(item["media_url"], use_container_width=True)
                else:
                    st.image("https://placehold.co/300x200/2d3a4a/white?text=No+Image", use_container_width=True)

                # Titre et prix
                st.markdown(f"**{item['title']}**")
                st.markdown(f"<h3 style='color:#ff9d00;'>{item['price_kc']:,.0f} KC</h3>", unsafe_allow_html=True)

                # Métadonnées
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.caption(f"👤 {item['profiles']['username']}")
                with col_info2:
                    st.caption(f"📦 Stock: {item.get('stock', 1)}")

                # Description extensible
                with st.expander("Description"):
                    st.write(item['description'])

                # Actions selon propriétaire
                if item["user_id"] == user.id:
                    # Actions vendeur
                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        if st.button("✏️ Modifier", key=f"edit_{item['id']}", use_container_width=True):
                            st.session_state.edit_mode[item['id']] = True
                    with col_a2:
                        if st.button("🚫 Retirer", key=f"del_{item['id']}", type="secondary", use_container_width=True):
                            supabase.table("marketplace_listings").update({"is_active": False}).eq("id", item["id"]).execute()
                            st.toast("Annonce retirée.")
                            time.sleep(1)
                            st.rerun()
                else:
                    # Actions acheteur
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        # Favoris
                        fav = supabase.table("user_favorites").select("id").eq("user_id", user.id).eq("listing_id", item["id"]).execute()
                        if fav.data:
                            if st.button("★", key=f"fav_{item['id']}", help="Retirer des favoris", use_container_width=True):
                                supabase.table("user_favorites").delete().eq("user_id", user.id).eq("listing_id", item["id"]).execute()
                                st.rerun()
                        else:
                            if st.button("☆", key=f"fav_{item['id']}", help="Ajouter aux favoris", use_container_width=True):
                                supabase.table("user_favorites").insert({"user_id": user.id, "listing_id": item["id"]}).execute()
                                st.rerun()
                    with col_b2:
                        # Achat
                        if st.button("🛒 Acheter", key=f"buy_{item['id']}", type="primary", use_container_width=True):
                            try:
                                supabase.rpc('process_marketplace_purchase', {
                                    'p_listing_id': item['id'],
                                    'p_buyer_id': user.id,
                                    'p_seller_id': item['user_id'],
                                    'p_amount': float(item['price_kc'])
                                }).execute()

                                supabase.table("notifications").insert({
                                    "user_id": item['user_id'],
                                    "title": "💰 Article Vendu !",
                                    "message": f"Votre article '{item['title']}' a été acheté pour {item['price_kc']} KC."
                                }).execute()

                                st.balloons()
                                st.success("Achat réussi !")
                                time.sleep(2)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors de l'achat : {e}")

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
elif menu == "👤 Mon Profil":
    profile_page()
elif menu == "✉️ Messages":
    messages_page()
elif menu == "🏪 Marketplace":
    marketplace_page()
elif menu == "💰 Wallet":
    wallet_page()
elif menu == "⚙️ Paramètres":
    settings_page()
elif menu == "🛡️ Admin":
    admin_page()
