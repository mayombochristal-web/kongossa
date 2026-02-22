import streamlit as st
from cryptography.fernet import Fernet
import datetime

# =====================================================
# ARCHITECTURE TRIPLE-COFFRE (Mémoire Vive Partagée)
# =====================================================
@st.cache_resource
def initialiser_systeme_triadique():
    return {
        "COFFRE_M": {}, # Fragment Mémoire
        "COFFRE_C": {}, # Fragment Cohérence
        "COFFRE_D": {}, # Fragment Dissipation
        "METADATA": {}  # Clés et Noms de fichiers
    }

SYSTEME = initialiser_systeme_triadique()

# =====================================================
# INTERFACE SOUVERAINE
# =====================================================
st.set_page_config(page_title="FREE-KONGOSSA", page_icon="✊", layout="wide")
st.title("✊ FREE-KONGOSSA : Transmetteur Universel")
st.markdown("---")

# Zone de saisie du code (Le lien entre vous)
code_secret = st.text_input("🔑 CODE SECRET DE LIAISON", help="Entrez le code convenu avec votre proche").strip().upper()

tab_emit, tab_recv = st.tabs(["📤 ÉMETTEUR (Déposer tout type de fichier)", "📥 RÉCEPTEUR (Aspirer la vérité)"])

# --- SECTION ÉMETTEUR ---
with tab_emit:
    st.subheader("📦 Préparer le colis numérique")
    fichier = st.file_uploader("Document, Vidéo, Audio, Archive...", type=None) # Accepte tout
    
    if fichier and code_secret:
        if st.button("🚀 Éclater et Sceller dans les Coffres"):
            # 1. Chiffrement Global (Fernet)
            cle_unique = Fernet.generate_key()
            cipher = Fernet(cle_unique)
            donnees_brutes = fichier.getvalue()
            donnees_chiffrees = cipher.encrypt(donnees_brutes)
            
            # 2. Fragmentation Triadique
            taille = len(donnees_chiffrees)
            p1, p2 = taille // 3, (taille // 3) * 2
            
            # 3. Distribution dans les 3 coffres
            SYSTEME["COFFRE_M"][code_secret] = donnees_chiffrees[:p1]
            SYSTEME["COFFRE_C"][code_secret] = donnees_chiffrees[p1:p2]
            SYSTEME["COFFRE_D"][code_secret] = donnees_chiffrees[p2:]
            
            # 4. Sauvegarde des métadonnées (Nom, Type, Clé)
            SYSTEME["METADATA"][code_secret] = {
                "key": cle_unique,
                "name": fichier.name,
                "type": fichier.type,
                "time": datetime.datetime.now()
            }
            
            st.success(f"✅ Flux scellé ! Type détecté : {fichier.type}")
            st.info(f"Dites à votre proche d'utiliser le code : **{code_secret}**")

# --- SECTION RÉCEPTEUR ---
with tab_recv:
    st.subheader("🌪️ Aspiration du Flux")
    
    # Vérification de l'existence de la Triade pour ce code
    triade_complete = (
        code_secret in SYSTEME["COFFRE_M"] and 
        code_secret in SYSTEME["COFFRE_C"] and 
        code_secret in SYSTEME["COFFRE_D"]
    )
    
    if triade_complete:
        meta = SYSTEME["METADATA"][code_secret]
        st.write(f"📁 Un fichier **{meta['name']}** est prêt à être aspiré.")
        
        if st.button("🔓 Déclencher l'aspiration et la fusion"):
            try:
                # 1. Récupération des 3 ondes
                m = SYSTEME["COFFRE_M"][code_secret]
                c = SYSTEME["COFFRE_C"][code_secret]
                d = SYSTEME["COFFRE_D"][code_secret]
                
                # 2. Reconstitution et Déchiffrement
                flux_total = m + c + d
                cipher = Fernet(meta['key'])
                donnees_finales = cipher.decrypt(flux_total)
                
                # 3. Mise à disposition
                st.download_button(
                    label="💾 Sauvegarder sur cet appareil",
                    data=donnees_finales,
                    file_name=meta['name'],
                    mime=meta['type']
                )
                
                # 4. DISSIPATION (Effacement immédiat des 3 coffres + métadonnées)
                del SYSTEME["COFFRE_M"][code_secret]
                del SYSTEME["COFFRE_C"][code_secret]
                del SYSTEME["COFFRE_D"][code_secret]
                del SYSTEME["METADATA"][code_secret]
                
                st.warning("🔒 Le tunnel s'est refermé. Les données sont effacées du serveur.")
                
            except Exception as e:
                st.error("Rupture de symétrie : le flux a été altéré.")
    else:
        if code_secret:
            st.write("🔎 Aucun flux complet trouvé. Attente de l'émetteur...")
