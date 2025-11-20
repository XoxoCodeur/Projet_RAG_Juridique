"""
Module de parsing des requêtes utilisateur.
Extraction de filtres et d'informations de la requête pour améliorer le retrieval.
"""

import re
import logging
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)

# Types de documents reconnus (doit correspondre aux types dans metadata.py)
DOC_TYPES = {
    "contrat": ["contrat", "accord", "convention"],
    "note": ["note", "note interne", "mémo", "memorandum"],
    "jurisprudence": ["jurisprudence", "arrêt", "jugement", "décision"],
    "litige": ["litige", "contentieux", "procédure", "mise en demeure"],
    "facture": ["facture", "devis", "honoraire"],
    "consultation": ["consultation", "avis juridique", "conseil"],
    "correspondance": ["courrier", "lettre", "email"]
}

# Patterns pour extraire les noms de personnes dans les requêtes
QUERY_PERSON_PATTERNS = [
    r"(?:contrat|accord|document|note|facture|courrier).*?(?:de|concernant|pour|avec)\s+([A-ZÉÈÊË][a-zéèêëàâôûç]+(?:\s+[A-ZÉÈÊË][a-zéèêëàâôûç]+)*)",
    r"(?:M\.|Monsieur|Mme|Madame)\s+([A-ZÉÈÊË][a-zéèêëàâôûç]+(?:\s+[A-ZÉÈÊË][a-zéèêëàâôûç]+)*)",
    r"(?:client|partie|personne)\s+([A-ZÉÈÊË][a-zéèêëàâôûç]+(?:\s+[A-ZÉÈÊË][a-zéèêëàâôûç]+)*)",
]

def detect_doc_type_from_query(query: str) -> Optional[str]:
    """
    Détecte le type de document recherché depuis la requête.

    Args:
        query: Requête utilisateur

    Returns:
        Type de document ou None
    """
    query_lower = query.lower()

    for doc_type, keywords in DOC_TYPES.items():
        for keyword in keywords:
            if keyword in query_lower:
                logger.debug(f"Type de document détecté: {doc_type} (mot-clé: '{keyword}')")
                return doc_type

    return None

def extract_person_from_query(query: str) -> Optional[str]:
    """
    Tente d'extraire un nom de personne depuis la requête.

    Args:
        query: Requête utilisateur

    Returns:
        Nom de la personne ou None
    """
    for pattern in QUERY_PERSON_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            person_name = match.group(1).strip()
            # Normaliser en Title Case
            person_name = person_name.title()
            logger.debug(f"Nom de personne extrait: {person_name}")
            return person_name

    # Essayer un pattern plus simple : chercher des mots en majuscule
    # Pattern: 2 ou 3 mots consécutifs commençant par une majuscule
    simple_pattern = r"\b([A-ZÉÈÊË][a-zéèêëàâôûç]+(?:\s+[A-ZÉÈÊË][a-zéèêëàâôûç]+){1,2})\b"
    matches = re.findall(simple_pattern, query)

    if matches:
        # Filtrer les mots communs qui ne sont pas des noms
        common_words = ["Monsieur", "Madame", "Client", "Contrat", "Document", "Note"]
        for match in matches:
            if match not in common_words and len(match) > 3:
                logger.debug(f"Nom de personne extrait (pattern simple): {match}")
                return match

    return None

def parse_user_query(query: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Parse la requête utilisateur pour extraire la question et les filtres.

    Args:
        query: Requête utilisateur brute

    Returns:
        Tuple (question_clean, personne, type_doc)
        - question_clean: La question (identique à la requête pour le moment)
        - personne: Nom de la personne détectée ou None
        - type_doc: Type de document détecté ou None
    """
    logger.info(f"Parsing de la requête: {query}")

    # 1. Détecter le type de document
    type_doc = detect_doc_type_from_query(query)

    # 2. Extraire le nom de la personne
    personne = extract_person_from_query(query)

    # 3. La question reste la requête originale
    question_clean = query.strip()

    logger.info(f"Résultat du parsing - Personne: {personne}, Type: {type_doc}")

    return question_clean, personne, type_doc

def build_search_filters(personne: Optional[str] = None, type_doc: Optional[str] = None) -> Optional[Dict]:
    """
    Construit un dictionnaire de filtres pour le retrieval.
    Utilise la syntaxe ChromaDB avec opérateurs $and, $or, etc.

    Args:
        personne: Nom de la personne (optionnel)
        type_doc: Type de document (optionnel)

    Returns:
        Dictionnaire de filtres pour ChromaDB ou None si aucun filtre
    """
    conditions = []

    if personne:
        conditions.append({"personne": {"$eq": personne}})
        logger.debug(f"Filtre ajouté - personne: {personne}")

    if type_doc:
        conditions.append({"type_doc": {"$eq": type_doc}})
        logger.debug(f"Filtre ajouté - type_doc: {type_doc}")

    if not conditions:
        logger.debug("Aucun filtre appliqué")
        return None
    elif len(conditions) == 1:
        # Un seul filtre, pas besoin de $and
        logger.info(f"Filtres de recherche: {conditions[0]}")
        return conditions[0]
    else:
        # Plusieurs filtres, utiliser $and
        filters = {"$and": conditions}
        logger.info(f"Filtres de recherche: {filters}")
        return filters

def should_apply_filters(personne: Optional[str], type_doc: Optional[str]) -> bool:
    """
    Détermine si des filtres doivent être appliqués.

    Args:
        personne: Nom de la personne
        type_doc: Type de document

    Returns:
        True si au moins un filtre est présent
    """
    return personne is not None or type_doc is not None
