"""
Module de gestion de la base vectorielle.
Création, chargement, et gestion des embeddings avec ChromaDB.
Version robuste avec gestion propre des connexions.
"""

import logging
import shutil
import gc
import time
from typing import List, Optional
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import chromadb

from rag.config import (
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
    VECTOR_STORE_DIR,
    RAW_DOCS_DIR
)
from rag.loader import read_file
from rag.preprocessing import clean_text, split_into_chunks
from rag.metadata import extract_metadata

logger = logging.getLogger(__name__)

# Collection name pour ChromaDB
COLLECTION_NAME = "legal_documents"

# Client ChromaDB global (sera créé à la demande)
_chroma_client = None
_vectorstore_instance = None

def _get_chroma_client():
    """
    Retourne un client ChromaDB persistant.
    Utilise un singleton pour éviter les connexions multiples.
    """
    global _chroma_client

    if _chroma_client is None:
        logger.debug("Création d'un nouveau client ChromaDB")
        _chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))

    return _chroma_client

def _close_chroma_client():
    """
    Ferme proprement le client ChromaDB.
    """
    global _chroma_client, _vectorstore_instance

    if _chroma_client is not None:
        logger.debug("Fermeture du client ChromaDB")
        # Forcer le nettoyage
        _vectorstore_instance = None
        _chroma_client = None
        gc.collect()
        time.sleep(0.3)  # Petit délai pour Windows

def get_embeddings_model() -> OpenAIEmbeddings:
    """
    Retourne le modèle d'embeddings configuré.

    Returns:
        Instance d'OpenAIEmbeddings
    """
    logger.debug(f"Initialisation du modèle d'embeddings: {EMBEDDING_MODEL}")
    return OpenAIEmbeddings(
        openai_api_key=OPENAI_API_KEY,
        model=EMBEDDING_MODEL
    )

def init_vectorstore() -> Chroma:
    """
    Initialize ou charge la base vectorielle existante.
    Utilise un singleton pour éviter les reconnexions.

    Returns:
        Instance de Chroma
    """
    global _vectorstore_instance

    # Si déjà initialisé, retourner l'instance existante
    if _vectorstore_instance is not None:
        return _vectorstore_instance

    embeddings = get_embeddings_model()
    client = _get_chroma_client()

    logger.info("Initialisation de la base vectorielle")

    try:
        # Essayer de charger la collection existante
        _vectorstore_instance = Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings
        )

        count = _vectorstore_instance._collection.count()
        logger.info(f"Base vectorielle chargée avec {count} documents")

    except Exception as e:
        logger.warning(f"Erreur lors du chargement: {e}", exc_info=True)
        logger.info("Création d'une nouvelle base vectorielle")

        _vectorstore_instance = Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings
        )

    return _vectorstore_instance

def add_documents_to_vectorstore(docs: List[Document]) -> int:
    """
    Ajoute des documents à la base vectorielle.

    Args:
        docs: Liste de documents LangChain à indexer

    Returns:
        Nombre de documents ajoutés

    Raises:
        Exception: Si l'ajout échoue
    """
    if not docs:
        logger.warning("Aucun document à ajouter")
        return 0

    try:
        vectorstore = init_vectorstore()
        logger.info(f"Ajout de {len(docs)} documents à la base vectorielle")

        vectorstore.add_documents(docs)

        logger.info(f"{len(docs)} documents ajoutés avec succès")
        return len(docs)

    except Exception as e:
        logger.error(f"Erreur lors de l'ajout des documents: {e}")
        raise

def delete_document_by_source(source_filename: str) -> int:
    """
    Supprime tous les chunks d'un document source.

    Args:
        source_filename: Nom du fichier source à supprimer

    Returns:
        Nombre de chunks supprimés
    """
    try:
        vectorstore = init_vectorstore()
        collection = vectorstore._collection

        # Récupérer tous les documents avec cette source
        results = collection.get(
            where={"source": source_filename}
        )

        if not results['ids']:
            logger.warning(f"Aucun chunk trouvé pour {source_filename}")
            return 0

        # Supprimer par IDs
        collection.delete(ids=results['ids'])

        logger.info(f"{len(results['ids'])} chunks supprimés pour {source_filename}")
        return len(results['ids'])

    except Exception as e:
        logger.error(f"Erreur lors de la suppression: {e}")
        raise

def build_documents_from_file(uploaded_file) -> List[Document]:
    """
    Construit des objets Document LangChain à partir d'un fichier uploadé.

    Args:
        uploaded_file: Fichier uploadé via Streamlit

    Returns:
        Liste de documents LangChain avec métadonnées

    Raises:
        Exception: Si la construction échoue
    """
    filename = uploaded_file.name
    logger.info(f"Construction des documents depuis: {filename}")

    try:
        # 1. Lire le fichier
        raw_text = read_file(uploaded_file)

        # 2. Nettoyer le texte
        cleaned_text = clean_text(raw_text)

        # 3. Découper en chunks
        chunks = split_into_chunks(cleaned_text)

        if not chunks:
            logger.warning(f"Aucun chunk créé pour {filename}")
            return []

        # 4. Créer les documents avec métadonnées
        documents = []
        for idx, chunk in enumerate(chunks):
            metadata = extract_metadata(filename, chunk, chunk_id=idx)
            doc = Document(page_content=chunk, metadata=metadata)
            documents.append(doc)

        logger.info(f"{len(documents)} documents créés depuis {filename}")
        return documents

    except Exception as e:
        logger.error(f"Erreur lors de la construction des documents depuis {filename}: {e}")
        raise

