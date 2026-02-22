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
st.title("✊ FREE-KONGOSSA : Messagerie Triadique")
st.markdown("---")

# Zone de saisie du code (Le lien entre vous)
code_secret = st.text_input("🔑 CODE SECRET DE LIAISON", help="Le code que vous partagez avec votre proche").strip().upper()

tab_emit, tab_recv = st.tabs(["📤 ÉMETTEUR (Envoyer)", "📥 RÉCEPTEUR (Aspirer)"])

# --- SECTION ÉMETTEUR ---
with tab_emit:
    st.subheader("📝 Message ou Fichier à transmettre")
    
    # Choix du type d'envoi
    option = st.radio("Que voulez-vous envoyer ?", ["Texte Écrit", "Fichier (Audio, Vidéo, PDF, etc.)"], horizontal=True)
    
    contenu_a_chiffrer = None
    nom_affichage = ""
    type_mime = ""

    if option == "Texte Écrit":
        message_texte = st.text_area("Écrivez votre message secret ici...")
        if message_texte:
            contenu_a_chiffrer = message_texte.encode() # Conversion du texte en octets
            nom_affichage = "Message_Texte.txt"
            type_mime = "text/plain"
    else:
        fichier = st.file_uploader("Choisissez votre fichier (Vidéo, Audio, Image, Doc)", type=None)
        if fichier:
            contenu_a_chiffrer = fichier.getvalue()
            nom_affichage = fichier.name
            type_mime = fichier.type

    if contenu_a_chiffrer and code_secret:
        if st.button("🚀 Éclater et Sceller dans les Coffres"):
            # 1. Chiffrement Global
            cle_unique = Fernet.generate_key()
            cipher = Fernet(cle_unique)
            donnees_chiffrees = cipher.encrypt(contenu_a_chiffrer)
            
            # 2. Fragmentation Triadique
            taille = len(donnees_chiffrees)
            p1, p2 = taille // 3, (taille // 3) * 2
            
            # 3. Distribution dans les 3 coffres
            SYSTEME["COFFRE_M"][code_secret] = donnees_chiffrees[:p1]
            SYSTEME["COFFRE_C"][code_secret] = donnees_chiffrees[p1:p2]
            SYSTEME["COFFRE_D"][code_secret] = donnees_chiffrees[p2:]
            
            # 4. Sauvegarde des métadonnées
            SYSTEME["METADATA"][code_secret] = {
                "key": cle_unique,
                "name": nom_affichage,
                "type": type_mime,
                "is_text": (option == "Texte Écrit")
            }
            
            st.success(f"✅ Flux {nom_affichage} sécurisé !")
            st.info(f"Dites à votre proche d'aspirer avec le code : **{code_secret}**")

# --- SECTION RÉCEPTEUR ---
with tab_recv:
    st.subheader("🌪️ Aspiration du Flux")
    
    triade_complete = (
        code_secret in SYSTEME["COFFRE_M"] and 
        code_secret in SYSTEME["COFFRE_C"] and 
        code_secret in SYSTEME["COFFRE_D"]
    )
    
    if triade_complete:
        meta = SYSTEME["METADATA"][code_secret]
        st.write(f"📁 Un flux de type **{meta['name']}** est en attente.")
        
        if st.button("🔓 Déclencher l'aspiration et la fusion"):
            try:
                # 1. Récupération des 3 ondes
                m = SYSTEME["COFFRE_M"][code_secret]
                c = SYSTEME["COFFRE_C"][code_secret]
                d = SYSTEME["COFFRE_D"][code_secret]
                
                # 2. Fusion et Déchiffrement
                flux_total = m + c + d
                cipher = Fernet(meta['key'])
                donnees_finales = cipher.decrypt(flux_total)
                
                # 3. Affichage selon le type
                if meta['is_text']:
                    st.text_area("Message déchiffré :", value=donnees_finales.decode(), height=200)
                else:
                    # Pour les vidéos/audios, Streamlit peut les lire directement
                    if "video" in meta['type']:
                        st.video(donnees_finales)
                    elif "audio" in meta['type']:
                        st.audio(donnees_finales)
                    
                    st.download_button(
                        label="💾 Sauvegarder le fichier sur l'appareil",
                        data=donnees_finales,
                        file_name=meta['name'],
                        mime=meta['type']
                    )
                
                # 4. DISSIPATION (Effacement total)
                del SYSTEME["COFFRE_M"][code_secret]
                del SYSTEME["COFFRE_C"][code_secret]
                del SYSTEME["COFFRE_D"][code_secret]
                del SYSTEME["METADATA"][code_secret]
                
                st.warning("🔒 Le tunnel est fermé. Les données ont été effacées pour votre sécurité.")
                
            except Exception as e:
                st.error("Rupture de symétrie : le flux a été altéré.")
    else:
        if code_secret:
            st.write("🔎 Aucun flux complet trouvé pour ce code.")
