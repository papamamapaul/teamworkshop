from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import uuid

db = SQLAlchemy()

class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')  # 'active' or 'completed'
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    questions = db.relationship('Question', backref='survey', lazy=True, cascade='all, delete-orphan')
    
    @property
    def total_participants(self):
        return len(set([answer.participant_id for question in self.questions for answer in question.answers]))
    
    @property
    def last_answer_time(self):
        latest_answer = None
        for question in self.questions:
            for answer in question.answers:
                if latest_answer is None or answer.created_at > latest_answer.created_at:
                    latest_answer = answer
        return latest_answer.created_at if latest_answer else None

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(20), nullable=False, default='text')  # 'text' or 'choice'
    options = db.Column(db.JSON)  # Store options for multiple choice questions
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    answers = db.relationship('Answer', back_populates='question', lazy=True, cascade='all, delete-orphan')

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    participant_id = db.Column(db.String(36), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    question = db.relationship('Question', back_populates='answers')
