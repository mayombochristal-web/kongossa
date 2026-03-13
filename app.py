import streamlit as st
from supabase import create_client
import pandas as pd
import time
from datetime import datetime
import uuid
import hashlib
import hmac

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
# INITIALISATION SUPABASE
# =====================================================
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# =====================================================
# FONCTIONS DE HASH
# =====================================================
def hash_string(s: str) -> str:
    """Retourne le hash SHA-256 d'une chaîne"""
    return hashlib.sha256(s.encode()).hexdigest()

def verify_admin_code(email: str, code: str) -> bool:
    """Vérifie si l'email et le code correspondent aux hashs admin stockés."""
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
st.sidebar.image("https://via.placeholder.com/150x50?text=GEN-Z", use_column_width=True)
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
# FONCTIONS UTILES (likes, commentaires)
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

# =====================================================
# PAGES
# =====================================================
def feed_page():
    st.header("🌐 Fil d'actualité")

    with st.expander("✍️ Créer un post", expanded=False):
        with st.form("new_post"):
            post_text = st.text_area("Quoi de neuf ?")
            media_file = st.file_uploader("Ajouter une image/vidéo (optionnel)", type=["png", "jpg", "jpeg", "mp4"])
            submitted = st.form_submit_button("Publier")
            if submitted and post_text:
                try:
                    media_path = None
                    media_type = None
                    if media_file:
                        ext = media_file.name.split(".")[-1]
                        file_name = f"{user.id}/{uuid.uuid4()}.{ext}"
                        supabase.storage.from_("media").upload(file_name, media_file.getvalue())
                        media_path = file_name
                        media_type = media_file.type

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

    posts = supabase.table("posts").select(
        "*, profiles!inner(username, profile_pic), likes(count), comments(count)"
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
            if post.get("media_path"):
                file_url = supabase.storage.from_("media").get_public_url(post["media_path"])
                if post.get("media_type") and "image" in post["media_type"]:
                    st.image(file_url)
                elif post.get("media_type") and "video" in post["media_type"]:
                    st.video(file_url)

            like_count = len(post.get("likes", []))
            comment_count = len(post.get("comments", []))

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button(f"❤️ {like_count}", key=f"like_{post['id']}"):
                    like_post(post["id"])
            with col_b:
                with st.popover(f"💬 {comment_count} commentaires"):
                    comments = supabase.table("comments").select(
                        "*, profiles(username)"
                    ).eq("post_id", post["id"]).order("created_at").execute()
                    for c in comments.data:
                        st.markdown(f"**{c['profiles']['username']}** : {c['text']}")
                    new_comment = st.text_input("Votre commentaire", key=f"input_{post['id']}")
                    if st.button("Envoyer", key=f"send_{post['id']}"):
                        add_comment(post["id"], new_comment)
            with col_c:
                st.button("🔗 Partager", key=f"share_{post['id']}")
            st.divider()

def profile_page():
    st.header("👤 Mon Profil")
    with st.form("edit_profile"):
        username = st.text_input("Nom d'utilisateur", value=profile["username"])
        bio = st.text_area("Bio", value=profile.get("bio", ""))
        location = st.text_input("Localisation", value=profile.get("location", ""))
        profile_pic = st.text_input("URL photo de profil", value=profile.get("profile_pic", ""))
        if st.form_submit_button("Mettre à jour"):
            supabase.table("profiles").update({
                "username": username,
                "bio": bio,
                "location": location,
                "profile_pic": profile_pic
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
    st.header("✉️ Messagerie privée")
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
        st.subheader(f"Discussion avec {contact_dict[selected_contact]}")
        messages = supabase.table("messages").select("*").or_(
            f"and(sender.eq.{user.id},recipient.eq.{selected_contact}),"
            f"and(sender.eq.{selected_contact},recipient.eq.{user.id})"
        ).order("created_at").execute()

        for msg in messages.data:
            if msg["sender"] == user.id:
                st.markdown(
                    f"<div style='text-align: right; background-color: #dcf8c6; padding: 8px; border-radius: 10px; margin:5px;'>"
                    f"Vous : {msg.get('text', '')}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='text-align: left; background-color: #f1f0f0; padding: 8px; border-radius: 10px; margin:5px;'>"
                    f"{contact_dict[selected_contact]} : {msg.get('text', '')}</div>",
                    unsafe_allow_html=True
                )

        with st.form("new_message"):
            msg_text = st.text_area("Votre message")
            if st.form_submit_button("Envoyer"):
                if msg_text.strip():
                    supabase.table("messages").insert({
                        "sender": user.id,
                        "recipient": selected_contact,
                        "text": msg_text,
                        "created_at": datetime.now().isoformat()
                    }).execute()
                    st.success("Message envoyé")
                    st.rerun()
                else:
                    st.warning("Le message ne peut pas être vide.")

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
                try:
                    media_url = None
                    if media:
                        file_name = f"marketplace/{user.id}/{uuid.uuid4()}.jpg"
                        supabase.storage.from_("marketplace").upload(file_name, media.getvalue())
                        media_url = supabase.storage.from_("marketplace").get_public_url(file_name)

                    supabase.table("marketplace_listings").insert({
                        "user_id": user.id,
                        "title": title,
                        "description": description,
                        "price_kc": price,
                        "media_url": media_url,
                        "media_type": "image",
                        "created_at": datetime.now().isoformat(),
                        "is_active": True
                    }).execute()
                    st.success("Annonce ajoutée !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

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
            st.markdown(f"**{listing['title']}**")
            if listing.get("media_url"):
                st.image(listing["media_url"], use_column_width=True)
            st.write(listing["description"][:100] + "...")
            st.write(f"💰 {listing['price_kc']} KC")
            st.caption(f"Par {listing['profiles']['username']}")

def wallet_page():
    st.header("💰 Mon Wallet")
    wallet = supabase.table("wallets").select("*").eq("user_id", user.id).execute()
    if not wallet.data:
        supabase.table("wallets").insert({
            "user_id": user.id,
            "kongo_balance": 0.0,
            "total_mined": 0.0,
            "last_reward_at": datetime.now().isoformat()
        }).execute()
        wallet = supabase.table("wallets").select("*").eq("user_id", user.id).execute()
    wallet_data = wallet.data[0]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Solde KC", f"{wallet_data['kongo_balance']} KC")
    with col2:
        st.metric("Total miné", f"{wallet_data['total_mined']} KC")

    if st.button("⛏️ Miner (récompense quotidienne)"):
        last = datetime.fromisoformat(wallet_data["last_reward_at"].replace("Z", "+00:00"))
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
            st.warning(f"Tu pourras re-miner dans {int(reste//3600)}h{int((reste%3600)//60)}m.")

    st.subheader("Historique des transactions (à venir)")

def settings_page():
    st.header("⚙️ Paramètres")
    sub = supabase.table("subscriptions").select("*").eq("user_id", user.id).execute()
    if sub.data:
        plan = sub.data[0]["plan_type"]
        expires = sub.data[0].get("expires_at")
        st.info(f"Plan actuel : **{plan}**" + (f" (expire le {expires[:10]})" if expires else ""))
    else:
        st.info("Plan actuel : **Gratuit**")

    if st.button("Passer à Premium"):
        supabase.table("subscriptions").insert({
            "user_id": user.id,
            "plan_type": "Premium",
            "activated_at": datetime.now().isoformat(),
            "expires_at": (datetime.now().replace(year=datetime.now().year+1)).isoformat(),
            "is_active": True
        }).execute()
        st.success("Compte Premium activé !")
        st.rerun()

    st.divider()
    st.subheader("Zone dangereuse")
    if st.button("Supprimer mon compte", type="primary"):
        st.warning("Fonction désactivée pour le moment.")

def admin_page():
    st.header("🛡️ Espace Administration")
    st.caption("Actions réservées à la modération – utilisez‑les avec discernement.")
    tab1, tab2, tab3 = st.tabs(["Utilisateurs", "Posts signalés", "Logs d'action"])

    with tab1:
        st.subheader("Gestion des utilisateurs")
        # Note : la colonne email n'est pas dans profiles, on ne l'affiche pas
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
                    file_url = supabase.storage.from_("media").get_public_url(post["media_path"])
                    st.image(file_url, width=200)
                if st.button("🗑️ Supprimer ce post", key=f"del_{post['id']}"):
                    supabase.table("posts").delete().eq("id", post["id"]).execute()
                    st.success("Post supprimé")
                    st.rerun()

    with tab3:
        st.subheader("Journal des actions")
        st.info("Fonctionnalité à venir : traçabilité des actions d'administration.")

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
    
