import streamlit as st
import json
import time
import random
from datetime import datetime, timedelta
import base64
import io
from PIL import Image
import pandas as pd
import requests
import os

# Configuration de la page
st.set_page_config(
    page_title="RéviZIA - Plateforme Éducative Intelligente",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour un design moderne
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
        color: white;
    }
    
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    
    .stat-card {
        background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin-bottom: 1rem;
    }
    
    .quiz-question {
        background: #f8f9ff;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e0e6ff;
        margin-bottom: 1rem;
    }
    
    .correct-answer {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.5rem;
        border-radius: 5px;
    }
    
    .incorrect-answer {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 0.5rem;
        border-radius: 5px;
    }
    
    .ministry-badge {
        background: #28a745;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation des données de session
if 'user_data' not in st.session_state:
    st.session_state.user_data = {
        'name': '',
        'level': '',
        'points': 0,
        'rank': 'Débutant',
        'courses_uploaded': 0,
        'quizzes_completed': 0,
        'correct_answers': 0,
        'study_streak': 0,
        'last_study_date': None
    }

if 'courses' not in st.session_state:
    st.session_state.courses = []

if 'current_quiz' not in st.session_state:
    st.session_state.current_quiz = None

if 'quiz_results' not in st.session_state:
    st.session_state.quiz_results = []

# Configuration de l'API Google Gemini via REST
def configure_gemini():
    """Configure l'API Google Gemini via REST API"""
    # Interface pour saisir la clé API
    with st.sidebar:
        st.header("🔑 Configuration API")
        
        # Récupération de la clé API
        if 'gemini_api_key' not in st.session_state:
            st.session_state.gemini_api_key = ""
        
        # Interface pour la clé API
        api_key_input = st.text_input(
            "Clé API Google Gemini:", 
            value=st.session_state.gemini_api_key,
            type="password",
            help="Obtenez votre clé API sur https://aistudio.google.com/app/apikey"
        )
        
        if api_key_input != st.session_state.gemini_api_key:
            st.session_state.gemini_api_key = api_key_input
            if api_key_input:
                # Test de la clé API
                if test_gemini_api(api_key_input):
                    st.success("✅ API configurée!")
                    st.session_state.gemini_configured = True
                else:
                    st.error("❌ Clé API invalide")
                    st.session_state.gemini_configured = False
            else:
                st.session_state.gemini_configured = False
        
        # Status de l'API
        if st.session_state.get('gemini_configured', False):
            st.success("🤖 Gemini AI: Connecté")
        else:
            st.warning("🤖 Gemini AI: Non configuré")
            st.info("💡 Entrez votre clé API Google Gemini pour utiliser l'IA")

def test_gemini_api(api_key):
    """Test la validité de la clé API"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        data = {
            "contents": [{
                "parts": [{
                    "text": "Hello"
                }]
            }]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        return response.status_code == 200
        
    except Exception as e:
        return False

def call_gemini_api(prompt, api_key):
    """Appelle l'API Gemini via REST"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                content = result['candidates'][0]['content']['parts'][0]['text']
                return content
            else:
                return None
        else:
            st.error(f"Erreur API: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Erreur lors de l'appel API: {str(e)}")
        return None

def generate_quiz_with_gemini(text, num_questions=5, level="Terminale"):
    """Génère un quiz en utilisant l'API REST Google Gemini"""
    if not st.session_state.get('gemini_configured', False):
        # Fallback vers des questions simulées si l'API n'est pas configurée
        return generate_quiz_simulation(text, num_questions)
    
    try:
        # Prompt optimisé pour générer des quiz
        prompt = f"""
Tu es un expert pédagogique sénégalais spécialisé dans la création de quiz pour lycéens.

CONSIGNE: À partir du contenu de cours suivant, génère exactement {num_questions} questions de type QCM adaptées au niveau {level}.

CONTENU DU COURS:
{text[:2500]}

FORMAT DE RÉPONSE REQUIS (JSON strict):
{{
    "questions": [
        {{
            "question": "Question claire et précise basée sur le contenu",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct": 0,
            "explanation": "Explication détaillée de pourquoi cette réponse est correcte"
        }}
    ]
}}

CRITÈRES IMPORTANTS:
- Questions adaptées au programme sénégalais niveau {level}
- 4 options par question (A, B, C, D)
- Une seule bonne réponse par question (index 0-3)
- Explications pédagogiques claires
- Vocabulaire approprié au niveau scolaire
- Questions basées UNIQUEMENT sur le contenu fourni
- Éviter les questions trop évidentes ou trop difficiles

Réponds UNIQUEMENT avec le JSON valide, sans texte supplémentaire, sans balises markdown.
        """
        
        # Appel à l'API
        response_text = call_gemini_api(prompt, st.session_state.gemini_api_key)
        
        if response_text is None:
            return generate_quiz_simulation(text, num_questions)
        
        # Parsing de la réponse
        try:
            # Nettoyage de la réponse pour extraire le JSON
            response_text = response_text.strip()
            
            # Suppression des balises markdown si présentes
            if response_text.startswith('```json'):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith('```'):
                response_text = response_text[3:-3].strip()
            
            # Tentative de parsing JSON
            quiz_data = json.loads(response_text)
            
            if 'questions' in quiz_data and len(quiz_data['questions']) > 0:
                # Validation des questions
                valid_questions = []
                for q in quiz_data['questions'][:num_questions]:
                    if (isinstance(q.get('question'), str) and 
                        isinstance(q.get('options'), list) and 
                        len(q.get('options', [])) == 4 and
                        isinstance(q.get('correct'), int) and
                        0 <= q.get('correct', -1) < 4 and
                        isinstance(q.get('explanation'), str)):
                        valid_questions.append(q)
                
                if valid_questions:
                    return valid_questions
                else:
                    st.warning("⚠️ Questions générées invalides, utilisation du mode simulation")
                    return generate_quiz_simulation(text, num_questions)
            else:
                st.warning("⚠️ Format de réponse invalide, utilisation du mode simulation")
                return generate_quiz_simulation(text, num_questions)
                
        except json.JSONDecodeError as e:
            st.warning(f"⚠️ Erreur de parsing JSON, utilisation du mode simulation")
            return generate_quiz_simulation(text, num_questions)
            
    except Exception as e:
        st.error(f"❌ Erreur API Gemini: {str(e)}")
        return generate_quiz_simulation(text, num_questions)

def generate_quiz_simulation(text, num_questions=5):
    """Fonction de fallback avec questions simulées"""
    sample_questions = [
        {
            "question": "Quelle est l'idée principale développée dans ce cours ?",
            "options": [
                "Concept fondamental A", 
                "Théorie principale B", 
                "Principe central C", 
                "Notion essentielle D"
            ],
            "correct": 0,
            "explanation": "Cette réponse correspond au thème central développé dans le contenu du cours."
        },
        {
            "question": "Comment peut-on appliquer cette connaissance en pratique ?",
            "options": [
                "Application dans le domaine X", 
                "Utilisation en contexte Y", 
                "Mise en œuvre selon Z", 
                "Implementation via W"
            ],
            "correct": 1,
            "explanation": "Cette application pratique découle directement des principes théoriques énoncés."
        },
        {
            "question": "Quels sont les éléments clés à retenir de cette leçon ?",
            "options": [
                "Points secondaires", 
                "Éléments principaux", 
                "Détails complémentaires", 
                "Aspects périphériques"
            ],
            "correct": 1,
            "explanation": "Les éléments principaux constituent le cœur de la compréhension du sujet."
        },
        {
            "question": "Dans quel contexte cette notion est-elle particulièrement importante ?",
            "options": [
                "Contexte général", 
                "Situation spécifique", 
                "Cadre d'application précis", 
                "Environnement particulier"
            ],
            "correct": 2,
            "explanation": "Le cadre d'application précis permet une meilleure compréhension et utilisation."
        },
        {
            "question": "Quelle conclusion peut-on tirer de cette étude ?",
            "options": [
                "Conclusion partielle", 
                "Synthèse globale", 
                "Résumé incomplet", 
                "Vue d'ensemble limitée"
            ],
            "correct": 1,
            "explanation": "La synthèse globale offre la perspective la plus complète du sujet traité."
        }
    ]
    
    return random.sample(sample_questions, min(num_questions, len(sample_questions)))

# Fonctions utilitaires
def generate_quiz_from_text(text, num_questions=5):
    """Génère un quiz à partir du texte en utilisant Gemini AI"""
    level = st.session_state.user_data.get('level', 'Terminale')
    return generate_quiz_with_gemini(text, num_questions, level)

def update_user_stats(correct_answers, total_questions):
    """Met à jour les statistiques de l'utilisateur"""
    st.session_state.user_data['quizzes_completed'] += 1
    st.session_state.user_data['correct_answers'] += correct_answers
    st.session_state.user_data['points'] += correct_answers * 10
    
    # Mise à jour du rang
    points = st.session_state.user_data['points']
    if points >= 1000:
        st.session_state.user_data['rank'] = '🏆 Expert'
    elif points >= 500:
        st.session_state.user_data['rank'] = '⭐ Avancé'
    elif points >= 200:
        st.session_state.user_data['rank'] = '📚 Intermédiaire'
    else:
        st.session_state.user_data['rank'] = '🌱 Débutant'
    
    # Mise à jour de la série d'études
    today = datetime.now().date()
    if st.session_state.user_data['last_study_date'] == today - timedelta(days=1):
        st.session_state.user_data['study_streak'] += 1
    elif st.session_state.user_data['last_study_date'] != today:
        st.session_state.user_data['study_streak'] = 1
    
    st.session_state.user_data['last_study_date'] = today

# Configuration de l'API Gemini au démarrage
configure_gemini()

# En-tête principal
st.markdown("""
<div class="main-header">
    <h1>🎓 RéviZIA</h1>
    <h3>Plateforme Web Intelligente pour Lycéens Africains</h3>
    <span class="ministry-badge">Reconnu par le Ministère de l'Éducation Nationale du Sénégal</span>
    <p style="margin-top: 1rem;">Transformez vos cours en quiz interactifs avec l'IA Gemini</p>
</div>
""", unsafe_allow_html=True)

# Barre latérale - Profile utilisateur
with st.sidebar:
    st.header("👤 Profil Utilisateur")
    
    if not st.session_state.user_data['name']:
        with st.form("user_setup"):
            name = st.text_input("Nom complet")
            level = st.selectbox("Classe", ["Seconde", "Première", "Terminale"])
            submitted = st.form_submit_button("Créer mon profil")
            
            if submitted and name:
                st.session_state.user_data['name'] = name
                st.session_state.user_data['level'] = level
                st.success("Profil créé avec succès!")
                st.rerun()
    else:
        st.write(f"**{st.session_state.user_data['name']}**")
        st.write(f"📚 Classe: {st.session_state.user_data['level']}")
        st.write(f"🏅 Rang: {st.session_state.user_data['rank']}")
        st.write(f"⭐ Points: {st.session_state.user_data['points']}")
        st.write(f"🔥 Série: {st.session_state.user_data['study_streak']} jours")
        
        if st.button("🔄 Réinitialiser profil"):
            for key in st.session_state.user_data:
                if key == 'name' or key == 'level':
                    st.session_state.user_data[key] = ''
                else:
                    st.session_state.user_data[key] = 0
            st.rerun()

# Navigation principale
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📚 Mes Cours", "🎯 Quiz", "📊 Statistiques", "🎮 Jeu", "⚙️ Paramètres"])

# Onglet 1: Gestion des cours
with tab1:
    st.header("📚 Gestion de vos Cours")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Importer un nouveau cours")
        
        # Options d'import
        import_method = st.radio(
            "Choisissez votre méthode d'import:",
            ["📝 Texte", "🎤 Audio", "📷 Image (OCR)","📝 Base de connaissance commune google drive"]
        )
        
        if import_method == "📝 Texte":
            course_title = st.text_input("Titre du cours ou de la note")
            course_content = st.text_area("Contenu du cours ou de la note", height=200)
            
            if st.button("Importer le cours ou la prise de note") and course_title and course_content:
                new_course = {
                    'id': len(st.session_state.courses),
                    'title': course_title,
                    'content': course_content,
                    'type': 'text',
                    'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'quiz_generated': False
                }
                st.session_state.courses.append(new_course)
                st.session_state.user_data['courses_uploaded'] += 1
                st.success("✅ Cours importé avec succès!")
                
                # Génération automatique d'un aperçu de quiz
                if st.session_state.get('gemini_configured', False):
                    with st.spinner("🤖 Génération d'un aperçu de quiz avec Gemini AI..."):
                        preview_quiz = generate_quiz_from_text(course_content, 2)
                        if preview_quiz:
                            st.info("🎯 Aperçu des questions qui seront générées:")
                            for i, q in enumerate(preview_quiz):
                                st.write(f"**Question {i+1}:** {q['question']}")
                                for j, option in enumerate(q['options']):
                                    marker = "✅" if j == q['correct'] else "◯"
                                    st.write(f"  {marker} {option}")
                
                st.rerun()
        
        elif import_method == "🎤 Audio":
            st.info("🎤 Fonctionnalité de reconnaissance vocale")
            st.write("Cliquez sur 'Enregistrer' pour démarrer l'enregistrement audio")
            
            if st.button("🎙️ Enregistrer audio"):
                st.success("Enregistrement simulé - Dans la vraie app, ceci utiliserait l'API de reconnaissance vocale")
                # Simulation
                course_title = st.text_input("Titre du cours audio", key="audio_title")
                if course_title:
                    new_course = {
                        'id': len(st.session_state.courses),
                        'title': course_title,
                        'content': "Contenu transcrit de l'audio (simulation)",
                        'type': 'audio',
                        'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                        'quiz_generated': False
                    }
                    st.session_state.courses.append(new_course)
                    st.session_state.user_data['courses_uploaded'] += 1
        
        elif import_method == "📷 Image (OCR)":
            st.info("📷 Reconnaissance OCR avec l'IA")
            uploaded_file = st.file_uploader("Choisir une image", type=['png', 'jpg', 'jpeg'])
            
            if uploaded_file is not None:
                image = Image.open(uploaded_file)
                st.image(image, caption="Image uploadée", use_column_width=True)
                
                if st.button("🔍 Extraire le texte (OCR)"):
                    st.success("OCR simulé - Dans la vraie app, ceci utiliserait l'API OCR de Google")
                    course_title = st.text_input("Titre du cours OCR", key="ocr_title")
                    if course_title:
                        new_course = {
                            'id': len(st.session_state.courses),
                            'title': course_title,
                            'content': "Texte extrait de l'image via OCR (simulation)",
                            'type': 'image',
                            'date': datetime.now().strftime("%d/%m/%Y %H:%M"),
                            'quiz_generated': False
                        }
                        st.session_state.courses.append(new_course)
                        st.session_state.user_data['courses_uploaded'] += 1
        elif import_method == "📝 Base de connaissance commune google drive":
            st.info("🎤 Utilise la base de connaisasance commune de la classe, ou celle reconnu centrale reconnue par le minstère de l'éducation nationale")
            st.write("Cliquez sur 'Connecter' pour démarrer la connexion à la base de données centralisée")
            
            if st.button("📝 Connexion à la base Google drive"):
                st.success("Connexion simulé - Dans la vraie app, ceci utiliserait l'API de google drive")
                # Simulation
                
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h4>🤖 IA Gemini Configurée</h4>
            <p>Questions générées automatiquement par Google AI</p>
        </div>
        """ if st.session_state.get('gemini_configured', False) else """
        <div class="feature-card">
            <h4>⚙️ Configuration requise</h4>
            <p>Ajoutez votre clé API Gemini dans la barre latérale</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="feature-card">
            <h4>🎯 Adapté au niveau</h4>
            <p>Questions adaptées à votre classe</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Liste des cours
    if st.session_state.courses:
        st.subheader("📖 Vos cours importés")
        
        for course in st.session_state.courses:
            with st.expander(f"{course['title']} - {course['date']}"):
                st.write(f"**Type:** {course['type'].capitalize()}")
                st.write(f"**Contenu:** {course['content'][:200]}...")
                
                col_a, col_b, col_c , col_d, col_e, col_f, col_g, col_h = st.columns(8)
                with col_a:
                    num_questions = st.selectbox(
                        "Nombre de questions", 
                        [3, 5, 8, 10], 
                        index=1, 
                        key=f"num_q_{course['id']}"
                    )
                
                with col_b:
                    if st.button(f"🎯 Générer Quiz", key=f"gen_{course['id']}"):
                        if st.session_state.get('gemini_configured', False):
                            with st.spinner(f"🤖 Gemini AI génère {num_questions} questions..."):
                                quiz_questions = generate_quiz_from_text(course['content'], num_questions)
                        else:
                            st.warning("⚠️ API Gemini non configurée - Utilisation du mode simulation")
                            quiz_questions = generate_quiz_from_text(course['content'], num_questions)
                        
                        st.session_state.current_quiz = {
                            'course_id': course['id'],
                            'course_title': course['title'],
                            'questions': quiz_questions,
                            'current_question': 0,
                            'answers': [],
                            'score': 0
                        }
                        st.success(f"✅ Quiz de {len(quiz_questions)} questions généré!")
                        st.info("➡️ Allez dans l'onglet 'Quiz' pour commencer.")
                
                with col_c:
                    if st.button(f"🗑️ Supprimer", key=f"del_{course['id']}"):
                        st.session_state.courses = [c for c in st.session_state.courses if c['id'] != course['id']]
                        st.rerun()
                with col_d :
                    if st.button("Génèrer une synthèse", key=f"col_d_{course['id']}"):
                        st.success("Génèration une synthèse simulé - Dans la vraie app, ceci utiliserait l'API de de Google")
                # Simulation
                with col_e :
                    if st.button("Génèrer un podcast (Spech generation)",key=f"col_e_{course['id']}"):
                        st.success("Génèration podcast simulé - Dans la vraie app, ceci utiliserait l'API de de Google")
                with col_f :
                    if st.button("Story telling",key=f"col_f_{course['id']}"):
                        st.success("Génèration story telling simulé - Dans la vraie app, ceci utiliserait l'API de de Google")
                with col_g :
                    if st.button("Chatter par texte",key=f"col_g_{course['id']}"):
                        st.success("Chat simulé - Dans la vraie app, ceci utiliserait l'API de de Google")
                with col_h :
                    if st.button("Chatte par voice 2 voice", key=f"col_h_{course['id']}"):
                        st.success("Chat simulé - Dans la vraie app, ceci utiliserait l'API de de Google")
# Onglet 2: Quiz
with tab2:
    st.header("🎯 Quiz Interactif")
    
    if st.session_state.current_quiz is None:
        st.info("📚 Importez d'abord un cours et générez un quiz dans l'onglet 'Mes Cours'")
    else:
        quiz = st.session_state.current_quiz
        current_q = quiz['current_question']
        
        if current_q < len(quiz['questions']):
            question = quiz['questions'][current_q]
            
            st.markdown(f"""
            <div class="quiz-question">
                <h4>Question {current_q + 1}/{len(quiz['questions'])}</h4>
                <h3>{question['question']}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Barre de progression
            progress = (current_q) / len(quiz['questions'])
            st.progress(progress)
            
            # Options de réponse
            selected_answer = st.radio(
                "Choisissez votre réponse:",
                range(len(question['options'])),
                format_func=lambda x: question['options'][x],
                key=f"q_{current_q}"
            )
            
            if st.button("Valider la réponse"):
                quiz['answers'].append(selected_answer)
                
                # Vérification de la réponse
                if selected_answer == question['correct']:
                    st.markdown('<div class="correct-answer">✅ Bonne réponse!</div>', unsafe_allow_html=True)
                    quiz['score'] += 1
                else:
                    st.markdown(f'<div class="incorrect-answer">❌ Incorrect. La bonne réponse était: {question["options"][question["correct"]]}</div>', unsafe_allow_html=True)
                
                st.info(f"💡 **Explication:** {question['explanation']}")
                
                quiz['current_question'] += 1
                
                if quiz['current_question'] >= len(quiz['questions']):
                    # Fin du quiz
                    update_user_stats(quiz['score'], len(quiz['questions']))
                    st.success(f"🎉 Quiz terminé! Score: {quiz['score']}/{len(quiz['questions'])}")
                    
                    # Sauvegarde des résultats
                    st.session_state.quiz_results.append({
                        'course_title': quiz['course_title'],
                        'score': quiz['score'],
                        'total': len(quiz['questions']),
                        'percentage': (quiz['score'] / len(quiz['questions'])) * 100,
                        'date': datetime.now().strftime("%d/%m/%Y %H:%M")
                    })
                    
                    st.session_state.current_quiz = None
                
                time.sleep(2)  # Pause pour lire la réponse
                st.rerun()

# Onglet 3: Statistiques
with tab3:
    st.header("📊 Vos Statistiques")
    
    # Cartes de statistiques
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <h3>{st.session_state.user_data['courses_uploaded']}</h3>
            <p>Cours importés</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <h3>{st.session_state.user_data['quizzes_completed']}</h3>
            <p>Quiz complétés</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <h3>{st.session_state.user_data['points']}</h3>
            <p>Points totaux</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <h3>{st.session_state.user_data['study_streak']}</h3>
            <p>Jours consécutifs</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Graphiques
    if st.session_state.quiz_results:
        st.subheader("📈 Évolution de vos performances")
        
        df = pd.DataFrame(st.session_state.quiz_results)
        st.line_chart(df.set_index('date')['percentage'])
        
        st.subheader("📋 Historique des quiz")
        st.dataframe(df)
    else:
        st.info("Aucun quiz complété pour le moment. Commencez par importer un cours!")

# Onglet 4: Jeu
with tab4:
    st.header("🎮 Mode Jeu - Quiz Challenge")
    
    st.info("🏆 Défiez-vous avec des questions rapides!")
    
    if st.button("🚀 Démarrer un Quiz Challenge"):
        # Quiz rapide avec questions aléatoires
        challenge_questions = [
            {
                "question": "Quelle est la capitale du Sénégal?",
                "options": ["Dakar", "Thiès", "Saint-Louis", "Kaolack"],
                "correct": 0
            },
            {
                "question": "Combien de régions compte le Sénégal?",
                "options": ["12", "14", "16", "18"],
                "correct": 1
            },
            {
                "question": "Quelle est la langue officielle du Sénégal?",
                "options": ["Wolof", "Français", "Pulaar", "Serer"],
                "correct": 1
            }
        ]
        
        st.session_state.current_quiz = {
            'course_id': 'challenge',
            'course_title': 'Quiz Challenge',
            'questions': challenge_questions,
            'current_question': 0,
            'answers': [],
            'score': 0
        }
        st.success("Challenge démarré! Allez dans l'onglet Quiz.")
    
    # Classement fictif
    st.subheader("🏆 Classement des joueurs")
    leaderboard = [
        {"Nom": "Aminata D.", "Points": 1250, "Rang": "🏆 Expert"},
        {"Nom": "Mamadou S.", "Points": 980, "Rang": "⭐ Avancé"},
        {"Nom": st.session_state.user_data['name'] or "Vous", "Points": st.session_state.user_data['points'], "Rang": st.session_state.user_data['rank']},
        {"Nom": "Fatou M.", "Points": 750, "Rang": "📚 Intermédiaire"},
        {"Nom": "Ousmane T.", "Points": 420, "Rang": "🌱 Débutant"}
    ]
    
    df_leaderboard = pd.DataFrame(leaderboard).sort_values('Points', ascending=False)
    st.dataframe(df_leaderboard, use_container_width=True)

# Onglet 5: Paramètres
with tab5:
    st.header("⚙️ Paramètres")
    
    st.subheader("🔔 Rappels automatiques")
    
    col1, col2 = st.columns(2)
    
    with col1:
        reminder_enabled = st.checkbox("Activer les rappels")
        reminder_time = st.time_input("Heure du rappel quotidien")
        reminder_frequency = st.selectbox("Fréquence", ["Quotidien", "3 fois par semaine", "Hebdomadaire"])
    
    with col2:
        st.subheader("🎨 Préférences")
        theme = st.selectbox("Thème", ["Clair", "Sombre"])
        difficulty = st.selectbox("Niveau de difficulté par défaut", ["Facile", "Moyen", "Difficile"])
        language = st.selectbox("Langue", ["Français", "Wolof", "English"])
    
    if st.button("💾 Sauvegarder les paramètres"):
        st.success("✅ Paramètres sauvegardés!")
    
    st.subheader("ℹ️ À propos de RéviZIA")
    st.markdown("""
    **RéviZIA** est une plateforme éducative intelligente développée pour les lycéens africains, 
    reconnue par le Ministère de l'Éducation Nationale du Sénégal.
    
    **Fonctionnalités:**
    - 🤖 IA Gemini de Google pour génération automatique de quiz
    - 🔍 Reconnaissance OCR pour extraction de texte depuis images
    - 🎤 Reconnaissance vocale pour import audio
    - 📊 Suivi détaillé des performances
    - 🎮 Système de gamification avec points et rangs
    - 🔔 Rappels automatiques personnalisables
    
    **Version:** 1.0.0  
    **Développé avec:** Streamlit & IA Gemini (API REST)
    
    **Installation requise:**
    ```bash
    pip install streamlit pandas pillow requests
    ```
    
    **Pas de conflit de dépendances!** 🎉
    """)

# Footer
st.markdown("""
---
<div style="text-align: center; color: #666;">
    <p>🎓 RéviZIA - Plateforme Éducative Intelligente | Reconnu par le Ministère de l'Éducation Nationale du Sénégal</p>
    <p>Propulsé par l'IA Gemini de Google 🤖</p>
</div>
""", unsafe_allow_html=True)