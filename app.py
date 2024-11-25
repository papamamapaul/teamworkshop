from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import qrcode
import io
import base64
import uuid
from models import db, Question, Answer, Survey, QuestionOption

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
        title = request.form.get('title')
        description = request.form.get('description')
        survey = Survey(title=title, description=description)
        db.session.add(survey)
        db.session.commit()
        return redirect(url_for('view_survey', survey_uuid=survey.uuid))
    return render_template('survey_new.html')

# Umfrage anzeigen
@app.route('/surveys/<survey_uuid>')
def view_survey(survey_uuid):
    survey = Survey.query.filter_by(uuid=survey_uuid).first_or_404()
    return render_template('survey_detail.html', survey=survey)

# QR-Code für Umfrage generieren
@app.route('/surveys/<survey_uuid>/qr')
def survey_qr(survey_uuid):
    survey = Survey.query.filter_by(uuid=survey_uuid).first_or_404()
    participate_url = url_for('participate_survey', survey_uuid=survey_uuid, _external=True)
    
    # QR-Code generieren
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(participate_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # QR-Code in Base64 konvertieren
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    
    return render_template('survey_qr.html', survey=survey, qr_code=img_str, participate_url=participate_url)

# Umfrage präsentieren (Host-Ansicht)
@app.route('/surveys/<survey_uuid>/present')
def present_survey(survey_uuid):
    survey = Survey.query.filter_by(uuid=survey_uuid).first_or_404()
    
    # Konvertiere Fragen in ein serialisierbares Format
    questions_data = []
    for question in survey.questions:
        question_data = {
            'id': question.id,
            'text': question.text,
            'type': question.type,
            'options': [{'id': opt.id, 'text': opt.text} for opt in question.options]
        }
        questions_data.append(question_data)
    
    return render_template('survey_present.html', 
                         survey=survey,
                         questions_json=questions_data,
                         is_host=True)

# Umfrage teilnehmen (Teilnehmer-Ansicht)
@app.route('/surveys/<survey_uuid>/participate')
def participate_survey(survey_uuid):
    survey = Survey.query.filter_by(uuid=survey_uuid).first_or_404()
    session['participant_id'] = str(uuid.uuid4())  # Eindeutige ID für jeden Teilnehmer
    
    return render_template('survey_present.html', 
                         survey=survey,
                         is_host=False)

# API-Route für Fragendetails
@app.route('/api/questions/<int:question_id>')
def get_question(question_id):
    question = Question.query.get_or_404(question_id)
    return jsonify({
        'id': question.id,
        'text': question.text,
        'type': question.type,
        'options': [{'id': opt.id, 'text': opt.text} for opt in question.options]
    })

# Socket.IO Events
@socketio.on('host_change_question')
def handle_host_change_question(data):
    survey_uuid = data['survey_uuid']
    question_id = data['question_id']
    # Benachrichtige alle Teilnehmer über die neue aktive Frage
    emit('question_changed', {'question_id': question_id}, broadcast=True, include_self=False)

@socketio.on('submit_answer')
def handle_submit_answer(data):
    survey_uuid = data['survey_uuid']
    question_id = data['question_id']
    answer_text = data.get('answer_text')
    selected_option_id = data.get('selected_option_id')
    participant_id = session.get('participant_id')

    if not participant_id:
        return {'error': 'No participant ID found'}

    # Prüfe, ob bereits eine Antwort existiert
    existing_answer = Answer.query.filter_by(
        question_id=question_id,
        participant_id=participant_id
    ).first()

    if existing_answer:
        return {'error': 'Already answered'}

    # Speichere die neue Antwort
    answer = Answer(
        question_id=question_id,
        text=answer_text,
        selected_option_id=selected_option_id,
        participant_id=participant_id
    )
    db.session.add(answer)
    db.session.commit()

    # Sende die Antwort an den Host
    emit('answer_received', {
        'question_id': question_id,
        'answer': {
            'text': answer_text,
            'selected_option_id': selected_option_id
        }
    }, broadcast=True)

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

if __name__ == '__main__':
    socketio.run(app, debug=True)
