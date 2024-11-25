document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    
    // QR Code generieren
    fetch('/generate-qr')
        .then(response => response.json())
        .then(data => {
            const qrcodeContainer = document.getElementById('qrcode');
            const img = document.createElement('img');
            img.src = 'data:image/png;base64,' + data.qr_code;
            img.classList.add('max-w-xs');
            qrcodeContainer.appendChild(img);
        });

    // Formular für neue Fragen
    const questionForm = document.getElementById('questionForm');
    questionForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const questionText = document.getElementById('questionText').value;
        const questionType = document.getElementById('questionType').value;
        
        socket.emit('new_question', {
            question: questionText,
            type: questionType,
            from_participant: false
        });
        
        questionForm.reset();
    });

    // Neue Fragen empfangen
    socket.on('question_added', function(question) {
        const questionsContainer = document.getElementById('questionsContainer');
        const questionElement = createQuestionElement(question);
        questionsContainer.appendChild(questionElement);
    });

    // Neue Antworten empfangen
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
    div.innerHTML = `
        <div class="card-body">
            <h3 class="card-title text-lg">
                ${question.from_participant ? '👤' : '👨‍💼'} ${escapeHtml(question.text)}
            </h3>
            <div id="answers-${question.id}" class="space-y-2">
                <!-- Antworten werden hier eingefügt -->
            </div>
        </div>
    `;
    return div;
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
