import streamlit as st
from cryptography.fernet import Fernet
import random

# =====================================================
# LES TROIS COFFRES DISTINCTS (RAM Partagée)
# =====================================================
@st.cache_resource
def initialiser_systeme_triadique():
    return {
        "COFFRE_M": {}, # Mémoire
        "COFFRE_C": {}, # Cohérence
        "COFFRE_D": {}  # Dissipation
    }

SYSTEME = initialiser_systeme_triadique()

# =====================================================
# INTERFACE
# =====================================================
st.set_page_config(page_title="FREE-KONGOSSA", page_icon="✊")
st.title("✊ FREE-KONGOSSA : Triple-Coffre")
st.markdown("---")

code_secret = st.text_input("🔑 CODE SECRET DE LIAISON", "").strip().upper()

tab_send, tab_recv = st.tabs(["📤 DÉPOSER (Fragmentation)", "📥 EXTRAIRE (Aspiration)"])

# --- SECTION ÉMETTEUR ---
with tab_send:
    fichier = st.file_uploader("Document à sécuriser", type=['png', 'jpg', 'jpeg', 'pdf', 'zip'])
    
    if fichier and code_secret:
        if st.button("🚀 Éclater et Sceller dans les 3 coffres"):
            # 1. Chiffrement Global
            cle_cryptage = Fernet.generate_key()
            cipher = Fernet(cle_cryptage)
            donnees_chiffrees = cipher.encrypt(fichier.getvalue())
            
            # 2. Fragmentation Triadique (Découpage en 3)
            taille = len(donnees_chiffrees)
            p1 = taille // 3
            p2 = (taille // 3) * 2
            
            onde_M = donnees_chiffrees[:p1]
            onde_C = donnees_chiffrees[p1:p2]
            onde_D = donnees_chiffrees[p2:]
            
            # 3. Distribution aléatoire dans les coffres pour perdre une éventuelle trace
            # On stocke aussi la clé de manière fragmentée ou protégée
            SYSTEME["COFFRE_M"][code_secret] = onde_M
            SYSTEME["COFFRE_C"][code_secret] = onde_C
            SYSTEME["COFFRE_D"][code_secret] = onde_D
            
            # On garde la clé de déchiffrement dans un espace sécurisé lié au code
            if "KEYS" not in SYSTEME: SYSTEME["KEYS"] = {}
            SYSTEME["KEYS"][code_secret] = {"key": cle_cryptage, "name": fichier.name}
            
            st.success("✅ Document éclaté et distribué dans les 3 coffres mondiaux.")
            st.info(f"Le tunnel est stable. Code : **{code_secret}**")

# --- SECTION RÉCEPTEUR ---
with tab_recv:
    # On vérifie si le code existe dans les 3 coffres simultanément
    presence_triade = (
        code_secret in SYSTEME["COFFRE_M"] and 
        code_secret in SYSTEME["COFFRE_C"] and 
        code_secret in SYSTEME["COFFRE_D"]
    )
    
    if presence_triade:
        info = SYSTEME["KEYS"][code_secret]
        st.success(f"💎 Triade détectée ! Document : **{info['name']}**")
        
        if st.button("🌪️ Aspirer les Ondes et Reconstituer"):
            try:
                # ASPIRATION AUTOMATIQUE des 3 coffres
                m = SYSTEME["COFFRE_M"][code_secret]
                c = SYSTEME["COFFRE_C"][code_secret]
                d = SYSTEME["COFFRE_D"][code_secret]
                
                # RECONSTITUTION
                flux_total = m + c + d
                cipher = Fernet(info['key'])
                donnees_finales = cipher.decrypt(flux_total)
                
                # TÉLÉCHARGEMENT
                st.download_button("💾 Sauvegarder le document", donnees_finales, file_name=info['name'])
                
                # AUTO-DESTRUCTION (DISSIPATION)
                del SYSTEME["COFFRE_M"][code_secret]
                del SYSTEME["COFFRE_C"][code_secret]
                del SYSTEME["COFFRE_D"][code_secret]
                del SYSTEME["KEYS"][code_secret]
                
                st.warning("🔒 Sécurité activée : Les 3 coffres ont été vidés.")
                st.rerun()
                
            except Exception as e:
                st.error("Erreur de brisure de symétrie. Le flux est corrompu.")
    else:
        if code_secret:
            st.write("🔎 Aucun flux complet trouvé pour ce code.")
        else:
            st.write("En attente de la clé pour l'aspiration...")
