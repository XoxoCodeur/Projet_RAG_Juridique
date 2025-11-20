"""
Module d'extraction de métadonnées à partir des documents.
Détection du type de document et extraction d'informations clés.
"""

import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Patterns pour détecter les types de documents
DOC_TYPE_PATTERNS = {
    "contrat": r"contrat|accord|convention|engagement",
    "note": r"note|mémo|memorandum",
    "jurisprudence": r"jurisprudence|arrêt|jugement|décision|cour",
    "litige": r"litige|contentieux|procédure|assignation|mise\s+en\s+demeure",
    "facture": r"facture|devis|honoraires",
    "consultation": r"consultation|avis\s+juridique|conseil",
    "correspondance": r"courrier|lettre|email|correspondance"
}

# Patterns pour extraire les noms de personnes
PERSON_PATTERNS = [
    r"Client\s*:\s*([A-ZÉÈÊË][a-zéèêëàâôûç]+(?:\s+[A-ZÉÈÊË][a-zéèêëàâôûç]+)*)",
    r"M\.\s+([A-ZÉÈÊË][a-zéèêëàâôûç]+(?:\s+[A-ZÉÈÊË][a-zéèêëàâôûç]+)*)",
    r"Mme\s+([A-ZÉÈÊË][a-zéèêëàâôûç]+(?:\s+[A-ZÉÈÊË][a-zéèêëàâôûç]+)*)",
    r"Monsieur\s+([A-ZÉÈÊË][a-zéèêëàâôûç]+(?:\s+[A-ZÉÈÊË][a-zéèêëàâôûç]+)*)",
    r"Madame\s+([A-ZÉÈÊË][a-zéèêëàâôûç]+(?:\s+[A-ZÉÈÊË][a-zéèêëàâôûç]+)*)",
    r"Entre\s*:\s*.*?([A-ZÉÈÊË][a-zéèêëàâôûç]+(?:\s+[A-ZÉÈÊË][a-zéèêëàâôûç]+)*)",
    r"(?:contrat|accord).*?(?:de|avec)\s+([A-ZÉÈÊË][a-zéèêëàâôûç]+(?:\s+[A-ZÉÈÊË][a-zéèêëàâôûç]+)*)",
]

def detect_doc_type(filename: str, text: str) -> str:
    """
    Détecte le type de document à partir du nom de fichier et du contenu.

    Args:
        filename: Nom du fichier
        text: Contenu du document

    Returns:
        Type de document détecté
    """
    filename_lower = filename.lower()
    text_lower = text.lower()

    # Vérifier d'abord le nom du fichier
    for doc_type, pattern in DOC_TYPE_PATTERNS.items():
        if re.search(pattern, filename_lower):
            logger.debug(f"Type de document détecté depuis le nom de fichier: {doc_type}")
            return doc_type

    # Ensuite vérifier le contenu (premiers 1000 caractères)
    text_sample = text_lower[:1000]
    for doc_type, pattern in DOC_TYPE_PATTERNS.items():
        if re.search(pattern, text_sample):
            logger.debug(f"Type de document détecté depuis le contenu: {doc_type}")
            return doc_type

    logger.debug("Type de document non identifié, utilisation de 'autre'")
    return "autre"

def extract_person_name(text: str, filename: str = "") -> Optional[str]:
    """
    Tente d'extraire le nom d'une personne depuis le texte ou le nom de fichier.

    Args:
        text: Contenu du document
        filename: Nom du fichier

    Returns:
        Nom de la personne ou None si non trouvé
    """
    # Mots-clés à ignorer dans les noms de fichiers
    skip_words = ["contrat", "note", "facture", "interne", "projet", "accord", "convention",
                  "courrier", "lettre", "email", "memo", "memorandum", "litige", "procedure",
                  "commercial", "partenaire", "partenariat", "impaye", "client", "clientz",
                  "droit", "societes", "societe", "fiscal", "fiscalite", "consultation",
                  "juridique", "jurisprudence", "historique", "contentieux", "demeure", "mise"]

    # D'abord essayer d'extraire depuis le nom de fichier
    # Pattern: contrat_jean_dupont.txt -> Jean Dupont
    # Extraire tous les mots du nom de fichier (sans extension, sans timestamp)
    filename_clean = filename.lower()
    # Retirer l'extension
    filename_clean = re.sub(r'\.(txt|csv|html|htm|pdf)$', '', filename_clean)
    # Retirer les timestamps (format: YYYYMMDD_HHMMSS)
    filename_clean = re.sub(r'\d{8}_\d{6}_?', '', filename_clean)

    # Extraire les mots (séparés par _, -, ou espaces)
    words = re.split(r'[_\-\s]+', filename_clean)

    # Filtrer les mots vides et les mots-clés à ignorer
    name_words = [w for w in words if w and w not in skip_words and len(w) >= 2]

    # Si on a au moins 2 mots, on considère que c'est un nom
    if len(name_words) >= 2:
        person_name = ' '.join([w.title() for w in name_words[:2]])
        logger.debug(f"Nom extrait du fichier: {person_name}")
        return person_name

    # Ensuite essayer d'extraire depuis le contenu
    # Limiter la recherche aux 2000 premiers caractères
    text_sample = text[:2000]

    for pattern in PERSON_PATTERNS:
        match = re.search(pattern, text_sample)
        if match:
            person_name = match.group(1).strip()
            # Vérifier que le nom fait au moins 3 caractères
            if len(person_name) >= 3:
                logger.debug(f"Nom extrait du contenu: {person_name}")
                return person_name

    logger.debug("Aucun nom de personne identifié")
    return None

def extract_metadata(filename: str, text: str, chunk_id: int = 0) -> Dict:
    """
    Extrait les métadonnées complètes d'un document.

    Args:
        filename: Nom du fichier source
        text: Contenu du document ou du chunk
        chunk_id: Identifiant du chunk (0 pour le document entier)

    Returns:
        Dictionnaire de métadonnées
    """
    logger.info(f"Extraction des métadonnées pour: {filename} (chunk {chunk_id})")

    metadata = {
        "source": filename,
        "chunk_id": chunk_id,
        "type_doc": detect_doc_type(filename, text),
        "personne": extract_person_name(text, filename),
        "length": len(text)
    }

    # Ajouter des métadonnées additionnelles si disponibles
    # Par exemple, détecter une date
    try:
        date_match = re.search(r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}", text[:500])
        if date_match:
            metadata["date_mention"] = date_match.group(0)
    except (re.error, TypeError) as e:
        logger.debug(f"Erreur lors de l'extraction de date: {e}")

    logger.debug(f"Métadonnées extraites: {metadata}")
    return metadata

def normalize_person_name(name: str) -> str:
    """
    Normalise un nom de personne pour la recherche.

    Args:
        name: Nom à normaliser

    Returns:
        Nom normalisé (Title Case, espaces nettoyés)
    """
    if not name:
        return ""

    # Retirer les espaces multiples
    name = re.sub(r'\s+', ' ', name).strip()

    # Mettre en Title Case
    name = name.title()

    return name
