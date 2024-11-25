document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    
    // Formular für Teilnehmerfragen
    const participantQuestionForm = document.getElementById('participantQuestionForm');
    participantQuestionForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const questionText = document.getElementById('participantQuestionText').value;
        
        socket.emit('new_question', {
            question: questionText,
            type: 'text',
            from_participant: true
        });
        
        participantQuestionForm.reset();
    });

    // Neue Fragen empfangen
    socket.on('question_added', function(question) {
        const activeQuestions = document.getElementById('activeQuestions');
        const questionElement = createQuestionElement(question);
        activeQuestions.appendChild(questionElement);
    });

    // Bestehende Fragen aktualisieren
    socket.on('answer_added', function(data) {
        const answersContainer = document.querySelector(`#answers-${data.question_id}`);
        if (answersContainer) {
            updateAnswers(answersContainer, data.answers);
        }
    });
});

function createQuestionElement(question) {
    const div = document.createElement('div');
    div.className = 'card bg-base-200 shadow-sm';
    
    const answerForm = question.type === 'text' 
        ? createTextAnswerForm(question.id)
        : createChoiceAnswerForm(question.id);
    
    div.innerHTML = `
        <div class="card-body">
            <h3 class="card-title text-lg">
                ${question.from_participant ? '👤' : '👨‍💼'} ${escapeHtml(question.text)}
            </h3>
            ${answerForm}
            <div id="answers-${question.id}" class="space-y-2 mt-4">
                <!-- Antworten werden hier eingefügt -->
            </div>
        </div>
    `;

    // Event Listener für das Antwortformular
    const form = div.querySelector(`#answerForm-${question.id}`);
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const answer = question.type === 'text'
            ? div.querySelector(`#answerText-${question.id}`).value
            : div.querySelector(`input[name="choice-${question.id}"]:checked`).value;
        
        socket.emit('new_answer', {
            question_id: question.id,
            answer: answer
        });
        
        form.reset();
    });

    return div;
}

function createTextAnswerForm(questionId) {
    return `
        <form id="answerForm-${questionId}" class="space-y-4">
            <div class="form-control">
                <input type="text" id="answerText-${questionId}" 
                    class="input input-bordered" 
                    placeholder="Ihre Antwort" required>
            </div>
            <button type="submit" class="btn btn-primary">Antwort senden</button>
        </form>
    `;
}

function createChoiceAnswerForm(questionId) {
    // Hier könnte man später die Optionen dynamisch laden
    const options = ['Option 1', 'Option 2', 'Option 3'];
    
    return `
        <form id="answerForm-${questionId}" class="space-y-4">
            ${options.map((option, index) => `
                <div class="form-control">
                    <label class="label cursor-pointer">
                        <span class="label-text">${escapeHtml(option)}</span>
                        <input type="radio" name="choice-${questionId}" 
                            value="${escapeHtml(option)}" 
                            class="radio" 
                            ${index === 0 ? 'required' : ''}>
                    </label>
                </div>
            `).join('')}
            <button type="submit" class="btn btn-primary">Auswahl bestätigen</button>
        </form>
    `;
}

function updateAnswers(container, answers) {
    container.innerHTML = answers.map(answer => `
        <div class="bg-base-100 p-2 rounded">
            ${escapeHtml(answer)}
        </div>
    `).join('');
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
