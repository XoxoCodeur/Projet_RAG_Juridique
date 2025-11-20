"""
Page Streamlit de gestion des documents.
Version V3 avec synchronisation automatique et UX fluide.
"""

import streamlit as st
import logging
import time
import re
from pathlib import Path
from datetime import datetime

from rag.config import validate_config, RAW_DOCS_DIR
from rag.vectorstore import (
    rebuild_vectorstore_from_raw_docs,
    get_vectorstore_stats
)
from rag.sync_manager import get_sync_status

logger = logging.getLogger(__name__)

# Configuration de la page
st.set_page_config(
    page_title="Gestion des Documents",
    page_icon="📁",
    layout="wide"
)

# Initialiser session state
if "auto_sync_on_delete" not in st.session_state:
    st.session_state.auto_sync_on_delete = True

if "last_sync_status" not in st.session_state:
    st.session_state.last_sync_status = None

if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = None

if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0

# Paramètres de chunking
if "chunk_size" not in st.session_state:
    from rag.config import CHUNK_SIZE
    st.session_state.chunk_size = CHUNK_SIZE

if "chunk_overlap" not in st.session_state:
    from rag.config import CHUNK_OVERLAP
    st.session_state.chunk_overlap = CHUNK_OVERLAP

# Plus besoin de dossier de backup pour la nouvelle approche

def display_header():
    """Affiche l'en-tête avec statut de synchronisation."""
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title("📁 Gestion des Documents")
        st.caption("Upload, gestion et synchronisation automatique")

    with col2:
        # Statut de sync en haut à droite
        sync_status = get_sync_status()
        st.session_state.last_sync_status = sync_status

        if sync_status["needs_rebuild"]:
            st.warning("⚠️ À synchroniser", icon="⚠️")
        else:
            st.success("✓ Synchronisé", icon="✅")

def save_uploaded_file(uploaded_file) -> Path:
    """Sauvegarde un fichier uploadé."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uploaded_file.name}"
    file_path = RAW_DOCS_DIR / filename

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    logger.info(f"Fichier sauvegardé: {file_path}")
    return file_path

def auto_sync_after_upload():
    """Synchronise automatiquement après l'ajout de documents (toujours actif)."""
    sync_status = get_sync_status()
    if sync_status["needs_rebuild"]:
        with st.spinner("Synchronisation automatique..."):
            rebuild_vectorstore_from_raw_docs()
        # Ne pas faire de rerun ici, on le fera dans la fonction appelante

def auto_sync_after_delete():
    """Synchronise automatiquement après suppression si activé."""
    if st.session_state.auto_sync_on_delete:
        sync_status = get_sync_status()
        if sync_status["needs_rebuild"]:
            with st.spinner("Synchronisation automatique..."):
                rebuild_vectorstore_from_raw_docs()
            st.success("✅ Index nettoyé automatiquement!")
            time.sleep(0.5)
            st.rerun()

# Fonctions de suppression simplifiées supprimées - nouvelle approche ci-dessous

