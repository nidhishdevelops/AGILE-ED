let currentQuizId = null;
let studentAnswers = {};

document.getElementById('askBtn').addEventListener('click', async () => {
    const query = document.getElementById('queryInput').value.trim();
    if (!query) return;

    document.getElementById('loading').style.display = 'block';
    document.getElementById('askBtn').disabled = true;

    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await response.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        // Display response
        const responseDiv = document.getElementById('responseContent');
        responseDiv.innerHTML = formatResponse(data);
        MathJax.typesetPromise(); // Render LaTeX
        hljs.highlightAll();

        // Store quiz ID
        currentQuizId = data.quiz_id;

        // Move to step 2
        showStep(2);
    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('askBtn').disabled = false;
    }
});

document.getElementById('nextToQuizBtn').addEventListener('click', async () => {
    if (!currentQuizId) return;
    showStep(3);
    // Fetch and render quiz
    const resp = await fetch(`/get_quiz/${currentQuizId}`);
    const quiz = await resp.json();
    renderQuiz(quiz);
    document.getElementById('quizTopic').innerText = quiz.topic;
});

document.getElementById('submitQuizBtn').addEventListener('click', () => {
    // Collect all answers from quiz inputs
    const inputs = document.querySelectorAll('.quiz-question');
    inputs.forEach((questionDiv, idx) => {
        const qid = questionDiv.dataset.qid;
        const type = questionDiv.dataset.type;
        let answer = '';
        if (type === 'mcq') {
            const selected = questionDiv.querySelector('input[type="radio"]:checked');
            answer = selected ? selected.value : '';
        } else if (type === 'true_false') {
            const selected = questionDiv.querySelector('input[type="radio"]:checked');
            answer = selected ? selected.value : '';
        } else if (type === 'short_answer') {
            answer = questionDiv.querySelector('textarea').value;
        } else if (type === 'fill_blanks') {
            const blanks = [];
            questionDiv.querySelectorAll('.blank-input').forEach(inp => blanks.push(inp.value));
            answer = blanks.join(',');
        } else if (type === 'code_completion') {
            answer = questionDiv.querySelector('textarea').value;
        } else if (type === 'numerical_problem') {
            answer = questionDiv.querySelector('input').value;
        } else {
            answer = questionDiv.querySelector('input, textarea').value;
        }
        studentAnswers[qid] = answer;
    });
    // Move to email step
    showStep(4);
});

document.getElementById('sendEmailBtn').addEventListener('click', async () => {
    const email = document.getElementById('studentEmail').value.trim();
    if (!email || !email.includes('@')) {
        alert('Please enter a valid email address.');
        return;
    }
    const btn = document.getElementById('sendEmailBtn');
    btn.disabled = true;
    btn.innerText = 'Sending...';

    try {
        const resp = await fetch('/evaluate_quiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                quiz_id: currentQuizId,
                answers: studentAnswers,
                email: email
            })
        });
        const result = await resp.json();
        if (result.error) {
            alert(result.error);
            return;
        }
        const message = `Score: ${result.score}/${result.max_score} (${result.percentage}%) - Grade ${result.grade}. ${result.email_sent ? 'Assessment emailed!' : 'Email sending failed.'} Mastery: ${result.mastery_level}`;
        document.getElementById('resultMessage').innerText = message;
        showStep(5);
    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerText = 'Send Assessment →';
    }
});

function showStep(step) {
    for (let i = 1; i <= 5; i++) {
        const el = document.getElementById(`step${i}`);
        if (el) el.style.display = i === step ? 'block' : 'none';
    }
}

