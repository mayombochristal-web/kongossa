import streamlit as st
from cryptography.fernet import Fernet
import datetime
import hashlib

# =====================================================
# ARCHITECTURE TRIPLE-COFFRE (Mémoire Vive Partagée)
# =====================================================
@st.cache_resource
def initialiser_systeme_triadique():
    # Le dictionnaire SYSTEME reste en RAM, rien sur disque.
    return {
        "COFFRE_M": {}, # Fragment Mémoire
        "COFFRE_C": {}, # Fragment Cohérence
        "COFFRE_D": {}, # Fragment Dissipation
        "METADATA": {}  # Clés et Noms de fichiers
    }

SYSTEME = initialiser_systeme_triadique()

def generer_identifiant_temporel(code_base):
    """
    Transforme un code simple en identifiant technique qui change toutes les heures.
    """
    if not code_base:
        return None
    # On récupère l'année, mois, jour et heure actuelle
    grain_de_sel = datetime.datetime.now().strftime("%Y-%m-%d-%H")
    # On crée un hash unique pour cette heure précise
    melange = f"{code_base}-{grain_de_sel}"
    return hashlib.sha256(melange.encode()).hexdigest()[:12].upper()

# =====================================================
# INTERFACE SOUVERAINE
# =====================================================
st.set_page_config(page_title="FREE-KONGOSSA", page_icon="✊", layout="wide")
st.title("✊ FREE-KONGOSSA : Messagerie Triadique")
st.info("💡 Le tunnel de transmission change automatiquement chaque heure.")

# Zone de saisie du code secret (Connu seulement de vous deux)
code_racine = st.text_input("🔑 VOTRE CODE SECRET PARTAGÉ", type="password", help="Ex: Le nom de votre rue d'enfance").strip().upper()

# Génération de l'identifiant de session dynamique
id_session = generer_identifiant_temporel(code_racine)

tab_emit, tab_recv = st.tabs(["📤 ÉMETTEUR (Envoyer)", "📥 RÉCEPTEUR (Aspirer)"])

# --- SECTION ÉMETTEUR ---
with tab_emit:
    if not id_session:
        st.warning("Veuillez saisir un code secret pour activer l'émetteur.")
    else:
        st.subheader("📝 Préparation du Flux")
        option = st.radio("Type d'envoi :", ["Texte Écrit", "Fichier"], horizontal=True)
        
        contenu = None
        nom_f, mime_f = "", ""

        if option == "Texte Écrit":
            msg = st.text_area("Message à chiffrer...")
            if msg:
                contenu, nom_f, mime_f = msg.encode(), "Message.txt", "text/plain"
        else:
            f = st.file_uploader("Document / Multimédia")
            if f:
                contenu, nom_f, mime_f = f.getvalue(), f.name, f.type

        if contenu and st.button("🚀 Éclater et Envoyer"):
            # Chiffrement
            cle = Fernet.generate_key()
            donnees_chiffrees = Fernet(cle).encrypt(contenu)
            
            # Fragmentation
            taille = len(donnees_chiffrees)
            p1, p2 = taille // 3, (taille // 3) * 2
            
            # Stockage en RAM (Triade)
            SYSTEME["COFFRE_M"][id_session] = donnees_chiffrees[:p1]
            SYSTEME["COFFRE_C"][id_session] = donnees_chiffrees[p1:p2]
            SYSTEME["COFFRE_D"][id_session] = donnees_chiffrees[p2:]
            SYSTEME["METADATA"][id_session] = {"key": cle, "name": nom_f, "type": mime_f, "text": (option == "Texte Écrit")}
            
            st.success(f"✅ Flux sécurisé sous l'ID : {id_session}")
            st.write("Le récepteur a jusqu'à la fin de l'heure actuelle pour aspirer le contenu.")

# --- SECTION RÉCEPTEUR ---
with tab_recv:
    if not id_session:
        st.warning("Veuillez saisir le code secret pour vérifier les flux entrants.")
    else:
        # Vérification de la présence des 3 fragments
        if id_session in SYSTEME["COFFRE_M"]:
            meta = SYSTEME["METADATA"][id_session]
            st.write(f"📦 Flux détecté : **{meta['name']}**")
            
            if st.button("🔓 Aspirer et Détruire"):
                try:
                    # Fusion
                    complet = SYSTEME["COFFRE_M"][id_session] + SYSTEME["COFFRE_C"][id_session] + SYSTEME["COFFRE_D"][id_session]
                    dechi = Fernet(meta['key']).decrypt(complet)
                    
                    if meta['text']:
                        st.text_area("Message :", dechi.decode())
                    else:
                        st.download_button("💾 Télécharger", dechi, file_name=meta['name'], mime=meta['type'])
                    
                    # DISSIPATION IMMÉDIATE
                    for coffre in ["COFFRE_M", "COFFRE_C", "COFFRE_D", "METADATA"]:
                        del SYSTEME[coffre][id_session]
                    st.warning("🔒 Données dissipées du serveur.")
                except:
                    st.error("Erreur de synchronisation.")
        else:
            st.write("🔎 En attente d'un flux correspondant...")
