import streamlit as st
import os
import hashlib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from supabase import create_client, Client
from streamlit_autorefresh import st_autorefresh
from streamlit_mic_recorder import mic_recorder

# =====================================================
# CONFIG & CONNEXION SUPABASE
# =====================================================
st.set_page_config(page_title="Free_Kogossa", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

DATA_FOLDER = "data"
ASSETS_FOLDER = "assets"
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(ASSETS_FOLDER, exist_ok=True)

BUCKET_NAME = "uploads"       # Nom du bucket Supabase (doit être public)

# =====================================================
# SÉCURITÉ : HACHAGE DES MOTS DE PASSE
# =====================================================
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# =====================================================
# UPLOAD VERS SUPABASE STORAGE (URL PUBLIQUE)
# =====================================================
def upload_to_storage(file_data, filename, content_type=None):
    try:
        supabase.storage.from_(BUCKET_NAME).upload(
            path=filename,
            file=file_data,
            file_options={"content-type": content_type} if content_type else {}
        )
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
        return public_url
    except Exception as e:
        st.error(f"Erreur d'upload : {e}")
        return None

# =====================================================
# SESSION
# =====================================================
if "user" not in st.session_state:
    st.session_state.user = None

# --- Suivi de l'activité pour rafraîchissement adaptatif ---
if "last_activity" not in st.session_state:
    st.session_state.last_activity = datetime.now()

def update_activity():
    """Met à jour l'horodatage de dernière activité et le statut en ligne."""
    st.session_state.last_activity = datetime.now()
    if st.session_state.user:
        try:
            supabase.table("profiles").update({"last_active": datetime.now().isoformat()}).eq("username", st.session_state.user).execute()
        except Exception as e:
            st.error(f"Erreur mise à jour statut : {e}")

def get_refresh_interval():
    idle = (datetime.now() - st.session_state.last_activity).seconds
    if idle < 60:
        return 5000      # 5 sec (actif)
    elif idle < 300:
        return 10000     # 10 sec (inactif modéré)
    else:
        return 20000     # 20 sec (inactif)

# --- Nettoyage mémoire basé sur le score TST ---
if "last_cleanup" not in st.session_state:
    st.session_state.last_cleanup = datetime.now() - timedelta(hours=24)  # pour forcer au premier appel

# =====================================================
# FONCTIONS DE GESTION DU WALLET ET FORFAITS
# =====================================================

def get_wallet(username):
    clean_name = username.upper().strip()
    try:
        resp = supabase.table("wallets").select("kongo_balance").eq("username", clean_name).execute()
        if resp.data and len(resp.data) > 0:
            return resp.data[0]["kongo_balance"]
    except Exception as e:
        st.error(f"Erreur lors de la lecture du wallet : {e}")
    return 0.0

def update_wallet(username, amount, operation="add"):
    clean_name = username.upper().strip()
    try:
        wallet = supabase.table("wallets").select("kongo_balance").eq("username", clean_name).execute()
        if not wallet.data:
            st.error(f"Wallet introuvable pour {username}")
            return False
        current = wallet.data[0]["kongo_balance"]
        new_balance = current + amount if operation == "add" else current - amount
        if new_balance < 0:
            st.error("Solde insuffisant.")
            return False
        supabase.table("wallets").update({"kongo_balance": new_balance}).eq("username", clean_name).execute()
        return True
    except Exception as e:
        st.error(f"Erreur lors de la mise à jour du wallet : {e}")
        return False

def get_user_plan(username):
    clean_name = username.upper().strip()
    resp = supabase.table("subscriptions").select("plan_type", "expires_at", "is_active").eq("username", clean_name).execute()
    if resp.data:
        return resp.data[0]
    return {"plan_type": "Gratuit", "expires_at": None, "is_active": True}

def activate_plan(username, plan_type, duration_days=30):
    clean_name = username.upper().strip()
    expires_at = datetime.now() + timedelta(days=duration_days)
    data = {
        "username": clean_name,
        "plan_type": plan_type,
        "activated_at": datetime.now().isoformat(),
        "expires_at": expires_at.isoformat(),
        "is_active": True
    }
    supabase.table("subscriptions").delete().eq("username", clean_name).execute()
    supabase.table("subscriptions").insert(data).execute()

    params = {}
    if plan_type == "Gratuit":
        params = {"phi_m": 1.0, "phi_c": 1.0, "phi_d": 1.5}
    elif plan_type == "Pro_Memoire":
        params = {"phi_m": 5.0, "phi_c": 1.5, "phi_d": 0.1}
    elif plan_type == "Attracteur_Global":
        params = {"phi_m": 3.0, "phi_c": 15.0, "phi_d": 0.8}

    supabase.table("tst_params").update(params).eq("username", clean_name).execute()

def credit_creator(amount):
    return update_wallet("SCARABBE", amount, "add")

def ensure_scarabbe_wallet():
    if st.session_state.user == "SCARABBE":
        clean_name = "SCARABBE"
        try:
            wallet = supabase.table("wallets").select("kongo_balance").eq("username", clean_name).execute()
            if not wallet.data:
                supabase.table("wallets").insert({"username": clean_name, "kongo_balance": 1_000_000}).execute()
                st.sidebar.success("🎉 Bienvenue Créateur ! 1 000 000 KC ont été crédités sur votre wallet.")
            else:
                current = wallet.data[0]["kongo_balance"]
                if current == 0.0:
                    supabase.table("wallets").update({"kongo_balance": 1_000_000}).eq("username", clean_name).execute()
                    st.sidebar.success("🎉 Bienvenue Créateur ! 1 000 000 KC ont été crédités sur votre wallet.")
        except Exception as e:
            st.sidebar.error(f"Erreur lors de la création du wallet : {e}")

# =====================================================
# FONCTIONS DE GESTION DES SUIVIS (FOLLOWS)
# =====================================================
def follow_user(follower, followed):
    try:
        existing = supabase.table("follows").select("*").eq("follower", follower).eq("followed", followed).execute()
        if not existing.data:
            supabase.table("follows").insert({
                "follower": follower,
                "followed": followed,
                "created_at": datetime.now().isoformat()
            }).execute()
            return True
    except Exception as e:
        st.error(f"Erreur follow : {e}")
    return False

def unfollow_user(follower, followed):
    try:
        supabase.table("follows").delete().eq("follower", follower).eq("followed", followed).execute()
        return True
    except Exception as e:
        st.error(f"Erreur unfollow : {e}")
    return False

def is_following(follower, followed):
    try:
        existing = supabase.table("follows").select("*").eq("follower", follower).eq("followed", followed).execute()
        return len(existing.data) > 0
    except Exception as e:
        st.error(f"Erreur vérification follow : {e}")
    return False

def get_followers(username):
    try:
        resp = supabase.table("follows").select("follower").eq("followed", username).execute()
        return [r["follower"] for r in resp.data] if resp.data else []
    except Exception as e:
        st.error(f"Erreur récupération followers : {e}")
        return []

def get_following(username):
    try:
        resp = supabase.table("follows").select("followed").eq("follower", username).execute()
        return [r["followed"] for r in resp.data] if resp.data else []
    except Exception as e:
        st.error(f"Erreur récupération following : {e}")
        return []

# =====================================================
# FONCTIONS DE GESTION DU STATUT EN LIGNE
# =====================================================
def get_online_users(threshold_minutes=5):
    try:
        cutoff = (datetime.now() - timedelta(minutes=threshold_minutes)).isoformat()
        resp = supabase.table("profiles").select("username").gt("last_active", cutoff).execute()
        return [u["username"] for u in resp.data] if resp.data else []
    except Exception as e:
        st.error(f"Erreur récupération en ligne : {e}")
        return []

# =====================================================
# CŒUR TST : PARAMÈTRES ET SCORES
# =====================================================
def get_user_params(username):
    clean_name = username.upper().strip()
    resp = supabase.table("tst_params").select("phi_m", "phi_c", "phi_d").eq("username", clean_name).execute()
    if resp.data:
        return resp.data[0]
    return {"phi_m": 1.0, "phi_c": 1.0, "phi_d": 1.0}

# --- GESTION DES LIKES (doit être avant calculate_post_score) ---
def get_likes_count(post_id):
    resp = supabase.table("likes").select("*", count="exact").eq("post_id", post_id).execute()
    return resp.count if hasattr(resp, 'count') else len(resp.data)

def calculate_post_score(post, params=None):
    """Calcule le score TST d'un post public."""
    if params is None:
        params = get_user_params(post["username"])
    created_at = datetime.fromisoformat(post["created_at"].replace("Z", "+00:00"))
    hours_old = (datetime.now().astimezone() - created_at).total_seconds() / 3600
    likes = get_likes_count(post["id"])
    # Score = (Cohérence active) + (Inertie mémoire) - (Dissipation temporelle)
    score = (likes * params['phi_c']) + (params['phi_m'] * 10) - (hours_old * params['phi_d'])
    return score

def calculate_private_message_score(message, sender_params):
    """
    Calcule le score TST d'un message privé.
    - texte : longueur en caractères * phi_m
    - média : bonus de cohérence (phi_c)
    - âge : dissipation (phi_d)
    """
    age_hours = (datetime.now().astimezone() - datetime.fromisoformat(message["created_at"].replace("Z", "+00:00"))).total_seconds() / 3600
    base = 0
    if message.get("text"):
        base = len(message["text"]) * sender_params['phi_m']
    if message.get("audio_path"):
        base += sender_params['phi_c'] * 5   # bonus audio
    if message.get("video_path"):
        base += sender_params['phi_c'] * 10  # bonus vidéo
    score = base - (age_hours * sender_params['phi_d'])
    return max(score, 0)  # pas de score négatif

# =====================================================
# NETTOYAGE MÉMOIRE BASÉ SUR LA MOYENNE DES SCORES
# =====================================================
def perform_memory_cleanup(force=False):
    """
    Supprime les messages publics et privés dont le score est inférieur à la moyenne.
    Exécuté au maximum toutes les 6 heures (sauf force=True).
    """
    now = datetime.now()
    if not force and (now - st.session_state.last_cleanup).total_seconds() < 21600:  # 6h
        return
    st.session_state.last_cleanup = now

    # --- Nettoyage des posts publics ---
    try:
        posts_resp = supabase.table("posts").select("*").execute()
        posts = posts_resp.data if posts_resp.data else []
        if posts:
            scores = []
            for p in posts:
                params = get_user_params(p["username"])
                score = calculate_post_score(p, params)
                scores.append(score)
            if scores:
                mean_score = np.mean(scores)
                threshold = mean_score * 0.7  # légèrement en dessous de la moyenne
                to_delete = []
                for p in posts:
                    params = get_user_params(p["username"])
                    score = calculate_post_score(p, params)
                    if score < threshold:
                        to_delete.append(p["id"])
                if to_delete:
                    supabase.table("posts").delete().in_("id", to_delete).execute()
                    st.sidebar.info(f"🧹 {len(to_delete)} posts dissipés (score < seuil).")
    except Exception as e:
        st.error(f"Erreur nettoyage posts : {e}")

    # --- Nettoyage des messages privés ---
    try:
        msgs_resp = supabase.table("messages").select("*").execute()
        msgs = msgs_resp.data if msgs_resp.data else []
        if msgs:
            scores = []
            for m in msgs:
                sender_params = get_user_params(m["sender"])
                score = calculate_private_message_score(m, sender_params)
                scores.append(score)
            if scores:
                mean_score = np.mean(scores)
                threshold = mean_score * 0.7
                to_delete = []
                for m in msgs:
                    sender_params = get_user_params(m["sender"])
                    score = calculate_private_message_score(m, sender_params)
                    if score < threshold:
                        to_delete.append(m["id"])
                if to_delete:
                    supabase.table("messages").delete().in_("id", to_delete).execute()
                    st.sidebar.info(f"🧹 {len(to_delete)} messages privés dissipés (score < seuil).")
    except Exception as e:
        st.error(f"Erreur nettoyage messages : {e}")

# =====================================================
# LOGIN / REGISTER
# =====================================================
def login():
    st.title("🌍 Free_Kogossa x GEN-Z GABON")
    st.info("🔐 Connexion Cloud – vos données sont sécurisées.")

    tab1, tab2 = st.tabs(["Connexion", "Créer compte"])

    with tab1:
        username = st.text_input("Nom utilisateur")
        password = st.text_input("Mot de passe", type="password")
        if st.button("Connexion"):
            response = supabase.table("profiles").select("*").eq("username", username).execute()
            if response.data:
                user_data = response.data[0]
                if user_data["password"] == hash_password(password):
                    st.session_state.user = username
                    supabase.table("profiles").update({"last_active": datetime.now().isoformat()}).eq("username", username).execute()
                    update_activity()
                    ensure_scarabbe_wallet()
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect")
            else:
                st.error("Utilisateur non trouvé")

    with tab2:
        new_user = st.text_input("Nom utilisateur", key="newuser")
        new_pass = st.text_input("Mot de passe", type="password", key="newpass")
        bio = st.text_area("Bio")
        location = st.text_input("Localisation")
        pic = st.file_uploader("Photo profil", type=["png", "jpg", "jpeg"])

        if st.button("Créer compte"):
            check = supabase.table("profiles").select("username").eq("username", new_user).execute()
            if check.data:
                st.error("Ce pseudo est déjà pris")
            elif len(new_pass) < 4:
                st.error("Mot de passe trop court (minimum 4 caractères)")
            else:
                profile_pic_url = ""
                if pic:
                    ext = pic.name.split('.')[-1]
                    filename = f"profile_{new_user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
                    profile_pic_url = upload_to_storage(pic.getvalue(), filename, pic.type)
                    if not profile_pic_url:
                        st.error("Échec de l'upload de la photo de profil. Compte non créé.")
                        st.stop()

                user_dict = {
                    "username": new_user,
                    "password": hash_password(new_pass),
                    "bio": bio,
                    "location": location,
                    "profile_pic": profile_pic_url,
                    "last_active": datetime.now().isoformat()
                }
                supabase.table("profiles").insert(user_dict).execute()
                st.success("Compte créé sur le Cloud ! Vous pouvez maintenant vous connecter.")

# =====================================================
# BANNIERE DE PROFIL
# =====================================================
def banner():
    user = st.session_state.user
    response = supabase.table("profiles").select("*").eq("username", user).execute()
    if response.data:
        profile = response.data[0]
    else:
        st.error("Profil introuvable")
        return

    st.divider()
    col1, col2 = st.columns([1, 4])
    with col1:
        pic_url = profile.get("profile_pic", "")
        if pic_url:
            st.image(pic_url, width=120)
        else:
            st.caption("(aucune photo)")
    with col2:
        st.title(user)
        if profile.get("bio"):
            st.write(profile["bio"])
        if profile.get("location"):
            st.caption("📍 " + profile["location"])
    st.divider()

# =====================================================
# GESTION DES LIKES (suite)
# =====================================================
def like_post(post_id, username):
    existing = supabase.table("likes").select("*").eq("post_id", post_id).eq("username", username).execute()
    if not existing.data:
        supabase.table("likes").insert({"post_id": post_id, "username": username}).execute()

        post_author_resp = supabase.table("posts").select("username").eq("id", post_id).execute()
        if post_author_resp.data:
            author = post_author_resp.data[0]["username"]
            update_wallet(author, 0.1, "add")

            current_params = get_user_params(author)
            new_phi_m = current_params['phi_m'] + 0.01
            supabase.table("tst_params").update({"phi_m": new_phi_m}).eq("username", author.upper()).execute()

        update_activity()

# =====================================================
# FIL SOCIAL
# =====================================================
def get_tst_ranked_posts():
    try:
        posts_resp = supabase.table("posts").select("*, tst_params(*)").order("created_at", desc=True).limit(50).execute()
        posts = posts_resp.data if posts_resp.data else []
        ranked_posts = []
        now = datetime.now().astimezone()
        for p in posts:
            params = p.get('tst_params', {"phi_m": 1.0, "phi_c": 1.0, "phi_d": 1.0})
            created_at = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))
            hours_old = (now - created_at).total_seconds() / 3600
            likes = get_likes_count(p["id"])
            score = (likes * params['phi_c']) + (params['phi_m'] * 10) - (hours_old * params['phi_d'])
            p['tst_rank_score'] = score
            ranked_posts.append(p)
        ranked_posts.sort(key=lambda x: x['tst_rank_score'], reverse=True)
        return ranked_posts
    except Exception as e:
        st.error(f"Erreur classement TST : {e}")
        return []

