# 🤖 Komara Agency - Bot Telegram RAG

Bot Telegram intelligent avec système RAG (Retrieval-Augmented Generation) 100% gratuit et local.

## ✨ Fonctionnalités

- 🌍 **Multilingue** : Français, Arabe, Anglais (détection automatique)
- 🧠 **RAG Local** : Embeddings avec sentence-transformers (pas d'API payante)
- 💬 **Flux conversationnels** : Devis, portfolio, FAQ
- 📊 **Logging Google Sheets** : Historique complet des conversations
- 🖼️ **Portfolio Drive** : Affichage des images depuis Google Drive
- 🔒 **Sécurité** : Protection contre l'extraction de prompts
- ⚡ **Performance** : Logging asynchrone, cache TTL, anti-doublon

## 🚀 Déploiement rapide

### 1. Prérequis

```bash
Python 3.10+
Compte Google Cloud (Sheets + Drive API activées)
Bot Telegram (token depuis @BotFather)
```

### 2. Installation

```bash
# Cloner le repo
git clone https://github.com/komaraagency/Komara-Agency-Aya-2.git
cd Komara-Agency-Aya-2

# Installer les dépendances
pip install -r requirements.txt

# Télécharger le modèle d'embedding
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Copier .env.example vers .env
cp .env.example .env

# Éditer .env avec vos valeurs
nano .env
```
