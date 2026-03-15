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
    st.header("🌐 Fil d'actualité")
    with st.expander("✍️ Créer un post", expanded=False):
        with st.form("new_post"):
            post_text = st.text_area("Quoi de neuf ?")
            media_file = st.file_uploader("Image / Vidéo / Audio", type=["png", "jpg", "jpeg", "mp4", "mp3", "wav"])
            submitted = st.form_submit_button("Publier")
            if submitted and (post_text or media_file):
                # Vérification taille fichier
                if media_file and media_file.size > 50 * 1024 * 1024:  # 50 Mo max
                    st.error("Le fichier est trop volumineux (max 50 Mo).")
                    st.stop()
                try:
                    media_path = None
                    media_type = None
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

                    post_data = {
                        "user_id": user.id,
                        "text": post_text,
                        "media_path": media_path,
                        "media_type": media_type,
                        "created_at": datetime.now().isoformat()
                    }
                    supabase.table("posts").insert(post_data).execute()
                    st.success("Post publié !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de la publication : {e}")

    # Récupération des posts avec les profils
    posts = supabase.table("posts").select(
        "*, profiles!inner(username, profile_pic)"
    ).order("created_at", desc=True).limit(50).execute()

    if not posts.data:
        st.info("Aucun post pour le moment. Sois le premier à poster !")
        return

    for post in posts.data:
        with st.container():
            col1, col2 = st.columns([1, 20])
            with col1:
                pic = post["profiles"].get("profile_pic")
                if pic:
                    st.image(pic, width=40)
                else:
                    st.image("https://via.placeholder.com/40", width=40)
            with col2:
                st.markdown(f"**{post['profiles']['username']}** · {post['created_at'][:10]}")
            st.write(post["text"])

            # Affichage du média
            if post.get("media_path"):
                file_url = get_signed_url("media", post["media_path"])
                if file_url:
                    if post.get("media_type") and "image" in post["media_type"]:
                        st.image(file_url)
                    elif post.get("media_type") and "video" in post["media_type"]:
                        st.video(file_url)
                    elif post.get("media_type") and "audio" in post["media_type"]:
                        st.audio(file_url)
                else:
                    st.warning("Média temporairement indisponible")

            # Statistiques du post
            stats = get_post_stats(post["id"])
            st.markdown(f"❤️ {stats['likes']}  |  💬 {stats['comments']}  |  🔥 {stats['reactions']}")

            # Boutons d'interaction
            col_a, col_b, col_c, col_d, col_e = st.columns([1, 1, 1, 1, 1])
            with col_a:
                if st.button("❤️", key=f"like_{post['id']}"):
                    like_post(post["id"])
            with col_b:
                with st.popover("💬"):
                    comments = supabase.table("comments").select(
                        "*, profiles(username)"
                    ).eq("post_id", post["id"]).order("created_at").execute()
                    for c in comments.data:
                        st.markdown(f"**{c['profiles']['username']}** : {c['text']}")
                    new_comment = st.text_input("Votre commentaire", key=f"input_{post['id']}")
                    if st.button("Envoyer", key=f"send_{post['id']}"):
                        add_comment(post["id"], new_comment)
            with col_c:
                if st.button("🔥 (10 KC)", key=f"fire_{post['id']}"):
                    process_emoji_payment(post["id"], post["user_id"], "🔥")
            with col_d:
                if st.button("💎 (50 KC)", key=f"diamond_{post['id']}"):
                    process_emoji_payment(post["id"], post["user_id"], "💎")
            with col_e:
                if st.button("👑 (100 KC)", key=f"crown_{post['id']}"):
                    process_emoji_payment(post["id"], post["user_id"], "👑")

            # Bouton de suppression (si propriétaire ou admin)
            if post["user_id"] == user.id or is_admin():
                if st.button("🗑️ Supprimer", key=f"del_{post['id']}"):
                    delete_post(post["id"])

            st.divider()

