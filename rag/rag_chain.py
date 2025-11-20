"""
Module de la chaîne RAG complète.
Gestion du retrieval, du prompting et de la génération de réponses.
"""

import logging
from typing import List, Tuple, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from rag.config import OPENAI_API_KEY, MODEL_NAME, TEMPERATURE, RETRIEVAL_K
from rag.vectorstore import init_vectorstore
from rag.query_parser import parse_user_query, build_search_filters, should_apply_filters

logger = logging.getLogger(__name__)

def extract_used_sources(answer: str, all_docs: List[Document]) -> Tuple[str, List[Document]]:
    """
    Extrait les sources réellement utilisées par le LLM depuis sa réponse.
    Nettoie la réponse en retirant la ligne [Sources: ...].

    Args:
        answer: Réponse du LLM contenant potentiellement [Sources: 1, 3]
        all_docs: Tous les documents récupérés

    Returns:
        Tuple (réponse_nettoyée, documents_utilisés)
    """
    import re

    # Pattern pour extraire [Sources: 1, 3] ou [Sources: 1,3] etc.
    pattern = r'\[Sources?:\s*([\d,\s]+)\]'
    match = re.search(pattern, answer, re.IGNORECASE)

    if not match:
        # Pas de sources explicites, retourner tous les docs
        logger.debug("Aucune source explicite trouvée dans la réponse")
        return answer, all_docs

    # Extraire les numéros de documents
    source_numbers_str = match.group(1)
    source_numbers = [int(n.strip()) for n in source_numbers_str.split(',') if n.strip().isdigit()]

    logger.info(f"Sources utilisées par le LLM: {source_numbers}")

    # Filtrer les documents (indices commencent à 1 dans le prompt)
    used_docs = []
    for num in source_numbers:
        if 1 <= num <= len(all_docs):
            used_docs.append(all_docs[num - 1])  # -1 car les listes Python commencent à 0

    # Nettoyer la réponse en retirant la ligne [Sources: ...]
    clean_answer = re.sub(pattern, '', answer, flags=re.IGNORECASE).strip()

    return clean_answer, used_docs

def reformulate_query_with_history(
    current_query: str,
    conversation_history: List[Dict[str, str]],
    max_history: int = 3
) -> str:
    """
    Reformule la question actuelle en tenant compte de l'historique de conversation.
    Permet de gérer les questions de suivi et les références implicites.

    Args:
        current_query: La question actuelle de l'utilisateur
        conversation_history: Liste des messages précédents [{"role": "user/assistant", "content": "..."}]
        max_history: Nombre maximum de messages d'historique à considérer

    Returns:
        Question reformulée avec le contexte nécessaire
    """
    # Si pas d'historique ou historique vide, retourner la question telle quelle
    if not conversation_history or len(conversation_history) == 0:
        logger.info("Pas d'historique, question non reformulée")
        return current_query

    # Limiter l'historique aux N derniers messages
    recent_history = conversation_history[-max_history * 2:] if len(conversation_history) > max_history * 2 else conversation_history

    # Construire le contexte de conversation
    context_messages = []
    for msg in recent_history:
        role = "Utilisateur" if msg["role"] == "user" else "Assistant"
        context_messages.append(f"{role}: {msg['content'][:200]}")  # Limiter à 200 chars par message

    conversation_context = "\n".join(context_messages)

    # Créer un prompt pour reformuler la question
    reformulation_prompt = f"""Tu es un assistant qui reformule des questions en tenant compte du contexte de conversation.

HISTORIQUE DE CONVERSATION:
{conversation_context}

QUESTION ACTUELLE: {current_query}

TÂCHE:
Si la question actuelle contient des références implicites (comme "Et l'article 4?", "Combien ça coûte?", "Et pour Marie?"), reformule-la en une question complète et autonome en utilisant le contexte.

Si la question est déjà complète et autonome, retourne-la telle quelle.

RÈGLES:
- Sois concis, ne rajoute que le contexte nécessaire
- Garde le même sens et la même intention
- Ne réponds PAS à la question, reformule-la seulement

QUESTION REFORMULÉE:"""

    try:
        # Utiliser un LLM léger pour la reformulation
        llm = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY,
            model="gpt-5-mini",  # Utiliser le même modèle
            temperature=0.0
        )

        reformulated = llm.invoke(reformulation_prompt).content.strip()

        logger.info(f"Question originale: {current_query}")
        logger.info(f"Question reformulée: {reformulated}")

        return reformulated

    except Exception as e:
        logger.warning(f"Erreur lors de la reformulation, utilisation de la question originale: {e}", exc_info=True)
        return current_query

