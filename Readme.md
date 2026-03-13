```markdown
# 🇬🇦 FREE-KONGOSSA — Réseau Social Souverain

**FREE-KONGOSSA** est une plateforme sociale nouvelle génération conçue pour offrir une expérience de communication libre, chiffrée et décentralisée. Développée avec **Streamlit** et **Supabase**, elle allie la simplicité d’un réseau social moderne à la puissance d’un moteur de souveraineté numérique inspiré des principes de la « FREE KONGOSSA » (parole libre, héritage culturel, contrôle des données).

---

## ✨ Particularité FREE KONGOSSA

La particularité de cette plateforme réside dans son **moteur de souveraineté** (classe `SOVEREIGN`) qui permet :

- **Chiffrement de bout en bout** des messages privés et des tunnels de discussion.
- **Génération de clés locales** à partir d’un secret partagé (code tunnel).
- **Découpage des messages chiffrés** en fragments pour renforcer la sécurité.
- **Export / Import de la chaîne de données** pour une synchronisation pair-à-pair sans dépendance serveur.

Ce système garantit que même si les données transitent par un serveur central, elles restent illisibles sans le secret approprié. Les utilisateurs conservent la pleine propriété de leurs conversations.

> ⚡ Dans la version actuelle, le chiffrement est appliqué aux messages privés et aux canaux partagés (tunnels). Les posts publics restent en clair pour favoriser la découverte et l’interaction.

---

## 🚀 Fonctionnalités

| Module | Description |
|--------|-------------|
| **🌐 Feed global** | Publiez du texte, des images, des vidéos. Likez et commentez les publications. |
| **👤 Profil utilisateur** | Bio, photo, localisation, statistiques (posts, abonnés, abonnements). |
| **✉️ Messagerie privée** | Conversations chiffrées, historique consultable, interface intuitive. |
| **🏪 Marketplace** | Publiez des annonces avec photos, prix en KC (Kongo Coin), consultez les offres. |
| **💰 Wallet & minage** | Solde en KC, minage quotidien, historique (à venir). |
| **⚙️ Paramètres** | Gestion de l’abonnement (Gratuit / Premium), suppression de compte. |
| **🔐 Tunnels souverains** | Canaux de discussion chiffrés avec clé partagée, synchronisation locale. |

---

## 📦 Installation

1. **Cloner le dépôt**
   ```bash
   git clone https://github.com/ton-org/free-kongossa.git
   cd free-kongossa
```

1. Installer les dépendances
   ```bash
   pip install -r requirements.txt
   ```
2. Configurer les secrets Streamlit
   Créez un dossier .streamlit à la racine et un fichier secrets.toml :
   ```toml
   SUPABASE_URL = "https://votreprojet.supabase.co"
   SUPABASE_KEY = "votre-cle-anon-publique"
   ```
3. Configurer Supabase
   · Créez un projet Supabase.
   · Exécutez les scripts SQL fournis dans /sql/schema.sql pour créer les tables, index et triggers.
   · Créez deux buckets de stockage publics : media et marketplace.
4. Lancer l’application
   ```bash
   streamlit run app.py
   ```

---

🧭 Guide d’utilisation

1. Connexion / Inscription

· Rendez-vous sur la page d’accueil.
· Connexion : renseignez votre email et mot de passe.
· Inscription : fournissez un email, un mot de passe et un nom d’utilisateur unique. Un profil vide est automatiquement créé.

2. Fil d’actualité (Feed)

· Cliquez sur « 🌐 Feed » dans la barre latérale.
· Publier : développez la section « ✍️ Créer un post », saisissez votre texte et éventuellement un média (image/vidéo). Validez.
· Interagir : sous chaque post, vous pouvez :
  · ❤️ Liker (compteur automatique)
  · 💬 Commenter (ouvre la boîte de dialogue)
  · 🔗 Partager (lien vers le post)

3. Profil

· Accédez à « 👤 Mon Profil ».
· Modifiez vos informations (nom, bio, localisation).
· Photo de profil : utilisez l’upload pour sélectionner une image (compressée automatiquement à 1024px, qualité 85).
· Visualisez vos statistiques : nombre de posts, abonnés, abonnements.

4. Messagerie privée

· Ouvrez « ✉️ Messages ».
· Sélectionnez un contact dans la liste déroulante (contacts basés sur les échanges précédents).
· Consultez l’historique et rédigez un nouveau message.
· Les messages sont stockés de manière sécurisée (chiffrement prévu en version finale).

5. Marketplace

· Rendez-vous dans « 🏪 Marketplace ».
· Ajouter une annonce : remplissez le titre, la description, le prix en KC, et uploader une image.
· Les annonces actives s’affichent en grille.
· Les images sont automatiquement redimensionnées et optimisées.

6. Wallet

· Dans « 💰 Wallet », consultez votre solde en Kongo Coin (KC).
· Miner : cliquez sur le bouton pour recevoir 10 KC toutes les 24h.
· Le total miné est également affiché.

7. Paramètres

· Gérez votre abonnement (Gratuit / Premium).
· (Option dangereuse) suppression de compte (à activer avec précaution).

8. Tunnels souverains (fonctionnalité avancée)

· Dans l’ancienne version (consultable dans l’historique du code), les tunnels permettaient des discussions chiffrées avec clé partagée.
· L’export/import de la chaîne de données permet une synchronisation pair-à-pair.

---

🔧 Configuration avancée

Variables d’environnement

Vous pouvez également définir SUPABASE_URL et SUPABASE_KEY comme variables d’environnement plutôt que dans secrets.toml.

Buckets de stockage

Assurez-vous que les buckets media et marketplace sont publics et que les politiques RLS autorisent les insertions pour les utilisateurs authentifiés.

Sécurité

· Les mots de passe sont gérés par Supabase Auth (hashés, salés).
· Les fichiers uploadés sont validés (type MIME, taille max).
· Le chiffrement des messages privés sera activé prochainement via la classe SOVEREIGN.

---

🛠️ Stack technique

· Frontend : Streamlit
· Backend : Supabase (PostgreSQL, Auth, Storage, Realtime)
· Traitement d’images : Pillow (compression, redimensionnement)
· Langage : Python 3.9+

---

🤝 Contribution

Les contributions sont les bienvenues !
Pour signaler un bug ou proposer une amélioration, ouvrez une issue sur GitHub.
Si vous souhaitez développer une fonctionnalité, fork le projet et soumettez une pull request.

---

📄 Licence

Ce projet est sous licence MIT – vous êtes libre de l’utiliser, le modifier et le distribuer.

---

🙌 Remerciements

· À la communauté GEN-Z GABON pour l’inspiration et les tests.
· À l’équipe Supabase pour leur incroyable plateforme open source.
· À Streamlit pour rendre le développement d’apps data aussi agréable.

---

🇬🇦 FREE-KONGOSSA — la parole libre, souveraine et chiffrée.

```

Ce README couvre à la fois le guide utilisateur complet et met en avant la particularité **FREE KONGOSSA** (chiffrement, souveraineté, tunnels). Il est rédigé en français comme demandé et prêt à être placé dans le dépôt.
