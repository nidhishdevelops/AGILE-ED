from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    quizzes = db.relationship('QuizResult', backref='user', lazy=True)

class QuizResult(db.Model):
    __tablename__ = 'quiz_results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    total_score = db.Column(db.Float)
    max_score = db.Column(db.Float)
    percentage = db.Column(db.Float)
    grade = db.Column(db.String(2))
    mastery_level = db.Column(db.String(20))
    quiz_data = db.Column(db.Text)  # JSON string of questions/answers
    taken_at = db.Column(db.DateTime, default=datetime.utcnow)