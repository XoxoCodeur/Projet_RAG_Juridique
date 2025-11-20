"""
Gestionnaire de synchronisation entre fichiers et base vectorielle.
Suit l'état de synchronisation et détecte les changements.
"""

import logging
from pathlib import Path
from typing import Dict, List, Set
from rag.config import RAW_DOCS_DIR
from rag.vectorstore import init_vectorstore

logger = logging.getLogger(__name__)

class SyncStatus:
    """États de synchronisation possibles"""
    SYNCED = "synced"  # Fichier indexé et à jour
    PENDING = "pending"  # Fichier présent mais pas encore indexé
    DELETED = "deleted"  # Fichier supprimé mais encore dans l'index

def get_files_in_raw_docs() -> Set[str]:
    """
    Retourne l'ensemble des noms de fichiers dans raw_docs.

    Returns:
        Set de noms de fichiers
    """
    raw_files = list(RAW_DOCS_DIR.glob("*"))
    return {f.name for f in raw_files if f.is_file() and not f.name.startswith('.')}

def get_indexed_sources() -> Set[str]:
    """
    Retourne l'ensemble des sources indexées dans ChromaDB.

    Returns:
        Set de noms de fichiers sources
    """
    try:
        vectorstore = init_vectorstore()
        collection = vectorstore._collection

        # Récupérer tous les documents
        all_data = collection.get()

        if not all_data or not all_data.get('metadatas'):
            return set()

        # Extraire les sources uniques
        sources = {
            metadata.get('source')
            for metadata in all_data['metadatas']
            if metadata.get('source')
        }

        return sources

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des sources indexées: {e}")
        return set()

def get_sync_status() -> Dict[str, Dict]:
    """
    Analyse l'état de synchronisation entre fichiers et index.

    Returns:
        Dict avec:
        - synced: Liste des fichiers synchronisés
        - pending: Liste des fichiers en attente d'indexation
        - orphaned: Liste des sources dans l'index sans fichier
        - needs_rebuild: Boolean indiquant si une reconstruction est nécessaire
    """
    files_on_disk = get_files_in_raw_docs()
    indexed_sources = get_indexed_sources()

    # Fichiers synchronisés (présents des deux côtés)
    synced = files_on_disk & indexed_sources

    # Fichiers en attente (sur disque mais pas indexés)
    pending = files_on_disk - indexed_sources

    # Sources orphelines (indexées mais fichier supprimé)
    orphaned = indexed_sources - files_on_disk

    # Besoin de rebuild si des changements sont détectés
    needs_rebuild = len(pending) > 0 or len(orphaned) > 0

    result = {
        "synced": sorted(list(synced)),
        "pending": sorted(list(pending)),
        "orphaned": sorted(list(orphaned)),
        "needs_rebuild": needs_rebuild,
        "total_files": len(files_on_disk),
        "total_indexed": len(indexed_sources)
    }

    logger.info(
        f"Sync status: {len(synced)} synced, "
        f"{len(pending)} pending, {len(orphaned)} orphaned"
    )

    return result

def is_synced() -> bool:
    """
    Vérifie si les fichiers et l'index sont synchronisés.

    Returns:
        True si tout est synchronisé
    """
    status = get_sync_status()
    return not status["needs_rebuild"]

def get_file_status(filename: str) -> str:
    """
    Retourne le statut d'un fichier spécifique.

    Args:
        filename: Nom du fichier

    Returns:
        État du fichier (SYNCED, PENDING, DELETED)
    """
    status = get_sync_status()

    if filename in status["synced"]:
        return SyncStatus.SYNCED
    elif filename in status["pending"]:
        return SyncStatus.PENDING
    elif filename in status["orphaned"]:
        return SyncStatus.DELETED
    else:
        return SyncStatus.PENDING