def profile_page():
    st.header("👤 Mon Profil")
    with st.expander("Changer ma photo de profil", expanded=False):
        uploaded_file = st.file_uploader("Choisir une image", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            # Limite de taille (5 Mo)
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

def marketplace_page():
    apply_custom_design()
    st.header("🏪 Marketplace Souverain")

    # --- SECTION NOTIFICATIONS (déjà existante, conservée) ---
    show_notifications()

    # --- INITIALISATION DES ÉTATS DE SESSION POUR FILTRES ---
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = "Toutes"

    # --- SIDEBAR : FILTRES ET ACTIONS RAPIDES ---
    with st.sidebar:
        st.subheader("🔍 Filtres")
        search = st.text_input("Rechercher un article", value=st.session_state.search_query,
                               key="search_input", placeholder="Nom, description...")
        st.session_state.search_query = search

        # Récupération des catégories depuis la base (si table categories existe)
        try:
            categories_resp = supabase.table("categories").select("name").execute()
            cat_list = ["Toutes"] + [c["name"] for c in categories_resp.data]
        except:
            cat_list = ["Toutes", "Art", "Technologie", "Services", "Autre"]
        category = st.selectbox("Catégorie", cat_list, index=cat_list.index(st.session_state.selected_category) if st.session_state.selected_category in cat_list else 0)
        st.session_state.selected_category = category

        st.divider()
        st.subheader("💰 Mon Portefeuille")
        # Récupération du solde KC de l'utilisateur (à adapter selon ta table users/profiles)
        try:
            profile = supabase.table("profiles").select("kc_balance").eq("id", user.id).execute()
            balance = profile.data[0]["kc_balance"] if profile.data else 0
            st.metric("Solde KC", f"{balance:,.0f}")
        except:
            st.metric("Solde KC", "N/A")

        if st.button("📥 Recharger", use_container_width=True):
            st.info("Fonctionnalité à venir")  # ou lien vers un système de recharge

    # --- DASHBOARD VENDEUR AMÉLIORÉ ---
    with st.expander("📊 Mon Dashboard Vendeur", expanded=False):
        my_listings = supabase.table("marketplace_listings").select("*").eq("user_id", user.id).execute()
        if my_listings.data:
            df = pd.DataFrame(my_listings.data)
            # Calcul des ventes et revenus
            total_sales = df['sales_count'].sum() if 'sales_count' in df.columns else 0
            total_revenue = (df['sales_count'] * df['price_kc']).sum() if 'sales_count' in df.columns else 0
            avg_price = df['price_kc'].mean()

            col_d1, col_d2, col_d3, col_d4 = st.columns(4)
            col_d1.metric("📦 Ventes", f"{total_sales}")
            col_d2.metric("💰 Revenus", f"{total_revenue:,.0f} KC")
            col_d3.metric("📈 Prix moyen", f"{avg_price:,.0f} KC")
            col_d4.metric("🏷️ Articles", f"{len(df)}")

            # Graphique des ventes par article
            if total_sales > 0:
                st.subheader("Performances des ventes")
                df_sorted = df.sort_values('sales_count', ascending=False).head(10)
                st.bar_chart(df_sorted.set_index('title')['sales_count'])
            else:
                st.info("Aucune vente enregistrée pour le moment.")
        else:
            st.info("Publiez votre premier article pour voir vos stats.")

    # --- PUBLIER UNE ANNONCE AMÉLIORÉ ---
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
                    # Upload de l'image si fournie
                    media_url = None
                    if img is not None:
                        # Générer un nom unique
                        file_ext = img.name.split(".")[-1]
                        file_name = f"{uuid.uuid4()}.{file_ext}"
                        # Upload vers Supabase Storage (bucket 'marketplace')
                        try:
                            supabase.storage.from_("marketplace").upload(file_name, img.getvalue(), {"content-type": img.type})
                            media_url = supabase.storage.from_("marketplace").get_public_url(file_name)
                        except Exception as e:
                            st.warning(f"L'image n'a pas pu être uploadée : {e}")

                    # Insertion dans la base
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

    # --- CONSTRUCTION DE LA REQUÊTE DES ANNONCES AVEC FILTRES ---
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

    # Définir le nombre de colonnes en fonction de la largeur (responsive)
    # Utilisation de st.columns avec un nombre fixe (3) et laisser le CSS gérer le responsive
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

                # Description tronquée
                with st.expander("Description"):
                    st.write(item['description'])

                # Boutons d'action selon propriétaire
                if item["user_id"] == user.id:
                    # Actions pour le vendeur
                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        if st.button("✏️ Modifier", key=f"edit_{item['id']}", use_container_width=True):
                            st.session_state[f"edit_{item['id']}"] = True
                    with col_a2:
                        if st.button("🚫 Retirer", key=f"del_{item['id']}", type="secondary", use_container_width=True):
                            supabase.table("marketplace_listings").update({"is_active": False}).eq("id", item["id"]).execute()
                            st.toast("Annonce retirée.")
                            time.sleep(1)
                            st.rerun()
                else:
                    # Actions pour l'acheteur
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        # Bouton favoris
                        # Vérifier si déjà en favori
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
                                # Appel de la fonction RPC sécurisée (doit exister)
                                supabase.rpc('process_marketplace_purchase', {
                                    'p_listing_id': item['id'],
                                    'p_buyer_id': user.id,
                                    'p_seller_id': item['user_id'],
                                    'p_amount': float(item['price_kc'])
                                }).execute()

                                # Notification au vendeur
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
