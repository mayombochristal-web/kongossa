# dissipation_phi.py
import streamlit as st
import pandas as pd
import time
import random
import gc
from datetime import datetime, timedelta
from memory_phi import supabase, user, profile, is_admin, tst_params, update_dissipation, encrypt_text, decrypt_text, get_user_badge, get_signed_url, logout
from coherence_phi import get_post_stats, like_post, add_comment, delete_post, process_emoji_payment, send_message, buy_listing

# =====================================================
# CONTRÔLEUR DE STABILITÉ
# =====================================================
def stability_control(func):
    def wrapper(*args, **kwargs):
        params = st.session_state.tst_params
        if params["phi_d"] > params["stability_threshold"]:
            st.warning("⚡ Mode économie d'énergie activé", icon="🔄")
            kwargs["low_power"] = True
        else:
            kwargs["low_power"] = False
        return func(*args, **kwargs)
    return wrapper

# =====================================================
# PAGES
# =====================================================
@stability_control
def feed_page(low_power=False):
    st.header("🌐 Fil d'actualité")
    # ... (code existant de feed_page, en utilisant les fonctions importées)
    # Pour gagner de la place, on ne recopie pas ici l'intégralité,
    # mais dans le fichier final il faudra l'inclure.

def ttu_vertical_feed():
    st.subheader("📷 Lancer mon Live")
    # webrtc_streamer(...)  # optionnel, à décommenter si nécessaire
    # ... (code simplifié de la page TokTok)

def profile_page():
    st.header("👤 Mon Profil")
    # ... (code existant)

def messages_page():
    st.header("✉️ Messagerie")
    # ... (code existant)

def marketplace_page():
    st.header("🏪 Marketplace")
    # ... (code existant)

def wallet_page():
    st.header("💰 Wallet")
    # ... (code existant)

def settings_page():
    st.header("⚙️ Paramètres")
    # ... (code existant)

def admin_page():
    st.header("🛡️ Admin")
    # ... (code existant)

# =====================================================
# ROUTAGE
# =====================================================
def run():
    st.sidebar.image("https://via.placeholder.com/150x50?text=GEN-Z", width=150)
    st.sidebar.write(f"Connecté : **{profile['username']}**")
    if is_admin():
        st.sidebar.markdown("🔑 Administrateur")

    menu_options = ["🎵 TokTok", "🌐 Feed", "👤 Profil", "✉️ Messages", "🏪 Marketplace", "💰 Wallet", "⚙️ Paramètres"]
    if is_admin():
        menu_options.append("🛡️ Admin")
    menu = st.sidebar.radio("Navigation", menu_options)

    if st.sidebar.button("🚪 Déconnexion"):
        logout()

    if menu == "🎵 TokTok":
        ttu_vertical_feed()
    elif menu == "🌐 Feed":
        feed_page()
    elif menu == "👤 Profil":
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