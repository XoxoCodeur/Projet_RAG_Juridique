# 📚 Test technique AI Sisters


**Points clés du projet :**
- ✅ Interface utilisateur moderne et intuitive (Streamlit)
- ✅ Pipeline RAG complet avec reformulation de requêtes
- ✅ Extraction et filtrage intelligent par métadonnées
- ✅ Gestion de conversations persistantes (style ChatGPT)
- ✅ Système de synchronisation automatique
- ✅ Export multi-format des conversations

## Architecture et choix techniques

### Stack technologique

**Framework UI : Streamlit**

**LLM : OpenAI GPT-5 Mini**
- Modèle léger et performant pour la génération de réponses
- Température à 0.0 pour des réponses déterministes (important en juridique)
- Utilisé aussi pour la reformulation de requêtes et la génération de titres de conversations

**Embeddings : text-embedding-3-small**
- Bon compromis entre performance et coût
- Dimension de vecteurs optimale pour notre cas d'usage
- Compatible avec ChromaDB

**Vector Store : ChromaDB**
- Base vectorielle légère et persistante
- Pas besoin de serveur externe
- Support natif des filtres de métadonnées (crucial pour notre système)

### Architecture modulaire

J'ai structuré le code en modules clairement séparés :

```
├── app.py                          # Page d'accueil
├── pages/
│   ├── 1_Chatbot.py               # Interface conversationnelle
│   └── 2_Gestion_documents.py     # Gestion des documents et paramètres
└── rag/
    ├── config.py                  # Configuration centralisée
    ├── loader.py                  # Chargement multi-formats (TXT, CSV, HTML)
    ├── preprocessing.py           # Nettoyage et chunking
    ├── metadata.py                # Extraction intelligente de métadonnées
    ├── query_parser.py            # Parsing des requêtes utilisateur
    ├── rag_chain.py              # Orchestration du pipeline RAG
    ├── vectorstore.py            # Gestion de ChromaDB
    ├── conversation_manager.py    # Persistence des conversations
    └── sync_manager.py           # Synchronisation fichiers ↔ base
```


## 🎨 Interface utilisateur moderne

J'ai accordé une attention particulière à l'expérience utilisateur :

### Design et ergonomie

**Page d'accueil**
- Design minimaliste avec cartes de fonctionnalités
- Info box explicative pour guider l'utilisateur
- Effet hover subtil sur les cartes (glow violet)
- Navigation directe vers les sections principales

**Page Chatbot**
- Interface conversationnelle claire et aérée
- Métriques en temps réel (documents, chunks, conversation)
- Affichage des sources avec expanders
- Export de conversations directement depuis l'interface

**Page Gestion des Documents**
- Upload drag & drop intuitif
- Indicateur de synchronisation visuel (✓ ou ⚠️)
- Statistiques en temps réel
- Paramètres de chunking ajustables
- Paramètre de synchronisation automatique 


## 🚀 Fonctionnalités principales

### 1. RAG Conversationnel avec reformulation de requêtes

**Problématique** : Les questions de suivi du type "Et l'article 4 ?" ne fonctionnent pas sans contexte.

**Solution** : J'ai implémenté une reformulation contextuelle des requêtes :
```python
def reformulate_query_with_history(current_query, conversation_history, max_history=3):
    """Reformule la question en tenant compte des 3 derniers échanges"""
    if not conversation_history:
        return current_query

    # Construire le contexte
    recent_history = conversation_history[-max_history * 2:]

    # Utiliser le LLM pour reformuler
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0.0)
    reformulated = llm.invoke(prompt).content.strip()

    return reformulated
```

Cela permet des conversations naturelles sans répéter le contexte à chaque fois.

### 2. Extraction et filtrage intelligent par métadonnées

**Défi** : Comment retrouver efficacement "le contrat de Jean Dupont" parmi des centaines de documents ?

**Solution** : Extraction automatique de métadonnées à partir des noms de fichiers et du contenu :

- **Type de document** : contrat, note, jurisprudence, litige, consultation, facture, correspondance
- **Nom de personne** : extraction via regex depuis le filename et le contenu
- **Date** : détection automatique des mentions de dates

