// ─── State ───────────────────────────────────────────────────────────────────
let currentSteps = null;
let quizData = [];
let quizIndex = 0;
let quizScore = 0;
let quizAnswered = false;

// ─── Tab Switching ───────────────────────────────────────────────────────────
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`tab-${tabName}`).classList.add('active');
}

// ─── Toggle Initial Conditions ───────────────────────────────────────────────
function toggleInitial() {
    const checked = document.getElementById('toggleInitial').checked;
    const ic = document.getElementById('initialConditions');
    if (checked) {
        ic.classList.add('show');
    } else {
        ic.classList.remove('show');
    }
}

// ─── Example Click ───────────────────────────────────────────────────────────
function useExample(expr) {
    document.getElementById('equationInput').value = expr;
}

// ─── Solve ───────────────────────────────────────────────────────────────────
async function solveEquation() {
    const btn = document.getElementById('solveBtn');
    const resultArea = document.getElementById('resultArea');
    const equation = document.getElementById('equationInput').value.trim();

    if (!equation) {
        showError('Masukkan persamaan terlebih dahulu.');
        return;
    }

    const useInitial = document.getElementById('toggleInitial').checked;
    const x0 = useInitial ? parseFloat(document.getElementById('x0Input').value) : null;
    const y0 = useInitial ? parseFloat(document.getElementById('y0Input').value) : null;

    if (useInitial && (isNaN(x0) || isNaN(y0) || x0 === 0)) {
        showError('Masukkan syarat awal yang valid (x₀ ≠ 0).');
        return;
    }

    // Loading state
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Menghitung...';
    resultArea.classList.remove('show');

    try {
        const res = await fetch('/api/solve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ equation, useInitial, x0, y0 })
        });

        const data = await res.json();

        if (data.error) {
            showError(data.error);
            if (data.steps) {
                currentSteps = data.steps;
                renderSteps(data.steps);
            }
        } else {
            showResult(data);
            currentSteps = data.steps;
            renderSteps(data.steps);
        }
    } catch (err) {
        showError('Gagal terhubung ke server: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🚀 Hitung Solusi';
    }
}

function showError(msg) {
    const resultArea = document.getElementById('resultArea');
    resultArea.innerHTML = `
        <div class="result-box error">
            <div class="result-label">⚠️ Error</div>
            <div class="result-math">${msg}</div>
        </div>
    `;
    resultArea.classList.add('show');
}

function showResult(data) {
    const resultArea = document.getElementById('resultArea');
    let html = '';

    // General solution
    html += `
        <div class="result-box solution">
            <div class="result-label">✅ Solusi Umum</div>
            <div class="result-math">\\(${data.solution_latex}\\)</div>
        </div>
    `;

    // C expression
    if (data.c_expression) {
        html += `
            <div class="result-box c-value">
                <div class="result-label">📐 Konstanta</div>
                <div class="result-math">\\(${data.c_expression}\\)</div>
            </div>
        `;
    }

    // Particular solution
    if (data.c_value) {
        html += `
            <div class="result-box c-value">
                <div class="result-label">🎯 Nilai C (Syarat Awal)</div>
                <div class="result-math">\\(C = ${data.c_value}\\)</div>
            </div>
        `;
    }
    if (data.particular) {
        html += `
            <div class="result-box solution">
                <div class="result-label">📌 Solusi Khusus</div>
                <div class="result-math">\\(${data.particular}\\)</div>
            </div>
        `;
    }

    resultArea.innerHTML = html;
    resultArea.classList.add('show');

    // Re-render MathJax
    if (window.MathJax) {
        MathJax.typesetPromise([resultArea]);
    }
}

// ─── Steps Rendering ─────────────────────────────────────────────────────────
function renderSteps(steps) {
    const container = document.getElementById('stepsContainer');
    if (!steps || steps.length === 0) {
        container.innerHTML = `
            <div class="steps-placeholder">
                <div class="icon-big">📝</div>
                <p>Belum ada langkah penyelesaian.<br>Selesaikan soal di tab Kalkulator terlebih dahulu.</p>
            </div>
        `;
        return;
    }

    let html = '';
    steps.forEach((step, i) => {
        html += `
            <div class="step-card" style="animation-delay: ${i * 0.1}s">
                <div class="step-number">${i + 1}</div>
                <div class="step-title">${step.title}</div>
                <div class="step-math">\\(${step.latex}\\)</div>
                ${step.latex2 ? `<div class="step-math">\\(${step.latex2}\\)</div>` : ''}
                ${step.result ? `<div class="step-result">${step.result}</div>` : ''}
            </div>
        `;
    });

    container.innerHTML = html;

    if (window.MathJax) {
        MathJax.typesetPromise([container]);
    }
}

