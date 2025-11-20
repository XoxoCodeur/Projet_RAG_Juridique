"""
Page Streamlit du chatbot RAG.
Interface de conversation avec le système RAG.
"""

import streamlit as st
import logging
import json
from datetime import datetime

from rag.config import validate_config
from rag.rag_chain import answer_question_with_rag
from rag.vectorstore import get_vectorstore_stats
from rag.conversation_manager import (
    get_all_conversations,
    save_conversation,
    load_conversation,
    delete_conversation,
    rename_conversation,
    create_new_conversation
)

logger = logging.getLogger(__name__)

# Configuration de la page
st.set_page_config(
    page_title="Chatbot Juridique",
    page_icon="⚖️",
    layout="wide"
)

def init_session_state():
    """Initialise les variables de session."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = create_new_conversation()

    if "conversation_title" not in st.session_state:
        st.session_state.conversation_title = "Nouvelle conversation"

def export_conversation():
    """Permet d'exporter la conversation actuelle en TXT, JSON ou Markdown."""

    # Bouton avec menu déroulant pour choisir le format
    with st.popover("📥 Exporter", use_container_width=True):
        st.markdown("**Choisir le format d'export**")

        export_format = st.radio(
            "Format",
            ["TXT", "JSON", "Markdown"],
            label_visibility="collapsed"
        )

        if st.button("Télécharger", type="primary", use_container_width=True):
            try:
                if export_format == "TXT":
                    content = export_to_txt()
                    filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    mime_type = "text/plain"
                elif export_format == "JSON":
                    content = export_to_json()
                    filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    mime_type = "application/json"
                else:  # Markdown
                    content = export_to_markdown()
                    filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                    mime_type = "text/markdown"

                st.download_button(
                    label=f"💾 Télécharger {export_format}",
                    data=content,
                    file_name=filename,
                    mime=mime_type,
                    use_container_width=True
                )

            except Exception as e:
                logger.error(f"Erreur lors de l'export: {e}", exc_info=True)
                st.error(f"Erreur lors de l'export: {str(e)}")

