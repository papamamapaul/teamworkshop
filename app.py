import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import qrcode
import io
import base64
import uuid
from datetime import datetime
from sqlalchemy import func, distinct

from models import db, Question, Answer, Survey

app = Flask(__name__)
app.config['SECRET_KEY'] = 'geheim!'  # In Produktion durch sichere Umgebungsvariable ersetzen
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///workshop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Hauptseite
@app.route('/')
def index():
    return render_template('index.html')

# Umfragen-Übersicht
@app.route('/surveys')
def list_surveys():
    surveys = Survey.query.all()
    return render_template('surveys.html', surveys=surveys)

# Neue Umfrage erstellen
@app.route('/surveys/new', methods=['GET', 'POST'])
def new_survey():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        
        survey = Survey(title=title, description=description, status='active')
        db.session.add(survey)
        db.session.flush()  # Get survey ID
        
        # Process questions
        i = 0
        while True:
            question_text = request.form.get(f'questions[{i}][text]')
            if question_text is None:
                break
                
            question_type = request.form.get(f'questions[{i}][type]', 'text')
            options = request.form.getlist(f'questions[{i}][options][]') if question_type == 'choice' else None
            
            question = Question(
                survey_id=survey.id,
                text=question_text,
                type=question_type,
                options=options
            )
            db.session.add(question)
            i += 1
        
        db.session.commit()
        flash('Umfrage wurde erfolgreich erstellt!', 'success')
        return redirect(url_for('list_surveys'))
    
    return render_template('survey_new.html')

# Umfrage anzeigen
@app.route('/surveys/<survey_uuid>')
def view_survey(survey_uuid):
    survey = Survey.query.filter_by(uuid=survey_uuid).first_or_404()
    return render_template('survey_detail.html', survey=survey)

# Umfrage Ergebnisse anzeigen
@app.route('/surveys/<survey_uuid>/results')
def view_survey_results(survey_uuid):
    survey = Survey.query.filter_by(uuid=survey_uuid).first_or_404()
    
    # Sammle Statistiken für jede Frage
    questions_data = []
    for question in survey.questions:
        answers = question.answers
        question_data = {
            'text': question.text,
            'total_answers': len(answers),
            'answers': [{'text': answer.text, 'created_at': answer.created_at} for answer in answers]
        }
        questions_data.append(question_data)
    
    return render_template('survey_results.html', 
                         survey=survey,
                         questions_data=questions_data)

# Umfrage abschließen
@app.route('/surveys/<survey_uuid>/complete', methods=['POST'])
def complete_survey(survey_uuid):
    survey = Survey.query.filter_by(uuid=survey_uuid).first_or_404()
    survey.status = 'completed'
    survey.completed_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('view_survey_results', survey_uuid=survey_uuid))