def upload_documents_section():
    """Section d'upload simplifiée."""
    st.subheader("📤 Ajouter des documents")

    # File uploader avec clé dynamique pour permettre le reset
    uploaded_files = st.file_uploader(
        "📁 Glissez vos fichiers ici ou cliquez pour parcourir",
        type=["txt", "csv", "html", "htm"],
        accept_multiple_files=True,
        help="Formats acceptés: TXT, CSV, HTML - Taille max: 10 MB par fichier - L'indexation se fera automatiquement",
        key=f"file_uploader_{st.session_state.upload_key}"
    )

    if uploaded_files:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{len(uploaded_files)} fichier(s) sélectionné(s)**")
        with col2:
            if st.button("🗑️ Annuler", key="cancel_upload", use_container_width=True):
                # Incrémenter la clé pour vider le widget et forcer le rerun
                st.session_state.upload_key += 1
                st.rerun()

        if st.button("➕ Ajouter ces fichiers", type="primary", use_container_width=True, key="add_files"):
            progress_bar = st.progress(0)
            status_container = st.empty()

            files_added = []
            files_skipped = []
            MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB en bytes

            for idx, uploaded_file in enumerate(uploaded_files):
                try:
                    # Validation de la taille du fichier
                    if uploaded_file.size > MAX_FILE_SIZE:
                        size_mb = uploaded_file.size / (1024 * 1024)
                        files_skipped.append(f"{uploaded_file.name} ({size_mb:.1f} MB)")
                        logger.warning(f"Fichier trop volumineux ignoré: {uploaded_file.name} ({size_mb:.1f} MB)")
                        progress_bar.progress((idx + 1) / len(uploaded_files))
                        continue

                    status_container.info(f"📄 Ajout de {uploaded_file.name}...")

                    # Sauvegarder le fichier
                    save_uploaded_file(uploaded_file)
                    files_added.append(uploaded_file.name)

                    progress_bar.progress((idx + 1) / len(uploaded_files))

                except Exception as e:
                    st.error(f"❌ {uploaded_file.name}: {str(e)}")
                    logger.error(f"Erreur: {e}", exc_info=True)

            progress_bar.empty()
            status_container.empty()

            # Afficher les fichiers ignorés si présents
            if files_skipped:
                st.warning(f"⚠️ {len(files_skipped)} fichier(s) ignoré(s) (taille > 10 MB):")
                for skipped in files_skipped:
                    st.text(f"  • {skipped}")

            if files_added:
                # Synchronisation automatique (toujours active à l'ajout)
                auto_sync_after_upload()

                # Incrémenter la clé AVANT le rerun pour vider le file_uploader
                st.session_state.upload_key += 1

                # Afficher message de succès
                st.success(f"✅ {len(files_added)} fichier(s) ajouté(s) et indexé(s) avec succès!")
                time.sleep(0.8)  # Petite pause pour que l'utilisateur voie le message

                # Rerun pour recréer le widget avec la nouvelle clé
                st.rerun()
            elif files_skipped:
                # Tous les fichiers ont été ignorés
                st.error("❌ Aucun fichier n'a pu être ajouté. Vérifiez la taille des fichiers.")

def display_sync_warning():
    """Affiche un warning si des changements ne sont pas synchronisés (uniquement si synchro auto désactivée)."""
    # Ne pas afficher si la synchro auto est activée (la base sera toujours synchro)
    if st.session_state.auto_sync_on_delete:
        return

    sync_status = get_sync_status()

    if sync_status["needs_rebuild"]:
        col1, col2 = st.columns([4, 1])

        with col1:
            if sync_status["pending"]:
                count = len(sync_status['pending'])
                st.warning(
                    f"⚠️ **{count} fichier{'s' if count > 1 else ''} à indexer** - Cliquez sur Synchroniser pour mettre à jour le chatbot",
                    icon="⚠️"
                )
            elif sync_status["orphaned"]:
                count = len(sync_status['orphaned'])
                st.warning(
                    f"⚠️ **{count} fichier{'s' if count > 1 else ''} supprimé{'s' if count > 1 else ''}** - Cliquez sur Synchroniser pour nettoyer l'index",
                    icon="⚠️"
                )

        with col2:
            if st.button("🔄 Synchroniser", use_container_width=True, key="manual_sync", type="primary"):
                with st.spinner("Synchronisation en cours..."):
                    num_chunks = rebuild_vectorstore_from_raw_docs()
                st.success(f"✅ Synchronisé! {num_chunks} chunks indexés")
                time.sleep(0.5)
                st.rerun()

def list_documents():
    """Liste tous les documents."""
    st.subheader("📚 Documents")

    # Récupérer tous les fichiers
    raw_files = list(RAW_DOCS_DIR.glob("*"))
    raw_files = [f for f in raw_files if f.is_file() and not f.name.startswith('.')]
    raw_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    if not raw_files:
        st.info("Aucun document. Ajoutez-en via la section ci-dessus.")
        return

    st.caption(f"{len(raw_files)} document{'s' if len(raw_files) > 1 else ''}")

    display_file_list(raw_files, tab_prefix="main")