function formatResponse(data) {
    let html = `<h2>${escapeHtml(data.topic)}</h2>`;
    html += `<p><strong>Learning Style:</strong> ${escapeHtml(data.learning_style)} | <strong>LLM:</strong> ${escapeHtml(data.llm_used)}</p>`;
    
    // Main explanation
    html += `<div class="explanation">${marked(data.explanation)}</div>`;
    
    // Sources (from RAG)
    if (data.sources && data.sources.length) {
        html += `<h3>Sources</h3><ul>`;
        data.sources.forEach(s => {
            html += `<li>${escapeHtml(s.original_file)} (${escapeHtml(s.location)})</li>`;
        });
        html += `</ul>`;
    }
    
    // Recent Advancements
    if (data.recent_advancements && data.recent_advancements.length) {
        html += `<h3>Recent Advancements</h3><ul>`;
        data.recent_advancements.forEach(adv => {
            html += `<li><strong>${escapeHtml(adv.title)}</strong><br>`;
            html += `${escapeHtml(adv.summary)}<br>`;
            html += `<small>Source: ${escapeHtml(adv.source)} | ${escapeHtml(adv.date)}</small><br>`;
            if (adv.link) html += `<a href="${adv.link}" target="_blank">Read more →</a>`;
            html += `</li>`;
        });
        html += `</ul>`;
    }
    
    // Research Papers
    if (data.research_papers && data.research_papers.length) {
        html += `<h3>Research Papers</h3><ul>`;
        data.research_papers.forEach(paper => {
            html += `<li><strong>${escapeHtml(paper.title)}</strong><br>`;
            html += `Authors: ${escapeHtml(paper.authors)} (${escapeHtml(paper.year)})<br>`;
            html += `${escapeHtml(paper.summary)}<br>`;
            if (paper.link) html += `<a href="${paper.link}" target="_blank">Access paper →</a>`;
            html += `</li>`;
        });
        html += `</ul>`;
    }
    
    // YouTube Videos
    if (data.video_recommendations && data.video_recommendations.length) {
        html += `<h3>Recommended Videos</h3><ul>`;
        data.video_recommendations.forEach(v => {
            html += `<li><a href="https://youtu.be/${v.video_id}" target="_blank">${escapeHtml(v.title)}</a> - ${escapeHtml(v.channel)}</li>`;
        });
        html += `</ul>`;
    }
    
    // Reference Books
    if (data.reference_books && data.reference_books.length) {
        html += `<h3>Reference Books</h3><ul>`;
        data.reference_books.forEach(book => {
            html += `<li><strong>${escapeHtml(book.title)}</strong> by ${escapeHtml(book.authors)} (${escapeHtml(book.year)})<br>`;
            html += `${escapeHtml(book.description)}<br>`;
            if (book.link) html += `<a href="${book.link}" target="_blank">View book →</a>`;
            html += `</li>`;
        });
        html += `</ul>`;
    }
    
    return html;
}

function renderQuiz(quiz) {
    const container = document.getElementById('quizContainer');
    container.innerHTML = '';
    quiz.questions.forEach(q => {
        const div = document.createElement('div');
        div.className = 'quiz-question';
        div.dataset.qid = q.id;
        div.dataset.type = q.type;
        let inner = `<p><strong>Q${q.id}. ${q.question}</strong> (${q.max_score} pts)</p>`;
        switch (q.type) {
            case 'mcq':
                inner += `<div class="options">`;
                for (let [opt, text] of Object.entries(q.options)) {
                    inner += `<label><input type="radio" name="q${q.id}" value="${opt}"> ${opt}) ${text}</label><br>`;
                }
                inner += `</div>`;
                break;
            case 'true_false':
                inner += `<div class="options">
                            <label><input type="radio" name="q${q.id}" value="true"> True</label><br>
                            <label><input type="radio" name="q${q.id}" value="false"> False</label>
                          </div>`;
                break;
            case 'short_answer':
                inner += `<textarea rows="3" class="answer-input" data-qid="${q.id}"></textarea>`;
                break;
            case 'fill_blanks':
                if (q.blanks) {
                    q.blanks.forEach((blank, idx) => {
                        inner += `<p>Blank ${idx+1}: <input type="text" class="blank-input" placeholder="Answer ${idx+1}"></p>`;
                    });
                } else {
                    inner += `<input type="text" class="answer-input" placeholder="Your answers (comma separated)">`;
                }
                break;
            case 'code_completion':
                inner += `<pre><code>${escapeHtml(q.incomplete_code || '')}</code></pre>`;
                inner += `<textarea rows="6" class="answer-input" placeholder="Write your code here..."></textarea>`;
                break;
            case 'numerical_problem':
                inner += `<input type="text" class="answer-input" placeholder="Your numerical answer">`;
                break;
            default:
                inner += `<input type="text" class="answer-input">`;
        }
        div.innerHTML = inner;
        container.appendChild(div);
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// Simple markdown parser (for bold, lists, code blocks)
function marked(text) {
    if (!text) return '';
    // Code blocks
    text = text.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code class="language-${lang || 'plaintext'}">${escapeHtml(code)}</code></pre>`;
    });
    // Inline code
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Headers
    text = text.replace(/^### (.*$)/gm, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gm, '<h2>$1</h2>');
    text = text.replace(/^# (.*$)/gm, '<h1>$1</h1>');
    // Bold
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Lists
    text = text.replace(/^\s*-\s+(.*$)/gm, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    // Paragraphs
    text = text.replace(/\n\n/g, '</p><p>');
    text = '<p>' + text + '</p>';
    return text;
}