def clear_vectorstore():
    """
    Vide complètement la base vectorielle en supprimant tous les documents.
    Méthode propre qui ne nécessite pas de supprimer les fichiers.
    """
    try:
        logger.info("Suppression de tous les documents de la base vectorielle")

        vectorstore = init_vectorstore()
        collection = vectorstore._collection

        # Récupérer tous les IDs
        all_data = collection.get()

        if all_data['ids']:
            # Supprimer tous les documents
            collection.delete(ids=all_data['ids'])
            logger.info(f"{len(all_data['ids'])} documents supprimés")
        else:
            logger.info("La base est déjà vide")

    except Exception as e:
        logger.error(f"Erreur lors du vidage de la base: {e}")
        raise

def rebuild_vectorstore_from_raw_docs() -> int:
    """
    Reconstruit complètement la base vectorielle depuis les fichiers bruts.
    Version simplifiée qui vide et recharge sans supprimer les fichiers.

    Returns:
        Nombre total de chunks indexés
    """
    logger.info("Reconstruction complète de la base vectorielle")

    try:
        # 1. Vider la base vectorielle (sans supprimer les fichiers)
        clear_vectorstore()

        # 2. Récupérer tous les fichiers dans raw_docs
        raw_files = list(RAW_DOCS_DIR.glob("*"))
        raw_files = [f for f in raw_files if f.is_file() and not f.name.startswith('.')]

        if not raw_files:
            logger.info("Aucun fichier à indexer")
            return 0

        logger.info(f"Reconstruction depuis {len(raw_files)} fichiers")

        # 3. Traiter chaque fichier
        all_documents = []
        for file_path in raw_files:
            try:
                # Créer un objet file-like pour build_documents_from_file
                class FileWrapper:
                    def __init__(self, path):
                        self.name = path.name
                        try:
                            with open(path, 'rb') as f:
                                self._content = f.read()
                        except (OSError, IOError) as e:
                            logger.error(f"Impossible de lire le fichier {path.name}: {e}", exc_info=True)
                            raise

                    def getvalue(self):
                        return self._content

                file_wrapper = FileWrapper(file_path)
                docs = build_documents_from_file(file_wrapper)
                all_documents.extend(docs)

            except Exception as e:
                logger.error(f"Erreur lors du traitement de {file_path.name}: {e}", exc_info=True)
                continue

        # 4. Ajouter tous les documents à la base
        if all_documents:
            add_documents_to_vectorstore(all_documents)

        logger.info(f"Reconstruction terminée: {len(all_documents)} chunks indexés")
        return len(all_documents)

    except Exception as e:
        logger.error(f"Erreur lors de la reconstruction de la base vectorielle: {e}")
        raise

def reset_vectorstore():
    """
    Reset complet: ferme la connexion, supprime les fichiers, recrée.
    À utiliser UNIQUEMENT en cas de corruption totale.
    """
    try:
        logger.warning("Reset complet de la base vectorielle")

        # 1. Fermer proprement la connexion
        _close_chroma_client()

        # 2. Attendre que les fichiers soient libérés
        time.sleep(1)
        gc.collect()

        # 3. Supprimer les fichiers ChromaDB
        if VECTOR_STORE_DIR.exists():
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    shutil.rmtree(VECTOR_STORE_DIR)
                    logger.info("Fichiers ChromaDB supprimés")
                    break
                except (PermissionError, OSError) as e:
                    if attempt < max_attempts - 1:
                        logger.warning(f"Tentative {attempt + 1} échouée, attente...")
                        time.sleep(2)
                        gc.collect()
                    else:
                        raise Exception(
                            "Impossible de supprimer les fichiers ChromaDB. "
                            "Fermez l'application et supprimez manuellement le dossier data/vector_store/"
                        )

        # 4. Recréer le dossier
        VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

        # 5. Réinitialiser la base
        init_vectorstore()

        logger.info("Reset terminé, base vectorielle recréée")
        return True

    except Exception as e:
        logger.error(f"Erreur lors du reset: {e}")
        raise

def get_vectorstore_stats() -> dict:
    """
    Récupère des statistiques sur la base vectorielle.

    Returns:
        Dictionnaire avec les statistiques
    """
    try:
        vectorstore = init_vectorstore()
        count = vectorstore._collection.count()

        # Compter les fichiers sources uniques
        raw_files = list(RAW_DOCS_DIR.glob("*"))
        raw_files = [f for f in raw_files if f.is_file() and not f.name.startswith('.')]

        return {
            "total_chunks": count,
            "total_files": len(raw_files),
            "collection_name": COLLECTION_NAME
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        return {
            "total_chunks": 0,
            "total_files": 0,
            "collection_name": COLLECTION_NAME
        }