// ─── Quiz ────────────────────────────────────────────────────────────────────
async function loadQuiz() {
    try {
        const res = await fetch('/api/quiz');
        quizData = await res.json();
        quizIndex = 0;
        quizScore = 0;
        quizAnswered = false;
        renderQuestion();
    } catch (err) {
        console.error('Failed to load quiz:', err);
    }
}

function renderQuestion() {
    const container = document.getElementById('quizContainer');
    const resultDiv = document.getElementById('quizResult');
    resultDiv.classList.remove('show');

    if (quizIndex >= quizData.length) {
        showQuizResult();
        return;
    }

    const q = quizData[quizIndex];
    const letters = ['A', 'B', 'C', 'D', 'E'];
    const progress = ((quizIndex) / quizData.length) * 100;

    let html = `
        <div class="quiz-header">
            <div class="quiz-progress">
                <div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div>
                <span>${quizIndex + 1} / ${quizData.length}</span>
            </div>
            <div class="quiz-score">Skor: <span class="score-num">${quizScore}</span></div>
        </div>
        <div class="question-card">
            <div class="question-number">Soal ${quizIndex + 1}</div>
            <div class="question-text">${q.question}</div>
            <div class="options-list" id="optionsList">
    `;

    q.options.forEach((opt, i) => {
        html += `
            <button class="option-btn" onclick="selectAnswer(${i})" id="opt-${i}">
                <span class="option-letter">${letters[i]}</span>
                <span>${opt}</span>
            </button>
        `;
    });

    html += `
            </div>
            <div class="explanation-box" id="explanationBox">
                <div class="expl-title">Penjelasan</div>
                <div class="expl-text" id="explanationText"></div>
            </div>
            <div class="quiz-nav">
                <button class="btn btn-primary" id="nextBtn" style="display:none" onclick="nextQuestion()">
                    ${quizIndex < quizData.length - 1 ? 'Soal Berikutnya →' : 'Lihat Hasil 🏆'}
                </button>
            </div>
        </div>
    `;

    container.innerHTML = html;
    quizAnswered = false;

    if (window.MathJax) {
        MathJax.typesetPromise([container]);
    }
}

function selectAnswer(idx) {
    if (quizAnswered) return;
    quizAnswered = true;

    const q = quizData[quizIndex];
    const correct = q.answer;

    // Highlight
    if (idx === correct) {
        document.getElementById(`opt-${idx}`).classList.add('correct');
        quizScore++;
    } else {
        document.getElementById(`opt-${idx}`).classList.add('wrong');
        document.getElementById(`opt-${correct}`).classList.add('correct');
    }

    // Disable all
    document.querySelectorAll('.option-btn').forEach(b => b.disabled = true);

    // Show explanation
    const explBox = document.getElementById('explanationBox');
    document.getElementById('explanationText').innerHTML = q.explanation;
    explBox.classList.add('show');

    // Show next button
    document.getElementById('nextBtn').style.display = 'inline-flex';

    // Update score display
    document.querySelector('.score-num').textContent = quizScore;

    if (window.MathJax) {
        MathJax.typesetPromise([explBox]);
    }
}

function nextQuestion() {
    quizIndex++;
    renderQuestion();
}

function showQuizResult() {
    const container = document.getElementById('quizContainer');
    container.innerHTML = '';

    const resultDiv = document.getElementById('quizResult');
    const pct = Math.round((quizScore / quizData.length) * 100);

    let msg, desc;
    if (pct >= 90) {
        msg = '🌟 Luar Biasa!';
        desc = 'Kamu menguasai materi PD homogen dengan sangat baik!';
    } else if (pct >= 70) {
        msg = '👏 Bagus Sekali!';
        desc = 'Pemahaman yang solid, terus berlatih!';
    } else if (pct >= 50) {
        msg = '💪 Cukup Baik';
        desc = 'Masih perlu sedikit latihan lagi.';
    } else {
        msg = '📚 Tetap Semangat!';
        desc = 'Pelajari kembali materinya dan coba lagi.';
    }

    resultDiv.innerHTML = `
        <div class="result-circle">
            <div class="score-big">${quizScore}/${quizData.length}</div>
            <div class="score-label">${pct}%</div>
        </div>
        <div class="result-message">${msg}</div>
        <div class="result-desc">${desc}</div>
        <button class="btn btn-primary" onclick="resetQuiz()" style="max-width:280px;margin:0 auto">
            🔄 Ulangi Kuis
        </button>
    `;
    resultDiv.classList.add('show');
}

function resetQuiz() {
    quizIndex = 0;
    quizScore = 0;
    quizAnswered = false;
    renderQuestion();
}

// ─── Init ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadQuiz();

    // Enter key to solve
    document.getElementById('equationInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') solveEquation();
    });
});