def display_file_list(files, tab_prefix=""):
    """Affiche une liste de fichiers."""
    if not files:
        st.info("Aucun fichier.")
        return

    for idx, file_path in enumerate(files):
        # Vérifier si ce fichier est en attente de confirmation
        is_confirming = st.session_state.confirm_delete == file_path.name

        if is_confirming:
            # Mode confirmation: afficher en ligne avec fond coloré
            col1, col2, col3, col4 = st.columns([0.5, 2.5, 1, 1])

            with col1:
                st.markdown("### ⚠️")

            with col2:
                # Retirer le préfixe timestamp pour l'affichage
                clean_filename = re.sub(r'^\d{8}_\d{6}_', '', file_path.name)
                st.markdown(f"**Confirmer la suppression de** `{clean_filename}` **?**")

            with col3:
                if st.button("✓ Confirmer", key=f"confirm_{tab_prefix}_{idx}", type="primary", use_container_width=True):
                    try:
                        # Supprimer le fichier
                        file_path.unlink()
                        logger.info(f"Fichier supprimé: {file_path.name}")

                        # Réinitialiser l'état
                        st.session_state.confirm_delete = None

                        # Afficher un message de succès
                        clean_filename = re.sub(r'^\d{8}_\d{6}_', '', file_path.name)
                        st.toast(f"✅ {clean_filename} supprimé", icon="✅")
                        time.sleep(0.3)

                        # Synchroniser automatiquement si activé
                        auto_sync_after_delete()

                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Erreur: {str(e)}")
                        logger.error(f"Erreur suppression: {e}", exc_info=True)

            with col4:
                if st.button("✗ Annuler", key=f"cancel_{tab_prefix}_{idx}", use_container_width=True):
                    st.session_state.confirm_delete = None
                    st.rerun()

            st.markdown("---")  # Séparateur visuel

        else:
            # Mode normal: affichage standard sans badge
            col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 0.7])

            with col1:
                # Icône de fichier + nom
                file_icon = "📄"
                if file_path.suffix.lower() == '.csv':
                    file_icon = "📊"
                elif file_path.suffix.lower() == '.html' or file_path.suffix.lower() == '.htm':
                    file_icon = "🌐"
                # Retirer le préfixe timestamp pour l'affichage
                clean_filename = re.sub(r'^\d{8}_\d{6}_', '', file_path.name)
                st.markdown(f"{file_icon} **{clean_filename}**")

            with col2:
                # Taille
                size_kb = file_path.stat().st_size / 1024
                st.caption(f"📦 {size_kb:.1f} KB")

            with col3:
                # Date
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                st.caption(f"🕒 {mtime.strftime('%d/%m/%Y %H:%M')}")

            with col4:
                # Bouton supprimer
                if st.button("🗑️", key=f"del_{tab_prefix}_{idx}_{file_path.name[:20]}", help="Supprimer"):
                    # Passer en mode confirmation
                    st.session_state.confirm_delete = file_path.name
                    st.rerun()

def display_statistics():
    """Affiche les statistiques."""
    st.subheader("📊 Statistiques")

    try:
        stats = get_vectorstore_stats()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("📁 Documents", stats.get("total_files", 0))

        with col2:
            st.metric("📦 Chunks indexés", stats.get("total_chunks", 0))

        with col3:
            try:
                # Calculer la taille totale des documents
                raw_files = list(RAW_DOCS_DIR.glob("*"))
                raw_files = [f for f in raw_files if f.is_file() and not f.name.startswith('.')]
                total_size_bytes = sum(f.stat().st_size for f in raw_files if f.exists())

                # Afficher en KB ou MB selon la taille
                if total_size_bytes < 1024 * 1024:  # Moins de 1 MB
                    size_display = f"{total_size_bytes / 1024:.1f} KB"
                else:
                    size_display = f"{total_size_bytes / (1024 * 1024):.2f} MB"

                st.metric("💾 Taille totale", size_display)
            except (OSError, IOError) as e:
                logger.error(f"Erreur lors du calcul de la taille des fichiers: {e}", exc_info=True)
                st.metric("💾 Taille totale", "N/A")

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}", exc_info=True)
        st.error(f"Erreur stats: {str(e)}")