Exemple de métadonnées extraites :
```json
{
    "source": "contrat_jean_dupont.txt",
    "chunk_id": 0,
    "type_doc": "contrat",
    "personne": "Jean Dupont",
    "length": 1523
}
```

Ces métadonnées sont utilisées pour filtrer les résultats avant la recherche vectorielle, améliorant drastiquement la précision.

### 3. Citation précise des sources

**Problème** : Les LLM peuvent halluciner des sources ou en citer trop.

**Solution** : J'ai implémenté un système de citation vérifiable :

1. Le prompt demande au LLM de citer explicitement les sources utilisées : `[Sources: 1, 3]`
2. Une fonction parse la réponse et extrait les numéros de documents
3. Seuls les documents réellement cités sont affichés à l'utilisateur

```python
def extract_used_sources(answer: str, all_docs: List[Document]):
    """Extrait et vérifie les sources citées par le LLM"""
    pattern = r'\[Sources?:\s*([\d,\s]+)\]'
    match = re.search(pattern, answer)

    if not match:
        return answer, all_docs

    # Extraire les numéros et valider
    source_numbers = [int(n.strip()) for n in match.group(1).split(',')]
    used_docs = [all_docs[num-1] for num in source_numbers if 1 <= num <= len(all_docs)]

    return clean_answer, used_docs
```

### 4. Gestion des conversations style ChatGPT

J'ai implémenté un système complet de gestion de conversations :

