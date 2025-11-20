"""
Module de chargement des documents.
Gestion de la lecture de différents types de fichiers : txt, csv, html.
"""

import logging
import pandas as pd
from bs4 import BeautifulSoup
from typing import BinaryIO
import io

logger = logging.getLogger(__name__)

class UnsupportedFileTypeError(Exception):
    """Exception levée lorsqu'un type de fichier n'est pas supporté."""
    pass

class EmptyFileError(Exception):
    """Exception levée lorsqu'un fichier est vide."""
    pass

def read_txt(file: BinaryIO) -> str:
    """
    Lit le contenu d'un fichier texte.

    Args:
        file: Fichier binaire uploadé

    Returns:
        Contenu du fichier sous forme de string

    Raises:
        EmptyFileError: Si le fichier est vide
    """
    try:
        content = file.read().decode('utf-8', errors='ignore')
        if not content.strip():
            raise EmptyFileError("Le fichier texte est vide")
        logger.info(f"Fichier TXT lu avec succès ({len(content)} caractères)")
        return content
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier TXT: {e}")
        raise

def read_csv(file: BinaryIO) -> str:
    """
    Lit un fichier CSV et le convertit en texte structuré.

    Args:
        file: Fichier binaire uploadé

    Returns:
        Contenu du CSV formaté en texte

    Raises:
        EmptyFileError: Si le CSV est vide
    """
    try:
        # Lire le CSV avec pandas
        df = pd.read_csv(file, encoding='utf-8', on_bad_lines='skip')

        if df.empty:
            raise EmptyFileError("Le fichier CSV est vide")

        # Convertir le DataFrame en texte structuré
        text_parts = []

        # Ajouter les noms de colonnes
        text_parts.append("Colonnes: " + ", ".join(df.columns))
        text_parts.append("\n" + "="*80 + "\n")

        # Convertir chaque ligne en texte
        for idx, row in df.iterrows():
            row_text = f"Ligne {idx + 1}:\n"
            for col in df.columns:
                value = row[col]
                if pd.notna(value):  # Ignorer les valeurs NaN
                    row_text += f"  - {col}: {value}\n"
            text_parts.append(row_text)

        content = "\n".join(text_parts)
        logger.info(f"Fichier CSV lu avec succès ({len(df)} lignes, {len(df.columns)} colonnes)")
        return content

    except pd.errors.EmptyDataError:
        raise EmptyFileError("Le fichier CSV est vide")
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier CSV: {e}")
        raise

def read_html(file: BinaryIO) -> str:
    """
    Lit un fichier HTML et extrait le texte.

    Args:
        file: Fichier binaire uploadé

    Returns:
        Texte extrait du HTML

    Raises:
        EmptyFileError: Si le HTML ne contient pas de texte
    """
    try:
        html_content = file.read().decode('utf-8', errors='ignore')

        # Parser le HTML avec BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Retirer les scripts et styles
        for script in soup(["script", "style"]):
            script.decompose()

        # Extraire le texte
        text = soup.get_text()

        # Nettoyer le texte
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        if not text.strip():
            raise EmptyFileError("Le fichier HTML ne contient pas de texte")

        logger.info(f"Fichier HTML lu avec succès ({len(text)} caractères)")
        return text

    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier HTML: {e}")
        raise

def read_file(uploaded_file) -> str:
    """
    Lit un fichier uploadé et retourne son contenu en fonction du type.

    Args:
        uploaded_file: Fichier uploadé via Streamlit

    Returns:
        Contenu du fichier sous forme de string

    Raises:
        UnsupportedFileTypeError: Si le type de fichier n'est pas supporté
        EmptyFileError: Si le fichier est vide
    """
    filename = uploaded_file.name
    file_extension = filename.split('.')[-1].lower()

    logger.info(f"Lecture du fichier: {filename} (type: {file_extension})")

    # Créer un objet file-like à partir des bytes
    file_bytes = io.BytesIO(uploaded_file.getvalue())

    try:
        if file_extension == 'txt':
            return read_txt(file_bytes)
        elif file_extension == 'csv':
            return read_csv(file_bytes)
        elif file_extension in ['html', 'htm']:
            return read_html(file_bytes)
        else:
            raise UnsupportedFileTypeError(
                f"Type de fichier non supporté: .{file_extension}. "
                f"Types supportés: txt, csv, html"
            )
    except (UnsupportedFileTypeError, EmptyFileError):
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la lecture de {filename}: {e}")
        raise Exception(f"Impossible de lire le fichier {filename}: {str(e)}")