def display_settings():
    """Affiche les paramètres."""
    with st.expander("⚙️ Paramètres"):
        st.markdown("**Synchronisation automatique**")

        # Toggle pour la suppression
        auto_sync_delete = st.toggle(
            "Synchronisation automatique à la suppression",
            value=st.session_state.auto_sync_on_delete,
            help="Si activé, l'index est nettoyé automatiquement après chaque suppression",
            key="auto_sync_delete_toggle"
        )

        st.session_state.auto_sync_on_delete = auto_sync_delete

        if auto_sync_delete:
            st.success("✅ L'index sera nettoyé automatiquement après chaque suppression")
        else:
            st.warning("⚠️ Vous devrez synchroniser manuellement après les suppressions")

        st.divider()

        st.markdown("**Paramètres de découpage des documents (Chunking)**")

        st.info("""
        **À quoi ça sert ?**

        Les documents sont découpés en petits morceaux (chunks) pour améliorer la recherche :

        - **Taille du chunk** : Nombre de caractères par morceau (plus petit = recherche plus précise mais plus de morceaux)
        - **Chevauchement** : Nombre de caractères qui se répètent entre deux morceaux consécutifs (évite de couper les informations importantes)

        💡 *Valeurs recommandées : 1000 caractères avec 200 de chevauchement*
        """)

        col1, col2 = st.columns(2)

        with col1:
            chunk_size = st.number_input(
                "Taille du chunk (caractères)",
                min_value=100,
                max_value=2000,
                value=st.session_state.get("chunk_size", 1000),
                step=100,
                help="Nombre de caractères par morceau de document",
                key="chunk_size_input"
            )

        with col2:
            chunk_overlap = st.number_input(
                "Chevauchement (caractères)",
                min_value=0,
                max_value=500,
                value=st.session_state.get("chunk_overlap", 200),
                step=50,
                help="Nombre de caractères qui se répètent entre deux morceaux",
                key="chunk_overlap_input"
            )

        # Validation
        if chunk_overlap >= chunk_size:
            st.error("⚠️ Le chevauchement doit être inférieur à la taille du chunk!")
        else:
            # Sauvegarder dans session state
            st.session_state.chunk_size = chunk_size
            st.session_state.chunk_overlap = chunk_overlap

            # Afficher un avertissement si les valeurs ont changé
            from rag.config import CHUNK_SIZE, CHUNK_OVERLAP
            if chunk_size != CHUNK_SIZE or chunk_overlap != CHUNK_OVERLAP:
                st.warning("⚠️ Les paramètres ont changé. Synchronisez pour appliquer les modifications.")

        st.divider()

        st.markdown("**Actions de maintenance**")

        if st.button("🔄 Synchroniser maintenant", use_container_width=True, key="force_sync"):
            with st.spinner("Synchronisation forcée..."):
                # Mettre à jour temporairement les variables d'environnement pour cette session
                import os
                os.environ["CHUNK_SIZE"] = str(st.session_state.chunk_size)
                os.environ["CHUNK_OVERLAP"] = str(st.session_state.chunk_overlap)

                num_chunks = rebuild_vectorstore_from_raw_docs()
            st.success(f"✅ {num_chunks} chunks indexés avec les nouveaux paramètres")
            time.sleep(0.5)
            st.rerun()

def check_navigation_warning():
    """Affiche un warning si l'utilisateur veut naviguer avec des changements (uniquement si synchro auto désactivée)."""
    # Ne pas afficher si la synchro auto est activée
    if st.session_state.auto_sync_on_delete:
        return

    sync_status = st.session_state.get("last_sync_status")

    if sync_status and sync_status["needs_rebuild"]:
        count_pending = len(sync_status.get("pending", []))
        count_orphaned = len(sync_status.get("orphaned", []))

        if count_pending > 0:
            st.sidebar.warning(
                f"⚠️ **{count_pending} fichier{'s' if count_pending > 1 else ''} non indexé{'s' if count_pending > 1 else ''}**\n\n"
                "Synchronisez pour que le chatbot puisse les utiliser.",
                icon="⚠️"
            )
        elif count_orphaned > 0:
            st.sidebar.warning(
                f"⚠️ **{count_orphaned} fichier{'s' if count_orphaned > 1 else ''} à nettoyer**\n\n"
                "Synchronisez pour mettre à jour l'index.",
                icon="⚠️"
            )

        if st.sidebar.button("🔄 Synchroniser", use_container_width=True, key="sidebar_sync", type="primary"):
            with st.spinner("Synchronisation..."):
                rebuild_vectorstore_from_raw_docs()
            st.success("✅ Synchronisé!")
            time.sleep(0.5)
            st.rerun()

def main():
    """Fonction principale."""
    try:
        validate_config()

        # Header avec statut
        display_header()

        st.divider()

        # Warning si changements non synchronisés
        display_sync_warning()

        # Section upload
        upload_documents_section()

        st.divider()

        # Statistiques
        display_statistics()

        st.divider()

        # Liste des documents
        list_documents()

        st.divider()

        # Paramètres
        display_settings()

        # Warning dans la sidebar si nécessaire
        check_navigation_warning()

    except ValueError as e:
        st.error(str(e))
        st.info("Veuillez configurer votre fichier .env")
    except Exception as e:
        st.error(f"Erreur: {str(e)}")
        logger.error(f"Erreur: {e}", exc_info=True)

if __name__ == "__main__":
    main()
