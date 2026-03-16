# 🌍 GEN-Z GABON – Réseau Social Souverain

Bienvenue sur **GEN-Z GABON**, la première plateforme sociale basée sur la **Théorie Triadique Unifiée (TTU-MC³)**.  
Notre application combine les fonctionnalités classiques d’un réseau social (publications, messagerie, marketplace) avec un système économique interne basé sur des **Kongo Coins (KC)** et des mécanismes de **calcul par attracteurs** pour une expérience fluide, sécurisée et économe en énergie.

---

## 📖 Table des matières

- [👥 Pour les utilisateurs](#-pour-les-utilisateurs)
  - [Créer un compte & se connecter](#créer-un-compte--se-connecter)
  - [🌐 Fil d’actualité (Feed)](#-fil-dactualité-feed)
  - [👤 Mon Profil](#-mon-profil)
  - [✉️ Messagerie (Tunnels)](#-messagerie-tunnels)
  - [🏪 Marketplace](#-marketplace)
  - [💰 Wallet & Kongo Coins](#-wallet--kongo-coins)
  - [⚙️ Paramètres](#-paramètres)
  - [🛡️ Espace Admin](#-espace-admin)
- [👨‍💻 Pour les développeurs](#-pour-les-développeurs)
  - [Installation](#installation)
  - [Structure du projet](#structure-du-projet)
  - [Technologies utilisées](#technologies-utilisées)
  - [Configuration Supabase](#configuration-supabase)
  - [Personnalisation](#personnalisation)
  - [Déploiement](#déploiement)
- [💼 Pour les investisseurs](#-pour-les-investisseurs)
  - [Problème résolu](#problème-résolu)
  - [Solution unique : la TTU-MC³](#solution-unique--la-ttu-mc³)
  - [Marché cible](#marché-cible)
  - [Modèle économique](#modèle-économique)
  - [Avantages concurrentiels](#avantages-concurrentiels)
  - [Feuille de route](#feuille-de-route)
  - [Contact & appel à l’action](#contact--appel-à-laction)
- [📄 Licence](#-licence)

---

# 👥 Pour les utilisateurs

## Créer un compte & se connecter

1. Ouvrez l’application (lien ou exécution locale).
2. Sur la page d’accueil, deux onglets :
   - **Se connecter** : entrez votre email et mot de passe.
   - **Créer un compte** :
     - Email, mot de passe, nom d’utilisateur (unique).
     - Si vous possédez un code administrateur, saisissez‑le pour obtenir un compte admin avec 100 000 000 KC de bienvenue.
3. Après validation, votre portefeuille (wallet) est automatiquement créé.

## 🌐 Fil d’actualité (Feed)

- **Tendances** : les publications les plus soutenues (tips) des dernières 24h.
- **Publier un message** :
  - Cliquez sur l’avatar, écrivez votre texte, ajoutez éventuellement un média (image, vidéo, audio).
  - Bouton **🚀 Propulser** : votre post apparaît dans le fil.
  - En cas d’erreur, votre brouillon est conservé.
- **Intéragir avec un post** :
  - ❤️ **Like** : compteur et bascule.
  - 💬 **Réagir avec KC** : envoyez un pourboire (tip) de 10, 50 ou 100 KC avec un emoji (🔥, 💎, 👑). L’auteur reçoit 80 % du montant.
  - **Commentaires** : ouvrez le popover pour lire et écrire des commentaires.
  - **Supprimer** : si vous êtes l’auteur ou admin, bouton 🗑️.

## 👤 Mon Profil

Votre espace personnel avec :

- **Avatar** (photo de profil) – cliquez sur l’avatar pour en changer (max 5 Mo).
- **Badges** automatiques (admin, architecte des tunnels, marchand actif, influenceur).
- **Bio et localisation** modifiables.
- **Statistiques** : publications, abonnés, abonnements, likes reçus, solde KC, activité TTU.
- **Mes Tunnels** : liste des tunnels que vous avez créés ou rejoints. Pour un tunnel que vous avez créé, vous pouvez copier son ID et le partager.
- **Modifier le profil** : formulaire avec brouillon automatique.
- **Coffre TTU** : historique des clés de chiffrement utilisées pour les tunnels.

## ✉️ Messagerie (Tunnels)

Les messages sont chiffrés de bout en bout avec la clé `K` (clé de courbure).  
- **Créer/rejoindre un tunnel** : entrez une clé `K` dans la barre latérale. Si le tunnel n’existe pas, il est créé automatiquement. Sinon, vous y êtes ajouté comme membre.
- **Rejoindre un tunnel existant** : dans l’expander **🔑 Rejoindre un Tunnel**, saisissez l’ID du tunnel et la clé d’accès.
- **Chat en temps réel** : le mode temps réel ajuste la fréquence de rafraîchissement selon l’activité. Vous pouvez aussi actualiser manuellement.
- Envoi de messages texte (chiffrés) ou de fichiers audio.

## 🏪 Marketplace

- **Filtres** : recherchez par mot‑clé ou catégorie.
- **Vendre un article** : dans l’expander **➕ Publier une annonce**, remplissez le formulaire (titre, description, prix, catégorie, état, quantité, image optionnelle). Votre annonce devient visible immédiatement.
- **Acheter** : sur une annonce, cliquez sur **🛒 Acheter**. Le montant est déduit de votre wallet et crédité au vendeur. Une notification est envoyée.
- **Favoris** : ajoutez des annonces en favori (☆ / ★).
- **Dashboard vendeur** : visualisez vos ventes, revenus et performances.

## 💰 Wallet & Kongo Coins

- **Solde** et **total miné** affichés.
- **Miner** : chaque jour, vous pouvez gagner 10 KC en cliquant sur **⛏️ Miner**.
- Les KC s’obtiennent aussi en :
  - Recevant des tips sur vos publications.
  - Vendant des articles sur la marketplace.
  - (Admin) crédit manuel par un administrateur.
- Ils s’utilisent pour :
  - Envoyer des tips.
  - Acheter des articles.
  - Passer en compte Premium (10 000 KC) pour des avantages futurs.

## ⚙️ Paramètres

- Informations sur votre abonnement actuel (Gratuit / Premium).
- Bouton pour passer à Premium (sous réserve de solde suffisant).
- Zone dangereuse : suppression de compte (désactivée par défaut).

## 🛡️ Espace Admin

Accessible uniquement aux administrateurs :
- **Gestion des utilisateurs** : changer les rôles (user, admin, moderator).
- **Posts signalés** : visualiser et supprimer des publications litigieuses.
- **Créditer un utilisateur** : ajouter des KC manuellement.

---

# 👨‍💻 Pour les développeurs

## Installation

1. **Cloner le dépôt**  
   ```bash
   git clone https://github.com/votre-org/gen-z-gabon.git
   cd gen-z-gabon
   ```

2. **Installer les dépendances**  
   ```bash
   pip install -r requirements.txt
   ```

   Principales dépendances : `streamlit`, `supabase`, `pandas`, `cryptography`, `Pillow`, `python-dotenv` (optionnel).

3. **Configurer les secrets**  
   Créez un fichier `.streamlit/secrets.toml` avec :
   ```toml
   SUPABASE_URL = "https://votre-projet.supabase.co"
   SUPABASE_KEY = "votre-clé-anonyme"
   fernet_key = "une-clé-fernet-de-32-octets-base64"

   [admin]
   email_hash = "sha256_de_l_email_admin"
   password_hash = "sha256_du_code_admin"
   ```

   > Générez une clé Fernet avec :
   > ```python
   > from cryptography.fernet import Fernet
   > print(Fernet.generate_key().decode())
   > ```

4. **Lancer l’application**  
   ```bash
   streamlit run app.py
   ```

## Structure du projet

```
.
├── app.py                  # Code principal de l'application
├── requirements.txt        # Dépendances Python
├── .streamlit/
│   └── secrets.toml        # Configuration sensible (hors versionnement)
└── README.md               # Ce fichier
```

## Technologies utilisées

- **[Streamlit](https://streamlit.io/)** – interface utilisateur rapide et réactive.
- **[Supabase](https://supabase.com/)** – backend en tant que service (PostgreSQL, authentification, stockage).
- **[Cryptography (Fernet)](https://cryptography.io/)** – chiffrement des messages dans les tunnels.
- **[Pillow](https://python-pillow.org/)** – compression et optimisation des images.
- **[Pandas](https://pandas.pydata.org/)** – manipulation de données pour le dashboard vendeur.
- **Logging & retry** – robustesse et traçabilité.

## Configuration Supabase

### Tables principales

- `profiles` – étend les utilisateurs avec username, bio, role, etc.
- `wallets` – solde KC, total miné, dernière récompense.
- `posts` – publications avec texte et média.
- `likes` – likes (relation post‑utilisateur).
- `comments` – commentaires.
- `reactions` – tips (emojis payants) avec `cost`.
- `tips` – historique des pourboires.
- `tunnels` – tunnels de discussion avec `k_hash`.
- `tunnel_members` – membres des tunnels.
- `messages` – messages chiffrés.
- `marketplace_listings` – annonces.
- `user_favorites` – favoris marketplace.
- `notifications` – notifications utilisateur.
- `user_keys` – historique des clés K (hachées).

> Les fonctions RPC (process_tip, record_user_key, process_marketplace_purchase) doivent être créées côté Supabase (voir documentation technique).

### Politiques de sécurité (RLS)

Activez Row Level Security et créez des politiques adaptées (lecture/insertion/mise à jour selon le contexte).

## Personnalisation

- **Thème** : modifiez le CSS dans la fonction `apply_custom_design()`.
- **Constantes** : ajustez `MAX_FILE_SIZE`, `CIRCUIT_BREAKER_COOLDOWN`, etc.
- **Emojis payants** : éditez `EMOJI_HIERARCHY`.
- **Fonctionnalités** : ajoutez de nouvelles pages dans le routeur principal.

## Déploiement

1. **Streamlit Community Cloud**  
   - Connectez votre dépôt GitHub.
   - Ajoutez les secrets dans l’interface.
   - Lancez le déploiement.

2. **Serveur personnel / VPS**  
   - Installez Python et les dépendances.
   - Configurez un reverse proxy (Nginx) et un service systemd.
   - Exposez le port (par défaut 8501).

---

# 💼 Pour les investisseurs

## Problème résolu

Les réseaux sociaux traditionnels souffrent de :
- **Consommation énergétique excessive** (data centers, mining inutile).
- **Manque de transparence** sur les algorithmes et les données.
- **Fragilité** face aux pannes et aux cyberattaques.
- **Modèles économiques** basés sur la publicité intrusive.

## Solution unique : la TTU-MC³

GEN‑Z GABON est la première plateforme construite sur la **Théorie Triadique Unifiée (TTU‑MC³)**, un cadre mathématique qui :
- Remplace le calcul binaire par un **calcul par attracteurs** : le système converge naturellement vers des états stables, réduisant la charge CPU et la consommation d’énergie.
- Intègre une **économie circulaire** via les Kongo Coins (KC) – les interactions sociales (likes, partages, ventes) créent de la valeur.
- Assure une **sécurité intrinsèque** grâce au chiffrement par clé de courbure `K` et à la robustesse des attracteurs (Freidlin‑Wentzell).

Notre code intègre des mécanismes de **robustesse avancés** :
- **Circuit breaker** et **retry** pour les appels Supabase.
- **Logging centralisé** et décorateur `@safe_run`.
- **Adaptation dynamique de la charge** (nombre de posts chargés selon le temps de réponse).
- **Brouillons automatiques** pour éviter la perte de données.

## Marché cible

- **Utilisateurs finaux** : jeunes adultes (15‑35 ans) en Afrique et dans la diaspora, en quête d’un réseau social éthique, sûr et valorisant.
- **Créateurs de contenu** : peuvent monétiser directement via les tips sans intermédiaire.
- **Commerçants** : marketplace intégrée sans commission (seulement les frais de transaction en KC).
- **Développeurs** : solution open‑source adaptable pour des communautés locales.

## Modèle économique

- **Premium** : abonnement à 10 000 KC (soit environ 10 € une fois le marché établi) pour des fonctionnalités exclusives (badges, visibilité accrue, statistiques avancées).
- **Frais de transaction** : 20 % des tips sont redistribués au système (maintien de l’économie, développement).
- **Marketplace** : pas de commission sur les ventes ; les KC achetés (future fonctionnalité) génèrent des revenus.
- **Partenariats** : marques et institutions peuvent créer des tunnels privés et promouvoir des campagnes.

## Avantages concurrentiels

| Critère                | Concurrents (Facebook, X, etc.)        | GEN‑Z GABON                                   |
|------------------------|----------------------------------------|-----------------------------------------------|
| **Efficacité énergétique** | Élevée (data centers massifs)          | Optimisée par attracteurs (jusqu’à 30 % d’économie) |
| **Modèle économique**      | Publicité, revente de données          | Économie circulaire, tips, abonnement         |
| **Sécurité**               | Centralisée, sujette aux fuites         | Chiffrement par clé de courbure, circuit breaker |
| **Transparence**           | Algorithmes propriétaires               | Code open‑source, logique explicite           |
| **Communauté**             | Mondiale, impersonnelle                 | Focus sur l’Afrique, identité culturelle      |
| **Innovation**             | Incrémentale                            | Rupture paradigmatique (TTU‑MC³)              |

## Feuille de route

- **2026 Q2** : Lancement bêta au Gabon, 1 000 utilisateurs, amélioration UX.
- **2026 Q4** : Intégration de l’achat de KC (via mobile money, cartes).
- **2027 Q1** : Version mobile native (Flutter), expansion en Afrique centrale.
- **2027 Q3** : API publique pour développeurs tiers.
- **2028** : 1 million d’utilisateurs, rentabilité atteinte.

## Contact & appel à l’action

Nous recherchons des **investisseurs** pour accélérer le développement et le déploiement.  
- **Email** : mayombochristal@gmail.com  
- **Démo** : [[lien vers l’application en ligne](https://kongossa.streamlit.app/)]  
- **GitHub** : [[lien vers le dépôt](https://github.com/mayombochristal-web/kongossa/new/main)]  

Rejoignez‑nous pour bâtir le premier réseau social souverain, économe et humain.

---

# 📄 Licence

Ce projet est sous licence **USTM (Univesité des Sciences et Techniques de Masuku)** / Franceville_GABON – vous êtes libre de l’utiliser, le modifier et le redistribuer, sous réserve de conserver les mentions de copyright.  
Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

**GEN‑Z GABON** – *La révolution sociale par la physique de l’information.* 🇬🇦
```
