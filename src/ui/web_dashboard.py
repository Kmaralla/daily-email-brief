import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from flask import Flask, render_template_string, jsonify, request
from src.storage.database import Database
from src.ai.summarizer import BriefSummarizer
from src.ai.scorer import ImportanceScorer
from src.email_connectors.gmail import GmailConnector
from src.ui.feedback import InteractiveFeedback
from config.settings import EMAIL_FETCH_HOURS

app = Flask(__name__)
app.secret_key = os.urandom(24)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Daily Email Brief - Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 40px;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e2e8f0;
        }
        h1 {
            color: #1e3c72;
            margin-bottom: 10px;
            font-size: 36px;
        }
        .header-actions {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .btn-header {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-block;
        }
        .btn-setup {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
        }
        .btn-setup:hover {
            background: linear-gradient(135deg, #2a5298 0%, #1e3c72 100%);
            transform: translateY(-2px);
        }
        .btn-onboarding {
            background: linear-gradient(135deg, #f5a623 0%, #f59e0b 100%);
            color: white;
        }
        .btn-onboarding:hover {
            background: linear-gradient(135deg, #f59e0b 0%, #f5a623 100%);
            transform: translateY(-2px);
        }
        .btn-preferences {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
        }
        .btn-preferences:hover {
            background: linear-gradient(135deg, #059669 0%, #10b981 100%);
            transform: translateY(-2px);
        }
        .btn-action {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            margin: 10px;
            transition: all 0.2s;
        }
        .btn-action:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            border-bottom: 2px solid #e2e8f0;
        }
        .tab {
            padding: 12px 24px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 16px;
            color: #64748b;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }
        .tab:hover {
            color: #1e3c72;
        }
        .tab.active {
            color: #1e3c72;
            border-bottom-color: #f5a623;
            font-weight: 600;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .email-card {
            background: #f8f9fa;
            border-left: 4px solid #2a5298;
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .email-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        .email-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 10px;
        }
        .email-subject {
            font-size: 18px;
            font-weight: 600;
            color: #1e3c72;
            margin-bottom: 5px;
        }
        .email-sender {
            color: #64748b;
            font-size: 14px;
        }
        .email-score {
            background: #f5a623;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
        }
        .email-snippet {
            color: #475569;
            margin-top: 10px;
            line-height: 1.6;
        }
        .email-actions {
            margin-top: 15px;
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #2a5298;
            color: white;
        }
        .btn-primary:hover {
            background: #1e3c72;
        }
        .btn-success {
            background: #10b981;
            color: white;
        }
        .btn-danger {
            background: #ef4444;
            color: white;
        }
        .brief-content {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 8px;
            line-height: 1.8;
            white-space: pre-wrap;
            font-size: 15px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 14px;
            opacity: 0.9;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #64748b;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #64748b;
        }
        .empty-state-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📬 Daily Email Brief Dashboard</h1>
            <p>View your emails and briefs without opening Gmail/Outlook</p>
            <div class="header-actions">
                <a href="http://127.0.0.1:5000/" class="btn-header btn-setup" target="_blank">🔗 Connect Gmail/Outlook</a>
                <a href="http://127.0.0.1:5000/onboarding" class="btn-header btn-onboarding" target="_blank">🎯 Onboarding</a>
                <a href="http://127.0.0.1:5000/preferences" class="btn-header btn-preferences" target="_blank">⚙️ Preferences</a>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('brief')">Daily Brief</button>
            <button class="tab" onclick="showTab('emails')">All Emails</button>
            <button class="tab" onclick="showTab('stats')">Statistics</button>
        </div>
        
        <div id="brief-tab" class="tab-content active">
            <div class="loading" id="brief-loading">Loading brief...</div>
            <div id="brief-content"></div>
        </div>
        
        <div id="emails-tab" class="tab-content">
            <div class="loading" id="emails-loading">Loading emails...</div>
            <div id="emails-content"></div>
        </div>
        
        <div id="stats-tab" class="tab-content">
            <div class="loading" id="stats-loading">Loading statistics...</div>
            <div id="stats-content"></div>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.add('active');
            
            // Load content
            if (tabName === 'brief') loadBrief();
            else if (tabName === 'emails') loadEmails();
            else if (tabName === 'stats') loadStats();
        }
        
        function loadBrief() {
            fetch('/api/brief')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('brief-loading').style.display = 'none';
                    const content = document.getElementById('brief-content');
                    if (data.brief) {
                        content.innerHTML = '<div class="brief-content">' + 
                            data.brief.replace(/\\n/g, '<br>') + '</div>';
                    } else {
                        content.innerHTML = '<div class="empty-state">' +
                            '<div class="empty-state-icon">📭</div>' +
                            '<h3>No brief available</h3>' +
                            '<p>Fetch and score your emails first, then generate a brief.</p>' +
                            '<div style="margin-top: 20px;">' +
                            '<button class="btn-action" onclick="fetchEmails()">📥 Fetch Emails</button>' +
                            '<button class="btn-action" onclick="scoreEmails()">⭐ Score Emails</button>' +
                            '<button class="btn-action" onclick="generateBrief()">📊 Generate Brief</button>' +
                            '</div></div>';
                    }
                });
        }
        
        function loadEmails() {
            fetch('/api/emails')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('emails-loading').style.display = 'none';
                    const content = document.getElementById('emails-content');
                    if (data.emails && data.emails.length > 0) {
                        content.innerHTML = data.emails.map(email => `
                            <div class="email-card">
                                <div class="email-header">
                                    <div>
                                        <div class="email-subject">${escapeHtml(email.subject)}</div>
                                        <div class="email-sender">From: ${escapeHtml(email.sender)}</div>
                                    </div>
                                    <div class="email-score">${email.importance_score.toFixed(2)}</div>
                                </div>
                                <div class="email-snippet">${escapeHtml(email.snippet || 'No preview')}</div>
                                <div class="email-actions">
                                    <button class="btn btn-primary" onclick="viewEmail('${email.id}')">View</button>
                                    <button class="btn btn-success" onclick="markImportant('${email.id}')">Important</button>
                                    <button class="btn btn-danger" onclick="markNotImportant('${email.id}')">Not Important</button>
                                </div>
                            </div>
                        `).join('');
                    } else {
                        content.innerHTML = '<div class="empty-state">' +
                            '<div class="empty-state-icon">📭</div>' +
                            '<h3>No emails found</h3>' +
                            '<p>Fetch your emails to get started.</p>' +
                            '<div style="margin-top: 20px;">' +
                            '<button class="btn-action" onclick="fetchEmails()">📥 Fetch Emails</button>' +
                            '</div></div>';
                    }
                });
        }
        
        function loadStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('stats-loading').style.display = 'none';
                    const content = document.getElementById('stats-content');
                    content.innerHTML = `
                        <div class="stats">
                            <div class="stat-card">
                                <div class="stat-value">${data.total_emails || 0}</div>
                                <div class="stat-label">Total Emails</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${data.important_emails || 0}</div>
                                <div class="stat-label">Important</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${data.avg_score ? data.avg_score.toFixed(2) : '0.00'}</div>
                                <div class="stat-label">Avg Score</div>
                            </div>
                        </div>
                    `;
                });
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function viewEmail(emailId) {
            fetch(`/api/email/${emailId}`)
                .then(r => r.json())
                .then(data => {
                    alert(`Email Details:\\n\\nFrom: ${data.email.sender}\\nSubject: ${data.email.subject}\\n\\n${data.email.body || data.email.snippet}`);
                });
        }
        
        function markImportant(emailId) {
            fetch(`/api/feedback/${emailId}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({important: true})
            }).then(() => {
                alert('Marked as important!');
                loadEmails();
            });
        }
        
        function markNotImportant(emailId) {
            fetch(`/api/feedback/${emailId}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({important: false})
            }).then(() => {
                alert('Marked as not important!');
                loadEmails();
            });
        }
        
        function fetchEmails() {
            fetch('/action/fetch', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        alert('✅ Emails fetched successfully!');
                        loadEmails();
                        loadBrief();
                        loadStats();
                    } else {
                        alert('❌ Error: ' + (data.error || 'Failed to fetch emails'));
                    }
                })
                .catch(err => {
                    alert('❌ Error: ' + err.message);
                });
        }
        
        function scoreEmails() {
            fetch('/action/score', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        alert('✅ Emails scored successfully!');
                        loadEmails();
                        loadBrief();
                        loadStats();
                    } else {
                        alert('❌ Error: ' + (data.error || 'Failed to score emails'));
                    }
                })
                .catch(err => {
                    alert('❌ Error: ' + err.message);
                });
        }
        
        function generateBrief() {
            fetch('/action/generate-brief', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        alert('✅ Brief generated successfully!');
                        loadBrief();
                    } else {
                        alert('❌ Error: ' + (data.error || 'Failed to generate brief'));
                    }
                })
                .catch(err => {
                    alert('❌ Error: ' + err.message);
                });
        }
        
        // Load initial content
        loadBrief();
    </script>
