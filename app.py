import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_migrate import Migrate
import qrcode
from io import BytesIO
import base64
from models import db, Question, Answer
from config import config

app = Flask(__name__)
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])

db.init_app(app)
migrate = Migrate(app, db)
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/host')
def host():
    """Host view for creating questions"""
    return render_template('host.html')

@app.route('/participate')
def participate():
    """Participant view for answering questions"""
    return render_template('participate.html')

@app.route('/generate-qr')
def generate_qr():
    """Generate QR code for the participation URL"""
    url = request.host_url + "participate"
    img = qrcode.make(url)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return jsonify({'qr_code': img_str})

@socketio.on('new_question')
def handle_new_question(data):
    """Handle new questions from host or participants"""
    question = Question(
        text=data['question'],
        type=data.get('type', 'text'),
        from_participant=data.get('from_participant', False)
    )
    db.session.add(question)
    db.session.commit()
    
    emit('question_added', {
        'id': question.id,
        'text': question.text,
        'type': question.type,
        'from_participant': question.from_participant
    }, broadcast=True)

@socketio.on('new_answer')
def handle_new_answer(data):
    """Handle new answers from participants"""
    answer = Answer(
        text=data['answer'],
        question_id=data['question_id']
    )
    db.session.add(answer)
    db.session.commit()
    
    question = Question.query.get(data['question_id'])
    answers = [a.text for a in question.answers]
    
    emit('answer_added', {
        'question_id': data['question_id'],
        'answers': answers
    }, broadcast=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.getenv('PORT', 8080))
    socketio.run(app, 
                debug=os.getenv('FLASK_ENV') == 'development',
                host='0.0.0.0',
                port=port,
                allow_unsafe_werkzeug=True)