def get_llm() -> ChatOpenAI:
    """
    Retourne une instance du modèle LLM configuré.

    Returns:
        Instance de ChatOpenAI
    """
    logger.debug(f"Initialisation du LLM: {MODEL_NAME} (température: {TEMPERATURE})")
    return ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model=MODEL_NAME,
        temperature=TEMPERATURE
    )

def get_retriever(filters: Optional[Dict] = None, k: int = RETRIEVAL_K):
    """
    Retourne un retriever configuré avec des filtres optionnels.

    Args:
        filters: Dictionnaire de filtres pour la recherche
        k: Nombre de documents à récupérer

    Returns:
        Retriever configuré
    """
    vectorstore = init_vectorstore()

    search_kwargs = {"k": k}

    # Ajouter les filtres si présents
    if filters:
        # ChromaDB utilise le format {"filter": {...}}
        search_kwargs["filter"] = filters
        logger.info(f"Retriever configuré avec filtres: {filters}")
    else:
        logger.info("Retriever configuré sans filtres")

    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
    return retriever

def build_system_prompt() -> str:
    """
    Construit le prompt système pour le LLM.

    Returns:
        Prompt système
    """
    return """Vous êtes un assistant juridique interne pour un cabinet d'avocats en droit des affaires.

INSTRUCTIONS IMPORTANTES:

1. **Répondez en vous basant UNIQUEMENT sur les documents fournis ci-dessous**
   - Lisez attentivement tous les extraits fournis
   - Utilisez les informations présentes dans ces extraits pour répondre

2. **Si l'information est présente dans les documents**:
   - Répondez de manière claire et précise
   - À la fin de votre réponse, indiquez UNIQUEMENT les numéros des documents que vous avez réellement utilisés
   - Format: [Sources: 1, 3] (si vous avez utilisé les documents 1 et 3)
   - N'incluez QUE les documents dont vous avez extrait des informations pour votre réponse
   - Si plusieurs documents contiennent des informations pertinentes, synthétisez-les

3. **Si l'information n'est PAS présente dans les documents**:
   - Répondez: "Je ne trouve pas cette information dans les documents disponibles."
   - Ne générez JAMAIS d'informations qui ne sont pas dans les documents fournis

4. **Soyez précis et professionnel** dans vos réponses

---

DOCUMENTS DE RÉFÉRENCE:
{context}

---

QUESTION: {question}

RÉPONSE:"""

def build_context(docs: List[Document]) -> str:
    """
    Construit le contexte à partir des documents récupérés.

    Args:
        docs: Liste de documents récupérés

    Returns:
        Contexte formaté
    """
    if not docs:
        return "Aucun document pertinent trouvé."

    context_parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "source inconnue")
        chunk_id = doc.metadata.get("chunk_id", "?")
        content = doc.page_content

        context_parts.append(
            f"--- Document {i} ---\n"
            f"Source: {source} (chunk {chunk_id})\n"
            f"Contenu:\n{content}\n"
        )

    return "\n".join(context_parts)

