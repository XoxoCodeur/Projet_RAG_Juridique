"""
Page d'accueil de l'application RAG - Assistant Juridique Interne
"""

import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="Assistant Juridique RAG",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Page d'accueil de l'application."""

    # CSS personnalisé pour un design moderne et épuré
    st.markdown("""
        <style>
        /* Carte de fonctionnalité moderne */
        .feature-card {
            padding: 2.5rem;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            background: rgba(255, 255, 255, 0.02);
            transition: all 0.3s ease;
            height: 100%;
        }

        .feature-card:hover {
            border-color: rgba(139, 92, 246, 0.5);
            background: rgba(139, 92, 246, 0.05);
            transform: translateY(-4px);
        }

        /* Icône de fonctionnalité */
        .feature-icon {
            font-size: 3.5rem;
            text-align: center;
            margin-bottom: 1.5rem;
            display: block;
            line-height: 1;
        }

        /* Titre de fonctionnalité */
        .feature-title {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            text-align: center;
            color: rgba(255, 255, 255, 0.95);
        }

        /* Description */
        .feature-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .feature-list li {
            padding: 0.6rem 0;
            font-size: 0.95rem;
            line-height: 1.6;
            color: rgba(255, 255, 255, 0.7);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .feature-list li:last-child {
            border-bottom: none;
        }

        /* Espacement */
        .spacer {
            margin: 2rem 0;
        }

        /* Info box */
        .info-box {
            padding: 1.5rem;
            border-radius: 8px;
            background: rgba(59, 130, 246, 0.1);
            border-left: 4px solid rgba(59, 130, 246, 0.8);
            margin: 2rem 0;
        }

        .info-box p {
            margin: 0;
            line-height: 1.6;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header principal
    st.title("⚖️ Assistant Juridique Interne")
    st.markdown("### Interrogez vos documents juridiques avec l'intelligence artificielle")

    st.divider()

    # Info box avec instructions
    st.markdown("""
        <div class="info-box">
            <p><strong>🎯 Comment ça marche ?</strong></p>
            <p>Ajoutez vos documents juridiques, puis posez vos questions en langage naturel.
            L'assistant analyse vos documents et vous fournit des réponses précises avec les sources.</p>
        </div>
    """, unsafe_allow_html=True)

    # Cartes de fonctionnalités
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">💬</div>
                <div class="feature-title">Chatbot Intelligent</div>
                <ul class="feature-list">
                    <li>🤖 Conversation en langage naturel</li>
                    <li>📖 Réponses basées sur vos documents</li>
                    <li>🔗 Visualisation des sources utilisées</li>
                    <li>💾 Gestion de conversations multiples</li>
                    <li>📥 Export des conversations</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

        if st.button("🚀 Accéder au Chatbot", use_container_width=True, type="primary"):
            st.switch_page("pages/1_Chatbot.py")

    with col2:
        st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📁</div>
                <div class="feature-title">Gestion des Documents</div>
                <ul class="feature-list">
                    <li>📤 Upload de fichiers (TXT, CSV, HTML)</li>
                    <li>🔄 Synchronisation automatique</li>
                    <li>⚙️ Configuration du chunking</li>
                    <li>📊 Statistiques en temps réel</li>
                    <li>🗑️ Suppression et nettoyage</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

        if st.button("📂 Gérer les Documents", use_container_width=True, type="primary"):
            st.switch_page("pages/2_Gestion_documents.py")


if __name__ == "__main__":
    main()
