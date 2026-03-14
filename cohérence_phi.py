# coherence_phi.py
import streamlit as st
import time
from datetime import datetime
from memory_phi import supabase, encrypt_text, decrypt_text, user, update_dissipation

# =====================================================
# STATISTIQUES ET INTERACTIONS
# =====================================================
def get_post_stats(post_id):
    try:
        likes = supabase.table("likes").select("*", count="exact").eq("post_id", post_id).execute()
        comments = supabase.table("comments").select("*", count="exact").eq("post_id", post_id).execute()
        reactions = supabase.table("reactions").select("*", count="exact").eq("post_id", post_id).execute()
        return {
            "likes": likes.count or 0,
            "comments": comments.count or 0,
            "reactions": reactions.count or 0
        }
    except Exception:
        return {"likes": 0, "comments": 0, "reactions": 0}

def like_post(post_id):
    try:
        supabase.table("likes").insert({"post_id": post_id, "user_id": user.id}).execute()
        post = supabase.table("posts").select("like_count").eq("id", post_id).execute()
        if post.data:
            new_count = post.data[0]["like_count"] + 1
            supabase.table("posts").update({"like_count": new_count}).eq("id", post_id).execute()
        update_dissipation(0.02)
        st.success("👍 Like ajouté !")
        time.sleep(0.5)
        st.rerun()
    except Exception:
        st.error("Vous avez déjà liké ce post.")

def add_comment(post_id, text):
    if not text.strip():
        st.warning("Commentaire vide.")
        return
    try:
        supabase.table("comments").insert({"post_id": post_id, "user_id": user.id, "text": text}).execute()
        post = supabase.table("posts").select("comment_count").eq("id", post_id).execute()
        if post.data:
            new_count = post.data[0]["comment_count"] + 1
            supabase.table("posts").update({"comment_count": new_count}).eq("id", post_id).execute()
        update_dissipation(0.03)
        st.success("💬 Commentaire ajouté")
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.error(f"Erreur : {e}")

def delete_post(post_id):
    try:
        post = supabase.table("posts").select("media_path").eq("id", post_id).execute()
        if post.data and post.data[0].get("media_path"):
            supabase.storage.from_("media").remove([post.data[0]["media_path"]])
        supabase.table("posts").delete().eq("id", post_id).execute()
        update_dissipation(0.05)
        st.success("Post supprimé")
        st.rerun()
    except Exception as e:
        st.error(f"Erreur : {e}")

# =====================================================
# RÉACTIONS ÉMOJI PAYANTES
# =====================================================
EMOJI_HIERARCHY = {
    "🔥": {"cost": 10, "share": 8},
    "💎": {"cost": 50, "share": 40},
    "👑": {"cost": 100, "share": 80}
}

def process_emoji_payment(post_id, author_id, emoji_type):
    cost = EMOJI_HIERARCHY[emoji_type]["cost"]
    share = EMOJI_HIERARCHY[emoji_type]["share"]
    try:
        wallet = supabase.table("wallets").select("kongo_balance").eq("user_id", user.id).execute()
        if not wallet.data or wallet.data[0]["kongo_balance"] < cost:
            st.error("Solde insuffisant.")
            return
        # Débiter l'utilisateur
        new_bal = wallet.data[0]["kongo_balance"] - cost
        supabase.table("wallets").update({"kongo_balance": new_bal}).eq("user_id", user.id).execute()
        # Créditer l'auteur
        author_wallet = supabase.table("wallets").select("kongo_balance").eq("user_id", author_id).execute()
        if author_wallet.data:
            new_author_bal = author_wallet.data[0]["kongo_balance"] + share
            supabase.table("wallets").update({"kongo_balance": new_author_bal}).eq("user_id", author_id).execute()
        supabase.table("reactions").insert({
            "post_id": post_id,
            "user_id": user.id,
            "emoji": emoji_type,
            "cost": cost
        }).execute()
        update_dissipation(0.1)
        st.success(f"Réaction {emoji_type} envoyée !")
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.error(f"Erreur : {e}")

# =====================================================
# MESSAGERIE
# =====================================================
def send_message(recipient_id, text):
    if not text.strip():
        return
    encrypted = encrypt_text(text)
    supabase.table("messages").insert({
        "sender": user.id,
        "recipient": recipient_id,
        "text": encrypted,
        "created_at": datetime.now().isoformat()
    }).execute()
    update_dissipation(0.1)

# =====================================================
# MARKETPLACE
# =====================================================
def buy_listing(listing_id, seller_id, price):
    try:
        # Vérifier disponibilité
        listing = supabase.table("marketplace_listings").select("status").eq("id", listing_id).single().execute()
        if listing.data and listing.data["status"] != "Disponible":
            st.error("Annonce déjà vendue.")
            return False
        # Vérifier solde acheteur
        buyer_wallet = supabase.table("wallets").select("kongo_balance").eq("user_id", user.id).execute()
        if not buyer_wallet.data or buyer_wallet.data[0]["kongo_balance"] < price:
            st.error("Solde insuffisant.")
            return False
        # Transaction
        new_buyer_bal = buyer_wallet.data[0]["kongo_balance"] - price
        supabase.table("wallets").update({"kongo_balance": new_buyer_bal}).eq("user_id", user.id).execute()
        seller_wallet = supabase.table("wallets").select("kongo_balance").eq("user_id", seller_id).execute()
        if seller_wallet.data:
            new_seller_bal = seller_wallet.data[0]["kongo_balance"] + price
            supabase.table("wallets").update({"kongo_balance": new_seller_bal}).eq("user_id", seller_id).execute()
        # Mettre à jour l'annonce
        supabase.table("marketplace_listings").update({
            "status": "Vendu",
            "sales_count": supabase.table("marketplace_listings").select("sales_count").eq("id", listing_id).execute().data[0]["sales_count"] + 1
        }).eq("id", listing_id).execute()
        # Notifier le vendeur
        msg = f"🚨 ACHAT : {listing['title']} a été acheté. {price} KC transférés."
        send_message(seller_id, msg)
        update_dissipation(0.3)
        st.success("Transaction réussie !")
        return True
    except Exception as e:
        st.error(f"Erreur transaction : {e}")
        return False