- **Sauvegarde automatique** : Chaque échange est persisté en JSON
- **Titres auto-générés** : Le LLM crée des titres courts (3-5 mots) à partir du premier message
- **Organisation temporelle** : Groupement par date (Aujourd'hui, Hier, 7 derniers jours...)
- **Export multi-format** : TXT, JSON, Markdown avec formatage adapté

### 5. Chunking paramétrable

J'ai rendu les paramètres de découpage configurables par l'utilisateur :

- **Taille des chunks** : 100-2000 caractères (défaut : 1000)
- **Chevauchement** : 0-500 caractères (défaut : 200)

Le choix de ces valeurs impacte directement la qualité du RAG :
- Chunks trop petits → perte de contexte
- Chunks trop grands → bruit dans les résultats
- Chevauchement → évite de couper les informations importantes

### 6. Système de synchronisation avec état

Pour éviter les incohérences entre fichiers et base vectorielle, j'ai créé un gestionnaire de synchronisation qui compare les fichiers bruts avec les documents indexés et affiche un indicateur visuel (✓ ou ⚠️).

## Pipeline RAG détaillé

Voici le flow complet d'une requête utilisateur :

```
1. REFORMULATION (si historique existe)
   ├─ Question originale : "Et l'article 4 ?"
   └─ Question reformulée : "Quel est le contenu de l'article 4 du contrat Jean Dupont ?"

2. PARSING DE LA REQUÊTE
   ├─ Détection type document : "contrat"
   ├─ Détection personne : "Jean Dupont"
   └─ Construction filtres ChromaDB : {"type_doc": "contrat", "personne": "Jean Dupont"}

3. RETRIEVAL AVEC FILTRES
   ├─ Embedding de la question
   ├─ Recherche vectorielle dans ChromaDB avec filtres
   └─ Récupération des 5 chunks les plus pertinents

4. FALLBACK (si aucun résultat)
   ├─ Retirer le filtre "personne"
   └─ Nouvelle recherche avec seulement le type de document

5. GÉNÉRATION DE RÉPONSE
   ├─ Construction du contexte avec les chunks
   ├─ Appel au LLM avec système prompt strict
   └─ Réponse + citations [Sources: 1, 3]

6. POST-PROCESSING
   ├─ Extraction des sources réellement utilisées
   ├─ Affichage de la réponse nettoyée
   └─ Affichage des extraits cités avec expanders
```

## Gestion d'erreurs et robustesse

J'ai porté une attention particulière à la robustesse du système :

### Logging exhaustif
Tous les modules utilisent le logger Python avec des niveaux appropriés :
```python
logger.info(f"Documents récupérés : {len(docs)}")
logger.warning(f"Aucun résultat avec filtres, fallback sans personne")
logger.error(f"Erreur lors de l'indexation : {e}", exc_info=True)
```

Le `exc_info=True` permet d'avoir la stack trace complète en production.

### Validation des entrées
- Taille maximale des fichiers : 10 MB (configuré dans `.streamlit/config.toml`)
- Validation du chevauchement < taille chunk
- Vérification de la présence de documents avant d'autoriser le chat

### Feedback utilisateur
Toutes les opérations critiques ont un retour visuel :
```python
with st.spinner("Recherche dans les documents..."):
    answer, sources = answer_question_with_rag(query)

st.success("✅ Document indexé avec succès")
st.error("❌ Erreur lors de l'upload")
st.warning("⚠️ Taille de fichier supérieure à 10 MB")
```

## ⚡ Optimisations et choix de performance

### 1. Singleton pour ChromaDB
J'ai implémenté un pattern singleton pour ChromaDB afin d'éviter de réinitialiser la connexion à chaque requête. Une instance globale est conservée en mémoire.

### 2. Paramètres dynamiques sans redémarrage
Les paramètres de chunking peuvent être modifiés via l'interface utilisateur et sont appliqués dynamiquement via des variables d'environnement, sans nécessiter un redémarrage de l'application.

### 3. Limitation du contexte dans la reformulation
Seuls les 3 derniers échanges sont utilisés pour la reformulation des requêtes, ce qui évite de dépasser la fenêtre de contexte du LLM et réduit les coûts API.
Ce paramètre est à adapter en fonction des usages/besoins

### 4. Gestion efficace de la mémoire
- Déchargement automatique des fichiers après indexation
- Nettoyage des conversations inactives
- Stockage des conversations en JSON plutôt qu'en base de données pour éviter la surcharge

## Installation et démarrage

### Prérequis
```bash
Python 3.9+
OpenAI API Key
```

### Installation
```bash
# Cloner le projet
git clone <repository_url>
cd Test_technique_AI_Sisters

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer la clé API
cp .env.example .env
# Éditer .env et ajouter votre OPENAI_API_KEY
```

### Configuration
Le fichier `.env` contient tous les paramètres :
```env
OPENAI_API_KEY=sk-your-key-here
MODEL_NAME=gpt-5-mini
EMBEDDING_MODEL=text-embedding-3-small
TEMPERATURE=0.0
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
RETRIEVAL_K=5
```

### Lancement
```bash
streamlit run app.py
```

L'application sera accessible sur `http://localhost:8501`



## Structure des données

### Fichiers persistés
```
data/
├── raw_docs/              # Documents originaux avec timestamp
├── vector_store/          # Base ChromaDB
└── conversations/         # Conversations au format JSON
```

### Format de conversation
```json
{
  "id": "20251119_230449",
  "title": "Article 3 contrat Dupont",
  "created_at": "2025-11-19T23:04:49",
  "updated_at": "2025-11-19T23:06:20",
  "messages": [
    {
      "role": "user",
      "content": "Quel est l'article 3 ?"
    },
    {
      "role": "assistant",
      "content": "L'article 3 concerne...",
      "sources": [...]
    }
  ]
}
```

## 🔐 Sécurité et confidentialité

J'ai intégré plusieurs mesures pour garantir la sécurité des données :

- **Clé API sécurisée** : Stockée dans `.env` (non versionné)
- **Données locales** : Pas de transmission à des serveurs tiers (sauf OpenAI pour le LLM)
- **Logs sécurisés** : Aucune donnée sensible dans les logs
- **Isolation des conversations** : Chaque conversation est stockée séparément



## 👨‍💻 À propos

**Développé par** : Robin Baret - robin.baret1@gmail.com - 06 51 26 00 76
**Date** : Novembre 2025
**Contexte** : Test technique AI Sisters
**Stack** : Python 3.11, Streamlit, ChromaDB, OpenAI

**Technologies utilisées** :
- `streamlit` - Framework UI
- `langchain` - Orchestration RAG
- `chromadb` - Base vectorielle
- `openai` - LLM et embeddings
- `beautifulsoup4` - Parsing HTML
- `pandas` - Manipulation de données
- `python-dotenv` - Gestion de configuration

---