def feed():
    st_autorefresh(interval=get_refresh_interval(), key="feed_refresh")
    perform_memory_cleanup()
    banner()
    st.subheader("Exprime-toi")

    # 1. Zone de texte
    text = st.text_area("Message", placeholder="Quoi de neuf ?", key="main_feed_text")

    # 2. Zone de médias
    col_img, col_vid = st.columns(2)
    with col_img:
        img = st.file_uploader("Image", type=["png", "jpg", "jpeg"], key="feed_img")
    with col_vid:
        video = st.file_uploader("Vidéo", type=["mp4", "mov", "avi", "mkv"], key="feed_video")

    # 3. Micro (Remplace audio_input qui bug)
    st.write("🎙️ Message Vocal")
    audio_data = mic_recorder(
        start_prompt="Démarrer l'enregistrement", 
        stop_prompt="Arrêter & Valider", 
        key='feed_recorder'
    )

    if audio_data:
        st.audio(audio_data['bytes'])

    # Vérification taille
    if img and img.size > 50 * 1024 * 1024:
        st.error("Image trop lourde (max 50 Mo)")
        st.stop()
    if video and video.size > 50 * 1024 * 1024:
        st.error("Vidéo trop lourde (max 50 Mo)")
        st.stop()

    # 4. Bouton de publication unique
    if st.button("Publier", key="btn_publier_main"):
        if not text and not img and not video and not audio_data:
            st.warning("Ton post est vide !")
            return

        with st.spinner("Publication en cours..."):
            media_url, audio_url, video_url = "", "", ""

            if img:
                media_url = upload_to_storage(img.getvalue(), f"img_{datetime.now().timestamp()}.jpg", img.type)
            if video:
                video_url = upload_to_storage(video.getvalue(), f"vid_{datetime.now().timestamp()}.mp4", video.type)
            if audio_data:
                audio_url = upload_to_storage(audio_data['bytes'], f"vocal_{datetime.now().timestamp()}.wav", "audio/wav")

            post_data = {
                "username": st.session_state.user,
                "text": text,
                "media_url": media_url,
                "video_url": video_url,
                "audio_url": audio_url,
                "created_at": datetime.now().isoformat()
            }

            try:
                supabase.table("posts").insert(post_data).execute()
                st.success("Post publié !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.divider()
    st.subheader("Fil d'actualité Triadique")

    posts = get_tst_ranked_posts()
    for post in posts:
        with st.container():
            score = post.get('tst_rank_score', 0)
            col_name, col_score = st.columns([3, 1])
            with col_name:
                st.markdown(f"### @{post['username']}")
            with col_score:
                if score > 50:
                    st.markdown("🌟 **Attracteur Global**")
                elif score > 20:
                    st.markdown("🔥 **Stable**")
                else:
                    st.markdown(f"❄️ Score: {score:.1f}")

            st.write(post.get("text", ""))

            media_url = post.get("media_path", "")
            media_type = post.get("media_type")
            if media_url and media_type:
                if media_type == "image":
                    st.image(media_url)
                elif media_type == "video":
                    st.video(media_url)

            created_at = datetime.fromisoformat(post["created_at"].replace("Z", "+00:00"))
            st.caption(created_at.strftime("%Y-%m-%d %H:%M"))

            likes_count = get_likes_count(post["id"])
            col1, col2 = st.columns([1, 10])
            with col1:
                if st.button("❤️", key=f"like_{post['id']}"):
                    like_post(post["id"], st.session_state.user)
                    st.rerun()
            with col2:
                st.write(f"**{likes_count}** likes")

            comments_response = supabase.table("comments").select("*").eq("post_id", post["id"]).order("created_at").execute()
            comments = comments_response.data if comments_response.data else []

            comment_key = f"c_{post['id']}"
            comment_text = st.text_input("Commenter", key=comment_key)
            if st.button("Envoyer", key=f"b_{post['id']}"):
                if comment_text.strip():
                    comment_dict = {
                        "post_id": post["id"],
                        "username": st.session_state.user,
                        "text": comment_text,
                    }
                    supabase.table("comments").insert(comment_dict).execute()
                    update_activity()
                    st.rerun()

            for c in comments:
                st.write(f"**{c['username']}** : {c['text']}")
            st.divider()

# =====================================================
# MESSAGERIE (avec gestion d'erreurs)
# =====================================================

@st.cache_data(ttl=300)
def get_other_users(current_user):
    resp = supabase.table("profiles").select("username").neq("username", current_user).execute()
    return [u["username"] for u in resp.data] if resp.data else []

def messenger():
    st_autorefresh(interval=get_refresh_interval(), key="msg_refresh")
    perform_memory_cleanup()
    st.header("Messagerie")

    users_list = get_other_users(st.session_state.user)
    if not users_list:
        st.info("Aucun autre utilisateur")
        return

    target = st.selectbox("Choisir utilisateur", users_list, key="msg_target")

    conv_key = f"page_{st.session_state.user}_{target}"
    if conv_key not in st.session_state:
        st.session_state[conv_key] = 1

    last_seen_key = f"last_seen_{st.session_state.user}_{target}"
    if last_seen_key not in st.session_state:
        st.session_state[last_seen_key] = None

    def load_messages(page=1, per_page=10):
        offset = (page - 1) * per_page
        filter_str = f"and(sender.eq.{st.session_state.user},recipient.eq.{target}),and(sender.eq.{target},recipient.eq.{st.session_state.user})"
        try:
            resp = supabase.table("messages").select("*")\
                .or_(filter_str)\
                .order("created_at", desc=True)\
                .range(offset, offset + per_page - 1)\
                .execute()
            messages = resp.data if resp.data else []
            messages.reverse()
            return messages
        except Exception as e:
            st.error(f"Erreur chargement messages : {e}")
            return []

    messages = load_messages(st.session_state[conv_key])

    # Indicateur de nouveaux messages
    try:
        if messages:
            last_msg_time = datetime.fromisoformat(messages[-1]["created_at"].replace("Z", "+00:00"))
            last_seen = st.session_state.get(last_seen_key)
            if last_seen is None or last_msg_time > datetime.fromisoformat(last_seen):
                st.info("🔔 Nouveaux messages dans cette conversation")
            st.session_state[last_seen_key] = messages[-1]["created_at"]
    except Exception as e:
        st.error(f"Erreur indicateur messages : {e}")

    for m in messages:
        if m["sender"] == st.session_state.user:
            prefix = "🟢 **Moi** : "
        else:
            prefix = f"🔵 **{m['sender']}** : "

        if m.get("audio_path"):
            st.write(prefix + "[Message audio]")
            st.audio(m["audio_path"])
        elif m.get("video_path"):
            st.write(prefix + "[Message vidéo]")
            st.video(m["video_path"])
        else:
            st.write(prefix + m.get("text", ""))

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if len(messages) == 10:
            if st.button("📜 Messages plus anciens"):
                st.session_state[conv_key] += 1
                st.rerun()
        elif st.session_state[conv_key] > 1:
            if st.button("⬆️ Revenir aux messages récents"):
                st.session_state[conv_key] = 1
                st.rerun()

    st.divider()
    st.subheader("Nouveau message")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        text_msg = st.text_area("Texte", key="msg_text", height=100, placeholder="Écris ton message...")
    with col2:
        audio_file = st.file_uploader("🎵 Audio (fichier)", type=["mp3", "wav", "ogg"], key="msg_audio")
    with col3:
        video_file = st.file_uploader("🎬 Vidéo (fichier)", type=["mp4", "mov", "avi"], key="msg_video")
    with col4:
        st.write("🎙️ Enregistrement vocal")
        recorder_output = mic_recorder(
            start_prompt="Démarrer",
            stop_prompt="Arrêter",
            just_once=False,
            key="recorder"
        )

    if st.button("Envoyer message", type="primary"):
        if audio_file and audio_file.size > 50 * 1024 * 1024:
            st.error("Fichier audio trop lourd (max 50 Mo)")
            st.stop()
        if video_file and video_file.size > 50 * 1024 * 1024:
            st.error("Fichier vidéo trop lourd (max 50 Mo)")
            st.stop()

        audio_bytes = None
        if recorder_output:
            if isinstance(recorder_output, dict):
                audio_bytes = recorder_output.get("bytes")
            else:
                audio_bytes = recorder_output

        message_dict = {"sender": st.session_state.user, "recipient": target}
        upload_success = False

        if audio_bytes:
            filename = f"voice_{st.session_state.user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            url = upload_to_storage(audio_bytes, filename, "audio/wav")
            if url:
                message_dict["audio_path"] = url
                upload_success = True
            else:
                st.error("L'enregistrement audio n'a pas pu être uploadé.")
                st.stop()
        elif audio_file:
            ext = audio_file.name.split('.')[-1]
            filename = f"audio_{st.session_state.user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            url = upload_to_storage(audio_file.getvalue(), filename, audio_file.type)
            if url:
                message_dict["audio_path"] = url
                upload_success = True
            else:
                st.error("Le fichier audio n'a pas pu être uploadé.")
                st.stop()
        elif video_file:
            ext = video_file.name.split('.')[-1]
            filename = f"video_{st.session_state.user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            url = upload_to_storage(video_file.getvalue(), filename, video_file.type)
            if url:
                message_dict["video_path"] = url
                upload_success = True
            else:
                st.error("Le fichier vidéo n'a pas pu être uploadé.")
                st.stop()
        elif text_msg.strip():
            message_dict["text"] = text_msg
            upload_success = True
        else:
            st.warning("Écris un message, enregistre un audio ou ajoute un fichier.")
            st.stop()

        if upload_success:
            supabase.table("messages").insert(message_dict).execute()
            st.session_state[conv_key] = 1
            st.session_state[last_seen_key] = datetime.now().isoformat()
            get_other_users.clear()
            update_activity()
            st.rerun()

# =====================================================
# PROFIL
# =====================================================
def profile():
    user = st.session_state.user
    st.header("Profil")

    response = supabase.table("profiles").select("*").eq("username", user).execute()
    if not response.data:
        st.error("Profil introuvable")
        return
    profile_data = response.data[0]

    pic_url = profile_data.get("profile_pic", "")
    if pic_url:
        st.image(pic_url, width=150)
    else:
        st.caption("(aucune photo)")

    st.write("Bio :", profile_data.get("bio", ""))
    st.write("Localisation :", profile_data.get("location", ""))
    st.caption("Compte créé : " + profile_data.get("created_at", ""))

    kc_balance = get_wallet(user)
    st.metric("💰 Kongo Coins", f"{kc_balance:.2f} KC")

    plan_info = get_user_plan(user)
    st.info(f"Forfait actuel : **{plan_info['plan_type']}**")
    if plan_info['expires_at']:
        expires = datetime.fromisoformat(plan_info['expires_at'].replace("Z", "+00:00"))
        st.caption(f"Expire le : {expires.strftime('%Y-%m-%d %H:%M')}")

    followers = get_followers(user)
    following = get_following(user)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("👥 Followers", len(followers))
    with col2:
        st.metric("👤 Suivis", len(following))

    with st.expander("Voir les followers"):
        if followers:
            for f in followers:
                st.write(f"@{f}")
        else:
            st.write("Aucun follower pour l'instant.")

    with st.expander("Voir les personnes suivies"):
        if following:
            for f in following:
                st.write(f"@{f}")
        else:
            st.write("Vous ne suivez personne.")

    st.subheader("Modifier les informations")
    new_bio = st.text_area("Bio", value=profile_data.get("bio", ""))
    new_loc = st.text_input("Localisation", value=profile_data.get("location", ""))
    new_pic = st.file_uploader("Changer photo", type=["png", "jpg", "jpeg"])

    if st.button("Mettre à jour le profil"):
        update_dict = {}
        if new_bio != profile_data.get("bio"):
            update_dict["bio"] = new_bio
        if new_loc != profile_data.get("location"):
            update_dict["location"] = new_loc
        if new_pic:
            ext = new_pic.name.split('.')[-1]
            filename = f"profile_{user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            pic_url = upload_to_storage(new_pic.getvalue(), filename, new_pic.type)
            if pic_url:
                update_dict["profile_pic"] = pic_url
            else:
                st.error("Échec de l'upload.")
                st.stop()

        if update_dict:
            supabase.table("profiles").update(update_dict).eq("username", user).execute()
            update_activity()
            st.rerun()

    st.divider()
    st.subheader("Sécurité")
    with st.expander("Modifier le mot de passe"):
        old_pass = st.text_input("Ancien mot de passe", type="password")
        new_pass1 = st.text_input("Nouveau mot de passe", type="password")
        new_pass2 = st.text_input("Confirmer", type="password")

        if st.button("Changer le mot de passe"):
            if profile_data["password"] != hash_password(old_pass):
                st.error("Ancien mot de passe incorrect")
            elif new_pass1 != new_pass2:
                st.error("Les nouveaux mots de passe ne correspondent pas")
            elif len(new_pass1) < 4:
                st.error("Mot de passe trop court (min 4)")
            else:
                supabase.table("profiles").update({"password": hash_password(new_pass1)}).eq("username", user).execute()
                st.success("Mot de passe modifié !")
                update_activity()

# =====================================================
# BOUTIQUE
# =====================================================
def shop():
    st.header("💎 Boutique de Stabilité (Forfaits TST)")
    user = st.session_state.user
    balance = get_wallet(user)
    st.metric("Votre Trésorerie", f"{balance:.2f} KC")

    plans = {
        "Gratuit": {"price": 0, "phi_m": 1.0, "phi_c": 1.0, "phi_d": 1.5, "desc": "Visibilité standard"},
        "Pro_Memoire": {"price": 500, "phi_m": 5.0, "phi_c": 1.5, "phi_d": 0.1, "desc": "Tes posts restent visibles plus longtemps (Faible Déclin)"},
        "Attracteur_Global": {"price": 2500, "phi_m": 3.0, "phi_c": 15.0, "phi_d": 0.8, "desc": "Priorité maximale dans le fil d'actualité (Forte Cohérence)"}
    }

    cols = st.columns(3)
    for i, (name, info) in enumerate(plans.items()):
        with cols[i]:
            st.subheader(name)
            st.write(info["desc"])
            st.code(f"Prix: {info['price']} KC")

            if st.button(f"Activer {name}", key=f"buy_{name}"):
                if balance >= info["price"]:
                    if update_wallet(user, info["price"], "subtract"):
                        activate_plan(user, name)
                        taxe = info["price"] * 0.1
                        if taxe > 0:
                            if not credit_creator(taxe):
                                update_wallet(user, info["price"], "add")
                                st.error("Erreur lors du crédit au créateur. Transaction annulée.")
                                st.stop()
                        st.success(f"Plan {name} activé ! Vos paramètres TST ont été mis à jour.")
                        st.rerun()
                    else:
                        st.error("Erreur lors du débit de votre wallet.")
                else:
                    st.error("Solde insuffisant pour ce niveau de stabilité.")

    st.divider()
    st.subheader("Acheter des Kongo Coins (simulation)")
    amount = st.number_input("Montant de KC à ajouter", min_value=10, step=10, value=50)
    if st.button("Ajouter KC"):
        if update_wallet(user, amount, "add"):
            st.success(f"{amount} KC ajoutés !")
            st.rerun()
        else:
            st.error("Erreur lors de l'ajout.")

# =====================================================
# MARKETPLACE
# =====================================================
def marketplace():
    st.header("🏪 Marketplace Free_Kogossa")
    user = st.session_state.user
    balance = get_wallet(user)
    st.sidebar.metric("💰 Votre solde", f"{balance:.2f} KC")

    with st.expander("➕ Publier une offre"):
        title = st.text_input("Titre")
        desc = st.text_area("Description")
        price = st.number_input("Prix (KC)", min_value=1.0, step=1.0)
        if st.button("Mettre en vente"):
            supabase.table("marketplace_listings").insert({
                "username": user,
                "title": title,
                "description": desc,
                "price_kc": price,
                "is_active": True
            }).execute()
            st.success("Annonce publiée !")
            update_activity()
            st.rerun()

    st.divider()

    resp = supabase.table("marketplace_listings").select("*").eq("is_active", True).execute()
    listings = resp.data if resp.data else []
    for item in listings:
        params = get_user_params(item['username'])
        item['phi_c'] = params['phi_c']
    listings.sort(key=lambda x: x['phi_c'], reverse=True)

    for item in listings:
        with st.container():
            col_info, col_buy = st.columns([3, 1])
            with col_info:
                st.subheader(item['title'])
                st.write(item['description'])
                st.caption(f"Vendeur : @{item['username']} | Visibilité : {item['phi_c']}x")
            with col_buy:
                st.markdown(f"### {item['price_kc']} KC")
                if st.button("Acheter", key=f"buy_{item['id']}"):
                    seller = item['username']
                    price = item['price_kc']
                    taxe = price * 0.10
                    if user == seller:
                        st.error("Vous ne pouvez pas acheter votre propre offre.")
                    elif update_wallet(user, price, "subtract"):
                        if update_wallet(seller, price - taxe, "add") and update_wallet("SCARABBE", taxe, "add"):
                            supabase.table("marketplace_listings").update({"is_active": False}).eq("id", item['id']).execute()
                            st.success(f"Achat réussi ! Taxe de {taxe:.2f} KC prélevée.")
                            st.rerun()
                        else:
                            update_wallet(user, price, "add")
                            st.error("Erreur lors du crédit au vendeur ou au créateur. Transaction annulée.")
                    else:
                        st.error("Solde insuffisant.")
            st.divider()

# =====================================================
# ADMIN PANEL
# =====================================================
def admin_panel():
    admin_email_hash = hashlib.sha256("mayombochristal@gmail.com".encode()).hexdigest()
    admin_pass_hash = hashlib.sha256("Broozy040200".encode()).hexdigest()

    if st.session_state.user != "SCARABBE":
        st.error("⚠️ Accès restreint.")
        return

    st.title("🛡️ Administration Centrale TTU-MC³")
    st.markdown("---")

    with st.expander("🔑 Authentification supplémentaire"):
        email_input = st.text_input("Email")
        pass_input = st.text_input("Mot de passe", type="password")
        if st.button("Vérifier"):
            if (hashlib.sha256(email_input.encode()).hexdigest() == admin_email_hash and
                hashlib.sha256(pass_input.encode()).hexdigest() == admin_pass_hash):
                st.session_state.admin_auth = True
                st.success("Accès autorisé.")
            else:
                st.error("Identifiants incorrects.")
                st.session_state.admin_auth = False

    if not st.session_state.get("admin_auth", False):
        st.warning("Authentification requise.")
        return

    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Monitoring TST")
    mon_solde = get_wallet("SCARABBE")
    st.sidebar.metric("Trésor", f"{mon_solde:.2f} KC")

    if st.sidebar.button("🧹 Forcer le nettoyage mémoire TST"):
        perform_memory_cleanup(force=True)
        st.sidebar.success("Nettoyage forcé effectué.")

    if st.sidebar.button("🧹 Lancer la Dissipation (posts anciens)"):
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        gratuit_users = supabase.table("subscriptions").select("username").eq("plan_type", "Gratuit").eq("is_active", True).execute()
        usernames = [u["username"] for u in gratuit_users.data] if gratuit_users.data else []
        if usernames:
            supabase.table("posts").delete().filter("username", "in", usernames).filter("created_at", "lt", cutoff).execute()
        st.sidebar.success("Dissipation effectuée (posts gratuits >7j).")

    if st.sidebar.button("🗑️ Dissipation des messages (30 jours)"):
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        try:
            supabase.table("messages").delete().lt("created_at", cutoff).execute()
            st.sidebar.success("Messages de plus de 30 jours supprimés.")
        except Exception as e:
            st.sidebar.error(f"Erreur : {e}")

    users_resp = supabase.table("profiles").select("username").execute()
    users_list = [u["username"] for u in users_resp.data] if users_resp.data else []
    target_user = st.selectbox("Utilisateur", users_list)

    params = get_user_params(target_user)
    sub_info = get_user_plan(target_user)

    st.subheader(f"⚙️ Configuration de @{target_user}")
    col1, col2, col3 = st.columns(3)
    with col1:
        new_m = st.number_input("Φm", value=params["phi_m"], step=0.1)
    with col2:
        new_c = st.number_input("Φc", value=params["phi_c"], step=0.1)
    with col3:
        new_d = st.number_input("Φd", value=params["phi_d"], step=0.1)

    new_plan = st.selectbox("Forfait", ["Gratuit", "Pro_Memoire", "Attracteur_Global"],
                            index=["Gratuit", "Pro_Memoire", "Attracteur_Global"].index(sub_info["plan_type"]) if sub_info["plan_type"] in ["Gratuit", "Pro_Memoire", "Attracteur_Global"] else 0)

    if st.button("🚀 Appliquer"):
        supabase.table("tst_params").update({"phi_m": new_m, "phi_c": new_c, "phi_d": new_d}).eq("username", target_user).execute()
        expires = (datetime.now() + timedelta(days=30)).isoformat()
        supabase.table("subscriptions").update({"plan_type": new_plan, "expires_at": expires}).eq("username", target_user).execute()
        st.success("Paramètres mis à jour.")

    st.divider()
    st.subheader("💰 Récolte de la Taxe")
    if st.button("Récolter (1 KC par forfait actif)"):
        active_subs = supabase.table("subscriptions").select("username").eq("is_active", True).execute()
        count = 0
        for sub in active_subs.data:
            if update_wallet(sub['username'], 1, "subtract"):
                if credit_creator(1):
                    count += 1
                else:
                    update_wallet(sub['username'], 1, "add")
        st.success(f"{count} KC récoltés.")

    st.divider()
    st.header("💰 Trésor de SCARABBE")
    solde_maitre = get_wallet("SCARABBE")
    st.metric("Total KC", f"{solde_maitre:,.2f} KC")
    st.info("Taxes de stabilité et ventes de forfaits.")
    amount = st.number_input("Montant à convertir en FCFA", min_value=100, step=100)
    if st.button("Demander retrait (simulation)"):
        st.warning("Demande envoyée (simulation).")

# =====================================================
# LABORATOIRE TST
# =====================================================
def tst_laboratory():
    st.header("🔬 Laboratoire de Dynamique Triadique")
    st.info("Visualisation de la convergence vers l'attracteur.")

    def lorenz(x, y, z, s=10, r=28, b=2.667):
        x_dot = s*(y - x)
        y_dot = r*x - y - x*z
        z_dot = x*y - b*z
        return x_dot, y_dot, z_dot

    dt = 0.01
    num_steps = 2000
    xs = np.empty(num_steps + 1)
    ys = np.empty(num_steps + 1)
    zs = np.empty(num_steps + 1)
    xs[0], ys[0], zs[0] = (0., 1., 1.05)

    for i in range(num_steps):
        x_dot, y_dot, z_dot = lorenz(xs[i], ys[i], zs[i])
        xs[i+1] = xs[i] + (x_dot * dt)
        ys[i+1] = ys[i] + (y_dot * dt)
        zs[i+1] = zs[i] + (z_dot * dt)

    fig = go.Figure(data=[go.Scatter3d(x=xs, y=ys, z=zs, mode='lines', line=dict(color='blue', width=1))])
    fig.update_layout(
        title="Attracteur de Lorenz",
        scene=dict(xaxis_title="Mémoire (M)", yaxis_title="Cohérence (C)", zaxis_title="Dissipation (D)")
    )
    st.plotly_chart(fig)

    st.markdown("""
    Visualisation de la stabilité sociale selon la TST.
    """)

# =====================================================
# À PROPOS
# =====================================================
def about():
    st.header("👤 Créateur & Vision Scientifique")

    col1, col2 = st.columns([1, 2])
    with col1:
        creator_pic = os.path.join(ASSETS_FOLDER, "creator.jpg")
        if os.path.exists(creator_pic):
            st.image(creator_pic, use_container_width=True)
        else:
            st.info("Photo de SCARABBE")

    with col2:
        st.markdown("""
        ### **SCARABBE** *Fondateur de Free_Kogossa & Chercheur*

        Free_Kogossa est le premier réseau social piloté par la **Théorie Spectrale Triadique (TST)**.
        """)

    st.divider()
    st.subheader("🔬 Le Moteur Théorique : TTU-MC³")
    with st.expander("En savoir plus"):
        st.markdown("""
        * **Convergence vers l'Attracteur** : Vos flux sont optimisés pour atteindre un état d'équilibre.
        * **Stabilité de Lyapunov** : Modération organique.
        * **Énergie Dissipative** : Auto-scaling.
        """)
        st.write("📊 **Simulation de Convergence**")
        t = np.linspace(0, 20, 200)
        y = np.exp(-0.2 * t) * np.cos(1.5 * t)
        st.line_chart(pd.DataFrame({"Stabilité": y}, index=t))
        st.caption("Stabilisation d'un flux après interaction.")

        st.markdown("### 📄 Documents")
        doc_path_pdf = os.path.join(ASSETS_FOLDER, "TST_Thesis.pdf")
        if os.path.exists(doc_path_pdf):
            with open(doc_path_pdf, "rb") as f:
                st.download_button("📥 Télécharger la thèse (PDF)", f, file_name="TST_Thesis.pdf")

    st.divider()
    st.header("🌟 Avantages")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("- 🔒 Confidentialité\n- 🎙️ Multi-modalité\n- ⚡ Algorithme Physique")
    with col_b:
        st.markdown("- 🔄 Stabilité Structurelle\n- 📐 Auto-scaling\n- 🧠 Recherche intégrée")

    st.divider()
    st.caption("Free_Kogossa – Science gabonaise et technologie cloud. © 2026")

# =====================================================
# MAIN
# =====================================================
if not st.session_state.user:
    login()
else:
    st.sidebar.title("Free_Kogossa")
    kc_balance = get_wallet(st.session_state.user)
    st.sidebar.metric("💰 Kongo Coins", f"{kc_balance:.2f} KC")

    # Affichage des utilisateurs en ligne
    st.sidebar.markdown("---")
    st.sidebar.subheader("🟢 En ligne")
    online_users = get_online_users(threshold_minutes=5)
    online_users = [u for u in online_users if u != st.session_state.user]
    if online_users:
        for ou in online_users:
            col1, col2 = st.sidebar.columns([3, 1])
            with col1:
                st.write(f"@{ou}")
            with col2:
                if is_following(st.session_state.user, ou):
                    if st.button("Unfollow", key=f"unfollow_{ou}"):
                        unfollow_user(st.session_state.user, ou)
                        st.rerun()
                else:
                    if st.button("Follow", key=f"follow_{ou}"):
                        follow_user(st.session_state.user, ou)
                        st.rerun()
    else:
        st.sidebar.write("Aucun utilisateur en ligne.")

    menu_options = ["Fil social", "Messagerie", "Profil", "Boutique", "Marketplace", "Laboratoire TST", "À propos / Créateur"]
    if st.session_state.user == "SCARABBE":
        menu_options.append("Administration")

    page = st.sidebar.radio("Navigation", menu_options)

    if st.sidebar.button("Déconnexion"):
        st.session_state.user = None
        if "admin_auth" in st.session_state:
            del st.session_state.admin_auth
        st.rerun()

    if page == "Fil social":
        feed()
    elif page == "Messagerie":
        messenger()
    elif page == "Profil":
        profile()
    elif page == "Boutique":
        shop()
    elif page == "Marketplace":
        marketplace()
    elif page == "Laboratoire TST":
        tst_laboratory()
    elif page == "À propos / Créateur":
        about()
    elif page == "Administration":
        admin_panel()