</body>
</html>
"""

@app.route('/')
@app.route('/dashboard')
def dashboard():
    """Render dashboard."""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/brief')
def api_brief():
    """Get latest brief."""
    db = Database()
    summarizer = BriefSummarizer()
    
    emails = db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
    emails.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
    
    if not emails:
        return jsonify({'brief': None})
    
    top_n = int(db.get_user_preference('brief_top_n', '10') or '10')
    brief = summarizer.generate_brief(emails, top_n=top_n)
    
    return jsonify({'brief': brief})

@app.route('/api/emails')
def api_emails():
    """Get recent emails."""
    db = Database()
    emails = db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
    emails.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
    
    return jsonify({'emails': emails[:50]})  # Top 50

@app.route('/api/email/<email_id>')
def api_email(email_id):
    """Get email by ID."""
    db = Database()
    email = db.get_email_by_id(email_id)
    
    if not email:
        return jsonify({'error': 'Email not found'}), 404
    
    return jsonify({'email': email})

@app.route('/api/feedback/<email_id>', methods=['POST'])
def api_feedback(email_id):
    """Save feedback."""
    data = request.json
    db = Database()
    db.save_enhanced_feedback(email_id, data.get('important', True))
    
    return jsonify({'status': 'success'})

@app.route('/api/stats')
def api_stats():
    """Get statistics."""
    db = Database()
    emails = db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
    
    total = len(emails)
    important = sum(1 for e in emails if e.get('importance_score', 0) > 0.7)
    avg_score = sum(e.get('importance_score', 0) for e in emails) / total if total > 0 else 0
    
    return jsonify({
        'total_emails': total,
        'important_emails': important,
        'avg_score': avg_score
    })

@app.route('/action/fetch', methods=['POST'])
def action_fetch():
    """Fetch emails from Gmail."""
    try:
        gmail = GmailConnector()
        if not gmail.authenticate():
            return jsonify({'success': False, 'error': 'Gmail authentication failed. Please connect your account first.'})
        
        emails = gmail.fetch_recent_emails(hours=EMAIL_FETCH_HOURS)
        db = Database()
        
        count = 0
        for email in emails:
            db.save_email(email, account_type='gmail')
            count += 1
        
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/action/score', methods=['POST'])
def action_score():
    """Score email importance."""
    try:
        db = Database()
        scorer = ImportanceScorer(db)
        
        emails = db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
        if not emails:
            return jsonify({'success': False, 'error': 'No emails found. Please fetch emails first.'})
        
        count = 0
        for email in emails:
            score = scorer.score_email(email)
            db.update_importance_score(email['id'], score)
            count += 1
        
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/action/generate-brief', methods=['POST'])
def action_generate_brief():
    """Generate daily brief."""
    try:
        db = Database()
        summarizer = BriefSummarizer()
        
        emails = db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
        if not emails:
            return jsonify({'success': False, 'error': 'No emails found. Please fetch and score emails first.'})
        
        emails.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
        top_n = int(db.get_user_preference('brief_top_n', '10') or '10')
        
        brief = summarizer.generate_brief(emails, top_n=top_n)
        
        # Save brief (optional - you could save to database)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"brief_{timestamp}.txt"
        with open(filename, 'w') as f:
            f.write(brief)
        
        return jsonify({'success': True, 'brief': brief})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=False, port=5001, host='127.0.0.1')
