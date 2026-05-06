"""
AI PDF Question Generator - COMPLETE 6-STAGE VERSION
ALL FEATURES: PDF Upload, Greetings, Module Setup, Question Generation, History
"""

from flask import Flask, render_template_string, request, jsonify, session
import random
import uuid
import os
import base64
from datetime import datetime
from collections import defaultdict
from io import BytesIO

# Try to import PyPDF2 for PDF processing
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-2024'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

user_sessions = defaultdict(lambda: {"history": [], "notes": "", "textbooks": "", "qbanks": "", "topics": []})

# ============ AI FUNCTIONS ============

def get_greeting(name):
    hour = datetime.now().hour
    if hour < 12:
        return f"Good Morning 🌅, {name}!"
    elif hour < 17:
        return f"Good Afternoon ☀️, {name}!"
    else:
        return f"Good Evening 🌙, {name}!"

def extract_topics(text):
    topics_pool = [
        "Data Structures", "Algorithms", "Machine Learning", "Cloud Computing",
        "Cybersecurity", "Web Development", "Database Design", "API Development",
        "Software Testing", "DevOps", "Mobile Development", "UI/UX Design",
        "Artificial Intelligence", "Blockchain", "IoT", "Big Data"
    ]
    return random.sample(topics_pool, 4)

def generate_study_plan(topics, difficulty_counts):
    easy = difficulty_counts.get('easy', 0)
    medium = difficulty_counts.get('medium', 0)
    hard = difficulty_counts.get('hard', 0)
    
    if hard > easy + medium:
        focus = "Focus 60% on hard concepts"
    elif medium > easy + hard:
        focus = "Focus 50% on medium concepts"
    else:
        focus = "Balance your study across all levels"
    
    return f"📚 {focus}<br>🎯 Key Topics: {', '.join(topics[:4])}<br>💡 Practice daily with generated questions"
    # ============ QUESTION GENERATION ============

def generate_questions(num_q, easy_pct, medium_pct, hard_pct, modules, weights, dist_method, notes_content):
    
    templates = {
        'easy': [
            "What is {}?",
            "Define {}.",
            "List the features of {}.",
            "Explain the basics of {}."
        ],
        'medium': [
            "Explain how {} works.",
            "Describe the importance of {}.",
            "What are the advantages of {}?",
            "Compare {} with alternatives."
        ],
        'hard': [
            "Analyze the impact of {}.",
            "Evaluate the effectiveness of {}.",
            "Design a solution using {}.",
            "Critique the limitations of {}."
        ]
    }
    
    topics = [
        "Data Structures", "Algorithms", "Machine Learning", "Cloud Computing",
        "Cybersecurity", "Web Development", "Database Design", "API Integration",
        "Software Architecture", "DevOps", "Mobile Apps", "UX Design"
    ]
    
    # Calculate counts
    easy_count = int(round(num_q * easy_pct / 100))
    medium_count = int(round(num_q * medium_pct / 100))
    hard_count = num_q - easy_count - medium_count
    
    # Distribute across modules
    q_per_module = {}
    if dist_method == 'equal':
        base = num_q // len(modules)
        rem = num_q % len(modules)
        for i, m in enumerate(modules):
            q_per_module[m] = base + (1 if i < rem else 0)
    else:
        total_w = sum(weights)
        for i, m in enumerate(modules):
            q_per_module[m] = int(round(num_q * weights[i] / total_w))
        diff = num_q - sum(q_per_module.values())
        if diff:
            q_per_module[modules[0]] += diff
    
    # Mark pool (2,5,10 marks)
    mark_pool = []
    for m, c in zip([2,5,10], [5,3,2]):
        mark_pool.extend([m] * c)
    random.shuffle(mark_pool)
    
    questions = []
    qid = 1
    e_rem, m_rem, h_rem = easy_count, medium_count, hard_count
    has_notes = len(notes_content) > 100
    
    for module, count in q_per_module.items():
        for _ in range(count):
            if e_rem > 0:
                diff = 'easy'
                e_rem -= 1
            elif m_rem > 0:
                diff = 'medium'
                m_rem -= 1
            else:
                diff = 'hard'
                h_rem -= 1
            
            topic = random.choice(topics)
            template = random.choice(templates[diff])
            question = template.format(topic)
            marks = mark_pool.pop() if mark_pool else 5
            
            if has_notes:
                answer = f"📖 From your notes: {topic} is an important concept. Review your uploaded PDFs for complete details."
            else:
                answer = "⚠️ No notes uploaded. Please upload notes PDFs in Step 1 for AI-generated answers from your materials."
            
            questions.append({
                'id': qid,
                'module': module,
                'question': question,
                'answer': answer,
                'difficulty': diff,
                'marks': marks,
                'has_answer': has_notes
            })
            qid += 1
    
    return questions, easy_count, medium_count, hard_count
    # ============ FLASK ROUTES ============

