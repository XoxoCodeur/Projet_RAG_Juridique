"""
Configuration globale de l'application.
Gestion des variables d'environnement et des chemins.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Chemins racine
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DOCS_DIR = DATA_DIR / "raw_docs"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
CONVERSATIONS_DIR = DATA_DIR / "conversations"
LOGS_DIR = PROJECT_ROOT / "logs"

# Créer les répertoires s'ils n'existent pas
for directory in [DATA_DIR, RAW_DOCS_DIR, VECTOR_STORE_DIR, CONVERSATIONS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Configuration API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))

# Paramètres de chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Paramètres de retrieval
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "5"))

# Configuration du logging
LOG_FILE = LOGS_DIR / "app.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.INFO

def setup_logging():
    """Configure le système de logging."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def validate_config():
    """Valide que la configuration est correcte."""
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY n'est pas définie. "
            "Veuillez créer un fichier .env avec votre clé API."
        )
    return True

# Initialiser le logging au chargement du module
setup_logging()
