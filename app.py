from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import uuid
import json
from terminal_app import handle_query, generate_quiz, evaluate_and_send_assessment
from agents.quiz_agent import QuizGenerator, QuizEvaluator
from database.models import db, User, QuizResult
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    app.secret_key = 'dev-key-change-in-production'  # fallback
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Render provides a postgres:// URL, but SQLAlchemy requires postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///learning_system.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

quiz_store = {}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables (run once)
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Username taken'}), 400
    
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, username=username, password_hash=hashed)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({'success': True})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

@app.route('/history')
@login_required
def history():
    quizzes = QuizResult.query.filter_by(user_id=current_user.id).order_by(QuizResult.taken_at.desc()).all()
    return render_template('history.html', quizzes=quizzes)

@app.route('/ask', methods=['POST'])
@login_required
def ask():
    data = request.get_json()
    query = data.get('query', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    response = handle_query(query)
    if response['status'] != 'success':
        return jsonify({'error': response.get('message', 'Unknown error')}), 400

    quiz = generate_quiz(response['topic'], response['explanation'])
    quiz_id = str(uuid.uuid4())
    quiz_store[quiz_id] = {
        'quiz': quiz,
        'topic': response['topic'],
        'explanation': response['explanation']
    }

    return jsonify({
        'status': 'success',
        'topic': response['topic'],
        'module': response['module'],
        'learning_style': response['learning_style'],
        'llm_used': response['llm_used'],
        'explanation': response['explanation'],
        'sources': response['sources'][:5],
        'recent_advancements': response.get('recent_advancements', []),
        'research_papers': response.get('research_papers', []),
        'video_recommendations': response.get('video_recommendations', []),
        'reference_books': response.get('reference_books_web', []),
        'quiz_id': quiz_id
    })

@app.route('/get_quiz/<quiz_id>', methods=['GET'])
@login_required
def get_quiz(quiz_id):
    if quiz_id not in quiz_store:
        return jsonify({'error': 'Quiz not found'}), 404
    quiz = quiz_store[quiz_id]['quiz']
    quiz_data = {
        'topic': quiz['topic'],
        'difficulty': quiz['difficulty'],
        'questions': []
    }
    for q in quiz['questions']:
        q_data = {
            'id': q['id'],
            'type': q['type'],
            'question': q.get('question') or q.get('statement') or q.get('problem') or q.get('text'),
            'options': q.get('options'),
            'statement': q.get('statement'),
            'incomplete_code': q.get('incomplete_code'),
            'expected_output': q.get('expected_output'),
            'blanks': q.get('blanks'),
            'max_score': q.get('max_score', 1)
        }
        quiz_data['questions'].append(q_data)
    return jsonify(quiz_data)

@app.route('/evaluate_quiz', methods=['POST'])
@login_required
def evaluate_quiz():
    data = request.get_json()
    quiz_id = data.get('quiz_id')
    student_answers = data.get('answers', {})
    student_email = data.get('email', current_user.email)

    if quiz_id not in quiz_store:
        return jsonify({'error': 'Quiz session expired'}), 400

    quiz = quiz_store[quiz_id]['quiz']
    evaluator = QuizEvaluator()
    result = evaluator.evaluate_answers(quiz, student_answers, student_email)

    # Save to database
    quiz_result = QuizResult(
        user_id=current_user.id,
        topic=quiz['topic'],
        total_score=result['total_score'],
        max_score=result['max_score'],
        percentage=result['percentage'],
        grade=result['grade'],
        mastery_level=result['assessment'].get('mastery_level', 'Unknown'),
        quiz_data=json.dumps({
            'questions': quiz['questions'],
            'answers': student_answers,
            'result': result
        })
    )
    db.session.add(quiz_result)
    db.session.commit()

    # Send email
    email_sent = evaluate_and_send_assessment(quiz, student_answers, student_email)
    if isinstance(email_sent, tuple):
        result, email_sent = email_sent

    del quiz_store[quiz_id]

    return jsonify({
        'score': result['total_score'],
        'max_score': result['max_score'],
        'percentage': result['percentage'],
        'grade': result['grade'],
        'email_sent': email_sent,
        'mastery_level': result['assessment'].get('mastery_level', 'Not assessed')
    })

@app.route('/mastery')
@login_required
def mastery():
    # Get all quizzes for the user
    quizzes = QuizResult.query.filter_by(user_id=current_user.id).all()
    
    # Calculate overall mastery
    if quizzes:
        avg_percentage = sum(q.percentage for q in quizzes) / len(quizzes)
    else:
        avg_percentage = 0
    
    # Group by topic
    topic_mastery = {}
    for q in quizzes:
        if q.topic not in topic_mastery:
            topic_mastery[q.topic] = {'scores': [], 'mastery': q.mastery_level}
        topic_mastery[q.topic]['scores'].append(q.percentage)
    
    # Prepare data for template
    topic_summary = []
    for topic, data in topic_mastery.items():
        avg_score = sum(data['scores']) / len(data['scores'])
        topic_summary.append({
            'topic': topic,
            'avg_score': avg_score,
            'level': data['mastery'],
            'attempts': len(data['scores'])
        })
    
    # Get weak topics (score < 70%)
    weak_topics = [t for t in topic_summary if t['avg_score'] < 70]
    
    return render_template('mastery.html', 
                         avg_percentage=avg_percentage,
                         topic_summary=topic_summary,
                         weak_topics=weak_topics,
                         total_quizzes=len(quizzes))

@app.route('/test_email')
def test_email():
    from agents.email_agent import send_notification
    success = send_notification("Test Subject", "<p>Test body</p>", "your_test_email@gmail.com")
    return f"Email sent: {success}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)