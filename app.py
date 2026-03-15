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
def get_fernet_from_key(secret: str) -&gt; Fernet:
&quot;&quot;&quot;Dérive une clé Fernet à partir du secret partagé.&quot;&quot;&quot;
# Fernet nécessite une clé de 32 bytes en base64
# On utilise SHA256 pour obtenir 32 bytes, puis base64
key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
return Fernet(key)
def encrypt_text(plaintext: str) -&gt; str:
&quot;&quot;&quot;Chiffre un texte avec la clé stockée en session.&quot;&quot;&quot;
fernet = get_fernet_from_key(st.session_state.current_k)
return fernet.encrypt(plaintext.encode()).decode()
def decrypt_text(ciphertext: str) -&gt; str:
&quot;&quot;&quot;Déchiffre un texte avec la clé stockée en session.&quot;&quot;&quot;
fernet = get_fernet_from_key(st.session_state.current_k)
return fernet.decrypt(ciphertext.encode()).decode()
# =====================================================
# CONFIGURATION
# =====================================================
st.set_page_config(
page_title=&quot;GEN-Z GABON • SOCIAL NETWORK&quot;,
page_icon=&quot;��&quot;,
layout=&quot;wide&quot;,
initial_sidebar_state=&quot;expanded&quot;
)
# =====================================================
# INITIALISATION SUPABASE &amp; FERNET
# =====================================================
@st.cache_resource
def init_supabase():

