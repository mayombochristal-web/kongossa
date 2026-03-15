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
def feed_page():
    apply_custom_design()  # garde le design de base si tu veux, mais on va le surcharger avec un design plus avancé
    apply_advanced_feed_design()  # design glassmorphism

    # Récupération du profil utilisateur (avatar)
    try:
        profile_data = supabase.table("profiles").select("profile_pic, username").eq("id", user.id).single().execute()
        profile = profile_data.data
    except:
        profile = {"profile_pic": None, "username": user.username}

    st.title("🌊 Flux Souverain")

    # =============================================
    # FONCTIONS UTILITAIRES AVANCÉES
    # =============================================
    @st.cache_data(ttl=3600)
    def get_cached_media_url(path: str) -> str:
        """URL signée mise en cache pour 1 heure."""
        try:
            res = supabase.storage.from_("media").create_signed_url(path, 3600)
            return res['signedURL']
        except Exception as e:
            st.error(f"Erreur de lien média : {e}")
            return None

    def upload_file(bucket: str, file, user_id: str) -> str:
        ext = file.name.split(".")[-1].lower()
        mime_map = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
            'mp4': 'video/mp4', 'mov': 'video/quicktime', 'webm': 'video/webm',
            'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'ogg': 'audio/ogg'
        }
        content_type = mime_map.get(ext, 'application/octet-stream')
        path = f"{user_id}/{uuid.uuid4()}.{ext}"
        try:
            supabase.storage.from_(bucket).upload(
                path=path,
                file=file.getvalue(),
                file_options={"content-type": content_type, "cache-control": "3600"}
            )
            return path
        except Exception as e:
            st.error(f"Erreur upload : {e}")
            return None

    def fast_tip(post_id: str, amount: int, emoji: str):
        """Don rapide de KC."""
        try:
            # Récupérer l'ID du propriétaire du post
            post_owner = supabase.table("posts").select("user_id").eq("id", post_id).single().execute()
            receiver_id = post_owner.data["user_id"]
            if receiver_id == user.id:
                st.warning("Vous ne pouvez pas vous envoyer un don à vous-même.")
                return
            supabase.rpc('process_tip', {
                'p_post_id': post_id,
                'p_sender_id': user.id,
                'p_receiver_id': receiver_id,
                'p_amount': amount,
                'p_emoji': emoji
            }).execute()
            # Notification
            supabase.table("notifications").insert({
                "user_id": receiver_id,
                "title": f"🎁 Don reçu !",
                "message": f"{user.username} vous a envoyé {amount} KC avec {emoji}."
            }).execute()
            st.toast(f"💸 Don de {amount} KC envoyé !")
            time.sleep(0.5)
            st.rerun()
        except Exception as e:
            st.error(f"Erreur de transaction : {e}")

    def delete_post(post_id: str):
        try:
            post = supabase.table("posts").select("media_path").eq("id", post_id).single().execute()
            if post.data and post.data.get("media_path"):
                supabase.storage.from_("media").remove([post.data["media_path"]])
            supabase.table("posts").delete().eq("id", post_id).execute()
            st.toast("Post supprimé.")
        except Exception as e:
            st.error(f"Erreur suppression : {e}")

    # =============================================
    # SECTION TRENDING (Posts populaires en KC)
    # =============================================
    st.subheader("🔥 Tendances")
    try:
        # On récupère les posts des dernières 24h, on les trie par somme des tips
        # Si table 'tips' existe, on peut faire une requête plus précise. Sinon, on se base sur les likes (simulé).
        # Ici, on suppose que la table 'tips' enregistre les dons avec 'post_id' et 'amount'.
        # On va faire une requête avec jointure pour avoir les posts + total des dons.
        trending_query = """
        SELECT p.id, p.user_id, p.text, p.media_path, p.media_type, p.created_at,
               pr.username, pr.profile_pic,
               COALESCE(SUM(t.amount), 0) as total_tips
        FROM posts p
        JOIN profiles pr ON p.user_id = pr.id
        LEFT JOIN tips t ON p.id = t.post_id AND t.created_at > NOW() - INTERVAL '24 hours'
        WHERE p.created_at > NOW() - INTERVAL '24 hours'
        GROUP BY p.id, pr.username, pr.profile_pic
        ORDER BY total_tips DESC
        LIMIT 5
        """
        # On exécute la requête SQL via Supabase (nécessite la fonction RPC ou client SQL)
        # Alternative : utiliser le client SQL raw si disponible.
        # Sinon, on peut simplement prendre les derniers posts et compter les dons en mémoire (simplifié)
        # Pour éviter la complexité, on va utiliser une approche simple : récupérer tous les posts récents et les trier manuellement.
        recent = supabase.table("posts").select("*, profiles!inner(username, profile_pic)").gte("created_at", (datetime.utcnow() - timedelta(days=1)).isoformat()).order("created_at", desc=True).limit(20).execute()
        if recent.data:
            # Récupérer les tips pour ces posts (si table tips existe)
            post_ids = [p['id'] for p in recent.data]
            tips = supabase.table("tips").select("post_id, amount").in_("post_id", post_ids).gte("created_at", (datetime.utcnow() - timedelta(days=1)).isoformat()).execute()
            tip_sum = {}
            for tip in tips.data:
                tip_sum[tip['post_id']] = tip_sum.get(tip['post_id'], 0) + tip['amount']
            # Ajouter le total à chaque post
            for p in recent.data:
                p['total_tips'] = tip_sum.get(p['id'], 0)
            # Trier
            trending = sorted(recent.data, key=lambda x: x['total_tips'], reverse=True)[:5]
        else:
            trending = []
    except Exception as e:
        st.warning("Module tendances temporairement indisponible.")
        trending = []

    if trending:
        cols = st.columns(len(trending))
        for i, post in enumerate(trending):
            with cols[i]:
                with st.container(border=True):
                    if post.get("media_path"):
                        media_url = get_cached_media_url(post["media_path"])
                        if media_url:
                            ext = post["media_path"].split(".")[-1].lower()
                            if ext in ['jpg','jpeg','png','webp']:
                                st.image(media_url, use_container_width=True)
                            elif ext in ['mp4','mov','webm']:
                                st.video(media_url)
                    st.markdown(f"**{post['profiles']['username']}**")
                    st.caption(f"🔥 {post['total_tips']} KC")
    else:
        st.caption("Aucune tendance pour l'instant.")

    st.divider()

    # =============================================
    # QUICK PUBLISH (Style FB Modern)
    # =============================================
    with st.container(border=True):
        col_av, col_in = st.columns([1, 5])
        with col_av:
            avatar = profile.get("profile_pic")
            st.image(avatar if avatar else "https://via.placeholder.com/50", width=50)
        with col_in:
            post_text = st.text_area("Exprimez-vous...", placeholder="Quoi de neuf ?", label_visibility="collapsed", key="post_input")

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            upload = st.file_uploader("📷 Média", type=["png", "jpg", "jpeg", "mp4", "mov", "webm", "mp3", "wav", "ogg"], label_visibility="collapsed", key="media_upload")
        with c2:
            if st.button("🚀 Propulser", use_container_width=True, type="primary"):
                if post_text or upload:
                    try:
                        media_path = None
                        media_type = None
                        if upload:
                            ext = upload.name.split(".")[-1].lower()
                            media_path = upload_file("media", upload, user.id)
                            media_type = f"image/{ext}" if ext in ['jpg','jpeg','png','webp'] else f"video/{ext}" if ext in ['mp4','mov','webm'] else f"audio/{ext}"
                        supabase.table("posts").insert({
                            "user_id": user.id,
                            "text": post_text if post_text else None,
                            "media_path": media_path,
                            "media_type": media_type,
                            "created_at": datetime.utcnow().isoformat()
                        }).execute()
                        st.toast("✨ Post publié !")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur publication : {e}")
                else:
                    st.warning("Écrivez quelque chose ou ajoutez un média.")

    # =============================================
    # RÉCUPÉRATION DU FLUX PRINCIPAL
    # =============================================
    try:
        posts = supabase.table("posts").select(
            "*, profiles!inner(username, profile_pic)"
        ).order("created_at", desc=True).limit(30).execute()
    except Exception as e:
        st.error("Impossible de charger le fil.")
        return

    if not posts.data:
        st.info("🌙 Le fil est calme... Lancez la première conversation !")
        return

    # =============================================
    # AFFICHAGE DES POSTS
    # =============================================
    for post in posts.data:
        with st.container(border=True):
            # Header
            col_avatar, col_header = st.columns([1, 6])
            with col_avatar:
                avatar = post["profiles"].get("profile_pic")
                st.image(avatar if avatar else "https://via.placeholder.com/50", width=50)
            with col_header:
                st.markdown(f"**{post['profiles']['username']}**")
                st.caption(f"{post['created_at'][:10]} à {post['created_at'][11:16]}")

            # Contenu texte
            if post.get("text"):
                st.markdown(f"### {post['text']}")

            # Média
            if post.get("media_path"):
                media_url = get_cached_media_url(post["media_path"])
                if media_url:
                    ext = post["media_path"].split(".")[-1].lower()
                    if ext in ['jpg','jpeg','png','webp']:
                        st.image(media_url, use_container_width=True)
                    elif ext in ['mp4','mov','webm']:
                        st.video(media_url)
                    elif ext in ['mp3','wav','ogg']:
                        st.audio(media_url)
                    else:
                        st.warning("Format non supporté.")
                else:
                    st.caption("Média indisponible")

            st.divider()

            # Barre d'actions hybride (visible)
            action_cols = st.columns([1, 1, 1, 1, 1])
            with action_cols[0]:
                if st.button("❤️", key=f"like_{post['id']}"):
                    st.toast("Like (à implémenter)")
            with action_cols[1]:
                if st.button("🔥", key=f"tip10_{post['id']}", help="10 KC"):
                    fast_tip(post['id'], 10, "🔥")
            with action_cols[2]:
                if st.button("💎", key=f"tip50_{post['id']}", help="50 KC"):
                    fast_tip(post['id'], 50, "💎")
            with action_cols[3]:
                if st.button("👑", key=f"tip100_{post['id']}", help="100 KC"):
                    fast_tip(post['id'], 100, "👑")
            with action_cols[4]:
                if post["user_id"] == user.id:
                    if st.button("🗑️", key=f"del_{post['id']}", help="Supprimer"):
                        delete_post(post["id"])
                        st.rerun()
                else:
                    # Optionnel : signaler, etc.
                    st.button("🚩", key=f"flag_{post['id']}", help="Signaler")

def profile_page():
    apply_custom_design()
    
    # Récupération du profil utilisateur
    try:
        profile_data = supabase.table("profiles").select("*").eq("id", user.id).single().execute()
        profile = profile_data.data
    except Exception as e:
        st.error("Impossible de charger votre profil.")
        return

    # --- HEADER PROFIL AVEC BADGES ---
    col_pic, col_info = st.columns([1, 3])
    with col_pic:
        pic = profile.get("profile_pic")
        if pic:
            st.image(pic, width=120)
        else:
            st.image("https://via.placeholder.com/120", width=120)
    with col_info:
        st.title(f"@{profile['username']}")
        st.caption(f"📍 {profile.get('location', 'Localisation non définie')}")
        st.write(f"*{profile.get('bio', 'Aucune bio rédigée.')}*")
        
        # Calcul des badges
        badges = []
        if profile.get("is_verified"):
            badges.append("✅ Vérifié")
        tunnels_created = supabase.table("tunnels").select("*", count="exact").eq("creator_id", user.id).execute().count
        if tunnels_created >= 5:
            badges.append("🔑 Maître des Tunnels")
        sales = supabase.table("marketplace_listings").select("*", count="exact").eq("user_id", user.id).gt("sales_count", 0).execute().count
        if sales >= 3:
            badges.append("💰 Marchand Émérite")
        if badges:
            st.markdown(" ".join([f"`{b}`" for b in badges]))

    st.divider()

    # --- ONGLETS DU PROFIL ---
    tab_stats, tab_activity, tab_tunnels, tab_edit, tab_vault = st.tabs([
        "📊 Statistiques", "📋 Activité", "🚇 Mes Tunnels", "⚙️ Modifier", "🔐 Coffre TTU"
    ])

    with tab_stats:
        # Statistiques sociales
        post_count = supabase.table("posts").select("*", count="exact").eq("user_id", user.id).execute().count
        followers = supabase.table("follows").select("*", count="exact").eq("followed", user.id).execute().count
        following = supabase.table("follows").select("*", count="exact").eq("follower", user.id).execute().count
        col1, col2, col3 = st.columns(3)
        col1.metric("📝 Posts", post_count)
        col2.metric("👥 Abonnés", followers)
        col3.metric("👤 Abonnements", following)

        # Statistiques économiques
        wallet = supabase.table("wallets").select("*").eq("user_id", user.id).single().execute()
        if wallet.data:
            st.subheader("💰 Portefeuille KC")
            col_w1, col_w2 = st.columns(2)
            col_w1.metric("Solde", f"{wallet.data['kongo_balance']:,.0f}")
            col_w2.metric("Total miné", f"{wallet.data['total_mined']:,.0f}")
            # Transactions récentes
            try:
                transactions = supabase.table("transactions").select("*").eq("user_id", user.id).order("created_at", desc=True).limit(5).execute()
                if transactions.data:
                    st.subheader("Dernières transactions")
                    for t in transactions.data:
                        st.caption(f"{t['created_at'][:10]} : {t['type']} de {t['amount']} KC")
            except:
                pass

        # Statistiques TTU
        st.subheader("🚇 Activité TTU-MC³")
        msg_count = supabase.table("messages").select("*", count="exact").eq("sender", user.id).execute().count
        tunnels_member = supabase.table("tunnel_members").select("*", count="exact").eq("user_id", user.id).execute().count
        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("Messages envoyés", msg_count)
        col_t2.metric("Tunnels rejoints", tunnels_member)
        col_t3.metric("Tunnels créés", tunnels_created)

    with tab_activity:
        st.subheader("📋 Activité récente")
        # Derniers messages
        last_msgs = supabase.table("messages") \
            .select("text, created_at, tunnel_id, tunnels(name)") \
            .eq("sender", user.id) \
            .order("created_at", desc=True) \
            .limit(5) \
            .execute()
        if last_msgs.data:
            st.write("**Derniers messages**")
            for m in last_msgs.data:
                tunnel_name = m['tunnels']['name'] if m.get('tunnels') else "Inconnu"
                st.caption(f"🗣️ Dans {tunnel_name} – {m['created_at'][:16]}")
        else:
            st.caption("Aucun message récent.")

        # Dernières annonces marketplace
        last_listings = supabase.table("marketplace_listings") \
            .select("title, created_at") \
            .eq("user_id", user.id) \
            .order("created_at", desc=True) \
            .limit(3) \
            .execute()
        if last_listings.data:
            st.write("**Dernières annonces**")
            for l in last_listings.data:
                st.caption(f"🛒 {l['title']} – {l['created_at'][:10]}")

        # Derniers achats (si table purchases existe)
        try:
            purchases = supabase.table("purchases") \
                .select("listing_id, marketplace_listings(title), created_at") \
                .eq("buyer_id", user.id) \
                .order("created_at", desc=True) \
                .limit(3) \
                .execute()
            if purchases.data:
                st.write("**Derniers achats**")
                for p in purchases.data:
                    st.caption(f"🛍️ {p['marketplace_listings']['title']} – {p['created_at'][:10]}")
        except:
            pass

    with tab_tunnels:
        st.subheader("🚇 Mes Tunnels")
        tunnels = supabase.table("tunnel_members") \
            .select("tunnel_id, tunnels(name, k_hash, created_at)") \
            .eq("user_id", user.id) \
            .execute()
        if tunnels.data:
            for t in tunnels.data:
                tunnel = t['tunnels']
                with st.container(border=True):
                    col_tn1, col_tn2 = st.columns([3,1])
                    col_tn1.markdown(f"**{tunnel['name']}**")
                    col_tn2.caption(f"Créé le {tunnel['created_at'][:10]}")
                    members = supabase.table("tunnel_members").select("*", count="exact").eq("tunnel_id", t['tunnel_id']).execute().count
                    # 🔑 Gestion de l'affichage du hash (peut être None)
                    key_hash = tunnel.get('k_hash')
                    if key_hash:
                        key_display = key_hash[:8]
                    else:
                        key_display = "pas de clé"
                    st.caption(f"👥 {members} membre(s) | 🔑 {key_display}")
        else:
            st.info("Vous n'êtes membre d'aucun tunnel.")

    with tab_edit:
        st.subheader("⚙️ Modifier mon profil")
        # Changement d'avatar
        with st.expander("📸 Changer ma photo", expanded=False):
            up_file = st.file_uploader("Upload (Max 5Mo)", type=["png", "jpg", "jpeg"])
            if up_file:
                if up_file.size > 5 * 1024 * 1024:
                    st.error("Trop lourd !")
                else:
                    try:
                        ext = up_file.name.split(".")[-1]
                        fn = f"avatars/{user.id}/{uuid.uuid4()}.{ext}"
                        supabase.storage.from_("avatars").upload(file=up_file.getvalue(), path=fn)
                        url = supabase.storage.from_("avatars").get_public_url(fn)
                        supabase.table("profiles").update({"profile_pic": url}).eq("id", user.id).execute()
                        st.success("Photo mise à jour !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

        # Formulaire de profil
        with st.form("edit_form"):
            new_username = st.text_input("Nom d'utilisateur", value=profile["username"])
            new_bio = st.text_area("Bio", value=profile.get("bio", ""), max_chars=150)
            new_loc = st.text_input("Localisation", value=profile.get("location", ""))
            if st.form_submit_button("💾 Sauvegarder les modifications"):
                supabase.table("profiles").update({
                    "username": new_username,
                    "bio": new_bio,
                    "location": new_loc
                }).eq("id", user.id).execute()
                st.toast("Profil mis à jour ✅")
                time.sleep(1)
                st.rerun()

    with tab_vault:
        st.subheader("🔐 Coffre TTU-MC³")
        st.markdown("""
        Le coffre stocke l'historique de vos clés de courbure K utilisées pour les tunnels.
        Chaque clé est hachée et stockée de manière sécurisée.
        """)
        # Récupération des clés utilisées (table user_keys)
        try:
            keys = supabase.table("user_keys").select("*").eq("user_id", user.id).order("created_at", desc=True).limit(10).execute()
            if keys.data:
                for k in keys.data:
                    col_k1, col_k2, col_k3 = st.columns([2,1,1])
                    col_k1.caption(f"🔑 {k['key_hash'][:16]}...")
                    col_k2.caption(f"Utilisée le {k['created_at'][:10]}")
                    col_k3.caption(f"Tunnel: {k.get('tunnel_name', 'N/A')}")
            else:
                st.info("Aucune clé enregistrée. Utilisez un tunnel pour générer une clé.")
        except:
            st.info("Module de coffre en cours d'initialisation.")
        
        # Affichage de la clé courante
        if "current_k" in st.session_state:
            st.success("Clé K active dans cette session")
            st.code(hashlib.sha256(st.session_state.current_k.encode()).hexdigest(), language="text")
        else:
            st.warning("Aucune clé active. Vos tunnels sont actuellement invisibles.")

def messages_page():
    st.header("🌌 Tunnel Souverain TTU-MC³")

    # --- 1. BARRE LATÉRALE : STABILISATION K + CONTRÔLES ---
    with st.sidebar:
        st.subheader("Paramètres de Stabilité")
        shared_k = st.text_input("Clé de Courbure K (Secret)", type="password")
        
        if not shared_k:
            st.info("Tunnel en état fantôme. Entrez votre clé K.")
            st.stop()
            
        # Stockage de la clé en session pour les fonctions de chiffrement
        st.session_state.current_k = shared_k
            
        tunnel_id_hash = hashlib.sha256(shared_k.encode()).hexdigest()
        st.success(f"Phase Cohérente : {tunnel_id_hash[:8]}")

        st.divider()
        # 🔘 Toggle pour activer/désactiver le mode temps réel
        real_time = st.toggle("📡 Mode Temps Réel", value=True,
                              help="Actualisation automatique (l'intervalle s'adapte à l'activité)")

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