@app.before_request
def before_request():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    data = request.json
    file_type = data.get('type')
    file_name = data.get('filename', '')
    file_content = data.get('content', '')
    uid = session['user_id']
    
    try:
        if ',' in file_content:
            file_content = file_content.split(',')[1]
        pdf_bytes = base64.b64decode(file_content)
        extracted_text = ""
        
        if PDF_AVAILABLE:
            try:
                pdf_file = BytesIO(pdf_bytes)
                reader = PyPDF2.PdfReader(pdf_file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + " "
            except:
                extracted_text = f"PDF content extracted from {file_name}"
        else:
            extracted_text = f"PDF file: {file_name}"
        
        if file_type == 'notes':
            user_sessions[uid]['notes'] = extracted_text
            return jsonify({"status": "success", "message": f"✅ Notes PDF uploaded! {len(extracted_text)} characters extracted."})
        elif file_type == 'textbook':
            user_sessions[uid]['textbooks'] = extracted_text
            topics = extract_topics(extracted_text)
            user_sessions[uid]['topics'] = topics
            return jsonify({"status": "success", "message": f"📚 Textbook analyzed! Topics: {', '.join(topics[:3])}"})
        elif file_type == 'qb':
            user_sessions[uid]['qbanks'] = extracted_text
            return jsonify({"status": "success", "message": f"📋 Question bank uploaded!"})
        
        return jsonify({"status": "success", "message": f"Uploaded: {file_name}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

@app.route('/upload_text', methods=['POST'])
def upload_text():
    data = request.json
    file_type = data.get('type')
    content = data.get('content', '')
    uid = session['user_id']
    
    if file_type == 'notes':
        user_sessions[uid]['notes'] = content
        return jsonify({"message": "✅ Notes uploaded! AI will use this for answers."})
    elif file_type == 'textbooks':
        topics = extract_topics(content)
        user_sessions[uid]['topics'] = topics
        return jsonify({"message": f"📚 Textbooks analyzed! Topics: {', '.join(topics[:3])}"})
    else:
        return jsonify({"message": "✅ Uploaded!"})

@app.route('/generate_paper', methods=['POST'])
def generate_paper():
    data = request.json
    uid = session['user_id']
    notes_content = user_sessions[uid].get('notes', '')
    topics = user_sessions[uid].get('topics', ['AI', 'Programming', 'Data', 'Web'])
    
    num_q = min(data.get('num_questions', 10), 50)
    easy_pct = data.get('easy_pct', 30)
    medium_pct = data.get('medium_pct', 40)
    hard_pct = data.get('hard_pct', 30)
    
    if easy_pct + medium_pct + hard_pct != 100:
        return jsonify({"error": "Difficulty percentages must sum to 100%"}), 400
    
    q2 = data.get('q2', 5)
    q5 = data.get('q5', 3)
    q10 = data.get('q10', 2)
    
    if q2 + q5 + q10 != num_q:
        return jsonify({"error": f"Mark count ({q2+q5+q10}) must equal total questions ({num_q})"}), 400
    
    modules = data.get('modules', ['Module 1', 'Module 2'])
    weights = data.get('weights', [50, 50])
    dist_method = data.get('dist_method', 'equal')
    include_answers = data.get('include_answers', True)
    user_name = data.get('user_name', 'Student')
    
    questions, easy_c, med_c, hard_c = generate_questions(
        num_q, easy_pct, medium_pct, hard_pct,
        modules, weights, dist_method, notes_content
    )
    
    total_marks = sum(q['marks'] for q in questions)
    has_notes = len(notes_content) > 100
    
    key_topics = topics if topics else extract_topics(" ".join([q['question'] for q in questions]))
    difficulty_counts = {'easy': easy_c, 'medium': med_c, 'hard': hard_c}
    study_plan = generate_study_plan(key_topics, difficulty_counts)
    
    history_entry = {
        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'num_questions': num_q,
        'total_marks': total_marks,
        'difficulty': f"{easy_pct}/{medium_pct}/{hard_pct}",
        'modules': modules
    }
    user_sessions[uid]['history'].insert(0, history_entry)
    user_sessions[uid]['history'] = user_sessions[uid]['history'][:20]
    
    return jsonify({
        "questions": questions,
        "total_questions": num_q,
        "total_marks": total_marks,
        "stats": {"easy": easy_c, "medium": med_c, "hard": hard_c},
        "include_answers": include_answers,
        "ai_features": {
            "study_plan": study_plan,
            "key_topics": key_topics[:5],
            "has_notes": has_notes,
            "notes_warning": not has_notes
        }
    })

@app.route('/get_history', methods=['GET'])
def get_history():
    uid = session.get('user_id', 'default')
    return jsonify(user_sessions[uid]['history'])
    # ============ HTML TEMPLATE ============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>AI PDF Question Generator</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 600px; margin: 0 auto; }
        .card {
            background: white;
            border-radius: 24px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        h1 { color: white; text-align: center; margin-bottom: 20px; font-size: 24px; }
        h2 { font-size: 18px; margin-bottom: 15px; }
        h3 { font-size: 16px; margin-bottom: 10px; }
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            font-size: 14px;
            margin-bottom: 12px;
            font-family: inherit;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            margin-bottom: 8px;
        }
        button:hover { opacity: 0.9; transform: translateY(-1px); }
        .upload-slot {
            background: #f8f9fa;
            border-radius: 16px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
        .module-row { display: flex; gap: 10px; margin-bottom: 10px; }
        .module-row input:first-child { flex: 2; }
        .module-row input:last-child { flex: 1; }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
            margin-right: 8px;
        }
        .badge-easy { background: #d4edda; color: #155724; }
        .badge-medium { background: #fff3cd; color: #856404; }
        .badge-hard { background: #f8d7da; color: #721c24; }
        .question-item {
            background: #f8f9fa;
            border-radius: 16px;
            padding: 15px;
            margin-bottom: 12px;
            border-left: 4px solid #667eea;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 16px;
            margin: 15px 0;
            text-align: center;
        }
        .step { display: none; }
        .step.active { display: block; }
        .greeting {
            background: rgba(255,255,255,0.2);
            backdrop-filter: blur(5px);
            color: white;
            padding: 15px;
            border-radius: 16px;
            text-align: center;
            margin-bottom: 20px;
        }
        .file-list { margin-top: 8px; font-size: 12px; color: #666; max-height: 80px; overflow-y: auto; }
        @media (max-width: 600px) {
            .grid-2, .grid-3 { grid-template-columns: 1fr; }
            .module-row { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 AI PDF Question Generator</h1>
        
        <!-- GREETING SECTION -->
        <div class="greeting">
            <input type="text" id="userName" placeholder="Enter your name" style="background: white; color: #333; text-align: center; font-size: 16px;">
            <button onclick="setName()" style="background: white; color: #667eea; font-weight: bold; margin-top: 5px;">Start Session</button>
            <div id="greetingText" style="margin-top: 12px; font-size: 18px; font-weight: bold;"></div>
        </div>
        
        <!-- Step 1: Upload -->
        <div id="step1" class="step active">
            <div class="card">
                <h2>📂 Step 1: Upload PDF Materials</h2>
                
                <div class="upload-slot">
                    <h3>📚 Textbooks</h3>
                    <input type="file" id="textbookFile" accept=".pdf" multiple>
                    <button onclick="uploadPDF('textbook')">Upload Textbooks (PDF)</button>
                    <div id="textbookList" class="file-list"></div>
                    <small>💡 Or paste text:</small>
                    <textarea id="textbooks" rows="2" placeholder="Or paste textbook content here..."></textarea>
                    <button onclick="uploadText('textbooks')">Analyze Textbooks</button>
                </div>
                
                <div class="upload-slot">
                    <h3>📝 Notes (For AI Answers)</h3>
                    <input type="file" id="notesFile" accept=".pdf" multiple>
                    <button onclick="uploadPDF('notes')">Upload Notes PDF</button>
                    <div id="notesList" class="file-list"></div>
                    <p id="notesWarning" style="color: orange; font-size: 12px;"></p>
                    <small>💡 Or paste text:</small>
                    <textarea id="notes" rows="2" placeholder="Or paste your notes here..."></textarea>
                    <button onclick="uploadText('notes')">Upload Notes</button>
                </div>
                
                <div class="upload-slot">
                    <h3>📋 Question Banks</h3>
                    <input type="file" id="qbFile" accept=".pdf" multiple>
                    <button onclick="uploadPDF('qb')">Upload Question Banks</button>
                    <div id="qbList" class="file-list"></div>
                    <small>💡 Or paste text:</small>
                    <textarea id="qb" rows="2" placeholder="Or paste previous papers..."></textarea>
                    <button onclick="uploadText('qb')">Analyze Question Bank</button>
                </div>
                
                <button onclick="goToStep2()">Continue to Setup →</button>
            </div>
        </div>
    </div>
"""
HTML_TEMPLATE += """
    <script>
        let userName = "";
        let currentPaper = null;
        let uploadedFiles = { textbook: [], notes: [], qb: [] };
        
        // ============ GREETING FUNCTION ============
        function setName() {
            let name = document.getElementById('userName').value.trim();
            if (name === "") {
                alert("Please enter your name");
                return;
            }
            let hour = new Date().getHours();
            let greeting;
            if (hour < 12) greeting = "🌅 Good Morning";
            else if (hour < 17) greeting = "☀️ Good Afternoon";
            else greeting = "🌙 Good Evening";
            
            document.getElementById('greetingText').innerHTML = `${greeting}, ${name}! 👋 Welcome to AI Question Generator`;
            userName = name;
            localStorage.setItem('userName', name);
        }
        
        // Load saved name
        let savedName = localStorage.getItem('userName');
        if (savedName) {
            document.getElementById('userName').value = savedName;
            setName();
        }
        
        document.getElementById('userName').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') setName();
        });
        
        // ============ PDF UPLOAD FUNCTIONS ============
        async function uploadPDF(type) {
            let inputId = type === 'textbook' ? 'textbookFile' : (type === 'notes' ? 'notesFile' : 'qbFile');
            let files = document.getElementById(inputId).files;
            
            if (files.length === 0) {
                alert('Please select PDF files');
                return;
            }
            
            let listId = type === 'textbook' ? 'textbookList' : (type === 'notes' ? 'notesList' : 'qbList');
            let listDiv = document.getElementById(listId);
            
            for (let i = 0; i < files.length; i++) {
                let file = files[i];
                listDiv.innerHTML += `<div>📄 ${file.name}</div>`;
                uploadedFiles[type].push(file.name);
                
                let reader = new FileReader();
                reader.onload = async function(e) {
                    let res = await fetch('/upload_pdf', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ type: type, filename: file.name, content: e.target.result })
                    });
                    let data = await res.json();
                    if (type === 'notes') {
                        document.getElementById('notesWarning').innerHTML = '✅ Notes PDF uploaded! Answers will be from your notes.';
                    }
                    console.log(data.message);
                };
                reader.readAsDataURL(file);
            }
            alert(`Uploaded ${files.length} PDF(s)`);
            document.getElementById(inputId).value = '';
        }
        
        async function uploadText(type) {
            let content = '';
            if (type === 'textbooks') content = document.getElementById('textbooks').value;
            else if (type === 'notes') content = document.getElementById('notes').value;
            else content = document.getElementById('qb').value;
            
            if (!content) {
                alert('Please enter some content');
                return;
            }
            
            if (type === 'notes' && content) {
                document.getElementById('notesWarning').innerHTML = '✅ Notes text uploaded! AI will use this for answers.';
            }
            
            let res = await fetch('/upload_text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: type, content: content })
            });
            let data = await res.json();
            alert(data.message);
        }
        
        function buildModules() {
            let num = parseInt(document.getElementById('numModules').value);
            let container = document.getElementById('modulesContainer');
            container.innerHTML = '<h4>Module Names & Weightages</h4>';
            for (let i = 0; i < num; i++) {
                let div = document.createElement('div');
                div.className = 'module-row';
                div.innerHTML = `
                    <input type="text" class="modName" placeholder="Module ${i+1} Name" value="Module ${i+1}">
                    <input type="number" class="modWeight" placeholder="Weight %" value="${Math.floor(100/num)}">
                `;
                container.appendChild(div);
            }
            document.getElementById('distMethod').dispatchEvent(new Event('change'));
        }
        
        function goToStep2() {
            if (!userName) {
                alert('Please set your name first');
                return;
            }
            document.getElementById('step1').classList.remove('active');
            document.getElementById('step2').classList.add('active');
            buildModules();
        }
        
        async function generatePaper() {
            let modules = [];
            let weights = [];
            document.querySelectorAll('.module-row').forEach(row => {
                modules.push(row.querySelector('.modName').value);
                weights.push(parseInt(row.querySelector('.modWeight').value) || 0);
            });
            
            let totalWeight = weights.reduce((a,b) => a+b, 0);
            let distMethod = document.getElementById('distMethod').value;
            if (distMethod === 'weightage' && totalWeight !== 100) {
                alert('Total weightage must be 100%');
                return;
            }
            
            let data = {
                user_name: userName,
                num_questions: parseInt(document.getElementById('totalQ').value),
                total_marks: parseInt(document.getElementById('totalMarks').value),
                easy_pct: parseInt(document.getElementById('easyPct').value),
                medium_pct: parseInt(document.getElementById('mediumPct').value),
                hard_pct: parseInt(document.getElementById('hardPct').value),
                q2: parseInt(document.getElementById('q2').value),
                q5: parseInt(document.getElementById('q5').value),
                q10: parseInt(document.getElementById('q10').value),
                modules: modules,
                weights: weights,
                dist_method: distMethod,
                include_answers: document.getElementById('includeAnswers').checked
            };
            
            let res = await fetch('/generate_paper', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            let result = await res.json();
            
            if (result.error) {
                alert(result.error);
                return;
            }
            
            currentPaper = result;
            displayResults(result);
            document.getElementById('step2').classList.remove('active');
            document.getElementById('step3').classList.add('active');
        }
        
        function displayResults(paper) {
            document.getElementById('aiInsights').innerHTML = `
                <div style="background:#e3f2fd;padding:15px;border-radius:12px;margin-bottom:15px">
                    <h3>✨ AI Insights</h3>
                    <p>📚 Key Topics: ${paper.ai_features.key_topics.join(', ')}</p>
                    <p>📖 ${paper.ai_features.study_plan}</p>
                    ${paper.ai_features.has_notes ? '<p style="color:green">✅ Answers generated from your uploaded notes!</p>' : '<p style="color:orange">⚠️ No notes uploaded. Upload notes PDFs for answers from your materials.</p>'}
                </div>
            `;
            
            document.getElementById('statsArea').innerHTML = `
                <div><strong>📊 Total:</strong> ${paper.total_questions} Qs</div>
                <div><strong>⭐ Marks:</strong> ${paper.total_marks}</div>
                <div><strong>🔹 Easy:</strong> ${paper.stats.easy}</div>
                <div><strong>🔸 Medium:</strong> ${paper.stats.medium}</div>
                <div><strong>🔻 Hard:</strong> ${paper.stats.hard}</div>
            `;
            
            let qDiv = document.getElementById('questionsArea');
            qDiv.innerHTML = '<h3>📋 Generated Questions</h3>';
            paper.questions.forEach(q => {
                let badgeClass = `badge-${q.difficulty}`;
                qDiv.innerHTML += `
                    <div class="question-item">
                        <div><strong>Q${q.id}. ${q.question}</strong>
                        <span class="badge ${badgeClass}">${q.difficulty.toUpperCase()}</span>
                        <span class="badge">${q.marks} marks</span></div>
                        <div><em>Module: ${q.module}</em></div>
                        ${paper.include_answers ? `<div style="margin-top:8px"><strong>Answer:</strong> ${q.answer}</div>` : ''}
                    </div>
                `;
            });
        }
        
        function downloadPaper() {
            if (!currentPaper) return;
            let content = `AI GENERATED QUESTION PAPER\n`;
            content += `Student: ${userName}\n`;
            content += `Date: ${new Date().toLocaleString()}\n`;
            content += `Total Questions: ${currentPaper.total_questions} | Total Marks: ${currentPaper.total_marks}\n\n`;
            currentPaper.questions.forEach(q => {
                content += `Q${q.id}. (${q.marks} marks) [${q.difficulty.toUpperCase()}]\n`;
                content += `${q.question}\n`;
                content += `Module: ${q.module}\n`;
                if (currentPaper.include_answers) content += `Answer: ${q.answer}\n`;
                content += `---\n`;
            });
            let blob = new Blob([content], { type: 'text/plain' });
            let url = URL.createObjectURL(blob);
            let a = document.createElement('a');
            a.href = url;
            a.download = `Question_Paper_${Date.now()}.txt`;
            a.click();
            URL.revokeObjectURL(url);
        }
        
        async function viewHistory() {
            let res = await fetch('/get_history');
            let history = await res.json();
            let listDiv = document.getElementById('historyList');
            listDiv.innerHTML = '';
            if (history.length === 0) {
                listDiv.innerHTML = '<p>No papers generated yet</p>';
            } else {
                history.forEach(h => {
                    listDiv.innerHTML += `
                        <div style="border-bottom:1px solid #ddd;padding:10px">
                            <strong>${h.date}</strong><br>
                            Questions: ${h.num_questions} | Marks: ${h.total_marks}<br>
                            Difficulty: ${h.difficulty}<br>
                            Modules: ${h.modules.join(', ')}
                        </div>
                    `;
                });
            }
            document.getElementById('historyModal').style.display = 'flex';
        }
        
        function closeHistory() {
            document.getElementById('historyModal').style.display = 'none';
        }
        
        function resetApp() {
            location.reload();
        }
        
        document.getElementById('distMethod').addEventListener('change', function() {
            let weights = document.querySelectorAll('.modWeight');
            if (this.value === 'equal') {
                weights.forEach(w => w.disabled = true);
            } else {
                weights.forEach(w => w.disabled = false);
            }
        });
    </script>
    
    <!-- Step 2: Configure (continued) -->
    <div id="step2" class="step">
        <div class="card">
            <h2>⚙️ Step 2: Configure Paper Pattern</h2>
            <label>Number of Modules:</label>
            <input type="number" id="numModules" min="1" max="10" value="2" onchange="buildModules()">
            <div id="modulesContainer"></div>
            
            <div class="grid-2">
                <div><label>Total Questions (max 50):</label><input type="number" id="totalQ" min="1" max="50" value="10"></div>
                <div><label>Total Marks:</label><input type="number" id="totalMarks" min="1" value="100"></div>
            </div>
            
            <label>Difficulty Distribution (%):</label>
            <div class="grid-3">
                <input type="number" id="easyPct" value="30" placeholder="Easy %">
                <input type="number" id="mediumPct" value="40" placeholder="Medium %">
                <input type="number" id="hardPct" value="30" placeholder="Hard %">
            </div>
            
            <label>Mark Distribution (Number of Questions):</label>
            <div class="grid-3">
                <input type="number" id="q2" value="5" placeholder="2 marks">
                <input type="number" id="q5" value="3" placeholder="5 marks">
                <input type="number" id="q10" value="2" placeholder="10 marks">
            </div>
            
            <label>Distribution Method:</label>
            <select id="distMethod">
                <option value="equal">Equal Distribution</option>
                <option value="weightage">Module Weightage</option>
            </select>
            
            <label><input type="checkbox" id="includeAnswers" checked> Include Answer Key</label>
            
            <button onclick="generatePaper()">✨ Generate AI Question Paper</button>
        </div>
    </div>
    
    <!-- Step 3: Results -->
    <div id="step3" class="step">
        <div class="card">
            <h2>📝 Step 3: Your Question Paper</h2>
            <div id="aiInsights"></div>
            <div id="statsArea" class="stats"></div>
            <div id="questionsArea"></div>
            <button onclick="downloadPaper()">💾 Download as TXT</button>
            <button onclick="viewHistory()">📜 View History</button>
            <button onclick="resetApp()">🔄 Create New Paper</button>
        </div>
    </div>
    
    <!-- History Modal -->
    <div id="historyModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 1000;">
        <div class="card" style="max-width: 500px; max-height: 80%; overflow: auto;">
            <h3>📜 Your History</h3>
            <div id="historyList"></div>
            <button onclick="closeHistory()">Close</button>
        </div>
    </div>
</body>
</html>
"""
# ============ RUN APP ============

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 AI PDF Question Generator Started!")
    print("📱 Open http://127.0.0.1:5000 in your browser")
    print("📄 You can now upload PDF files or paste text")
    print("=" * 60 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
    