def answer_question_with_rag(
    query: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    verbose: bool = False
) -> Tuple[str, List[Document]]:
    """
    Répond à une question en utilisant le pipeline RAG complet.

    Args:
        query: Question de l'utilisateur
        conversation_history: Historique de conversation pour la reformulation contextuelle
        verbose: Si True, affiche des informations de débogage

    Returns:
        Tuple (réponse, documents_utilisés)

    Raises:
        Exception: Si une erreur survient durant le processus
    """
    logger.info(f"Traitement de la requête: {query}")

    try:
        # 1. Reformuler la question avec l'historique si disponible
        if conversation_history and len(conversation_history) > 0:
            reformulated_query = reformulate_query_with_history(query, conversation_history)
        else:
            reformulated_query = query

        # 2. Parser la requête (reformulée) pour extraire les filtres
        question_clean, personne, type_doc = parse_user_query(reformulated_query)

        if verbose:
            logger.info(f"Question: {question_clean}")
            logger.info(f"Personne détectée: {personne}")
            logger.info(f"Type de document détecté: {type_doc}")

        # 3. Construire les filtres
        filters = build_search_filters(personne, type_doc)

        # 4. Récupérer les documents avec filtres
        retriever = get_retriever(filters=filters if filters else None)

        try:
            docs_filtered = retriever.invoke(question_clean)
            logger.info(f"{len(docs_filtered)} documents récupérés avec filtres")

            if verbose:
                for i, doc in enumerate(docs_filtered, 1):
                    logger.info(f"Doc {i}: {doc.metadata.get('source')} (score pertinence)")

        except Exception as e:
            logger.warning(f"Erreur lors de la recherche avec filtres: {e}", exc_info=True)
            docs_filtered = []

        # 5. Fallback: si aucun résultat avec filtres et qu'un filtre personne était appliqué
        if not docs_filtered and personne:
            logger.info("Aucun résultat avec filtre personne, tentative sans filtre")

            # Retirer le filtre personne et réessayer
            filters_fallback = build_search_filters(personne=None, type_doc=type_doc)
            retriever_fallback = get_retriever(
                filters=filters_fallback if filters_fallback else None
            )

            docs_filtered = retriever_fallback.invoke(question_clean)
            logger.info(f"{len(docs_filtered)} documents récupérés sans filtre personne")

        # 6. Si toujours aucun résultat, réponse standard
        if not docs_filtered:
            logger.warning("Aucun document pertinent trouvé")
            return (
                "Je ne trouve pas cette information dans les documents disponibles. "
                "Veuillez vérifier que les documents pertinents ont bien été indexés.",
                []
            )

        # 7. Construire le contexte
        context = build_context(docs_filtered)

        if verbose:
            logger.info(f"Contexte construit ({len(context)} caractères)")

        # 8. Créer le LLM
        llm = get_llm()

        # 9. Construire le prompt final avec le contexte
        # IMPORTANT: Utiliser la question ORIGINALE pour la réponse, pas la reformulée
        prompt_text = build_system_prompt().format(
            context=context,
            question=query  # Question originale de l'utilisateur
        )

        if verbose:
            logger.debug(f"Prompt envoyé au LLM:\n{prompt_text[:500]}...")

        # 10. Générer la réponse
        logger.info("Génération de la réponse avec le LLM")
        answer = llm.invoke(prompt_text).content

        logger.info("Réponse générée avec succès")

        # 11. Extraire les sources réellement utilisées et nettoyer la réponse
        clean_answer, used_docs = extract_used_sources(answer, docs_filtered)

        return clean_answer, used_docs

    except Exception as e:
        logger.error(f"Erreur lors du traitement de la requête: {e}", exc_info=True)
        raise

def get_rag_statistics() -> Dict:
    """
    Retourne des statistiques sur le système RAG.

    Returns:
        Dictionnaire de statistiques
    """
    try:
        vectorstore = init_vectorstore()
        count = vectorstore._collection.count()

        return {
            "total_documents": count,
            "model": MODEL_NAME,
            "embedding_model": "text-embedding-3-small",
            "retrieval_k": RETRIEVAL_K
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        return {}