# QR-Code für Umfrage generieren
@app.route('/surveys/<survey_uuid>/qr')
def survey_qr(survey_uuid):
    survey = Survey.query.filter_by(uuid=survey_uuid).first_or_404()
    participate_url = request.url_root + url_for('participate_survey', survey_uuid=survey_uuid)
    
    # QR-Code generieren
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(participate_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # QR-Code in Base64 konvertieren
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    
    return jsonify({
        'qr_code': f'data:image/png;base64,{img_str}',
        'participate_url': participate_url
    })

def generate_qr_code(url):
    import qrcode
    import io
    import base64
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_code = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{qr_code}"

# Umfrage präsentieren (Host-Ansicht)
@app.route('/surveys/<survey_uuid>/present')
def present_survey(survey_uuid):
    survey = Survey.query.filter_by(uuid=survey_uuid).first_or_404()
    
    # Generate QR code
    qr_code = generate_qr_code(request.url_root + url_for('participate_survey', survey_uuid=survey_uuid))
    
    # Format questions for the template
    questions_data = []
    for question in survey.questions:
        question_data = {
            'id': question.id,
            'text': question.text,
            'type': question.type
        }
        if question.type == 'choice' and question.options:
            # Format each option as a dict with id and text
            question_data['options'] = [{'id': i, 'text': opt} for i, opt in enumerate(question.options)]
        questions_data.append(question_data)
    
    return render_template('present_survey.html', 
                         survey=survey,
                         questions=questions_data,
                         qr_code=qr_code)

# Umfrage teilnehmen (Teilnehmer-Ansicht)
@app.route('/surveys/<survey_uuid>/participate')
def participate_survey(survey_uuid):
    survey = Survey.query.filter_by(uuid=survey_uuid).first_or_404()
    
    # Generate unique participant ID if not exists
    if 'participant_id' not in session:
        session['participant_id'] = str(uuid.uuid4())
    
    # Format questions for the template
    questions_data = []
    for question in survey.questions:
        question_data = {
            'id': question.id,
            'text': question.text,
            'type': question.type
        }
        if question.type == 'choice' and question.options:
            question_data['options'] = [{'id': i, 'text': opt} for i, opt in enumerate(question.options)]
        questions_data.append(question_data)
    
    return render_template('participate_survey.html', 
                         survey=survey,
                         questions=questions_data,
                         participant_id=session['participant_id'])

# API-Route für Fragendetails
@app.route('/api/questions/<int:question_id>')
def get_question(question_id):
    question = Question.query.get_or_404(question_id)
    question_data = {
        'id': question.id,
        'text': question.text,
        'type': question.type
    }
    if question.type == 'choice' and question.options:
        question_data['options'] = [{'id': i, 'text': opt} for i, opt in enumerate(question.options)]
    return jsonify(question_data)

# API-Route für Fragendetails und Ergebnisse
@app.route('/questions/<int:question_id>/results')
def get_question_results(question_id):
    question = Question.query.get_or_404(question_id)
    answers = Answer.query.filter_by(question_id=question_id).all()
    
    # Count unique participants
    participant_count = db.session.query(func.count(distinct(Answer.participant_id))).\
        filter(Answer.question_id == question_id).scalar()
    
    if question.type == 'choice':
        # For choice questions, return yes/no counts
        yes_count = sum(1 for a in answers if a.text.lower() == 'ja')
        no_count = sum(1 for a in answers if a.text.lower() == 'nein')
        
        return jsonify({
            'participant_count': participant_count,
            'yes_count': yes_count,
            'no_count': no_count
        })
    else:
        # For text questions, return all answers without participant IDs
        return jsonify({
            'participant_count': participant_count,
            'answers': [{'text': a.text} for a in answers]
        })

# Socket.IO Events
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    print(f'Client joined room: {room}')

@socketio.on('host_change_question')
def handle_host_change_question(data):
    survey_uuid = data['survey_uuid']
    question_id = data['question_id']
    print(f'Host changing active question to {question_id} in survey {survey_uuid}')
    emit('update_question', {'question_id': question_id}, room=survey_uuid)

@socketio.on('submit_answer')
def handle_submit_answer(data):
    survey_uuid = data.get('survey_uuid')
    question_id = data.get('question_id')
    participant_id = data.get('participant_id')
    answer_text = data.get('text', '').lower()  # Convert to lowercase for consistent comparison
    answer_type = data.get('type')
    
    if all([survey_uuid, question_id, participant_id, answer_text]):
        # Save answer to database
        answer = Answer(
            question_id=question_id,
            participant_id=participant_id,
            text=answer_text
        )
        db.session.add(answer)
        db.session.commit()
        
        # Get updated statistics
        question = Question.query.get(question_id)
        survey = Survey.query.filter_by(uuid=survey_uuid).first()
        
        if question and survey:
            # Count total participants for this survey
            participant_count = db.session.query(func.count(distinct(Answer.participant_id))).\
                join(Question).\
                filter(Question.survey_id == survey.id).scalar()
            
            # Count answers for current question
            answers = Answer.query.filter_by(question_id=question_id).all()
            
            # For choice questions, count yes/no answers
            if answer_type == 'choice':
                yes_count = sum(1 for a in answers if a.text.lower() == 'ja')
                no_count = sum(1 for a in answers if a.text.lower() == 'nein')
                
                print(f'Choice answer stats for question {question_id}:')
                print(f'- Total participants: {participant_count}')
                print(f'- Yes answers: {yes_count}')
                print(f'- No answers: {no_count}')
                
                # Emit updated statistics for choice questions
                socketio.emit('update_stats', {
                    'participant_count': participant_count,
                    'yes_count': yes_count,
                    'no_count': no_count
                }, room=survey_uuid)
            else:
                # For text questions, emit the new answer
                print(f'Text answer received for question {question_id}:')
                print(f'- Answer: {answer_text}')
                print(f'- Participant: {participant_id}')
                
                socketio.emit('new_answer', {
                    'question_id': question_id,
                    'text': answer_text,
                    'participant_id': participant_id
                }, room=survey_uuid)

@socketio.on('show_question')
def handle_show_question(data):
    survey_uuid = data.get('survey_uuid')
    question_id = data.get('question_id')
    
    # Get the question text
    question = Question.query.get(question_id)
    if question:
        socketio.emit('update_question', {
            'question_id': question_id,
            'text': question.text
        }, room=survey_uuid)

@socketio.on('leave')
def on_leave(data):
    room = data['survey_uuid']
    leave_room(room)

@socketio.on('new_question')
def handle_new_question(data):
    survey_uuid = data['survey_uuid']
    text = data['text']
    question_type = data.get('type', 'text')
    options = data.get('options', [])
    
    survey = Survey.query.filter_by(uuid=survey_uuid).first()
    if survey:
        # Erstelle die neue Frage
        question = Question(text=text, type=question_type, survey=survey)
        db.session.add(question)
        db.session.flush()  # Damit wir die question.id haben
        
        # Erstelle die Antwortoptionen für Multiple-Choice-Fragen
        question_options = []
        if question_type == 'choice' and options:
            for i, option_text in enumerate(options):
                option = QuestionOption(
                    question_id=question.id,
                    text=option_text,
                    order=i
                )
                db.session.add(option)
                question_options.append({
                    'id': option.id,
                    'text': option.text
                })
        
        db.session.commit()
        
        # Sende die aktualisierte Frage an alle Clients
        emit('questions_updated', {
            'survey_uuid': survey_uuid,
            'question': {
                'id': question.id,
                'text': question.text,
                'type': question.type,
                'options': question_options
            }
        }, broadcast=True)

@socketio.on('new_answer')
def handle_new_answer(data):
    question_id = data['question_id']
    text = data.get('text')
    selected_option_id = data.get('selected_option_id')
    
    question = Question.query.get(question_id)
    if question:
        answer = Answer(
            question=question,
            text=text if question.type == 'text' else None,
            selected_option_id=selected_option_id if question.type == 'choice' else None
        )
        db.session.add(answer)
        db.session.commit()
        
        emit('answers_updated', {
            'question_id': question_id,
            'answer': {
                'id': answer.id,
                'text': answer.text,
                'selected_option_id': answer.selected_option_id
            }
        }, broadcast=True)

@app.route('/surveys/<survey_uuid>/delete', methods=['POST'])
def delete_survey(survey_uuid):
    survey = Survey.query.filter_by(uuid=survey_uuid).first_or_404()
    
    # Delete associated answers
    Answer.query.filter(Answer.question_id.in_([q.id for q in survey.questions])).delete(synchronize_session=False)
    
    # Delete associated questions
    Question.query.filter_by(survey_id=survey.id).delete()
    
    # Delete the survey
    db.session.delete(survey)
    db.session.commit()
    
    flash('Umfrage wurde erfolgreich gelöscht', 'success')
    return redirect(url_for('surveys'))

if __name__ == '__main__':
    socketio.run(app, debug=True)
