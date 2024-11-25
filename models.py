from datetime import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    questions = db.relationship('Question', backref='survey', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='text')  # 'text' oder 'choice'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    options = db.relationship('QuestionOption', back_populates='question', cascade='all, delete-orphan')
    answers = db.relationship('Answer', back_populates='question', cascade='all, delete-orphan')

class QuestionOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)

    question = db.relationship('Question', back_populates='options')

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.Text)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('question_option.id'))
    participant_id = db.Column(db.String(36), nullable=False)  # UUID für Teilnehmer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    question = db.relationship('Question', back_populates='answers')
    selected_option = db.relationship('QuestionOption')
