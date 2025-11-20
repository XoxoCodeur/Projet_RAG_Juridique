"""
Module de prétraitement des documents.
Nettoyage du texte et découpage en chunks.
"""

import re
import logging
import os
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag.config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)

def get_chunk_params():
    """
    Récupère les paramètres de chunking depuis les variables d'environnement.
    Permet de modifier dynamiquement les paramètres sans redémarrer l'app.

    Returns:
        Tuple (chunk_size, chunk_overlap)
    """
    try:
        chunk_size = int(os.environ.get("CHUNK_SIZE", CHUNK_SIZE))
        chunk_overlap = int(os.environ.get("CHUNK_OVERLAP", CHUNK_OVERLAP))
        return chunk_size, chunk_overlap
    except (ValueError, TypeError) as e:
        logger.warning(f"Erreur lors de la récupération des paramètres de chunking: {e}, utilisation des valeurs par défaut", exc_info=True)
        return CHUNK_SIZE, CHUNK_OVERLAP

def clean_text(text: str) -> str:
    """
    Nettoie le texte brut en normalisant les espaces et en supprimant les caractères inutiles.

    Args:
        text: Texte brut à nettoyer

    Returns:
        Texte nettoyé
    """
    if not text:
        return ""

    # Supprimer les balises HTML résiduelles
    text = re.sub(r'<[^>]+>', '', text)

    # Normaliser les espaces multiples
    text = re.sub(r'\s+', ' ', text)

    # Supprimer les lignes répétitives (headers/footers potentiels)
    lines = text.split('\n')
    cleaned_lines = []
    previous_line = None

    for line in lines:
        line = line.strip()
        # Ne pas répéter la même ligne plus de 2 fois consécutivement
        if line != previous_line or len(cleaned_lines) == 0:
            if line:  # Ignorer les lignes vides
                cleaned_lines.append(line)
            previous_line = line
        else:
            previous_line = line

    text = '\n'.join(cleaned_lines)

    # Nettoyer les espaces en début et fin
    text = text.strip()

    logger.debug(f"Texte nettoyé: {len(text)} caractères")
    return text

def split_into_chunks(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None
) -> List[str]:
    """
    Découpe le texte en chunks de taille appropriée pour le RAG.

    Args:
        text: Texte à découper
        chunk_size: Taille maximale d'un chunk (si None, utilise les paramètres d'environnement)
        chunk_overlap: Chevauchement entre les chunks (si None, utilise les paramètres d'environnement)

    Returns:
        Liste de chunks de texte
    """
    if not text or not text.strip():
        logger.warning("Tentative de découpage d'un texte vide")
        return []

    # Récupérer les paramètres dynamiques si non fournis
    if chunk_size is None or chunk_overlap is None:
        dynamic_chunk_size, dynamic_chunk_overlap = get_chunk_params()
        chunk_size = chunk_size or dynamic_chunk_size
        chunk_overlap = chunk_overlap or dynamic_chunk_overlap

    # Utiliser RecursiveCharacterTextSplitter de LangChain
    # Il essaie de découper sur des séparateurs naturels (paragraphes, phrases)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=[
            "\n\n",  # Paragraphes
            "\n",    # Lignes
            ". ",    # Phrases
            ", ",    # Clauses
            " ",     # Mots
            ""       # Caractères
        ],
        keep_separator=True
    )

    chunks = text_splitter.split_text(text)

    logger.info(f"Texte découpé en {len(chunks)} chunks (taille: {chunk_size}, overlap: {chunk_overlap})")

    # Filtrer les chunks trop petits (moins de 50 caractères)
    chunks = [chunk.strip() for chunk in chunks if len(chunk.strip()) > 50]

    logger.info(f"{len(chunks)} chunks conservés après filtrage")

    return chunks

def get_chunk_statistics(chunks: List[str]) -> dict:
    """
    Calcule des statistiques sur les chunks créés.

    Args:
        chunks: Liste de chunks

    Returns:
        Dictionnaire avec les statistiques
    """
    if not chunks:
        return {
            "count": 0,
            "avg_length": 0,
            "min_length": 0,
            "max_length": 0
        }

    lengths = [len(chunk) for chunk in chunks]

    return {
        "count": len(chunks),
        "avg_length": sum(lengths) / len(lengths),
        "min_length": min(lengths),
        "max_length": max(lengths)
    }