def export_to_txt() -> str:
    """Exporte la conversation au format TXT."""
    output = []
    output.append("=" * 80)
    output.append(f"CONVERSATION: {st.session_state.conversation_title}")
    output.append(f"DATE: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    output.append("=" * 80)
    output.append("")

    for msg in st.session_state.messages:
        role = "UTILISATEUR" if msg["role"] == "user" else "ASSISTANT"
        output.append(f"[{role}]")
        output.append(msg["content"])
        output.append("")
        output.append("-" * 80)
        output.append("")

    return "\n".join(output)

def export_to_json() -> str:
    """Exporte la conversation au format JSON."""
    export_data = {
        "title": st.session_state.conversation_title,
        "conversation_id": st.session_state.conversation_id,
        "export_date": datetime.now().isoformat(),
        "messages": [
            {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg.get("timestamp", datetime.now().isoformat())
            }
            for msg in st.session_state.messages
        ]
    }
    return json.dumps(export_data, ensure_ascii=False, indent=2)

def export_to_markdown() -> str:
    """Exporte la conversation au format Markdown."""
    output = []
    output.append(f"# {st.session_state.conversation_title}")
    output.append("")
    output.append(f"**Date d'export:** {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    output.append("")
    output.append("---")
    output.append("")

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            output.append(f"### 👤 Utilisateur")
        else:
            output.append(f"### 🤖 Assistant")
        output.append("")
        output.append(msg["content"])
        output.append("")
        output.append("---")
        output.append("")

    return "\n".join(output)

def export_specific_conversation(conversation_id: str, conversation_title: str):
    """Exporte une conversation spécifique (depuis le menu)."""
    # Charger la conversation
    conv_data = load_conversation(conversation_id)
    if not conv_data or not conv_data.get('messages'):
        st.error("Impossible d'exporter cette conversation")
        return

    with st.popover("📥 Exporter", use_container_width=True):
        st.markdown("**Choisir le format d'export**")

        export_format = st.radio(
            "Format",
            ["TXT", "JSON", "Markdown"],
            label_visibility="collapsed",
            key=f"export_format_{conversation_id}"
        )

        if st.button("Télécharger", type="primary", use_container_width=True, key=f"download_{conversation_id}"):
            try:
                if export_format == "TXT":
                    content = format_conversation_txt(conversation_title, conv_data['messages'])
                    filename = f"conversation_{conversation_id}.txt"
                    mime_type = "text/plain"
                elif export_format == "JSON":
                    content = format_conversation_json(conversation_id, conversation_title, conv_data['messages'])
                    filename = f"conversation_{conversation_id}.json"
                    mime_type = "application/json"
                else:  # Markdown
                    content = format_conversation_markdown(conversation_title, conv_data['messages'])
                    filename = f"conversation_{conversation_id}.md"
                    mime_type = "text/markdown"

                st.download_button(
                    label=f"💾 Télécharger {export_format}",
                    data=content,
                    file_name=filename,
                    mime=mime_type,
                    use_container_width=True,
                    key=f"dl_btn_{conversation_id}"
                )

            except Exception as e:
                logger.error(f"Erreur lors de l'export: {e}", exc_info=True)
                st.error(f"Erreur lors de l'export: {str(e)}")

def format_conversation_txt(title: str, messages: list) -> str:
    """Formate une conversation au format TXT."""
    output = []
    output.append("=" * 80)
    output.append(f"CONVERSATION: {title}")
    output.append(f"DATE: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    output.append("=" * 80)
    output.append("")

    for msg in messages:
        role = "UTILISATEUR" if msg["role"] == "user" else "ASSISTANT"
        output.append(f"[{role}]")
        output.append(msg["content"])
        output.append("")
        output.append("-" * 80)
        output.append("")

    return "\n".join(output)

def format_conversation_json(conv_id: str, title: str, messages: list) -> str:
    """Formate une conversation au format JSON."""
    export_data = {
        "title": title,
        "conversation_id": conv_id,
        "export_date": datetime.now().isoformat(),
        "messages": [
            {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg.get("timestamp", datetime.now().isoformat())
            }
            for msg in messages
        ]
    }
    return json.dumps(export_data, ensure_ascii=False, indent=2)

def format_conversation_markdown(title: str, messages: list) -> str:
    """Formate une conversation au format Markdown."""
    output = []
    output.append(f"# {title}")
    output.append("")
    output.append(f"**Date d'export:** {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    output.append("")
    output.append("---")
    output.append("")

    for msg in messages:
        if msg["role"] == "user":
            output.append(f"### 👤 Utilisateur")
        else:
            output.append(f"### 🤖 Assistant")
        output.append("")
        output.append(msg["content"])
        output.append("")
        output.append("---")
        output.append("")

    return "\n".join(output)

def display_conversations_sidebar():
    """Affiche la sidebar avec la gestion des conversations (style ChatGPT)."""
    with st.sidebar:
        # Bouton pour créer une nouvelle conversation (style ChatGPT)
        if st.button("✚ Nouvelle discussion", use_container_width=True, type="primary"):
            # Sauvegarder la conversation actuelle si elle contient des messages
            if st.session_state.messages:
                save_conversation(
                    st.session_state.conversation_id,
                    st.session_state.messages,
                    st.session_state.conversation_title
                )

            # Créer une nouvelle conversation
            st.session_state.conversation_id = create_new_conversation()
            st.session_state.conversation_title = "Nouvelle conversation"
            st.session_state.messages = []
            st.session_state.processing = False
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # Champ de recherche pour filtrer les conversations
        # La recherche se met à jour dès qu'on tape (chaque caractère déclenche un rerun)
        search_query = st.text_input(
            "🔍 Rechercher",
            placeholder="Rechercher une conversation...",
            label_visibility="collapsed",
            key="search_input"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Lister toutes les conversations
        conversations = get_all_conversations()

        # Filtrer les conversations selon la recherche
        if search_query:
            search_lower = search_query.lower()
            conversations = [
                conv for conv in conversations
                if search_lower in conv['title'].lower()
            ]

        if conversations:
            # Grouper par date (Aujourd'hui, Hier, 7 derniers jours, etc.)
            from datetime import datetime, timedelta
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            last_7_days = today - timedelta(days=7)
            last_30_days = today - timedelta(days=30)

            groups = {
                "Aujourd'hui": [],
                "Hier": [],
                "7 derniers jours": [],
                "30 derniers jours": [],
                "Plus ancien": []
            }

            for conv in conversations:
                try:
                    conv_date = datetime.fromisoformat(conv['updated_at']).date()

                    if conv_date == today:
                        groups["Aujourd'hui"].append(conv)
                    elif conv_date == yesterday:
                        groups["Hier"].append(conv)
                    elif conv_date > last_7_days:
                        groups["7 derniers jours"].append(conv)
                    elif conv_date > last_30_days:
                        groups["30 derniers jours"].append(conv)
                    else:
                        groups["Plus ancien"].append(conv)
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(f"Erreur lors du parsing de la date pour la conversation {conv.get('id', 'unknown')}: {e}", exc_info=True)
                    groups["Plus ancien"].append(conv)

            # Afficher chaque groupe
            for group_name, group_convs in groups.items():
                if not group_convs:
                    continue

                # Titre du groupe (style ChatGPT)
                st.markdown(f"<p style='font-size: 11px; color: #888; margin: 16px 0 8px 8px; font-weight: 600;'>{group_name.upper()}</p>", unsafe_allow_html=True)

                for conv in group_convs:
                    is_current = conv['id'] == st.session_state.conversation_id

                    # Vérifier si on est en mode édition pour cette conversation
                    edit_key = f"edit_{conv['id']}"
                    menu_key = f"menu_{conv['id']}"
                    is_editing = st.session_state.get(edit_key, False)
                    show_menu = st.session_state.get(menu_key, False)

                    if is_editing:
                        # Mode édition: afficher un champ texte pour renommer
                        cols = st.columns([4.5, 0.75, 0.75])

                        with cols[0]:
                            new_title = st.text_input(
                                "Nouveau titre",
                                value=conv['title'],
                                key=f"input_{conv['id']}",
                                label_visibility="collapsed"
                            )

                        with cols[1]:
                            if st.button("✓", key=f"save_{conv['id']}", help="Sauvegarder", use_container_width=True):
                                if new_title.strip():
                                    rename_conversation(conv['id'], new_title.strip())
                                    # Si c'est la conversation actuelle, mettre à jour le titre en session
                                    if is_current:
                                        st.session_state.conversation_title = new_title.strip()
                                    st.session_state[edit_key] = False
                                    st.rerun()

                        with cols[2]:
                            if st.button("✗", key=f"cancel_{conv['id']}", help="Annuler", use_container_width=True):
                                st.session_state[edit_key] = False
                                st.rerun()
                    else:
                        # Mode normal: afficher le titre avec menu 3 points
                        # Container avec hover pour le menu
                        conv_container = st.container()

                        with conv_container:
                            cols = st.columns([5.5, 0.5])

                            with cols[0]:
                                # Bouton de conversation
                                if st.button(
                                    f"💬 {conv['title']}",
                                    key=f"conv_{conv['id']}",
                                    use_container_width=True,
                                    type="primary" if is_current else "secondary",
                                    disabled=is_current
                                ):
                                    # Sauvegarder la conversation actuelle avant de changer
                                    if st.session_state.messages:
                                        save_conversation(
                                            st.session_state.conversation_id,
                                            st.session_state.messages,
                                            st.session_state.conversation_title
                                        )

                                    # Charger la nouvelle conversation
                                    loaded_conv = load_conversation(conv['id'])
                                    if loaded_conv:
                                        st.session_state.conversation_id = loaded_conv['id']
                                        st.session_state.conversation_title = loaded_conv['title']
                                        st.session_state.messages = loaded_conv['messages']
                                        st.session_state.processing = False
                                        st.rerun()

                            with cols[1]:
                                # Bouton menu 3 points
                                if st.button("⋮", key=f"menu_btn_{conv['id']}", help="Options", use_container_width=True):
                                    st.session_state[menu_key] = not show_menu
                                    st.rerun()

                        # Afficher le menu déroulant si activé (en dehors du container principal)
                        if show_menu:
                            st.markdown("<div style='margin-left: 8px; margin-top: -4px; margin-bottom: 4px;'>", unsafe_allow_html=True)

                            # Option Renommer
                            if st.button("✏️ Renommer", key=f"menu_rename_{conv['id']}", use_container_width=True):
                                st.session_state[menu_key] = False
                                st.session_state[edit_key] = True
                                st.rerun()

                            # Option Exporter
                            export_key = f"export_{conv['id']}"
                            show_export = st.session_state.get(export_key, False)

                            if st.button("📥 Exporter", key=f"menu_export_{conv['id']}", use_container_width=True):
                                st.session_state[export_key] = not show_export
                                st.session_state[menu_key] = False
                                st.rerun()

                            # Option Supprimer
                            if st.button("🗑️ Supprimer", key=f"menu_delete_{conv['id']}", use_container_width=True):
                                st.session_state[menu_key] = False
                                if delete_conversation(conv['id']):
                                    # Si on supprime la conversation active, créer une nouvelle
                                    if is_current:
                                        st.session_state.conversation_id = create_new_conversation()
                                        st.session_state.messages = []
                                        st.session_state.conversation_title = "Nouvelle conversation"
                                    st.rerun()

                            st.markdown("</div>", unsafe_allow_html=True)

                        # Afficher le sous-menu d'export si activé
                        export_key = f"export_{conv['id']}"
                        if st.session_state.get(export_key, False):
                            conv_data = load_conversation(conv['id'])
                            if conv_data and conv_data.get('messages'):
                                st.markdown("<div style='margin-left: 16px; margin-top: 4px; margin-bottom: 8px;'>", unsafe_allow_html=True)

                                # Bouton pour fermer
                                col_close1, col_close2 = st.columns([5, 1])
                                with col_close2:
                                    if st.button("✕", key=f"close_export_{conv['id']}", help="Fermer"):
                                        st.session_state[export_key] = False
                                        st.rerun()

                                export_format = st.radio(
                                    "Format d'export",
                                    ["TXT", "JSON", "Markdown"],
                                    key=f"export_format_{conv['id']}",
                                    horizontal=True
                                )

                                # Générer le contenu selon le format
                                if export_format == "TXT":
                                    content = format_conversation_txt(conv['title'], conv_data['messages'])
                                    filename = f"conversation_{conv['id']}.txt"
                                    mime_type = "text/plain"
                                elif export_format == "JSON":
                                    content = format_conversation_json(conv['id'], conv['title'], conv_data['messages'])
                                    filename = f"conversation_{conv['id']}.json"
                                    mime_type = "application/json"
                                else:  # Markdown
                                    content = format_conversation_markdown(conv['title'], conv_data['messages'])
                                    filename = f"conversation_{conv['id']}.md"
                                    mime_type = "text/markdown"

                                st.download_button(
                                    label=f"💾 Télécharger {export_format}",
                                    data=content,
                                    file_name=filename,
                                    mime=mime_type,
                                    use_container_width=True,
                                    key=f"dl_btn_{conv['id']}"
                                )

                                st.markdown("</div>", unsafe_allow_html=True)
        else:
            # Message différent selon si c'est un résultat de recherche vide ou aucune conversation
            if search_query:
                st.markdown("<p style='text-align: center; color: #888; margin-top: 40px;'>🔍 Aucune conversation trouvée</p>", unsafe_allow_html=True)
            else:
                st.markdown("<p style='text-align: center; color: #888; margin-top: 40px;'>Aucune conversation</p>", unsafe_allow_html=True)

def display_header():
    """Affiche l'en-tête de la page."""

    # CSS personnalisé pour le chatbot
    st.markdown("""
        <style>
        /* Header épuré */
        .chat-intro {
            padding: 1rem 0;
            margin-bottom: 1.5rem;
        }

        /* Metrics container */
        .metrics-container {
            background: rgba(255, 255, 255, 0.02);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 1rem;
        }

        /* Amélioration des metrics */
        [data-testid="stMetricValue"] {
            font-size: 1.8rem;
            font-weight: 700;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.9rem;
            font-weight: 500;
        }

        /* Messages du chat plus lisibles */
        .stChatMessage {
            border-radius: 12px;
            padding: 1rem;
            margin: 0.5rem 0;
        }

        /* Input du chat moderne */
        .stChatInputContainer {
            border-radius: 12px;
        }

        /* Expander des sources */
        .streamlit-expanderHeader {
            border-radius: 8px;
            font-weight: 600;
        }

        /* Export button dans header */
        .export-section {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header principal épuré
    st.title("💬 Assistant Juridique")
    st.markdown("Posez vos questions en langage naturel, l'assistant répondra en s'appuyant sur vos documents.")
    st.divider()
    
    # Afficher les statistiques et options d'export
    try:
        stats = get_vectorstore_stats()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("📄 Documents", stats.get("total_files", 0), help="Nombre de documents indexés dans la base")

        with col2:
            st.metric("📦 Chunks", stats.get("total_chunks", 0), help="Nombre de segments de texte indexés")

        with col3:
            if st.session_state.messages:
                # Si la conversation a des messages, afficher l'export
                export_conversation()
            else:
                # Sinon afficher le titre de la conversation
                conv_title = st.session_state.conversation_title[:20] + "..." if len(st.session_state.conversation_title) > 20 else st.session_state.conversation_title
                st.metric("💬 Discussion", conv_title, help="Conversation active")

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des stats: {e}", exc_info=True)
        st.warning("⚠️ Impossible de récupérer les statistiques")

    st.divider()
    st.space()

def check_documents_indexed() -> bool:
    """
    Vérifie si des documents sont indexés.

    Returns:
        True si des documents sont présents
    """
    try:
        stats = get_vectorstore_stats()
        return stats.get("total_chunks", 0) > 0
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des documents indexés: {e}", exc_info=True)
        return False

def display_chat_history():
    """Affiche l'historique des messages."""
    import re

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Afficher les sources si disponibles
            if message["role"] == "assistant" and "sources" in message and message["sources"]:
                # Vérifier si on a les docs complets (session en cours) ou le contenu sauvegardé (conversation chargée)
                if "used_docs" in message and message["used_docs"]:
                    # Session en cours - on a les objets Document de LangChain
                    used_docs = message["used_docs"]

                    with st.expander("📄 Sources utilisées"):
                        # Grouper les chunks par document source
                        sources_by_file = {}
                        for doc in used_docs:
                            source_file = doc.metadata.get('source', 'inconnu')
                            chunk_id = doc.metadata.get('chunk_id', '?')

                            if source_file not in sources_by_file:
                                sources_by_file[source_file] = []

                            sources_by_file[source_file].append({
                                'chunk_id': chunk_id,
                                'content': doc.page_content
                            })

                        # Afficher par fichier
                        for source_file, chunks in sources_by_file.items():
                            # Nettoyer le nom du fichier (retirer timestamp)
                            clean_filename = re.sub(r'^\d{8}_\d{6}_', '', source_file)

                            st.markdown(f"**📄 {clean_filename}**")

                            # Afficher chaque chunk avec son contenu
                            for chunk_info in chunks:
                                chunk_id = chunk_info['chunk_id']
                                content = chunk_info['content']

                                # Tronquer le contenu pour l'aperçu
                                preview = content[:150] + "..." if len(content) > 150 else content

                                # Utiliser un expander pour chaque chunk
                                with st.expander(f"Extrait {chunk_id + 1} - {preview}"):
                                    st.text(content)

                            st.divider()

                elif "used_docs_content" in message and message["used_docs_content"]:
                    # Conversation chargée - on a le contenu sauvegardé en JSON
                    used_docs_content = message["used_docs_content"]

                    with st.expander("📄 Sources utilisées"):
                        # Grouper les chunks par document source
                        sources_by_file = {}
                        for doc_data in used_docs_content:
                            source_file = doc_data['metadata'].get('source', 'inconnu')
                            chunk_id = doc_data['metadata'].get('chunk_id', 0)

                            if source_file not in sources_by_file:
                                sources_by_file[source_file] = []

                            sources_by_file[source_file].append({
                                'chunk_id': chunk_id,
                                'content': doc_data['page_content']
                            })

                        # Afficher par fichier
                        for source_file, chunks in sources_by_file.items():
                            # Nettoyer le nom du fichier (retirer timestamp)
                            clean_filename = re.sub(r'^\d{8}_\d{6}_', '', source_file)

                            st.markdown(f"**📄 {clean_filename}**")

                            # Afficher chaque chunk avec son contenu
                            for chunk_info in chunks:
                                chunk_id = chunk_info['chunk_id']
                                content = chunk_info['content']

                                # Tronquer le contenu pour l'aperçu
                                preview = content[:150] + "..." if len(content) > 150 else content

                                # Utiliser un expander pour chaque chunk
                                with st.expander(f"Extrait {chunk_id + 1} - {preview}"):
                                    st.text(content)

                            st.divider()

                else:
                    # Affichage simple si pas de contenu (anciennes conversations)
                    with st.expander("📄 Sources utilisées"):
                        for i, source in enumerate(message["sources"], 1):
                            st.text(f"{i}. {source}")

def handle_user_input():
    """Gère la saisie utilisateur et génère une réponse."""
    if prompt := st.chat_input("Posez votre question juridique..."):
        # Ajouter le message utilisateur à l'historique d'abord
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        # Marquer qu'on est en train de traiter une nouvelle question
        st.session_state.processing = True
        st.rerun()

    # Si on est en mode processing, générer la réponse
    if st.session_state.get('processing', False):
        # Récupérer la dernière question utilisateur
        user_messages = [msg for msg in st.session_state.messages if msg["role"] == "user"]
        if user_messages:
            last_prompt = user_messages[-1]["content"]

            # Générer la réponse
            with st.spinner("Recherche dans les documents..."):
                try:
                    # Appeler le système RAG avec l'historique de conversation
                    answer, used_docs = answer_question_with_rag(
                        query=last_prompt,
                        conversation_history=st.session_state.messages,
                        verbose=True
                    )

                    # Préparer les sources pour l'historique (format simple)
                    import re
                    sources = []
                    for doc in used_docs:
                        source_file = doc.metadata.get('source', 'inconnu')
                        clean_name = re.sub(r'^\d{8}_\d{6}_', '', source_file)
                        chunk_id = doc.metadata.get('chunk_id', '?')
                        sources.append(f"{clean_name} (extrait {chunk_id + 1})")

                    # Ajouter à l'historique
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "used_docs": used_docs  # Garder les docs pour l'affichage détaillé
                    })

                    # Sauvegarder la conversation après chaque message
                    save_conversation(
                        st.session_state.conversation_id,
                        st.session_state.messages,
                        st.session_state.conversation_title
                    )

                    # Générer un titre si c'est le premier échange
                    if len(st.session_state.messages) == 2:  # 1 user + 1 assistant
                        from rag.conversation_manager import generate_conversation_title
                        st.session_state.conversation_title = generate_conversation_title(st.session_state.messages)
                        save_conversation(
                            st.session_state.conversation_id,
                            st.session_state.messages,
                            st.session_state.conversation_title
                        )

                    # Arrêter le mode processing
                    st.session_state.processing = False
                    st.rerun()

                except Exception as e:
                    error_message = f"Erreur lors du traitement de la requête: {str(e)}"
                    st.error(error_message)
                    logger.error(error_message, exc_info=True)

                    # Ajouter le message d'erreur à l'historique
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "Désolé, une erreur s'est produite. Veuillez réessayer ou contacter l'administrateur.",
                        "sources": []
                    })

                    # Arrêter le mode processing
                    st.session_state.processing = False
                    st.rerun()

def main():
    """Fonction principale de la page."""
    try:
        # Valider la configuration
        validate_config()

        # Initialiser la session
        init_session_state()

        # Afficher la sidebar avec les conversations
        display_conversations_sidebar()

        # Afficher l'en-tête
        display_header()

        # Vérifier si des documents sont indexés
        if not check_documents_indexed():
            st.warning("""
            ⚠️ Aucun document n'est encore indexé.

            Pour commencer à utiliser le chatbot, veuillez :
            1. Aller sur la page **Gestion des documents**
            2. Uploader vos documents (.txt, .csv, .html)
            3. Les documents seront automatiquement indexés
            """)
            st.stop()

        # Afficher l'historique
        display_chat_history()

        # Gérer l'input utilisateur
        handle_user_input()

    except ValueError as e:
        st.error(str(e))
        st.info("Veuillez configurer votre fichier .env avec les variables nécessaires.")
    except Exception as e:
        st.error(f"Erreur inattendue: {str(e)}")
        logger.error(f"Erreur inattendue: {e}", exc_info=True)

if __name__ == "__main__":
    main()
