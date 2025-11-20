"""
Module de gestion des conversations.
Permet de sauvegarder, charger, lister et gérer les conversations du chatbot.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI

from rag.config import CONVERSATIONS_DIR, OPENAI_API_KEY

logger = logging.getLogger(__name__)


def get_all_conversations() -> List[Dict]:
    """
    Récupère toutes les conversations sauvegardées.

    Returns:
        Liste de dictionnaires avec id, title, created_at, updated_at
    """
    conversations = []

    if not CONVERSATIONS_DIR.exists():
        return conversations

    for conv_file in CONVERSATIONS_DIR.glob("*.json"):
        try:
            with open(conv_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                conversations.append({
                    'id': conv_file.stem,
                    'title': data.get('title', 'Sans titre'),
                    'created_at': data.get('created_at', ''),
                    'updated_at': data.get('updated_at', ''),
                    'message_count': len(data.get('messages', []))
                })
        except Exception as e:
            logger.error(f"Erreur lors de la lecture de {conv_file}: {e}")

    # Trier par date de modification (plus récent en premier)
    conversations.sort(key=lambda x: x['updated_at'], reverse=True)

    return conversations


def save_conversation(conversation_id: str, messages: List[Dict], title: Optional[str] = None) -> bool:
    """
    Sauvegarde une conversation.

    Args:
        conversation_id: ID unique de la conversation
        messages: Liste des messages de la conversation
        title: Titre de la conversation (généré automatiquement si None)

    Returns:
        True si sauvegarde réussie
    """
    try:
        conv_file = CONVERSATIONS_DIR / f"{conversation_id}.json"

        # Charger les données existantes si le fichier existe
        if conv_file.exists():
            with open(conv_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                created_at = data.get('created_at')
        else:
            created_at = datetime.now().isoformat()

        # Générer un titre si nécessaire
        if title is None:
            if conv_file.exists():
                with open(conv_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    title = data.get('title', 'Sans titre')
            else:
                # Générer un titre à partir du premier message utilisateur
                title = generate_conversation_title(messages)

        # Nettoyer les messages pour la sauvegarde
        clean_messages = []
        for msg in messages:
            clean_msg = {
                'role': msg['role'],
                'content': msg['content']
            }
            if 'sources' in msg:
                clean_msg['sources'] = msg['sources']

            # Sauvegarder le contenu des documents utilisés pour l'affichage ultérieur
            if 'used_docs' in msg and msg['used_docs']:
                clean_msg['used_docs_content'] = []
                for doc in msg['used_docs']:
                    clean_msg['used_docs_content'].append({
                        'page_content': doc.page_content,
                        'metadata': {
                            'source': doc.metadata.get('source', 'inconnu'),
                            'chunk_id': doc.metadata.get('chunk_id', 0)
                        }
                    })

            clean_messages.append(clean_msg)

        # Sauvegarder
        data = {
            'id': conversation_id,
            'title': title,
            'created_at': created_at,
            'updated_at': datetime.now().isoformat(),
            'messages': clean_messages
        }

        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Conversation {conversation_id} sauvegardée")
        return True

    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la conversation: {e}")
        return False


def load_conversation(conversation_id: str) -> Optional[Dict]:
    """
    Charge une conversation.

    Args:
        conversation_id: ID de la conversation à charger

    Returns:
        Dictionnaire avec title et messages, ou None si erreur
    """
    try:
        conv_file = CONVERSATIONS_DIR / f"{conversation_id}.json"

        if not conv_file.exists():
            logger.warning(f"Conversation {conversation_id} introuvable")
            return None

        with open(conv_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return {
            'id': data.get('id', conversation_id),
            'title': data.get('title', 'Sans titre'),
            'created_at': data.get('created_at', ''),
            'updated_at': data.get('updated_at', ''),
            'messages': data.get('messages', [])
        }

    except Exception as e:
        logger.error(f"Erreur lors du chargement de la conversation: {e}")
        return None


def delete_conversation(conversation_id: str) -> bool:
    """
    Supprime une conversation.

    Args:
        conversation_id: ID de la conversation à supprimer

    Returns:
        True si suppression réussie
    """
    try:
        conv_file = CONVERSATIONS_DIR / f"{conversation_id}.json"

        if conv_file.exists():
            conv_file.unlink()
            logger.info(f"Conversation {conversation_id} supprimée")
            return True
        else:
            logger.warning(f"Conversation {conversation_id} introuvable")
            return False

    except Exception as e:
        logger.error(f"Erreur lors de la suppression de la conversation: {e}")
        return False


def generate_conversation_title(messages: List[Dict]) -> str:
    """
    Génère automatiquement un titre TRÈS COURT pour la conversation (3-5 mots max).

    Args:
        messages: Liste des messages de la conversation

    Returns:
        Titre généré (court)
    """
    # Si pas de messages, titre par défaut
    if not messages:
        return "Nouvelle conversation"

    # Trouver le premier message utilisateur
    first_user_message = None
    for msg in messages:
        if msg['role'] == 'user':
            first_user_message = msg['content']
            break

    if not first_user_message:
        return "Nouvelle conversation"

    # Si le message est très court (moins de 30 caractères), l'utiliser tel quel
    if len(first_user_message) <= 30:
        return first_user_message

    # Sinon, utiliser un LLM pour générer un titre TRÈS court
    try:
        llm = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY,
            model="gpt-5-mini",
            temperature=0.0
        )

        prompt = f"""Génère un titre TRÈS COURT (3 à 5 mots MAXIMUM) pour résumer cette question:

Question: {first_user_message}

Règles:
- Maximum 5 mots
- Pas de guillemets
- Commence directement par les mots clés importants
- Style: substantifs + adjectifs principaux uniquement

Exemples:
- "Article 3 contrat Dupont"
- "Honoraires consultations supplémentaires"
- "Obligations client cabinet"

Titre:"""

        title = llm.invoke(prompt).content.strip()

        # Nettoyer le titre (retirer guillemets, points, etc.)
        title = title.strip('"').strip("'").strip('.').strip()

        # Limiter strictement la longueur (40 caractères max)
        if len(title) > 40:
            title = title[:37] + "..."

        return title

    except Exception as e:
        logger.error(f"Erreur lors de la génération du titre: {e}")
        # Fallback: tronquer le premier message de manière intelligente
        words = first_user_message.split()[:4]  # Prendre les 4 premiers mots
        return ' '.join(words) + "..."


def rename_conversation(conversation_id: str, new_title: str) -> bool:
    """
    Renomme une conversation.

    Args:
        conversation_id: ID de la conversation
        new_title: Nouveau titre

    Returns:
        True si renommage réussi
    """
    try:
        conv_file = CONVERSATIONS_DIR / f"{conversation_id}.json"

        if not conv_file.exists():
            logger.warning(f"Conversation {conversation_id} introuvable")
            return False

        with open(conv_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        data['title'] = new_title
        data['updated_at'] = datetime.now().isoformat()

        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Conversation {conversation_id} renommée en '{new_title}'")
        return True

    except Exception as e:
        logger.error(f"Erreur lors du renommage de la conversation: {e}")
        return False


def create_new_conversation() -> str:
    """
    Crée une nouvelle conversation avec un ID unique.

    Returns:
        ID de la nouvelle conversation
    """
    conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"Nouvelle conversation créée: {conversation_id}")
    return conversation_id