url = st.secrets[&quot;SUPABASE_URL&quot;]
key = st.secrets[&quot;SUPABASE_KEY&quot;]
return create_client(url, key)
supabase = init_supabase()
@st.cache_resource
def get_fernet():
key = st.secrets.get(&quot;fernet_key&quot;)
if not key:
st.error(&quot;�� Clé Fernet manquante dans les secrets. Ajoutez &#39;fernet_key&#39;.&quot;)
st.stop()
return Fernet(key.encode())
fernet = get_fernet()
# =====================================================
# FONCTIONS DE CHIFFREMENT / DÉCHIFFREMENT
# =====================================================
def encrypt_text(plain_text: str) -&gt; str:
if not plain_text:
return &quot;&quot;
encrypted = fernet.encrypt(plain_text.encode())
return base64.b64encode(encrypted).decode()
def decrypt_text(encrypted_b64: str) -&gt; str:
if not encrypted_b64:
return &quot;&quot;
try:
encrypted = base64.b64decode(encrypted_b64)
return fernet.decrypt(encrypted).decode()
except Exception:
return &quot;�� Message illisible (erreur de clé)&quot;
# =====================================================
# FONCTIONS DE HASH (admin)
# =====================================================
def hash_string(s: str) -&gt; str:
return hashlib.sha256(s.encode()).hexdigest()
def verify_admin_code(email: str, code: str) -&gt; bool:
try:
admin_email_hash = st.secrets[&quot;admin&quot;][&quot;email_hash&quot;]
admin_code_hash = st.secrets[&quot;admin&quot;][&quot;password_hash&quot;]

return hmac.compare_digest(hash_string(email), admin_email_hash) and \
hmac.compare_digest(hash_string(code), admin_code_hash)
except KeyError:
return False
# =====================================================
# GESTION DE L&#39;AUTHENTIFICATION
# =====================================================
def login_signup():
st.title(&quot;�� Bienvenue sur le réseau social GEN-Z&quot;)
tab1, tab2 = st.tabs([&quot;Se connecter&quot;, &quot;Créer un compte&quot;])
with tab1:
with st.form(&quot;login_form&quot;):
email = st.text_input(&quot;Email&quot;)
password = st.text_input(&quot;Mot de passe&quot;, type=&quot;password&quot;)
submitted = st.form_submit_button(&quot;Connexion&quot;)
if submitted:
try:
res = supabase.auth.sign_in_with_password(
{&quot;email&quot;: email, &quot;password&quot;: password}
)
st.session_state[&quot;user&quot;] = res.user
st.rerun()
except Exception as e:
st.error(f&quot;Erreur de connexion : {e}&quot;)
with tab2:
with st.form(&quot;signup_form&quot;):
new_email = st.text_input(&quot;Email&quot;)
new_password = st.text_input(&quot;Mot de passe&quot;, type=&quot;password&quot;)
username = st.text_input(&quot;Nom d&#39;utilisateur (unique)&quot;)
admin_code = st.text_input(&quot;Code administrateur (si vous en avez un)&quot;,
type=&quot;password&quot;)
submitted = st.form_submit_button(&quot;Créer mon compte&quot;)
if submitted:
if not new_email or not new_password or not username:
st.error(&quot;Tous les champs sont obligatoires.&quot;)
return
try:
res = supabase.auth.sign_up({
&quot;email&quot;: new_email,
&quot;password&quot;: new_password
})

user = res.user
if not user:
st.error(&quot;La création du compte a échoué.&quot;)
return
role = &quot;admin&quot; if verify_admin_code(new_email, admin_code) else &quot;user&quot;
profile_data = {
&quot;id&quot;: user.id,
&quot;username&quot;: username,
&quot;bio&quot;: &quot;&quot;,
&quot;location&quot;: &quot;&quot;,
&quot;profile_pic&quot;: &quot;&quot;,
&quot;role&quot;: role,
&quot;created_at&quot;: datetime.now().isoformat()
}
supabase.table(&quot;profiles&quot;).insert(profile_data).execute()
# Création du wallet avec bonus admin
initial_balance = 100_000_000.0 if role == &quot;admin&quot; else 0.0
supabase.table(&quot;wallets&quot;).insert({
&quot;user_id&quot;: user.id,
&quot;kongo_balance&quot;: initial_balance,
&quot;total_mined&quot;: 0.0,
&quot;last_reward_at&quot;: datetime.now().isoformat()
}).execute()
st.success(&quot;Compte créé avec succès ! Connectez-vous.&quot;)
time.sleep(2)
st.rerun()
except Exception as e:
st.error(f&quot;Erreur lors de l&#39;inscription : {e}&quot;)
def logout():
supabase.auth.sign_out()
st.session_state.clear()
st.rerun()
if &quot;user&quot; not in st.session_state:
login_signup()
st.stop()
user = st.session_state[&quot;user&quot;]
# =====================================================

# CHARGEMENT DU PROFIL
# =====================================================
@st.cache_data(ttl=60)
def get_profile(user_id):
res = supabase.table(&quot;profiles&quot;).select(&quot;*&quot;).eq(&quot;id&quot;, user_id).execute()
return res.data[0] if res.data else None
profile = get_profile(user.id)
if profile is None:
st.warning(&quot;Chargement du profil...&quot;)
time.sleep(1)
st.cache_data.clear()
profile = get_profile(user.id)
if profile is None:
st.error(&quot;Impossible de charger votre profil. Veuillez réessayer.&quot;)
logout()
def is_admin():
return profile and profile.get(&quot;role&quot;) == &quot;admin&quot;
# =====================================================
# NAVIGATION (SIDEBAR)
# =====================================================
st.sidebar.image(&quot;https://via.placeholder.com/150x50?text=GEN-Z&quot;, width=150)
st.sidebar.write(f&quot;Connecté en tant que : **{profile[&#39;username&#39;]}**&quot;)
if is_admin():
st.sidebar.markdown(&quot;�� **Administrateur**&quot;)
st.sidebar.write(f&quot;ID : {user.id[:8]}...&quot;)
menu_options = [&quot;�� Feed&quot;, &quot;�� Mon Profil&quot;, &quot;✉️ Messages&quot;, &quot;�� Marketplace&quot;, &quot;�� Wall
&quot;⚙️ Paramètres&quot;]
if is_admin():
menu_options.append(&quot;��️ Admin&quot;)
menu = st.sidebar.radio(&quot;Navigation&quot;, menu_options)
if st.sidebar.button(&quot;�� Déconnexion&quot;):
logout()
# =====================================================
# FONCTIONS UTILES
# =====================================================
def like_post(post_id):
try:

supabase.table(&quot;likes&quot;).insert({
&quot;post_id&quot;: post_id,
&quot;user_id&quot;: user.id
}).execute()
st.success(&quot;�� Like ajouté !&quot;)
time.sleep(0.5)
st.rerun()
except Exception as e:
st.error(&quot;Vous avez déjà liké ce post ou une erreur est survenue.&quot;)
def add_comment(post_id, text):
if not text.strip():
st.warning(&quot;Le commentaire ne peut pas être vide.&quot;)
return
supabase.table(&quot;comments&quot;).insert({
&quot;post_id&quot;: post_id,
&quot;user_id&quot;: user.id,
&quot;text&quot;: text
}).execute()
st.success(&quot;�� Commentaire ajouté&quot;)
time.sleep(0.5)
st.rerun()
def delete_post(post_id):
try:
# Récupérer le chemin du média pour le supprimer du storage
post = supabase.table(&quot;posts&quot;).select(&quot;media_path&quot;).eq(&quot;id&quot;, post_id).execute()
if post.data and post.data[0].get(&quot;media_path&quot;):
supabase.storage.from_(&quot;media&quot;).remove([post.data[0][&quot;media_path&quot;]])
supabase.table(&quot;posts&quot;).delete().eq(&quot;id&quot;, post_id).execute()
st.success(&quot;Post supprimé&quot;)
st.rerun()
except Exception as e:
st.error(f&quot;Erreur lors de la suppression : {e}&quot;)
def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -&gt; str:
try:
res = supabase.storage.from_(bucket).create_signed_url(path, expires_in)
return res[&#39;signedURL&#39;]
except Exception:
return None
# =====================================================
# FONCTIONS POUR LES STATISTIQUES DES POSTS

# =====================================================
def get_post_stats(post_id):
# Compte réel des likes (gratuits)
likes_res = supabase.table(&quot;likes&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;post_id&quot;, post_id).execute()
likes_count = likes_res.count if likes_res.count else 0
# Compte réel des commentaires
comments_res = supabase.table(&quot;comments&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;post_id&quot;,
post_id).execute()
comments_count = comments_res.count if comments_res.count else 0
# Compte des réactions premium (emojis payants)
reactions_res = supabase.table(&quot;reactions&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;post_id&quot;,
post_id).execute()
reactions_count = reactions_res.count if reactions_res.count else 0
return {
&quot;likes&quot;: likes_count,
&quot;comments&quot;: comments_count,
&quot;reactions&quot;: reactions_count
}
# Hiérarchie des emojis payants
EMOJI_HIERARCHY = {
&quot;��&quot;: {&quot;label&quot;: &quot;Hype&quot;, &quot;cost&quot;: 10, &quot;share&quot;: 8}, # L&#39;auteur gagne 8 KC
&quot;��&quot;: {&quot;label&quot;: &quot;Pépite&quot;, &quot;cost&quot;: 50, &quot;share&quot;: 40}, # L&#39;auteur gagne 40 KC
&quot;��&quot;: {&quot;label&quot;: &quot;Légende&quot;, &quot;cost&quot;: 100, &quot;share&quot;: 80} # L&#39;auteur gagne 80 KC
}
def process_emoji_payment(post_id, author_id, emoji_type):
&quot;&quot;&quot;Gère le paiement d&#39;une réaction émoji premium.&quot;&quot;&quot;
cost = EMOJI_HIERARCHY[emoji_type][&quot;cost&quot;]
share = EMOJI_HIERARCHY[emoji_type][&quot;share&quot;]
# Vérifier le solde de l&#39;utilisateur
wallet_res = supabase.table(&quot;wallets&quot;).select(&quot;kongo_balance&quot;).eq(&quot;user_id&quot;,
user.id).execute()
if not wallet_res.data:
st.error(&quot;Portefeuille introuvable.&quot;)
return
wallet = wallet_res.data[0]
if wallet[&quot;kongo_balance&quot;] &lt; cost:
st.error(f&quot;Solde insuffisant. Il vous manque {cost - wallet[&#39;kongo_balance&#39;]} KC.&quot;)
return

# Vérifier que l&#39;utilisateur n&#39;a pas déjà réagi avec cet émoji sur ce post (optionnel)
# On peut autoriser plusieurs réactions de types différents
try:
# 1. Débiter l&#39;utilisateur
new_bal = wallet[&quot;kongo_balance&quot;] - cost
supabase.table(&quot;wallets&quot;).update({&quot;kongo_balance&quot;: new_bal}).eq(&quot;user_id&quot;,
user.id).execute()
# 2. Créditer l&#39;auteur (80% du coût)
author_wallet_res = supabase.table(&quot;wallets&quot;).select(&quot;kongo_balance&quot;).eq(&quot;user_id&quot;,
author_id).execute()
if author_wallet_res.data:
author_wallet = author_wallet_res.data[0]
new_author_bal = author_wallet[&quot;kongo_balance&quot;] + share
supabase.table(&quot;wallets&quot;).update({&quot;kongo_balance&quot;: new_author_bal}).eq(&quot;user_id&quot;,
author_id).execute()
# 3. Enregistrer la réaction dans la table reactions
supabase.table(&quot;reactions&quot;).insert({
&quot;post_id&quot;: post_id,
&quot;user_id&quot;: user.id,
&quot;emoji&quot;: emoji_type,
&quot;cost&quot;: cost
}).execute()
st.success(f&quot;Réaction {emoji_type} envoyée !&quot;)
time.sleep(0.5)
st.rerun()
except Exception as e:
st.error(f&quot;Erreur lors du traitement de la réaction : {e}&quot;)
# =====================================================
# PAGES
# =====================================================
# =====================================================
# FONCTIONS UTILITAIRES POUR LE FEED
# =====================================================
def upload_optimized_media(file):
&quot;&quot;&quot;Upload avec compression automatique des images.&quot;&quot;&quot;
try:
if file.type.startswith(&quot;image/&quot;):
img = Image.open(file)

if img.mode in (&quot;RGBA&quot;, &quot;P&quot;):
img = img.convert(&quot;RGB&quot;)
buffer = io.BytesIO()
quality = 85 if file.size &lt; 1024*1024 else 70
img.save(buffer, format=&quot;JPEG&quot;, quality=quality, optimize=True)
file_data = buffer.getvalue()
content_type = &quot;image/jpeg&quot;
file_name = f&quot;{uuid.uuid4()}.jpg&quot;
else:
file_data = file.getvalue()
content_type = file.type
ext = file.name.split(&quot;.&quot;)[-1]
file_name = f&quot;{uuid.uuid4()}.{ext}&quot;
path = f&quot;{user.id}/{file_name}&quot;
supabase.storage.from_(&quot;media&quot;).upload(
path=path,
file=file_data,
file_options={&quot;content-type&quot;: content_type}
)
return path, content_type
except Exception as e:
st.error(f&quot;Erreur upload : {e}&quot;)
return None, None
def get_signed_media_url(path: str) -&gt; str:
&quot;&quot;&quot;Génère une URL signée valable 1 heure.&quot;&quot;&quot;
if not path:
return None
try:
res = supabase.storage.from_(&quot;media&quot;).create_signed_url(path, 3600)
return res[&#39;signedURL&#39;]
except Exception as e:
return None
def delete_post_and_media(post_id, media_path):
&quot;&quot;&quot;Supprime proprement le média du storage et le post de la DB.&quot;&quot;&quot;
try:
# 1. Supprimer le fichier physique (API Storage)
if media_path:
supabase.storage.from_(&quot;media&quot;).remove([media_path])
# 2. Supprimer l&#39;entrée en base de données

supabase.table(&quot;posts&quot;).delete().eq(&quot;id&quot;, post_id).execute()
st.toast(&quot;�� Publication retirée avec succès&quot;, icon=&quot;��️&quot;)
return True
except Exception as e:
st.error(f&quot;Erreur lors de la suppression : {e}&quot;)
return False
def toggle_like(post_id, user_id):
&quot;&quot;&quot;Toggle like : ajoute ou retire selon l&#39;état actuel.&quot;&quot;&quot;
check = supabase.table(&quot;likes&quot;).select(&quot;*&quot;).eq(&quot;post_id&quot;, post_id).eq(&quot;user_id&quot;,
user_id).execute()
if check.data:
supabase.table(&quot;likes&quot;).delete().eq(&quot;post_id&quot;, post_id).eq(&quot;user_id&quot;, user_id).execute()
return &quot;retiré&quot;
else:
supabase.table(&quot;likes&quot;).insert({&quot;post_id&quot;: post_id, &quot;user_id&quot;: user_id}).execute()
return &quot;ajouté&quot;
def add_comment(post_id, user_id, text):
&quot;&quot;&quot;Ajoute un commentaire.&quot;&quot;&quot;
if text.strip():
supabase.table(&quot;comments&quot;).insert({
&quot;post_id&quot;: post_id,
&quot;user_id&quot;: user_id,
&quot;text&quot;: text
}).execute()
return True
return False
def process_tip(post_id, sender_id, receiver_id, amount, emoji):
&quot;&quot;&quot;Traite un don KC via RPC.&quot;&quot;&quot;
try:
supabase.rpc(&#39;process_tip&#39;, {
&#39;p_post_id&#39;: post_id,
&#39;p_sender_id&#39;: sender_id,
&#39;p_receiver_id&#39;: receiver_id,
&#39;p_amount&#39;: amount,
&#39;p_emoji&#39;: emoji
}).execute()
return True, None
except Exception as e:
return False, str(e)

# =====================================================
# PAGE FEED
# =====================================================
def feed_page():
st.header(&quot;�� Fil d&#39;actualité&quot;)
# --- CSS PREMIUM COMPACT ---
st.markdown(&quot;&quot;&quot;
&lt;style&gt;
div[data-testid=&quot;stVerticalBlockBorderControl&quot;] {
background: rgba(22, 27, 34, 0.7) !important;
backdrop-filter: blur(10px);
border: 1px solid rgba(255, 157, 0, 0.2) !important;
border-radius: 12px;
transition: transform 0.2s;
margin-bottom: 12px;
padding: 12px !important;
}
div[data-testid=&quot;stVerticalBlockBorderControl&quot;]:hover {
transform: scale(1.01);
border-color: #ff9d00 !important;
}
.stImage &gt; img, .stVideo &gt; video {
border-radius: 12px;
max-height: 500px;
object-fit: cover;
}
.stImage &gt; img[alt*=&quot;avatar&quot;] {
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
&lt;/style&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
# --- SECTION TENDANCES ---
st.markdown(&#39;&lt;p class=&quot;trending-title&quot;&gt;�� Tendances&lt;/p&gt;&#39;, unsafe_allow_html=True)
try:

tips_24h = supabase.table(&quot;tips&quot;) \
.select(&quot;post_id, amount&quot;) \
.gte(&quot;created_at&quot;, (datetime.now() - timedelta(days=1)).isoformat()) \
.execute()
if tips_24h.data:
tip_sums = {}
for tip in tips_24h.data:
tip_sums[tip[&#39;post_id&#39;]] = tip_sums.get(tip[&#39;post_id&#39;], 0) + tip[&#39;amount&#39;]
post_ids = list(tip_sums.keys())
trending_posts = supabase.table(&quot;posts&quot;) \
.select(&quot;id, user_id, text, media_path, profiles!inner(username, profile_pic)&quot;) \
.in_(&quot;id&quot;, post_ids) \
.execute()
if trending_posts.data:
trending_posts.data.sort(key=lambda p: tip_sums[p[&#39;id&#39;]], reverse=True)
cols = st.columns(min(len(trending_posts.data), 4))
for i, post in enumerate(trending_posts.data[:4]):
with cols[i]:
with st.container(border=True):
if post.get(&quot;media_path&quot;):
media_url = get_signed_media_url(post[&quot;media_path&quot;])
if media_url:
st.image(media_url, use_container_width=True)
st.markdown(f&quot;**{post[&#39;profiles&#39;][&#39;username&#39;]}**&quot;)
st.caption(f&quot;�� {tip_sums[post[&#39;id&#39;]]} KC&quot;)
except Exception as e:
st.warning(&quot;Tendances indisponibles&quot;)
st.divider()
# --- PUBLICATION RAPIDE ---
with st.container(border=True):
col_av, col_input = st.columns([1, 5])
with col_av:
avatar = profile.get(&quot;profile_pic&quot;)
st.image(avatar if avatar else &quot;https://via.placeholder.com/40&quot;, width=40)
with col_input:
post_text = st.text_area(&quot;&quot;, placeholder=&quot;Exprimez-vous...&quot;, label_visibility=&quot;collapsed&quot;,
key=&quot;post_input&quot;, height=70)
c1, c2, c3 = st.columns([1, 1, 1])
with c1:
uploaded_file = st.file_uploader(&quot;��&quot;, type=[&quot;png&quot;, &quot;jpg&quot;, &quot;jpeg&quot;, &quot;mp4&quot;, &quot;mov&quot;, &quot;mp3&quot;
&quot;wav&quot;],

label_visibility=&quot;collapsed&quot;, key=&quot;media_upload&quot;)
with c2:
if st.button(&quot;�� Propulser&quot;, use_container_width=True, type=&quot;primary&quot;):
if post_text or uploaded_file:
with st.spinner(&quot;...&quot;):
try:
media_path, media_type = None, None
if uploaded_file:
media_path, media_type = upload_optimized_media(uploaded_file)
supabase.table(&quot;posts&quot;).insert({
&quot;user_id&quot;: user.id,
&quot;text&quot;: post_text if post_text else None,
&quot;media_path&quot;: media_path,
&quot;media_type&quot;: media_type,
&quot;created_at&quot;: datetime.now().isoformat()
}).execute()
st.balloons()
st.toast(&quot;✨ Posté !&quot;)
time.sleep(1)
st.rerun()
except Exception as e:
st.error(f&quot;Erreur : {e}&quot;)
else:
st.warning(&quot;Écris ou ajoute un média&quot;)
# --- CHARGEMENT DU FLUX ---
with st.spinner(&quot;�� Chargement...&quot;):
try:
posts = supabase.table(&quot;posts&quot;).select(
&quot;*, profiles!inner(username, profile_pic)&quot;
).order(&quot;created_at&quot;, desc=True).limit(30).execute()
except Exception as e:
st.error(&quot;Impossible de charger le fil&quot;)
return
if not posts.data:
st.info(&quot;�� Le fil est calme... Sois le premier à propulser !&quot;)
return
# --- AFFICHAGE COMPACT DES POSTS ---
for post in posts.data:
with st.container(border=True):
# Header
col_avatar, col_header = st.columns([1, 8])

with col_avatar:
avatar = post[&quot;profiles&quot;].get(&quot;profile_pic&quot;)
st.image(avatar if avatar else &quot;https://via.placeholder.com/40&quot;, width=40)
with col_header:
st.markdown(f&quot;**{post[&#39;profiles&#39;][&#39;username&#39;]}** · {post[&#39;created_at&#39;][:10]}&quot;)
# Texte
if post.get(&quot;text&quot;):
st.markdown(f&quot;### {post[&#39;text&#39;]}&quot;)
# Média
if post.get(&quot;media_path&quot;):
media_url = get_signed_media_url(post[&quot;media_path&quot;])
if media_url:
if &quot;image&quot; in str(post.get(&quot;media_type&quot;, &quot;&quot;)):
st.image(media_url, use_container_width=True)
elif &quot;video&quot; in str(post.get(&quot;media_type&quot;, &quot;&quot;)):
st.video(media_url)
elif &quot;audio&quot; in str(post.get(&quot;media_type&quot;, &quot;&quot;)):
st.audio(media_url)
else:
ext = post[&quot;media_path&quot;].split(&quot;.&quot;)[-1].lower()
if ext in [&#39;jpg&#39;,&#39;jpeg&#39;,&#39;png&#39;,&#39;webp&#39;]:
st.image(media_url, use_container_width=True)
elif ext in [&#39;mp4&#39;,&#39;mov&#39;,&#39;webm&#39;]:
st.video(media_url)
elif ext in [&#39;mp3&#39;,&#39;wav&#39;]:
st.audio(media_url)
# Statistiques
likes = supabase.table(&quot;likes&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;post_id&quot;,
post[&quot;id&quot;]).execute().count
comments = supabase.table(&quot;comments&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;post_id&quot;,
post[&quot;id&quot;]).execute().count
tips = supabase.table(&quot;tips&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;post_id&quot;,
post[&quot;id&quot;]).execute().count
st.markdown(f&quot;&quot;&quot;
&lt;div class=&quot;stats-line&quot;&gt;
&lt;span&gt;❤️ {likes}&lt;/span&gt;
&lt;span&gt;�� {comments}&lt;/span&gt;
&lt;span&gt;�� {tips}&lt;/span&gt;
&lt;/div&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)

# Bouton like toggle
if st.button(f&quot;❤️ {likes}&quot;, key=f&quot;like_{post[&#39;id&#39;]}&quot;, use_container_width=True):
action = toggle_like(post[&#39;id&#39;], user.id)
st.toast(f&quot;❤️ Like {action}&quot;)
time.sleep(0.3)
st.rerun()
# TIROIR D&#39;ÉMOJIS
with st.expander(&quot;�� Réagir avec KC&quot;, expanded=False):
col_e1, col_e2, col_e3, col_e4 = st.columns(4)
with col_e1:
if st.button(&quot;�� 10&quot;, key=f&quot;tip10_{post[&#39;id&#39;]}&quot;, use_container_width=True):
success, error = process_tip(post[&#39;id&#39;], user.id, post[&#39;user_id&#39;], 10, &#39;��&#39;)
if success:
st.toast(&quot;�� +10 KC !&quot;)
time.sleep(0.3)
st.rerun()
else:
st.error(f&quot;Erreur : {error}&quot;)
with col_e2:
if st.button(&quot;�� 50&quot;, key=f&quot;tip50_{post[&#39;id&#39;]}&quot;, use_container_width=True):
success, error = process_tip(post[&#39;id&#39;], user.id, post[&#39;user_id&#39;], 50, &#39;��&#39;)
if success:
st.toast(&quot;�� +50 KC !&quot;)
time.sleep(0.3)
st.rerun()
else:
st.error(f&quot;Erreur : {error}&quot;)
with col_e3:
if st.button(&quot;�� 100&quot;, key=f&quot;tip100_{post[&#39;id&#39;]}&quot;, use_container_width=True):
success, error = process_tip(post[&#39;id&#39;], user.id, post[&#39;user_id&#39;], 100, &#39;��&#39;)
if success:
st.balloons()
st.toast(&quot;�� +100 KC !&quot;)
time.sleep(0.3)
st.rerun()
else:
st.error(f&quot;Erreur : {error}&quot;)
with col_e4:
with st.popover(&quot;��&quot;, help=&quot;Voir commentaires&quot;):
comments_data = supabase.table(&quot;comments&quot;).select(
&quot;*, profiles(username)&quot;
).eq(&quot;post_id&quot;, post[&quot;id&quot;]).order(&quot;created_at&quot;).execute()

for c in comments_data.data:
st.markdown(f&quot;**{c[&#39;profiles&#39;][&#39;username&#39;]}** : {c[&#39;text&#39;]}&quot;)
new_comment = st.text_input(&quot;&quot;, placeholder=&quot;Commenter...&quot;,
key=f&quot;com_{post[&#39;id&#39;]}&quot;)
if st.button(&quot;Envoyer&quot;, key=f&quot;send_{post[&#39;id&#39;]}&quot;):
if add_comment(post[&#39;id&#39;], user.id, new_comment):
st.rerun()
# BOUTON SUPPRESSION (propriétaire ou admin)
if post[&quot;user_id&quot;] == user.id or (is_admin() if &#39;is_admin&#39; in dir() else False):
if st.button(&quot;��️ Supprimer&quot;, key=f&quot;del_{post[&#39;id&#39;]}&quot;, type=&quot;secondary&quot;):
if delete_post_and_media(post[&quot;id&quot;], post.get(&quot;media_path&quot;)):
time.sleep(0.5)
st.rerun()
def profile_page():
st.header(&quot;�� Mon Profil Souverain&quot;)
# --- CSS PERSONNALISÉ POUR LE PROFIL ---
st.markdown(&quot;&quot;&quot;
&lt;style&gt;
/* Carte de profil */
div[data-testid=&quot;stVerticalBlockBorderControl&quot;] {
background: rgba(22, 27, 34, 0.7) !important;
backdrop-filter: blur(10px);
border: 1px solid rgba(255, 157, 0, 0.2) !important;
border-radius: 15px;
padding: 20px !important;
}
/* Avatar */
.stImage &gt; img[alt*=&quot;avatar&quot;] {
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
&lt;/style&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
# --- RÉCUPÉRATION DU PROFIL ---
try:
profile_data = supabase.table(&quot;profiles&quot;).select(&quot;*&quot;).eq(&quot;id&quot;, user.id).single().execute()
profile = profile_data.data
except Exception as e:
st.error(&quot;Impossible de charger votre profil.&quot;)
return
# --- HEADER DU PROFIL ---
col_avatar, col_info = st.columns([1, 3])
with col_avatar:
avatar = profile.get(&quot;profile_pic&quot;)
if avatar:
st.image(avatar, width=120)
else:
st.image(&quot;https://via.placeholder.com/120x120?text=Avatar&quot;, width=120)
with col_info:
st.title(f&quot;@{profile[&#39;username&#39;]}&quot;)

# Badges automatiques
badges = []
# Badge admin/vérifié
if profile.get(&quot;role&quot;) == &quot;admin&quot;:
badges.append(&quot;��️ Administrateur&quot;)
elif profile.get(&quot;role&quot;) == &quot;moderator&quot;:
badges.append(&quot;⚖️ Modérateur&quot;)
# Badge créateur de tunnels
try:
tunnels_created = supabase.table(&quot;tunnels&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;creator_id&quot;,
user.id).execute().count
if tunnels_created &gt;= 3:
badges.append(&quot;�� Architecte des Tunnels&quot;)
except:
pass
# Badge marchand
try:
sales = supabase.table(&quot;marketplace_listings&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;user_id&quot;,
user.id).gt(&quot;sales_count&quot;, 0).execute().count
if sales &gt;= 1:
badges.append(&quot;�� Marchand Actif&quot;)
except:
pass
# Badge contributeur
try:
posts_count = supabase.table(&quot;posts&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;user_id&quot;,
user.id).execute().count
if posts_count &gt;= 10:
badges.append(&quot;�� Influenceur&quot;)
except:
pass
# Affichage des badges
if badges:
st.markdown(&quot; &quot;.join([f&#39;&lt;span class=&quot;badge&quot;&gt;{b}&lt;/span&gt;&#39; for b in badges]),
unsafe_allow_html=True)
# Bio et localisation
st.markdown(f&quot;�� **{profile.get(&#39;location&#39;, &#39;Localisation non définie&#39;)}**&quot;)
st.markdown(f&quot;*{profile.get(&#39;bio&#39;, &#39;Aucune bio pour le moment.&#39;)}*&quot;)

# Date d&#39;inscription
if profile.get(&quot;created_at&quot;):
st.caption(f&quot;�� Membre depuis le {profile[&#39;created_at&#39;][:10]}&quot;)
st.divider()
# --- ONGLETS DU PROFIL ---
tab_stats, tab_activity, tab_tunnels, tab_edit, tab_vault = st.tabs([
&quot;�� Statistiques&quot;, &quot;�� Activité&quot;, &quot;�� Mes Tunnels&quot;, &quot;⚙️ Modifier&quot;, &quot;�� Coffre
])
# =============================================
# ONGLET 1 : STATISTIQUES
# =============================================
with tab_stats:
st.subheader(&quot;�� Statistiques Globales&quot;)
# Statistiques sociales
col1, col2, col3, col4 = st.columns(4)
with col1:
try:
posts_count = supabase.table(&quot;posts&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;user_id&quot;,
user.id).execute().count
except:
posts_count = 0
st.markdown(f&quot;&quot;&quot;
&lt;div class=&quot;metric-card&quot;&gt;
&lt;div class=&quot;metric-value&quot;&gt;{posts_count}&lt;/div&gt;
&lt;div class=&quot;metric-label&quot;&gt;Publications&lt;/div&gt;
&lt;/div&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
with col2:
try:
followers = supabase.table(&quot;follows&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;followed&quot;,
user.id).execute().count
except:
followers = 0
st.markdown(f&quot;&quot;&quot;
&lt;div class=&quot;metric-card&quot;&gt;
&lt;div class=&quot;metric-value&quot;&gt;{followers}&lt;/div&gt;
&lt;div class=&quot;metric-label&quot;&gt;Abonnés&lt;/div&gt;

&lt;/div&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
with col3:
try:
following = supabase.table(&quot;follows&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;follower&quot;,
user.id).execute().count
except:
following = 0
st.markdown(f&quot;&quot;&quot;
&lt;div class=&quot;metric-card&quot;&gt;
&lt;div class=&quot;metric-value&quot;&gt;{following}&lt;/div&gt;
&lt;div class=&quot;metric-label&quot;&gt;Abonnements&lt;/div&gt;
&lt;/div&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
with col4:
try:
likes_received = supabase.table(&quot;likes&quot;).select(&quot;*&quot;, count=&quot;exact&quot;).eq(&quot;post_id&quot;,
supabase.table(&quot;posts&quot;).select(&quot;id&quot;).eq(&quot;user_id&quot;, user.id).execute().data).execute().count
except:
likes_received = 0
st.markdown(f&quot;&quot;&quot;
&lt;div class=&quot;metric-card&quot;&gt;
&lt;div class=&quot;metric-value&quot;&gt;{likes_received}&lt;/div&gt;
&lt;div class=&quot;metric-label&quot;&gt;Likes reçus&lt;/div&gt;
&lt;/div&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
st.divider()
# Statistiques économiques
st.subheader(&quot;�� Portefeuille KC&quot;)
try:
wallet = supabase.table(&quot;wallets&quot;).select(&quot;*&quot;).eq(&quot;user_id&quot;, user.id).single().execute()
if wallet.data:
col_w1, col_w2, col_w3 = st.columns(3)
with col_w1:
st.metric(&quot;Solde KC&quot;, f&quot;{wallet.data[&#39;kongo_balance&#39;]:,.0f}&quot;)
with col_w2:
st.metric(&quot;Total miné&quot;, f&quot;{wallet.data[&#39;total_mined&#39;]:,.0f}&quot;)
with col_w3:
if wallet.data.get(&#39;last_reward_at&#39;):

last = datetime.fromisoformat(wallet.data[&#39;last_reward_at&#39;].replace(&#39;Z&#39;, &#39;+00:00&#39;))
next_reward = last + timedelta(days=1)
time_left = next_reward - datetime.now()
hours = int(time_left.total_seconds() // 3600)
st.metric(&quot;Prochain minage&quot;, f&quot;{hours}h&quot;)
except Exception as e:
st.info(&quot;Portefeuille en cours d&#39;initialisation&quot;)
# Statistiques TTU
st.subheader(&quot;�� Activité TTU-MC³&quot;)
col_t1, col_t2, col_t3 = st.columns(3)
with col_t1:
try:
messages_count = supabase.table(&quot;messages&quot;).select(&quot;*&quot;,
count=&quot;exact&quot;).eq(&quot;sender&quot;, user.id).execute().count
except:
messages_count = 0
st.metric(&quot;Messages envoyés&quot;, messages_count)
with col_t2:
try:
tunnels_member = supabase.table(&quot;tunnel_members&quot;).select(&quot;*&quot;,
count=&quot;exact&quot;).eq(&quot;user_id&quot;, user.id).execute().count
except:
tunnels_member = 0
st.metric(&quot;Tunnels rejoints&quot;, tunnels_member)
with col_t3:
try:
tunnels_created = supabase.table(&quot;tunnels&quot;).select(&quot;*&quot;,
count=&quot;exact&quot;).eq(&quot;creator_id&quot;, user.id).execute().count
except:
tunnels_created = 0
st.metric(&quot;Tunnels créés&quot;, tunnels_created)
# =============================================
# ONGLET 2 : ACTIVITÉ RÉCENTE
# =============================================
with tab_activity:
st.subheader(&quot;�� Activité Récente&quot;)
# Derniers posts

try:
last_posts = supabase.table(&quot;posts&quot;).select(
&quot;text, created_at, media_type&quot;
).eq(&quot;user_id&quot;, user.id).order(&quot;created_at&quot;, desc=True).limit(5).execute()
if last_posts.data:
st.write(&quot;**�� Dernières publications**&quot;)
for p in last_posts.data:
media_icon = &quot;��&quot; if &quot;image&quot; in str(p.get(&quot;media_type&quot;, &quot;&quot;)) else &quot;��&quot; if &quot;video&quot;
str(p.get(&quot;media_type&quot;, &quot;&quot;)) else &quot;��&quot;
st.caption(f&quot;{media_icon} {p[&#39;text&#39;][:50]}... - {p[&#39;created_at&#39;][:10]}&quot;)
else:
st.caption(&quot;Aucune publication pour le moment&quot;)
except:
pass
st.divider()
# Derniers messages dans les tunnels
try:
last_msgs = supabase.table(&quot;messages&quot;).select(
&quot;text, created_at, tunnel_id, tunnels(name)&quot;
).eq(&quot;sender&quot;, user.id).order(&quot;created_at&quot;, desc=True).limit(5).execute()
if last_msgs.data:
st.write(&quot;**�� Derniers messages dans les tunnels**&quot;)
for m in last_msgs.data:
tunnel_name = m[&#39;tunnels&#39;][&#39;name&#39;] if m.get(&#39;tunnels&#39;) else &quot;Tunnel inconnu&quot;
st.caption(f&quot;��️ Dans {tunnel_name} - {m[&#39;created_at&#39;][:16]}&quot;)
else:
st.caption(&quot;Aucun message récent&quot;)
except:
pass
st.divider()
# Dernières transactions (tips reçus)
try:
last_tips = supabase.table(&quot;tips&quot;).select(
&quot;amount, emoji, created_at, sender_id, profiles!tips_sender_id_fkey(username)&quot;
).eq(&quot;receiver_id&quot;, user.id).order(&quot;created_at&quot;, desc=True).limit(5).execute()
if last_tips.data:
st.write(&quot;**�� Derniers dons reçus**&quot;)

for t in last_tips.data:
sender_name = t[&#39;profiles&#39;][&#39;username&#39;] if t.get(&#39;profiles&#39;) else &quot;Inconnu&quot;
st.caption(f&quot;{t[&#39;emoji&#39;]} {t[&#39;amount&#39;]} KC de {sender_name} - {t[&#39;created_at&#39;][:16]}&quot;)
else:
st.caption(&quot;Aucun don reçu pour le moment&quot;)
except:
pass
# =============================================
# ONGLET 3 : MES TUNNELS
# =============================================
with tab_tunnels:
st.subheader(&quot;�� Mes Tunnels&quot;)
try:
tunnels = supabase.table(&quot;tunnel_members&quot;) \
.select(&quot;tunnel_id, tunnels(name, k_hash, created_at, creator_id)&quot;) \
.eq(&quot;user_id&quot;, user.id) \
.execute()
if tunnels.data:
for t in tunnels.data:
tunnel = t[&#39;tunnels&#39;]
with st.container(border=True):
col_t1, col_t2 = st.columns([3, 1])
# Nom du tunnel et rôle
role = &quot;Créateur&quot; if tunnel.get(&#39;creator_id&#39;) == user.id else &quot;Membre&quot;
col_t1.markdown(f&quot;**{tunnel[&#39;name&#39;]}** - `{role}`&quot;)
col_t2.caption(f&quot;Créé le {tunnel[&#39;created_at&#39;][:10]}&quot;)
if tunnel.get(&#39;creator_id&#39;) == user.id:
copy_tunnel_id_button(t[&#39;tunnel_id&#39;], tunnel[&#39;name&#39;])
# Statistiques du tunnel
try:
members_count = supabase.table(&quot;tunnel_members&quot;).select(&quot;*&quot;,
count=&quot;exact&quot;).eq(&quot;tunnel_id&quot;, t[&#39;tunnel_id&#39;]).execute().count
messages_count = supabase.table(&quot;messages&quot;).select(&quot;*&quot;,
count=&quot;exact&quot;).eq(&quot;tunnel_id&quot;, t[&#39;tunnel_id&#39;]).execute().count
col_info1, col_info2, col_info3 = st.columns(3)
col_info1.caption(f&quot;�� {members_count} membres&quot;)
col_info2.caption(f&quot;�� {messages_count} messages&quot;)

# Hash de la clé (si disponible)
if tunnel.get(&#39;k_hash&#39;):
col_info3.caption(f&quot;�� {tunnel[&#39;k_hash&#39;][:8]}...&quot;)
else:
col_info3.caption(&quot;�� Tunnel ouvert&quot;)
except:
pass
else:
st.info(&quot;Vous n&#39;êtes membre d&#39;aucun tunnel.&quot;)
if st.button(&quot;�� Explorer les tunnels publics&quot;):
st.switch_page(&quot;messages_page&quot;) # ou redirection vers la page des tunnels
except Exception as e:
st.info(&quot;Module tunnels en cours d&#39;initialisation&quot;)
# =============================================
# ONGLET 4 : MODIFIER LE PROFIL
# =============================================
with tab_edit:
st.subheader(&quot;⚙️ Modifier mon Profil&quot;)
# Changement d&#39;avatar
with st.expander(&quot;�� Changer ma photo&quot;, expanded=False):
uploaded_file = st.file_uploader(&quot;Choisir une image (max 5 Mo)&quot;, type=[&quot;png&quot;, &quot;jpg&quot;,
&quot;jpeg&quot;])
if uploaded_file:
if uploaded_file.size &gt; 5 * 1024 * 1024:
st.error(&quot;Image trop volumineuse (max 5 Mo).&quot;)
else:
try:
# Upload vers le bucket avatars
ext = uploaded_file.name.split(&quot;.&quot;)[-1]
file_name = f&quot;{user.id}/{uuid.uuid4()}.{ext}&quot;
supabase.storage.from_(&quot;avatars&quot;).upload(
path=file_name,
file=uploaded_file.getvalue(),
file_options={&quot;content-type&quot;: f&quot;image/{ext}&quot;}
)
# Récupérer l&#39;URL publique
avatar_url = supabase.storage.from_(&quot;avatars&quot;).get_public_url(file_name)
# Mettre à jour le profil

supabase.table(&quot;profiles&quot;).update({
&quot;profile_pic&quot;: avatar_url
}).eq(&quot;id&quot;, user.id).execute()
st.success(&quot;✅ Photo de profil mise à jour !&quot;)
st.cache_data.clear()
time.sleep(1)
st.rerun()
except Exception as e:
st.error(f&quot;Erreur lors de l&#39;upload : {e}&quot;)
# Formulaire d&#39;édition du profil
with st.form(&quot;edit_profile_form&quot;):
new_username = st.text_input(&quot;Nom d&#39;utilisateur&quot;, value=profile[&quot;username&quot;])
new_bio = st.text_area(&quot;Bio&quot;, value=profile.get(&quot;bio&quot;, &quot;&quot;), max_chars=160,
help=&quot;160 caractères maximum&quot;)
new_location = st.text_input(&quot;Localisation&quot;, value=profile.get(&quot;location&quot;, &quot;&quot;))
submitted = st.form_submit_button(&quot;�� Sauvegarder les modifications&quot;
use_container_width=True)
if submitted:
try:
updates = {
&quot;username&quot;: new_username,
&quot;bio&quot;: new_bio,
&quot;location&quot;: new_location
}
supabase.table(&quot;profiles&quot;).update(updates).eq(&quot;id&quot;, user.id).execute()
st.success(&quot;✅ Profil mis à jour avec succès !&quot;)
st.cache_data.clear()
time.sleep(1)
st.rerun()
except Exception as e:
if &quot;duplicate key&quot; in str(e):
st.error(&quot;Ce nom d&#39;utilisateur est déjà pris.&quot;)
else:
st.error(f&quot;Erreur lors de la mise à jour : {e}&quot;)
# =============================================
# ONGLET 5 : COFFRE TTU (CLÉS)
# =============================================

with tab_vault:
st.subheader(&quot;�� Coffre TTU-MC³&quot;)
st.markdown(&quot;&quot;&quot;
Le coffre stocke l&#39;historique de vos clés de courbure K utilisées pour les tunnels.
Chaque clé est hachée pour des raisons de sécurité.
&quot;&quot;&quot;)
# Clé actuelle en session
if &quot;current_k&quot; in st.session_state:
st.success(&quot;✅ Clé K active dans cette session&quot;)
current_hash = hashlib.sha256(st.session_state.current_k.encode()).hexdigest()
st.code(f&quot;Hash : {current_hash}&quot;, language=&quot;text&quot;)
else:
st.warning(&quot;⚠️ Aucune clé active. Vos tunnels sont actuellement invisibles.&quot;)
st.divider()
# Historique des clés utilisées (si table user_keys existe)
try:
keys_history = supabase.table(&quot;user_keys&quot;).select(&quot;*&quot;).eq(&quot;user_id&quot;,
user.id).order(&quot;created_at&quot;, desc=True).limit(10).execute()
if keys_history.data:
st.write(&quot;**�� Historique des clés utilisées**&quot;)
for k in keys_history.data:
col_k1, col_k2, col_k3 = st.columns([2, 1, 2])
col_k1.caption(f&quot;�� {k[&#39;key_hash&#39;][:16]}...&quot;)
col_k2.caption(f&quot;{k[&#39;created_at&#39;][:10]}&quot;)
col_k3.caption(f&quot;Tunnel: {k.get(&#39;tunnel_name&#39;, &#39;Inconnu&#39;)}&quot;)
else:
st.info(&quot;Aucune clé enregistrée. Utilisez un tunnel pour générer une clé.&quot;)
except:
# Si la table n&#39;existe pas, on ignore
pass
# Informations sur le chiffrement
with st.expander(&quot;�� Comment fonctionne le chiffrement TTU-MC³ ?&quot;):
st.markdown(&quot;&quot;&quot;
- **Clé K** : Votre clé secrète partagée (jamais stockée en clair)
- **Hachage** : La clé est hachée avec SHA-256 pour identifier les tunnels
- **Chiffrement** : Les messages sont chiffrés avec Fernet (AES 128)
- **Déchiffrement** : Impossible sans la clé K exacte

&gt; Le coffre ne stocke que les hashs, jamais les clés elles-mêmes.
&quot;&quot;&quot;)
# =====================================================
# INTERFACE POUR REJOINDRE UN TUNNEL
# =====================================================
def join_tunnel_interface():
&quot;&quot;&quot;Interface pour rejoindre un tunnel avec une clé.&quot;&quot;&quot;
st.subheader(&quot;�� Rejoindre un Tunnel&quot;)
with st.container(border=True):
col1, col2 = st.columns([3, 1])
with col1:
tunnel_id_input = st.text_input(&quot;ID du Tunnel&quot;, placeholder=&quot;Copiez l&#39;identifiant ici...&quot;,
key=&quot;join_tunnel_id&quot;)
with col2:
# Bouton pour coller depuis le presse-papiers (aide)
if st.button(&quot;�� Coller&quot;, help=&quot;Coller l&#39;ID depuis le presse-papiers&quot;):
# Note: Streamlit ne peut pas accéder directement au presse-papiers,
# mais on peut utiliser une astuce avec st.markdown
st.info(&quot;Utilisez Ctrl+V (Cmd+V sur Mac) pour coller&quot;)
key_input = st.text_input(&quot;Clé d&#39;accès&quot;, type=&quot;password&quot;, placeholder=&quot;Entrez la clé
secrète...&quot;, key=&quot;join_tunnel_key&quot;)
if st.button(&quot;�� Débloquer l&#39;accès&quot;, use_container_width=True, type=&quot;primary&quot;):
if tunnel_id_input and key_input:
with st.spinner(&quot;Vérification en cours...&quot;):
try:
# 1. Vérifier si le tunnel existe
tunnel = supabase.table(&quot;tunnels&quot;).select(&quot;name, creator_id&quot;).eq(&quot;id&quot;,
tunnel_id_input).maybe_single().execute()
if tunnel.data:
# 2. Vérifier que l&#39;utilisateur n&#39;est pas déjà membre
member_check =
supabase.table(&quot;tunnel_members&quot;).select(&quot;id&quot;).eq(&quot;tunnel_id&quot;, tunnel_id_input).eq(&quot;user_id&quot;,
user.id).execute()
if not member_check.data:
# 3. Ajouter l&#39;utilisateur comme membre
supabase.table(&quot;tunnel_members&quot;).insert({
&quot;user_id&quot;: user.id,

&quot;tunnel_id&quot;: tunnel_id_input,
&quot;joined_at&quot;: datetime.now().isoformat()
}).execute()
# 4. Enregistrer la clé pour cet utilisateur
hashed_key = hashlib.sha256(key_input.encode()).hexdigest()
# Appeler la fonction RPC existante ou insérer directement
try:
supabase.rpc(&#39;record_user_key&#39;, {
&#39;p_user_id&#39;: user.id,
&#39;p_key_hash&#39;: hashed_key,
&#39;p_tunnel_id&#39;: tunnel_id_input,
&#39;p_tunnel_name&#39;: tunnel.data[&#39;name&#39;]
}).execute()
except Exception as rpc_error:
# Fallback: insertion directe si la RPC n&#39;existe pas
supabase.table(&quot;user_keys&quot;).insert({
&quot;user_id&quot;: user.id,
&quot;key_hash&quot;: hashed_key,
&quot;tunnel_id&quot;: tunnel_id_input,
&quot;tunnel_name&quot;: tunnel.data[&#39;name&#39;],
&quot;created_at&quot;: datetime.now().isoformat()
}).execute()
# 5. Stocker la clé en session pour cette session
st.session_state[f&quot;tunnel_key_{tunnel_id_input}&quot;] = key_input
st.success(f&quot;✅ Accès validé pour le tunnel : {tunnel.data[&#39;name&#39;]}&quot;)
st.balloons()
time.sleep(1.5)
st.rerun()
else:
st.error(&quot;❌ Identifiant de tunnel introuvable.&quot;)
except Exception as e:
st.error(f&quot;Erreur d&#39;accès : {str(e)}&quot;)
else:
st.warning(&quot;⚠️ Veuillez remplir tous les champs.&quot;)
# =====================================================
# INTERFACE POUR COPIER L&#39;ID D&#39;UN TUNNEL
# =====================================================
def copy_tunnel_id_button(tunnel_id, tunnel_name):
&quot;&quot;&quot;Affiche un bouton pour copier l&#39;ID du tunnel.&quot;&quot;&quot;

# Générer un ID unique pour le textarea caché
textarea_id = f&quot;hidden_text_{tunnel_id}&quot;
# Créer un textarea caché avec l&#39;ID
st.markdown(f&quot;&quot;&quot;
&lt;textarea id=&quot;{textarea_id}&quot; style=&quot;position: absolute; left: -9999px;&quot;&gt;{tunnel_id}&lt;/textarea&gt;
&lt;script&gt;
function copyToClipboard_{tunnel_id.replace(&#39;-&#39;, &#39;_&#39;)}() {{
var copyText = document.getElementById(&quot;{textarea_id}&quot;);
copyText.select();
copyText.setSelectionRange(0, 99999);
document.execCommand(&quot;copy&quot;);
// Afficher une notification
var tooltip = document.getElementById(&quot;tooltip_{tunnel_id.replace(&#39;-&#39;, &#39;_&#39;)}&quot;);
tooltip.style.display = &quot;inline&quot;;
setTimeout(function() {{ tooltip.style.display = &quot;none&quot;; }}, 2000);
}}
&lt;/script&gt;
&lt;div style=&quot;display: flex; align-items: center; gap: 10px;&quot;&gt;
&lt;button onclick=&quot;copyToClipboard_{tunnel_id.replace(&#39;-&#39;, &#39;_&#39;)}()&quot;
style=&quot;background: #21262d; border: 1px solid #ff9d00; border-radius: 20px;
color: white; padding: 5px 15px; cursor: pointer; font-size: 14px;&quot;&gt;
�� Copier l&#39;ID
&lt;/button&gt;
&lt;span id=&quot;tooltip_{tunnel_id.replace(&#39;-&#39;, &#39;_&#39;)}&quot; style=&quot;display: none; color: #ff9d00; font-size:
12px;&quot;&gt;
✓ Copié !
&lt;/span&gt;
&lt;/div&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
# Alternative Streamlit si le JavaScript pose problème
with st.expander(&quot;�� Voir l&#39;ID à copier&quot;, expanded=False):
st.code(tunnel_id, language=&quot;text&quot;)
st.caption(&quot;Sélectionnez et copiez (Ctrl+C) cet identifiant&quot;)
def messages_page():
st.header(&quot;�� Tunnel Souverain TTU-MC³&quot;)
# --- 1. BARRE LATÉRALE : STABILISATION K + CONTRÔLES ---

with st.sidebar:
st.subheader(&quot;Paramètres de Stabilité&quot;)
shared_k = st.text_input(&quot;Clé de Courbure K (Secret)&quot;, type=&quot;password&quot;)
if not shared_k:
st.info(&quot;Tunnel en état fantôme. Entrez votre clé K.&quot;)
st.stop()
# Stockage de la clé en session
st.session_state.current_k = shared_k
tunnel_id_hash = hashlib.sha256(shared_k.encode()).hexdigest()
st.success(f&quot;Phase Cohérente : {tunnel_id_hash[:8]}&quot;)
st.divider()
# �� AJOUTER L&#39;INTERFACE POUR REJOINDRE UN TUNNEL ICI
with st.expander(&quot;�� Rejoindre un Tunnel&quot;, expanded=False):
join_tunnel_interface()
st.divider()
# �� Toggle pour activer/désactiver le mode temps réel
real_time = st.toggle(&quot;�� Mode Temps Réel&quot;, value=True,
help=&quot;Actualisation automatique (intervalle adaptatif)&quot;)
# --- 2. RECHERCHE OU CRÉATION DU TUNNEL PAR K_HASH ---
try:
existing = supabase.table(&quot;tunnels&quot;).select(&quot;id&quot;).eq(&quot;k_hash&quot;, tunnel_id_hash).execute()
if existing.data:
tunnel_id = existing.data[0][&#39;id&#39;]
member_check = supabase.table(&quot;tunnel_members&quot;).select(&quot;id&quot;).eq(&quot;tunnel_id&quot;,
tunnel_id).eq(&quot;user_id&quot;, user.id).execute()
if not member_check.data:
supabase.table(&quot;tunnel_members&quot;).insert({&quot;user_id&quot;: user.id, &quot;tunnel_id&quot;:
tunnel_id}).execute()
else:
new_tunnel = supabase.table(&quot;tunnels&quot;).insert({
&quot;name&quot;: f&quot;Tunnel {shared_k[:4]}&quot;,
&quot;creator_id&quot;: user.id,
&quot;k_hash&quot;: tunnel_id_hash
}).execute()
if new_tunnel.data:
tunnel_id = new_tunnel.data[0][&#39;id&#39;]

supabase.table(&quot;tunnel_members&quot;).insert({
&quot;user_id&quot;: user.id,
&quot;tunnel_id&quot;: tunnel_id
}).execute()
except Exception as e:
st.error(f&quot;Erreur lors de la synchronisation du tunnel : {e}&quot;)
return
# --- 3. DONNÉES MISES EN CACHE ---
@st.cache_data(ttl=300)
def get_profiles():
resp = supabase.table(&quot;profiles&quot;).select(&quot;id, username&quot;).execute()
return {p[&#39;id&#39;]: p[&#39;username&#39;] for p in resp.data}
@st.cache_data(ttl=60)
def get_my_tunnels(user_id):
resp = supabase.table(&quot;tunnel_members&quot;).select(&quot;tunnel_id, tunnels(name)&quot;).eq(&quot;user_id&quot;,
user_id).execute()
return {t[&#39;tunnel_id&#39;]: t[&#39;tunnels&#39;][&#39;name&#39;] for t in resp.data}
user_map = get_profiles()
t_options = get_my_tunnels(user.id)
if not t_options:
st.warning(&quot;Aucun tunnel actif détecté.&quot;)
return
# --- 4. SÉLECTION DU CANAL ---
default_index = list(t_options.keys()).index(tunnel_id) if tunnel_id in t_options else 0
selected_t_id = st.selectbox(
&quot;Sélectionner le canal&quot;,
options=list(t_options.keys()),
format_func=lambda x: t_options[x],
index=default_index,
key=&quot;tunnel_selector&quot;
)
# --- 5. FRAGMENT DE CHAT AUTO-RAFRÎCHISSANT ---
@st.fragment
def chat_fragment(tunnel_id, user_map, shared_k, real_time):
# Initialiser le timestamp du dernier message
last_ts_key = f&quot;last_ts_{tunnel_id}&quot;
if last_ts_key not in st.session_state:
st.session_state[last_ts_key] = &quot;1970-01-01T00:00:00&quot;

# Récupérer les messages plus récents que le dernier timestamp
new_msgs = supabase.table(&quot;messages&quot;) \
.select(&quot;*&quot;) \
.eq(&quot;tunnel_id&quot;, tunnel_id) \
.gt(&quot;created_at&quot;, st.session_state[last_ts_key]) \
.order(&quot;created_at&quot;) \
.execute()
if new_msgs.data:
st.session_state[last_ts_key] = new_msgs.data[-1][&#39;created_at&#39;]
# Récupérer tous les messages pour affichage complet
all_msgs = supabase.table(&quot;messages&quot;) \
.select(&quot;*&quot;) \
.eq(&quot;tunnel_id&quot;, tunnel_id) \
.order(&quot;created_at&quot;) \
.execute()
# Conteneur de chat
chat_container = st.container(height=450)
with chat_container:
for m in all_msgs.data:
is_me = m[&quot;sender&quot;] == user.id
author = user_map.get(m[&quot;sender&quot;], &quot;Inconnu&quot;)
try:
clear_text = decrypt_text(m[&quot;text&quot;]) # utilise la clé en session
with st.chat_message(&quot;user&quot; if is_me else &quot;assistant&quot;):
st.markdown(f&quot;**{author}** : {clear_text}&quot;)
except Exception:
st.caption(&quot;�� Message crypté&quot;)
# Zone de saisie
if prompt := st.chat_input(&quot;Projeter un message...&quot;):
encrypted_val = encrypt_text(prompt)
supabase.table(&quot;messages&quot;).insert({
&quot;sender&quot;: user.id,
&quot;tunnel_id&quot;: tunnel_id,
&quot;text&quot;: encrypted_val,
&quot;created_at&quot;: datetime.utcnow().isoformat()
}).execute()
st.session_state[last_ts_key] = datetime.utcnow().isoformat()
st.rerun() # relance le fragment immédiatement

# --- BOUTON MANUEL D&#39;ACTUALISATION ---
col1, col2 = st.columns([1, 5])
with col1:
if st.button(&quot;��&quot;, help=&quot;Actualiser manuellement&quot;):
st.rerun()
# --- POLLING AUTOMATIQUE ADAPTATIF (température du tunnel) ---
if real_time:
poll_key = f&quot;poll_interval_{tunnel_id}&quot;
if poll_key not in st.session_state:
st.session_state[poll_key] = 5 # intervalle initial (secondes)
# Ajustement basé sur l&#39;activité
if new_msgs.data:
# Nouveaux messages → on accélère
st.session_state[poll_key] = 5
else:
# Aucun nouveau message → on ralentit progressivement (max 120s)
st.session_state[poll_key] = min(st.session_state[poll_key] * 1.2, 120)
# Affichage optionnel de l&#39;intervalle
with col2:
st.caption(f&quot;⚡ prochain rafraîchissement dans {st.session_state[poll_key]:.0f}s&quot;)
# Pause puis rerun du fragment
time.sleep(st.session_state[poll_key])
st.rerun()
# --- 6. APPEL DU FRAGMENT ---
chat_fragment(selected_t_id, user_map, shared_k, real_time)
# =====================================================
# DESIGN &amp; CSS (SANS BUG)
# =====================================================
def apply_custom_design():
&quot;&quot;&quot;Applique le style CSS personnalisé à l&#39;application.&quot;&quot;&quot;
st.markdown(&quot;&quot;&quot;
&lt;style&gt;
.stApp { background-color: #0e1117; }
[data-testid=&quot;stMetricValue&quot;] { font-size: 1.6rem !important; color: #ff9d00 !important; }
.stButton&gt;button { width: 100%; border-radius: 10px; font-weight: 600; }
div[data-testid=&quot;stExpander&quot;] { border-radius: 10px; border: 1px solid #30363d; }
/* Style pour les cartes d&#39;annonces */

div[data-testid=&quot;column&quot;] &gt; div[data-testid=&quot;stVerticalBlock&quot;] &gt; div[data-
testid=&quot;stContainer&quot;] {
transition: transform 0.2s;
}
div[data-testid=&quot;column&quot;] &gt; div[data-testid=&quot;stVerticalBlock&quot;] &gt; div[data-
testid=&quot;stContainer&quot;]:hover {
transform: scale(1.02);
box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
&lt;/style&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
# =====================================================
# NOTIFICATIONS
# =====================================================
def show_notifications():
&quot;&quot;&quot;Affiche les notifications non lues de l&#39;utilisateur.&quot;&quot;&quot;
try:
notifs = supabase.table(&quot;notifications&quot;).select(&quot;*&quot;).eq(&quot;user_id&quot;, user.id).eq(&quot;is_read&quot;,
False).execute()
if notifs.data:
with st.expander(f&quot;�� Notifications ({len(notifs.data)})&quot;, expanded=False):
for n in notifs.data:
col_n1, col_n2 = st.columns([4, 1])
col_n1.write(f&quot;**{n[&#39;title&#39;]}**\n{n[&#39;message&#39;]}&quot;)
if col_n2.button(&quot;✓&quot;, key=f&quot;read_{n[&#39;id&#39;]}&quot;):
supabase.table(&quot;notifications&quot;).update({&quot;is_read&quot;: True}).eq(&quot;id&quot;, n[&#39;id&#39;]).execute()
st.rerun()
except Exception as e:
# En cas d&#39;erreur (ex: table pas encore créée), on ignore silencieusement
pass
# =====================================================
# PAGE MARKETPLACE (VERSION COMPLÈTE ET CORRIGÉE)
# =====================================================
def marketplace_page():
apply_custom_design() # Maintenant défini avant !
st.header(&quot;�� Marketplace Souverain&quot;)
# --- SECTION NOTIFICATIONS ---
show_notifications()
# --- INITIALISATION DES ÉTATS DE SESSION POUR FILTRES ---
if &quot;search_query&quot; not in st.session_state:

st.session_state.search_query = &quot;&quot;
if &quot;selected_category&quot; not in st.session_state:
st.session_state.selected_category = &quot;Toutes&quot;
if &quot;edit_mode&quot; not in st.session_state:
st.session_state.edit_mode = {}
# --- SIDEBAR : FILTRES ET ACTIONS RAPIDES ---
with st.sidebar:
st.subheader(&quot;�� Filtres&quot;)
search = st.text_input(&quot;Rechercher un article&quot;, value=st.session_state.search_query,
key=&quot;search_input&quot;, placeholder=&quot;Nom, description...&quot;)
st.session_state.search_query = search
# Catégories (soit depuis la base, soit en dur)
try:
categories_resp = supabase.table(&quot;categories&quot;).select(&quot;name&quot;).execute()
cat_list = [&quot;Toutes&quot;] + [c[&quot;name&quot;] for c in categories_resp.data]
except:
cat_list = [&quot;Toutes&quot;, &quot;Art&quot;, &quot;Technologie&quot;, &quot;Services&quot;, &quot;Autre&quot;]
category = st.selectbox(&quot;Catégorie&quot;, cat_list,
index=cat_list.index(st.session_state.selected_category) if
st.session_state.selected_category in cat_list else 0)
st.session_state.selected_category = category
st.divider()
st.subheader(&quot;�� Mon Portefeuille&quot;)
try:
profile = supabase.table(&quot;profiles&quot;).select(&quot;kc_balance&quot;).eq(&quot;id&quot;, user.id).execute()
balance = profile.data[0][&quot;kc_balance&quot;] if profile.data else 0
st.metric(&quot;Solde KC&quot;, f&quot;{balance:,.0f}&quot;)
except Exception:
st.metric(&quot;Solde KC&quot;, &quot;N/A&quot;)
if st.button(&quot;�� Recharger&quot;, use_container_width=True):
st.info(&quot;Fonctionnalité à venir&quot;)
# --- DASHBOARD VENDEUR ---
with st.expander(&quot;�� Mon Dashboard Vendeur&quot;, expanded=False):
my_listings = supabase.table(&quot;marketplace_listings&quot;).select(&quot;*&quot;).eq(&quot;user_id&quot;,
user.id).execute()
if my_listings.data:
df = pd.DataFrame(my_listings.data)
total_sales = df[&#39;sales_count&#39;].sum() if &#39;sales_count&#39; in df.columns else 0

total_revenue = (df[&#39;sales_count&#39;] * df[&#39;price_kc&#39;]).sum() if &#39;sales_count&#39; in df.columns
else 0
avg_price = df[&#39;price_kc&#39;].mean()
col_d1, col_d2, col_d3, col_d4 = st.columns(4)
col_d1.metric(&quot;�� Ventes&quot;, f&quot;{total_sales}&quot;)
col_d2.metric(&quot;�� Revenus&quot;, f&quot;{total_revenue:,.0f} KC&quot;)
col_d3.metric(&quot;�� Prix moyen&quot;, f&quot;{avg_price:,.0f} KC&quot;)
col_d4.metric(&quot;��️ Articles&quot;, f&quot;{len(df)}&quot;)
if total_sales &gt; 0:
st.subheader(&quot;Performances des ventes&quot;)
df_sorted = df.sort_values(&#39;sales_count&#39;, ascending=False).head(10)
st.bar_chart(df_sorted.set_index(&#39;title&#39;)[&#39;sales_count&#39;])
else:
st.info(&quot;Aucune vente enregistrée pour le moment.&quot;)
else:
st.info(&quot;Publiez votre premier article pour voir vos stats.&quot;)
# --- PUBLIER UNE ANNONCE ---
with st.expander(&quot;➕ Publier une annonce&quot;):
with st.form(&quot;new_listing_form&quot;, clear_on_submit=True):
col_f1, col_f2 = st.columns(2)
with col_f1:
title = st.text_input(&quot;Nom de l&#39;article *&quot;, max_chars=100)
price = st.number_input(&quot;Prix (KC) *&quot;, min_value=0.0, step=10.0)
category = st.selectbox(&quot;Catégorie&quot;, cat_list[1:] if len(cat_list)&gt;1 else [&quot;Général&quot;])
with col_f2:
condition = st.selectbox(&quot;État&quot;, [&quot;Neuf&quot;, &quot;Comme neuf&quot;, &quot;Bon état&quot;, &quot;État correct&quot;])
stock = st.number_input(&quot;Quantité&quot;, min_value=1, value=1, step=1)
img = st.file_uploader(&quot;Image (optionnelle)&quot;, type=[&quot;jpg&quot;, &quot;jpeg&quot;, &quot;png&quot;])
description = st.text_area(&quot;Description *&quot;, height=100)
if st.form_submit_button(&quot;�� Lancer la vente&quot;, use_container_width=True):
if not title or not description or price &lt;= 0:
st.error(&quot;Veuillez remplir tous les champs obligatoires (*).&quot;)
else:
media_url = None
if img is not None:
# Upload vers Supabase Storage
file_ext = img.name.split(&quot;.&quot;)[-1]
file_name = f&quot;{uuid.uuid4()}.{file_ext}&quot;
try:
supabase.storage.from_(&quot;marketplace&quot;).upload(file_name, img.getvalue(),
{&quot;content-type&quot;: img.type})

media_url = supabase.storage.from_(&quot;marketplace&quot;).get_public_url(file_name)
except Exception as e:
st.warning(f&quot;L&#39;image n&#39;a pas pu être uploadée : {e}&quot;)
try:
supabase.table(&quot;marketplace_listings&quot;).insert({
&quot;user_id&quot;: user.id,
&quot;title&quot;: title,
&quot;description&quot;: description,
&quot;price_kc&quot;: price,
&quot;category&quot;: category,
&quot;condition&quot;: condition,
&quot;stock&quot;: stock,
&quot;media_url&quot;: media_url,
&quot;is_active&quot;: True,
&quot;created_at&quot;: datetime.utcnow().isoformat()
}).execute()
st.success(&quot;✅ Annonce publiée avec succès !&quot;)
time.sleep(1)
st.rerun()
except Exception as e:
st.error(f&quot;Erreur lors de la publication : {e}&quot;)
st.divider()
# --- REQUÊTE DES ANNONCES AVEC FILTRES ---
query = supabase.table(&quot;marketplace_listings&quot;).select(&quot;*, profiles(username)&quot;).eq(&quot;is_active&quot;,
True)
if st.session_state.search_query:
query = query.ilike(&quot;title&quot;, f&quot;%{st.session_state.search_query}%&quot;)
if st.session_state.selected_category != &quot;Toutes&quot;:
query = query.eq(&quot;category&quot;, st.session_state.selected_category)
listings = query.order(&quot;created_at&quot;, desc=True).execute()
if not listings.data:
st.info(&quot;�� Aucune annonce ne correspond à vos critères.&quot;)
return
# --- AFFICHAGE DES ANNONCES EN GRILLE ---
st.subheader(f&quot;�� Annonces disponibles ({len(listings.data)})&quot;)
cols = st.columns(3)
for idx, item in enumerate(listings.data):
with cols[idx % 3]:
with st.container(border=True):

# Image
if item.get(&quot;media_url&quot;):
st.image(item[&quot;media_url&quot;], use_container_width=True)
else:
st.image(&quot;https://placehold.co/300x200/2d3a4a/white?text=No+Image&quot;,
use_container_width=True)
# Titre et prix
st.markdown(f&quot;**{item[&#39;title&#39;]}**&quot;)
st.markdown(f&quot;&lt;h3 style=&#39;color:#ff9d00;&#39;&gt;{item[&#39;price_kc&#39;]:,.0f} KC&lt;/h3&gt;&quot;,
unsafe_allow_html=True)
# Métadonnées
col_info1, col_info2 = st.columns(2)
with col_info1:
st.caption(f&quot;�� {item[&#39;profiles&#39;][&#39;username&#39;]}&quot;)
with col_info2:
st.caption(f&quot;�� Stock: {item.get(&#39;stock&#39;, 1)}&quot;)
# Description extensible
with st.expander(&quot;Description&quot;):
st.write(item[&#39;description&#39;])
# Actions selon propriétaire
if item[&quot;user_id&quot;] == user.id:
# Actions vendeur
col_a1, col_a2 = st.columns(2)
with col_a1:
if st.button(&quot;✏️ Modifier&quot;, key=f&quot;edit_{item[&#39;id&#39;]}&quot;, use_container_width=True):
st.session_state.edit_mode[item[&#39;id&#39;]] = True
with col_a2:
if st.button(&quot;�� Retirer&quot;, key=f&quot;del_{item[&#39;id&#39;]}&quot;, type=&quot;secondary&quot;
use_container_width=True):
supabase.table(&quot;marketplace_listings&quot;).update({&quot;is_active&quot;: False}).eq(&quot;id&quot;,
item[&quot;id&quot;]).execute()
st.toast(&quot;Annonce retirée.&quot;)
time.sleep(1)
st.rerun()
else:
# Actions acheteur
col_b1, col_b2 = st.columns(2)
with col_b1:
# Favoris

fav = supabase.table(&quot;user_favorites&quot;).select(&quot;id&quot;).eq(&quot;user_id&quot;,
user.id).eq(&quot;listing_id&quot;, item[&quot;id&quot;]).execute()
if fav.data:
if st.button(&quot;★&quot;, key=f&quot;fav_{item[&#39;id&#39;]}&quot;, help=&quot;Retirer des favoris&quot;,
use_container_width=True):
supabase.table(&quot;user_favorites&quot;).delete().eq(&quot;user_id&quot;,
user.id).eq(&quot;listing_id&quot;, item[&quot;id&quot;]).execute()
st.rerun()
else:
if st.button(&quot;☆&quot;, key=f&quot;fav_{item[&#39;id&#39;]}&quot;, help=&quot;Ajouter aux favoris&quot;,
use_container_width=True):
supabase.table(&quot;user_favorites&quot;).insert({&quot;user_id&quot;: user.id, &quot;listing_id&quot;:
item[&quot;id&quot;]}).execute()
st.rerun()
with col_b2:
# Achat
if st.button(&quot;�� Acheter&quot;, key=f&quot;buy_{item[&#39;id&#39;]}&quot;, type=&quot;primary&quot;
use_container_width=True):
try:
supabase.rpc(&#39;process_marketplace_purchase&#39;, {
&#39;p_listing_id&#39;: item[&#39;id&#39;],
&#39;p_buyer_id&#39;: user.id,
&#39;p_seller_id&#39;: item[&#39;user_id&#39;],
&#39;p_amount&#39;: float(item[&#39;price_kc&#39;])
}).execute()
supabase.table(&quot;notifications&quot;).insert({
&quot;user_id&quot;: item[&#39;user_id&#39;],
&quot;title&quot;: &quot;�� Article Vendu !&quot;,
&quot;message&quot;: f&quot;Votre article &#39;{item[&#39;title&#39;]}&#39; a été acheté pour
{item[&#39;price_kc&#39;]} KC.&quot;
}).execute()
st.balloons()
st.success(&quot;Achat réussi !&quot;)
time.sleep(2)
st.rerun()
except Exception as e:
st.error(f&quot;Erreur lors de l&#39;achat : {e}&quot;)
def wallet_page():
st.header(&quot;�� Mon Wallet&quot;)
wallet = supabase.table(&quot;wallets&quot;).select(&quot;*&quot;).eq(&quot;user_id&quot;, user.id).execute()
if not wallet.data:

user_profile = supabase.table(&quot;profiles&quot;).select(&quot;role&quot;).eq(&quot;user_id&quot;,
user.id).single().execute()
is_admin_user = user_profile.data[&quot;role&quot;] == &quot;admin&quot; if user_profile.data else False
supabase.table(&quot;wallets&quot;).insert({
&quot;user_id&quot;: user.id,
&quot;kongo_balance&quot;: 100_000_000.0 if is_admin_user else 0.0,
&quot;total_mined&quot;: 0.0,
&quot;last_reward_at&quot;: datetime.now().isoformat()
}).execute()
wallet = supabase.table(&quot;wallets&quot;).select(&quot;*&quot;).eq(&quot;user_id&quot;, user.id).execute()
wallet_data = wallet.data[0]
col1, col2 = st.columns(2)
with col1:
st.metric(&quot;Solde KC&quot;, f&quot;{wallet_data[&#39;kongo_balance&#39;]:,.0f} KC&quot;)
with col2:
st.metric(&quot;Total miné&quot;, f&quot;{wallet_data[&#39;total_mined&#39;]:,.0f} KC&quot;)
if st.button(&quot;⛏️ Miner (récompense quotidienne)&quot;):
try:
last_str = wallet_data[&quot;last_reward_at&quot;]
if last_str.endswith(&quot;Z&quot;):
last_str = last_str.replace(&quot;Z&quot;, &quot;+00:00&quot;)
last = datetime.fromisoformat(last_str)
now = datetime.now()
delta = now - last
if delta.total_seconds() &gt; 86400:
new_balance = wallet_data[&quot;kongo_balance&quot;] + 10
new_mined = wallet_data[&quot;total_mined&quot;] + 10
supabase.table(&quot;wallets&quot;).update({
&quot;kongo_balance&quot;: new_balance,
&quot;total_mined&quot;: new_mined,
&quot;last_reward_at&quot;: now.isoformat()
}).eq(&quot;user_id&quot;, user.id).execute()
st.success(&quot;+10 KC minés !&quot;)
st.rerun()
else:
reste = 86400 - delta.total_seconds()
st.warning(f&quot;Prochain minage dans {int(reste//3600)}h {int((reste%3600)//60)}m.&quot;)
except Exception as e:
st.error(f&quot;Erreur lors du minage : {e}&quot;)
st.divider()
st.subheader(&quot;�� Activité récente&quot;)
st.info(&quot;L&#39;historique détaillé des transactions Marketplace sera bientôt disponible.&quot;)

def settings_page():
st.header(&quot;⚙️ Paramètres&quot;)
PREMIUM_PRICE = 10000.0
sub = supabase.table(&quot;subscriptions&quot;).select(&quot;*&quot;).eq(&quot;user_id&quot;, user.id).execute()
if sub.data:
plan = sub.data[0][&quot;plan_type&quot;]
expires = sub.data[0].get(&quot;expires_at&quot;)
st.info(f&quot;Plan actuel : **{plan}**&quot; + (f&quot; (expire le {expires[:10]})&quot; if expires else &quot;&quot;))
else:
st.info(&quot;Plan actuel : **Gratuit**&quot;)
if st.button(&quot;Passer à Premium (10 000 KC)&quot;):
wallet_res = supabase.table(&quot;wallets&quot;).select(&quot;*&quot;).eq(&quot;user_id&quot;, user.id).execute()
if wallet_res.data:
wallet_data = wallet_res.data[0]
current_balance = wallet_data[&quot;kongo_balance&quot;]
if current_balance &gt;= PREMIUM_PRICE:
try:
new_balance = current_balance - PREMIUM_PRICE
supabase.table(&quot;wallets&quot;).update({
&quot;kongo_balance&quot;: new_balance
}).eq(&quot;user_id&quot;, user.id).execute()
supabase.table(&quot;subscriptions&quot;).insert({
&quot;user_id&quot;: user.id,
&quot;plan_type&quot;: &quot;Premium&quot;,
&quot;activated_at&quot;: datetime.now().isoformat(),
&quot;expires_at&quot;: (datetime.now().replace(year=datetime.now().year+1)).isoformat(),
&quot;is_active&quot;: True
}).execute()
st.success(f&quot;Compte Premium activé ! {PREMIUM_PRICE:,.0f} KC ont été
débités.&quot;)
time.sleep(2)
st.rerun()
except Exception as e:
st.error(f&quot;Erreur lors de la transaction : {e}&quot;)
else:
st.error(f&quot;Solde insuffisant. Il vous manque {PREMIUM_PRICE - current_balance:,.0f}
KC.&quot;)
else:
st.error(&quot;Portefeuille introuvable. Veuillez d&#39;abord initialiser votre Wallet.&quot;)

st.divider()
st.subheader(&quot;Zone dangereuse&quot;)
if st.button(&quot;Supprimer mon compte&quot;, type=&quot;primary&quot;):
st.warning(&quot;Fonction désactivée pour le moment.&quot;)
def admin_page():
st.header(&quot;��️ Espace Administration&quot;)
st.caption(&quot;Actions réservées à la modération -- utilisez‑les avec discernement.&quot;)
tab1, tab2, tab3, tab4 = st.tabs([&quot;Utilisateurs&quot;, &quot;Posts signalés&quot;, &quot;Logs d&#39;action&quot;, &quot;Crédits&quot;])
with tab1:
st.subheader(&quot;Gestion des utilisateurs&quot;)
users = supabase.table(&quot;profiles&quot;).select(&quot;id, username, role, created_at&quot;).execute()
df_users = pd.DataFrame(users.data)
st.dataframe(df_users)
with st.form(&quot;change_role&quot;):
user_id = st.selectbox(
&quot;Sélectionner un utilisateur&quot;,
options=df_users[&quot;id&quot;],
format_func=lambda x: df_users[df_users[&quot;id&quot;] == x][&quot;username&quot;].values[0]
)
new_role = st.selectbox(&quot;Nouveau rôle&quot;, [&quot;user&quot;, &quot;admin&quot;, &quot;moderator&quot;])
if st.form_submit_button(&quot;Appliquer&quot;):
supabase.table(&quot;profiles&quot;).update({&quot;role&quot;: new_role}).eq(&quot;id&quot;, user_id).execute()
st.success(&quot;Rôle mis à jour&quot;)
st.cache_data.clear()
st.rerun()
with tab2:
st.subheader(&quot;Posts signalés&quot;)
posts = supabase.table(&quot;posts&quot;).select(&quot;*, profiles(username)&quot;).order(&quot;created_at&quot;,
desc=True).limit(100).execute()
for post in posts.data:
with st.expander(f&quot;Post de {post[&#39;profiles&#39;][&#39;username&#39;]} -- {post[&#39;created_at&#39;][:16]}&quot;):
st.write(post[&quot;text&quot;])
if post.get(&quot;media_path&quot;):
file_url = get_signed_url(&quot;media&quot;, post[&quot;media_path&quot;])
if file_url:
st.image(file_url, width=200)
if st.button(&quot;��️ Supprimer ce post&quot;, key=f&quot;del_{post[&#39;id&#39;]}&quot;):
delete_post(post[&quot;id&quot;])
with tab3:
st.subheader(&quot;Journal des actions&quot;)

st.info(&quot;Fonctionnalité à venir : traçabilité des actions d&#39;administration.&quot;)
with tab4:
st.subheader(&quot;Créditer un utilisateur&quot;)
users = supabase.table(&quot;profiles&quot;).select(&quot;id, username&quot;).execute()
user_options = {u[&quot;id&quot;]: u[&quot;username&quot;] for u in users.data}
selected_user = st.selectbox(
&quot;Choisir un utilisateur&quot;,
options=list(user_options.keys()),
format_func=lambda x: user_options[x]
)
amount = st.number_input(&quot;Montant (KC)&quot;, min_value=0.0, step=1000.0,
value=100_000_000.0)
if st.button(&quot;Ajouter des KC&quot;):
wallet = supabase.table(&quot;wallets&quot;).select(&quot;*&quot;).eq(&quot;user_id&quot;, selected_user).execute()
if wallet.data:
new_balance = wallet.data[0][&quot;kongo_balance&quot;] + amount
supabase.table(&quot;wallets&quot;).update({&quot;kongo_balance&quot;: new_balance}).eq(&quot;user_id&quot;,
selected_user).execute()
else:
supabase.table(&quot;wallets&quot;).insert({
&quot;user_id&quot;: selected_user,
&quot;kongo_balance&quot;: amount,
&quot;total_mined&quot;: 0.0,
&quot;last_reward_at&quot;: datetime.now().isoformat()
}).execute()
st.success(f&quot;{amount:,.0f} KC ajoutés à {user_options[selected_user]}&quot;)
# =====================================================
# ROUTEUR PRINCIPAL
# =====================================================
if menu == &quot;�� Feed&quot;:
feed_page()
elif menu == &quot;�� Mon Profil&quot;:
profile_page()
elif menu == &quot;✉️ Messages&quot;:
messages_page()
elif menu == &quot;�� Marketplace&quot;:
marketplace_page()
elif menu == &quot;�� Wallet&quot;:
wallet_page()
elif menu == &quot;⚙️ Paramètres&quot;:
settings_page()
elif menu == &quot;��️ Admin&quot;:
