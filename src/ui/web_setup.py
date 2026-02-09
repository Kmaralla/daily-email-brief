import os
import sys
import json
import sqlite3

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Disable HTTPS requirement for localhost development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import webbrowser
from threading import Timer

app = Flask(__name__)
app.secret_key = os.urandom(24)

# OAuth configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
REDIRECT_URI = 'http://127.0.0.1:5000/oauth/callback'
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# Prevent multiple simultaneous OAuth flows
_oauth_in_progress = False


HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Daily Email Brief - Setup</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #f5a623 100%);
            min-height: 100vh;
            padding: 20px;
            position: relative;
            overflow-x: hidden;
        }
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 50%, rgba(245, 166, 35, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(30, 60, 114, 0.2) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.98);
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.1);
            padding: 50px;
            position: relative;
            z-index: 1;
            backdrop-filter: blur(10px);
        }
        .header {
            text-align: center;
            margin-bottom: 50px;
            padding-bottom: 30px;
            border-bottom: 2px solid #f0f4f8;
        }
        h1 {
            color: #1e3c72;
            margin-bottom: 15px;
            font-size: 42px;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #1e3c72 0%, #f5a623 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .subtitle {
            color: #64748b;
            margin-bottom: 0;
            font-size: 20px;
            font-weight: 400;
            line-height: 1.6;
        }
        .providers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin-top: 40px;
        }
        .provider-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 2px solid #e2e8f0;
            border-radius: 20px;
            padding: 40px 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            text-decoration: none;
            color: inherit;
            display: block;
            position: relative;
            overflow: hidden;
        }
        .provider-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #1e3c72 0%, #f5a623 100%);
            transform: scaleX(0);
            transition: transform 0.4s;
        }
        .provider-card:hover {
            border-color: #f5a623;
            transform: translateY(-8px);
            box-shadow: 0 20px 40px rgba(30, 60, 114, 0.15), 0 0 0 1px rgba(245, 166, 35, 0.2);
        }
        .provider-card:hover::before {
            transform: scaleX(1);
        }
        .provider-icon {
            font-size: 64px;
            margin-bottom: 20px;
            filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
            transition: transform 0.3s;
        }
        .provider-card:hover .provider-icon {
            transform: scale(1.1) rotate(5deg);
        }
        .provider-name {
            font-size: 28px;
            font-weight: 600;
            color: #1e3c72;
            margin-bottom: 15px;
            letter-spacing: -0.3px;
        }
        .provider-status {
            font-size: 15px;
            margin-top: 15px;
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
            font-weight: 500;
        }
        .status-connected {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }
        .status-not-connected {
            background: #f1f5f9;
            color: #64748b;
            border: 1px solid #e2e8f0;
        }
        .btn {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 14px 32px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 15px;
            display: inline-block;
            text-decoration: none;
            box-shadow: 0 4px 12px rgba(30, 60, 114, 0.3);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(30, 60, 114, 0.4);
        }
        .coming-soon {
            opacity: 0.7;
            cursor: not-allowed;
            position: relative;
        }
        .coming-soon::after {
            content: 'Coming Soon';
            position: absolute;
            top: 10px;
            right: 10px;
            background: #f5a623;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📬 Daily Email Brief</h1>
            <p class="subtitle">Connect your email accounts to get AI-powered daily summaries<br>that help you focus on what matters most</p>
        </div>

        <div class="providers-grid">
            <div style="position: relative; display: inline-block; width: 100%;">
                <a href="{% if gmail_connected %}/dashboard{% else %}/setup/gmail{% endif %}" class="provider-card" style="position: relative;">
                    <div class="provider-icon">📧</div>
                    <div class="provider-name">Gmail</div>
                    <div class="provider-status {% if gmail_connected %}status-connected{% else %}status-not-connected{% endif %}">
                        {% if gmail_connected %}✓ Connected{% else %}Not Connected{% endif %}
                    </div>
                    {% if gmail_connected %}
                    <form method="POST" action="/setup/reset-credentials" style="position: absolute; top: 15px; right: 15px; z-index: 20; margin: 0;" onsubmit="event.stopPropagation(); return confirm('Are you sure you want to unlink Gmail? This will reset your connection and you\\'ll need to reconnect.');">
                        <button type="submit" style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; border: none; padding: 8px 16px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; box-shadow: 0 2px 8px rgba(220, 38, 38, 0.3); transition: all 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(220, 38, 38, 0.4)';" onmouseout="this.style.transform=''; this.style.boxShadow='0 2px 8px rgba(220, 38, 38, 0.3)';">
                            🔄 Unlink
                        </button>
                    </form>
                    {% endif %}
                </a>
            </div>

            <a href="/setup/outlook" class="provider-card coming-soon">
                <div class="provider-icon">📮</div>
                <div class="provider-name">Outlook</div>
                <div class="provider-status status-not-connected">
                    Coming Soon
                </div>
            </a>

            <div class="provider-card coming-soon">
                <div class="provider-icon">📨</div>
                <div class="provider-name">Other Providers</div>
                <div class="provider-status status-not-connected">
                    Coming Soon
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

SETUP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Daily Email Brief - {{ provider_name }} Setup</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #f5a623 100%);
            min-height: 100vh;
            padding: 20px;
            position: relative;
            overflow-x: hidden;
        }
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 50%, rgba(245, 166, 35, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(30, 60, 114, 0.2) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.98);
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.1);
            padding: 50px;
            position: relative;
            z-index: 1;
            backdrop-filter: blur(10px);
        }
        h1 {
            color: #1e3c72;
            margin-bottom: 15px;
            font-size: 36px;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #1e3c72 0%, #f5a623 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .subtitle {
            color: #64748b;
            margin-bottom: 30px;
            font-size: 18px;
            line-height: 1.6;
        }
        .step {
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
            border-left: 4px solid #f5a623;
            padding: 28px;
            margin: 25px 0;
            border-radius: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            transition: all 0.3s;
        }
        .step:hover {
            box-shadow: 0 4px 16px rgba(30, 60, 114, 0.1);
            transform: translateX(4px);
        }
        .step-number {
            display: inline-block;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            text-align: center;
            line-height: 36px;
            font-weight: 700;
            margin-right: 12px;
            box-shadow: 0 4px 12px rgba(30, 60, 114, 0.3);
        }
        .step h3 {
            color: #1e3c72;
            margin-bottom: 12px;
            font-size: 20px;
            font-weight: 600;
        }
        .step p {
            color: #475569;
            line-height: 1.7;
            margin-bottom: 12px;
            font-size: 15px;
        }
        .step ol {
            margin-left: 20px;
            color: #666;
        }
        .step li {
            margin: 8px 0;
        }
        .step a {
            color: #1e3c72;
            text-decoration: none;
            font-weight: 600;
            border-bottom: 2px solid #f5a623;
            transition: all 0.3s;
        }
        .step a:hover {
            color: #f5a623;
            border-bottom-color: #1e3c72;
        }
        .form-group {
            margin: 30px 0;
        }
        label {
            display: block;
            color: #1e3c72;
            font-weight: 600;
            margin-bottom: 10px;
            font-size: 15px;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 14px 18px;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            font-size: 15px;
            transition: all 0.3s;
            background: #ffffff;
            color: #1e3c72;
        }
        input[type="text"]:focus, input[type="password"]:focus {
            outline: none;
            border-color: #f5a623;
            box-shadow: 0 0 0 4px rgba(245, 166, 35, 0.1);
        }
        .btn {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 14px 32px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-right: 12px;
            box-shadow: 0 4px 12px rgba(30, 60, 114, 0.3);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(30, 60, 114, 0.4);
        }
        .btn-secondary {
            background: linear-gradient(135deg, #64748b 0%, #475569 100%);
        }
        .btn-secondary:hover {
            background: linear-gradient(135deg, #475569 0%, #334155 100%);
        }
        .alert {
            padding: 18px 20px;
            border-radius: 12px;
            margin: 25px 0;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .alert-success {
            background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
            color: #065f46;
            border: 2px solid #10b981;
        }
        .alert-error {
            background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
            color: #991b1b;
            border: 2px solid #ef4444;
        }
        .alert-info {
            background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
            color: #1e40af;
            border: 2px solid #3b82f6;
        }
        .status {
            padding: 20px;
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border-left: 4px solid #1e3c72;
            border-radius: 12px;
            margin: 25px 0;
            box-shadow: 0 2px 8px rgba(30, 60, 114, 0.1);
        }
        .code-block {
            background: #1e293b;
            color: #e2e8f0;
            padding: 18px;
            border-radius: 12px;
            font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            overflow-x: auto;
            margin: 12px 0;
            border: 1px solid #334155;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 {{ provider_name }} Setup</h1>
        <p class="subtitle">Connect your {{ provider_name }} account in just a few steps</p>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% if not has_credentials %}
        <div class="alert alert-info">
            <strong>⚠️ Important Requirements:</strong>
            <ul style="margin: 10px 0 0 20px; padding-left: 0;">
                <li>Google Cloud requires <strong>Two-Step Verification (2SV)</strong> - enable it in your <a href="https://myaccount.google.com/security" target="_blank">Google Account Security settings</a></li>
                <li><strong>You MUST add yourself as a test user</strong> in the OAuth consent screen (see step 1 below) - this is required for apps in testing mode</li>
            </ul>
        </div>
        
        <div class="step">
            <h3><span class="step-number">1</span> Get Gmail API Credentials</h3>
            <p>You need to create OAuth credentials from Google Cloud Console. Don't worry, it's free and takes just 2 minutes!</p>
            <ol>
                <li><strong>First:</strong> Make sure you have <a href="https://myaccount.google.com/security" target="_blank">Two-Step Verification enabled</a> on your Google account (required by Google Cloud)</li>
                <li>Go to <a href="https://console.cloud.google.com/" target="_blank">Google Cloud Console</a></li>
                <li>Click "Select a project" → "New Project" → Name it "Daily Email Brief" → Create</li>
                <li>Go to "APIs & Services" → "Library" → Search "Gmail API" → Enable it</li>
                <li>Go to "APIs & Services" → "Credentials" → "Create Credentials" → "OAuth client ID"</li>
                <li>If prompted, configure OAuth consent screen:
                    <ul>
                        <li>User Type: <strong>External</strong></li>
                        <li>App name: Daily Email Brief</li>
                        <li>User support email: Your email</li>
                        <li>Developer contact: Your email</li>
                        <li>Save and Continue (skip scopes for now)</li>
                        <li><strong>CRITICAL:</strong> Go to "Test users" section and click "+ ADD USERS"</li>
                        <li>Add <strong>your own email address</strong> (the one you want to connect) as a test user</li>
                        <li>Click "Save"</li>
                    </ul>
                </li>
                <li>Application type: <strong>Web application</strong> (NOT Desktop app - this is important!)</li>
                <li>Name: Daily Email Brief</li>
                <li><strong>⚠️ BEFORE clicking "Create" - Add Redirect URI:</strong>
                    <ul style="margin-top: 10px;">
                        <li>You'll see a section called <strong>"Authorized redirect URIs"</strong></li>
                        <li>Click <strong>"+ ADD URI"</strong></li>
                        <li>Paste this exact URL:
                            <div class="code-block" style="margin: 10px 0; background: #1e293b; color: #f5a623; font-weight: bold;">http://127.0.0.1:5000/oauth/callback</div>
                        </li>
                    </ul>
                </li>
                <li>Click <strong>"Create"</strong></li>
                <li>Copy the <strong>Client ID</strong> and <strong>Client Secret</strong> from the popup</li>
                <div class="alert alert-error" style="margin-top: 15px;">
                    <strong>⚠️ Important:</strong> If you already created a "Desktop app" type, you need to:
                    <ol style="margin-top: 10px; margin-left: 20px;">
                        <li>Delete the existing OAuth client</li>
                        <li>Create a new one with type <strong>"Web application"</strong></li>
                        <li>Add the redirect URI before creating</li>
                    </ol>
                </div>
            </ol>
            <p><strong>💡 Tip:</strong> Keep the Google Cloud Console tab open - you'll need to copy the credentials below.</p>
            <div class="alert alert-error" style="margin-top: 20px;">
                <strong>🚨 Common Mistake:</strong> Many users forget to add the redirect URI! Make sure you complete step 10 above - 
                click on your OAuth client name, add the redirect URI, and save before continuing.
            </div>
        </div>

        <form method="POST" action="/setup/credentials">
            <div class="form-group">
                <label for="client_id">Client ID</label>
                <input type="text" id="client_id" name="client_id" placeholder="xxxxx.apps.googleusercontent.com" required>
            </div>
            <div class="form-group">
                <label for="client_secret">Client Secret</label>
                <input type="password" id="client_secret" name="client_secret" placeholder="GOCSPX-xxxxx" required>
            </div>
            <button type="submit" class="btn">Save Credentials & Continue</button>
        </form>
        {% else %}
        <div class="status">
            <strong>✅ Credentials saved!</strong> Now let's connect your Gmail account.
            <div style="margin-top: 15px;">
                <form method="POST" action="/setup/reset-credentials" style="display: inline;" onsubmit="return confirm('Are you sure you want to reset credentials? You will need to enter them again.');">
                    <button type="submit" class="btn btn-secondary" style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); margin-left: 10px;">
                        🔄 Reset Credentials
                    </button>
                </form>
            </div>
        </div>

        {% if not has_token %}
        <div class="step">
            <h3><span class="step-number">2</span> Connect Your Gmail Account</h3>
            <p>Click the button below to authorize this app to read your emails. You'll be redirected to Google to sign in.</p>
            <p><strong>🔒 Privacy:</strong> All data stays on your computer. We only request read-only access to generate your daily brief.</p>
            <div class="alert alert-info" style="margin-top: 15px;">
                <strong>💡 Troubleshooting:</strong> If you see "access_denied" error, make sure you added your email as a test user in step 1 above. 
                Go back to Google Cloud Console → APIs & Services → OAuth consent screen → Test users → Add your email.
            </div>
        </div>

        <a href="/oauth/authorize" class="btn">🔗 Connect Gmail Account</a>
        {% else %}
        <div class="alert alert-success">
            <strong>✅ Successfully Connected!</strong> Your Gmail account is ready to use.
        </div>
        <div class="step">
            <h3>Next Steps</h3>
            <p>You can now use the CLI to fetch and generate your daily email brief:</p>
            <div class="code-block">
                source venv/bin/activate<br>
                python3 main.py fetch<br>
                python3 main.py score<br>
                python3 main.py brief
            </div>
        </div>
        <a href="/dashboard" class="btn">📊 Go to Dashboard</a>
        <a href="/" class="btn btn-secondary">← Back to Home</a>
        {% endif %}
        {% endif %}
        
        <div style="margin-top: 30px; text-align: center;">
            <a href="/" class="btn btn-secondary">← Back to Home</a>
        </div>
    </div>
</body>
</html>
"""


@app.route('/')
def home():
    """Home page - redirects to appropriate page based on setup status."""
    # Check if user explicitly wants to see home page (via query param)
    show_home = request.args.get('home', 'false').lower() == 'true'
    
    # If Gmail is connected and user didn't request home page, redirect
    if os.path.exists(TOKEN_FILE) and not show_home:
        from src.storage.database import Database
        db = Database()
        
        # Check feedback count
        try:
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM feedback')
            feedback_count = cursor.fetchone()[0]
            conn.close()
        except:
            feedback_count = 0
        
        # If no training done, go to onboarding
        if feedback_count < 5:
            return redirect(url_for('onboarding'))
        
        # Everything set up, go directly to dashboard (preferences are optional)
        return redirect(url_for('dashboard'))
    
    # Show home page (either no Gmail connected, or user requested it)
    gmail_connected = os.path.exists(TOKEN_FILE)
    return render_template_string(HOME_HTML, 
                                 gmail_connected=gmail_connected)


@app.route('/health')
def health():
    """Health check endpoint to verify server is running."""
    return jsonify({
        'status': 'ok',
        'server': 'running',
        'has_credentials': os.path.exists(CREDENTIALS_FILE),
        'has_token': os.path.exists(TOKEN_FILE)
    })


DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Daily Email Brief - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #f5a623 100%);
            min-height: 100vh;
            padding: 20px;
            position: relative;
            overflow-x: hidden;
        }
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 50%, rgba(245, 166, 35, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(30, 60, 114, 0.2) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.98);
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.1);
            padding: 50px;
            position: relative;
            z-index: 1;
            backdrop-filter: blur(10px);
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 2px solid #f0f4f8;
        }
        h1 {
            color: #1e3c72;
            margin-bottom: 15px;
            font-size: 42px;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #1e3c72 0%, #f5a623 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .subtitle {
            color: #64748b;
            font-size: 18px;
            font-weight: 400;
        }
        .success-badge {
            display: inline-block;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            margin-top: 15px;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }
        .section {
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
            border-left: 4px solid #f5a623;
            padding: 30px;
            margin: 25px 0;
            border-radius: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }
        .section h2 {
            color: #1e3c72;
            margin-bottom: 15px;
            font-size: 24px;
            font-weight: 600;
        }
        .section p {
            color: #475569;
            line-height: 1.7;
            margin-bottom: 15px;
            font-size: 16px;
        }
        .code-block {
            background: #1e293b;
            color: #e2e8f0;
            padding: 20px;
            border-radius: 12px;
            font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
            font-size: 14px;
            overflow-x: auto;
            margin: 15px 0;
            border: 1px solid #334155;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
            line-height: 1.8;
        }
        .btn {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 14px 32px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin: 10px 10px 10px 0;
            display: inline-block;
            text-decoration: none;
            box-shadow: 0 4px 12px rgba(30, 60, 114, 0.3);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(30, 60, 114, 0.4);
        }
        .btn-secondary {
            background: linear-gradient(135deg, #64748b 0%, #475569 100%);
        }
        .btn-secondary:hover {
            background: linear-gradient(135deg, #475569 0%, #334155 100%);
        }
        .info-box {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border-left: 4px solid #3b82f6;
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
        }
        .info-box strong {
            color: #1e40af;
        }
        .brief-container {
            background: #ffffff;
            padding: 30px;
            border-radius: 12px;
            border: 2px solid #e2e8f0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
            line-height: 1.8;
            color: #1e3c72;
        }
        .brief-container h1, .brief-container h2, .brief-container h3 {
            color: #1e3c72;
            margin-top: 25px;
            margin-bottom: 15px;
            font-weight: 600;
        }
        .brief-container h1 {
            font-size: 28px;
            border-bottom: 3px solid #f5a623;
            padding-bottom: 10px;
        }
        .brief-container h2 {
            font-size: 22px;
            color: #2a5298;
            margin-top: 30px;
        }
        .brief-container h3 {
            font-size: 18px;
            color: #1e3c72;
        }
        .brief-container h4 {
            font-size: 16px;
            color: #475569;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        .brief-container p {
            margin: 12px 0;
            color: #475569;
            line-height: 1.7;
        }
        .brief-container ul, .brief-container ol {
            margin: 15px 0;
            padding-left: 25px;
            color: #475569;
        }
        .brief-container li {
            margin: 8px 0;
            line-height: 1.6;
        }
        .brief-container strong {
            color: #1e3c72;
            font-weight: 600;
        }
        .brief-container hr {
            border: none;
            border-top: 2px solid #e2e8f0;
            margin: 25px 0;
        }
        .brief-container code {
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 14px;
            color: #1e3c72;
        }
        .brief-card-highlight {
            animation: brief-highlight 2s ease;
        }
        @keyframes brief-highlight {
            0%, 100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
            50% { box-shadow: 0 0 0 8px rgba(59, 130, 246, 0); }
        }
        .brief-header {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            border-radius: 12px;
            margin-bottom: 30px;
        }
        .brief-header h1 {
            color: white;
            border: none;
            margin: 0;
            padding: 0;
        }
        .email-item-brief {
            background: #f8fafc;
            padding: 20px;
            margin: 20px 0;
            border-radius: 12px;
            border-left: 4px solid #f5a623;
        }
        .email-item-brief.critical {
            border-left-color: #ef4444;
            background: #fef2f2;
        }
        .email-item-brief.important {
            border-left-color: #f5a623;
            background: #fffbeb;
        }
        .email-item-review {
            transition: all 0.3s;
        }
        .email-item-review:hover {
            transform: translateX(4px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        .brief-included {
            position: relative;
        }
        .brief-included::before {
            content: '✓';
            position: absolute;
            top: 10px;
            right: 10px;
            background: #10b981;
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
        }
    </style>
    <script>
        function toggleReview() {
            const panel = document.getElementById('review-panel');
            const toggleText = document.getElementById('review-toggle-text');
            if (!panel) return; // Safety check
            
            const isHidden = panel.style.display === 'none' || panel.style.display === '';
            if (isHidden) {
                panel.style.display = 'block';
                toggleText.textContent = '👁️ Hide Email Review';
                // Scroll to panel smoothly
                panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                panel.style.display = 'none';
                toggleText.textContent = '👁️ Review All Emails & Validate Selection';
            }
        }
        
        function scrollToFeedback() {
            // First show the review panel
            const panel = document.getElementById('review-panel');
            if (panel) {
                panel.style.display = 'block';
                // Scroll to first unmarked email
                const unmarkedEmails = panel.querySelectorAll('.email-item-review:not([data-feedback])');
                if (unmarkedEmails.length > 0) {
                    // Find emails with scores in ambiguous range (0.4-0.6) for better learning
                    let targetEmail = null;
                    for (let email of unmarkedEmails) {
                        const scoreText = email.querySelector('[data-score]');
                        if (scoreText) {
                            const score = parseFloat(scoreText.textContent.replace('Score: ', ''));
                            if (score >= 0.4 && score <= 0.6) {
                                targetEmail = email;
                                break;
                            }
                        }
                    }
                    // If no ambiguous emails, use first unmarked
                    if (!targetEmail && unmarkedEmails.length > 0) {
                        targetEmail = unmarkedEmails[0];
                    }
                    if (targetEmail) {
                        targetEmail.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        // Highlight it briefly
                        targetEmail.style.boxShadow = '0 0 20px rgba(245, 158, 11, 0.6)';
                        setTimeout(() => {
                            targetEmail.style.boxShadow = '';
                        }, 2000);
                    }
                }
                panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
        
        // Ensure panel starts hidden on page load
        document.addEventListener('DOMContentLoaded', function() {
            const panel = document.getElementById('review-panel');
            if (panel) {
                panel.style.display = 'none';
            }
        });
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📬 Daily Email Brief</h1>
            <p class="subtitle">Your AI-powered email assistant is ready!</p>
            <div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin-top: 15px;">
                <div class="success-badge">✓ Gmail Connected</div>
                <form method="POST" action="/setup/reset-credentials" style="display: inline; margin: 0;" onsubmit="return confirm('Are you sure you want to unlink Gmail? This will reset your connection and you\\'ll need to reconnect.');">
                    <button type="submit" style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; border: none; padding: 10px 20px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; box-shadow: 0 2px 8px rgba(220, 38, 38, 0.3); transition: all 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(220, 38, 38, 0.4)';" onmouseout="this.style.transform=''; this.style.boxShadow='0 2px 8px rgba(220, 38, 38, 0.3)';">
                        🔄 Unlink Gmail
                    </button>
                </form>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}" style="margin: 20px 0; padding: 15px; border-radius: 12px; 
                        {% if category == 'success' %}background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); color: #065f46; border: 2px solid #10b981;
                        {% elif category == 'error' %}background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); color: #991b1b; border: 2px solid #ef4444;
                        {% else %}background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); color: #1e40af; border: 2px solid #3b82f6;{% endif %}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="section">
            <h2>🚀 Get Your Daily Brief</h2>
            <p>Click the buttons below to fetch, score, and generate your daily email brief:</p>
            
            <div style="display: flex; gap: 15px; flex-wrap: wrap; margin: 20px 0;">
                <form method="POST" action="/dashboard/fetch" style="display: inline;">
                    <button type="submit" class="btn">📥 Fetch Emails</button>
                </form>
                <form method="POST" action="/dashboard/score" style="display: inline;">
                    <button type="submit" class="btn">⭐ Score Importance</button>
                </form>
                <form method="POST" action="/dashboard/generate-brief" style="display: inline;">
                    <button type="submit" class="btn">📊 Generate Brief</button>
                </form>
                <button onclick="scrollToFeedback()" class="btn" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
                    💬 Smart Feedback
                </button>
                <form method="POST" action="/dashboard/reset-training" style="display: inline;" onsubmit="return confirm('Are you sure you want to reset training? This will clear all your feedback and you\'ll need to go through onboarding again.');">
                    <button type="submit" class="btn" style="background: linear-gradient(135deg, #64748b 0%, #475569 100%);">
                        🔄 Reset Training
                    </button>
                </form>
            </div>
            
            <div class="info-box">
                <strong>💡 Tip:</strong> First fetch your emails, then score them for importance, and finally generate your brief. 
                The system will learn from your feedback over time to improve relevance.
            </div>
        </div>

        {% if brief_text %}
        <div class="section">
            <h2 style="color: #1e3c72; margin-bottom: 25px;">📬 Your Daily Email Brief</h2>
            
            <!-- Confidence & Statistics Panel -->
            <div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); padding: 25px; border-radius: 12px; margin-bottom: 25px; border: 2px solid #3b82f6;">
                <!-- Top Stats Row -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; text-align: center; margin-bottom: 25px;">
                    <div>
                        <div style="font-size: 36px; font-weight: 700; color: #1e3c72;">{{ brief_stats.total_emails }}</div>
                        <div style="color: #64748b; font-size: 13px; margin-top: 5px; font-weight: 600;">Total Emails</div>
                    </div>
                    <div>
                        <div style="font-size: 36px; font-weight: 700; color: #dc2626;">{{ brief_stats.critical_count }}</div>
                        <div style="color: #64748b; font-size: 13px; margin-top: 5px; font-weight: 600;">🔴 Critical</div>
                    </div>
                    <div>
                        <div style="font-size: 36px; font-weight: 700; color: #10b981;">{{ brief_stats.important_count }}</div>
                        <div style="color: #64748b; font-size: 13px; margin-top: 5px; font-weight: 600;">Important</div>
                    </div>
                    <div>
                        <div style="font-size: 36px; font-weight: 700; color: #94a3b8;">{{ brief_stats.filtered_count }}</div>
                        <div style="color: #64748b; font-size: 13px; margin-top: 5px; font-weight: 600;">Filtered Out</div>
                    </div>
                </div>
                
                <!-- Category Breakdown - Prominent Display -->
                {% if brief_stats.category_breakdown %}
                <div style="background: white; padding: 20px; border-radius: 12px; margin-top: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <h3 style="color: #1e3c72; font-size: 18px; margin-bottom: 20px; text-align: center; font-weight: 700;">📊 Breakdown: {{ brief_stats.important_count }} Important Emails</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 12px; justify-content: center;">
                        {% for category, count in brief_stats.category_breakdown.items()|sort(attribute='1', reverse=True) %}
                        <div style="background: {% if category == 'Security Alerts' %}#fee2e2{% elif category == 'Work/Jobs' %}#fef3c7{% elif category == 'Financial' %}#dbeafe{% elif category == 'Healthcare' %}#d1fae5{% elif category == 'Promotions' %}#f3f4f6{% elif category == 'Newsletters' %}#f1f5f9{% else %}#f8fafc{% endif %}; 
                            padding: 15px 24px; border-radius: 10px; border-left: 5px solid {% if category == 'Security Alerts' %}#ef4444{% elif category == 'Work/Jobs' %}#f59e0b{% elif category == 'Financial' %}#3b82f6{% elif category == 'Healthcare' %}#10b981{% elif category == 'Promotions' %}#94a3b8{% elif category == 'Newsletters' %}#64748b{% else %}#64748b{% endif %};
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1); min-width: 140px;">
                            <div style="font-size: 28px; font-weight: 700; color: #1e3c72; text-align: center;">{{ count }}</div>
                            <div style="color: #64748b; font-size: 13px; margin-top: 5px; text-align: center; font-weight: 600;">{{ category }}</div>
                        </div>
                        {% endfor %}
                    </div>
                    {% if brief_stats.critical_count > 0 %}
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 2px solid #e2e8f0; text-align: center;">
                        <span style="background: #fee2e2; color: #991b1b; padding: 8px 16px; border-radius: 20px; font-size: 14px; font-weight: 600;">
                            🔴 {{ brief_stats.critical_count }} Critical emails need immediate attention
                        </span>
                    </div>
                    {% endif %}
                </div>
                {% endif %}
                <div style="margin-top: 20px; padding-top: 20px; border-top: 2px solid #bfdbfe;">
                    <p style="color: #1e40af; font-size: 15px; line-height: 1.6; margin-bottom: 15px;">
                        <strong>✓ Quality Check:</strong> We reviewed all {{ brief_stats.total_emails }} emails and selected {{ brief_stats.important_count }} important emails 
                        ({{ brief_stats.critical_count }} critical) based on your preferences (threshold: {{ "%.1f"|format(brief_stats.threshold * 100) }}%). 
                        Filtered out {{ brief_stats.filtered_count }} low-priority emails to save you time.
                    </p>
                    
                    <!-- Sender Categories Summary - Collapsible -->
                    {% if brief_stats.sender_categories %}
                    <div style="background: white; padding: 20px; border-radius: 8px; margin-top: 15px;">
                        <details style="cursor: pointer;">
                            <summary style="color: #1e3c72; font-size: 18px; font-weight: 600; margin-bottom: 15px; list-style: none; cursor: pointer;">
                                📊 Email Breakdown by Category <span style="font-size: 14px; color: #64748b; font-weight: normal;">(click to expand)</span>
                            </summary>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 15px;">
                                {% for category, data in brief_stats.sender_categories.items() %}
                                <div class="category-breakdown-card" style="background: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid {% if category == 'Security Alerts' %}#ef4444{% elif category == 'Work/Jobs' %}#f5a623{% elif category == 'Financial' %}#3b82f6{% elif category == 'Healthcare' %}#10b981{% elif category == 'Promotions' %}#94a3b8{% else %}#64748b{% endif %}; {% if data.first_email_id %}cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;{% endif %}" {% if data.first_email_id %}onclick="var el = document.getElementById('email-{{ data.first_email_id }}'); if(el){ el.scrollIntoView({behavior:'smooth',block:'center'}); el.classList.add('brief-card-highlight'); setTimeout(function(){ el.classList.remove('brief-card-highlight'); }, 2000); }"{% endif %}>
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <strong style="color: #1e3c72; font-size: 14px;">{{ category }}</strong>
                                        <span style="background: {% if data.in_brief > 0 %}#10b981{% else %}#94a3b8{% endif %}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;">
                                            {{ data.count }} total{% if data.in_brief > 0 %} | {{ data.in_brief }} in brief{% endif %}
                                        </span>
                                    </div>
                                    <div style="color: #64748b; font-size: 12px; margin-top: 5px;">
                                        {% for sender in data.senders[:3] %}
                                        <div style="margin: 3px 0;">• {{ sender[:40] }}{% if sender|length > 40 %}...{% endif %}</div>
                                        {% endfor %}
                                        {% if data.sender_count > 3 %}
                                        <div style="color: #94a3b8; font-style: italic;">+ {{ data.sender_count - 3 }} more</div>
                                        {% endif %}
                                    </div>
                                    {% if data.first_email_id %}
                                    <div style="font-size: 11px; color: #3b82f6; margin-top: 8px;">↓ Click to jump to summary</div>
                                    {% endif %}
                                </div>
                                {% endfor %}
                            </div>
                            <p style="color: #64748b; font-size: 13px; margin-top: 15px; font-style: italic;">
                                💡 This breakdown helps you see what types of emails you received. Categories with emails "in brief" are highlighted in green.
                            </p>
                        </details>
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <!-- Brief Content -->
            <div style="margin-top: 30px;">
                <h3 style="color: #1e3c72; font-size: 20px; margin-bottom: 20px; font-weight: 600;">📋 Summary of Important Emails</h3>
                <div class="brief-container">
                    {{ brief_text|safe }}
                </div>
                <!-- Navigable email cards: click category above to scroll here -->
                {% if important_emails %}
                <div style="margin-top: 24px;">
                    <p style="color: #64748b; font-size: 14px; margin-bottom: 16px;">Jump to an email below or open in Gmail to reply.</p>
                    {% for email in important_emails %}
                    <div id="email-{{ email.id }}" class="brief-email-card" style="background: #f8fafc; border-left: 4px solid #3b82f6; padding: 18px; margin: 14px 0; border-radius: 8px; transition: box-shadow 0.2s;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                            <div style="flex: 1; min-width: 0;">
                                <strong style="color: #1e3c72; font-size: 15px;">{{ email.subject[:80] }}{% if email.subject|length > 80 %}...{% endif %}</strong><br>
                                <span style="color: #64748b; font-size: 13px;">From: {{ email.sender }}</span><br>
                                <span style="color: #94a3b8; font-size: 12px;">{{ email.date }}</span>
                            </div>
                            <div style="display: flex; gap: 8px; flex-shrink: 0;">
                                <a href="https://mail.google.com/mail/u/0/#inbox/{{ email.id }}" target="_blank" rel="noopener" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; text-decoration: none;">Open in Gmail to reply</a>
                                <button type="button" class="btn-view-full" data-email-id="{{ email.id }}" style="background: #e2e8f0; color: #475569; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; border: none; cursor: pointer;">View full email</button>
                            </div>
                        </div>
                        <p class="brief-email-snippet" style="color: #64748b; font-size: 14px; margin-top: 10px;">{{ (email.snippet or '')[:200] }}{% if (email.snippet or '')|length > 200 %}...{% endif %}</p>
                        <div class="brief-email-body" style="display: none; margin-top: 12px; padding: 12px; background: white; border-radius: 6px; border: 1px solid #e2e8f0; font-size: 14px; color: #334155; line-height: 1.5;"></div>
                    </div>
                    {% endfor %}
                </div>
                <script>
                (function(){
                    document.querySelectorAll('.btn-view-full').forEach(function(btn){
                        btn.addEventListener('click', function(){
                            var card = this.closest('.brief-email-card');
                            var bodyEl = card.querySelector('.brief-email-body');
                            if (bodyEl.style.display === 'block') {
                                bodyEl.style.display = 'none';
                                this.textContent = 'View full email';
                                return;
                            }
                            if (bodyEl.dataset.loaded === '1') {
                                bodyEl.style.display = 'block';
                                this.textContent = 'Hide full email';
                                return;
                            }
                            var id = this.getAttribute('data-email-id');
                            this.textContent = 'Loading...';
                            fetch('/api/email/' + encodeURIComponent(id)).then(function(r){ return r.json(); }).then(function(data){
                                bodyEl.innerHTML = (data.body || data.snippet || 'No content').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
                                bodyEl.dataset.loaded = '1';
                                bodyEl.style.display = 'block';
                                btn.textContent = 'Hide full email';
                            }).catch(function(){
                                bodyEl.innerHTML = 'Could not load email.';
                                bodyEl.style.display = 'block';
                                btn.textContent = 'Hide full email';
                            }).finally(function(){ btn.textContent = bodyEl.style.display === 'block' ? 'Hide full email' : 'View full email'; });
                        });
                    });
                })();
                </script>
                {% endif %}
            </div>
            
            <!-- Review Section -->
            <div style="margin-top: 30px;">
                <button onclick="toggleReview()" class="btn" style="width: 100%; margin-bottom: 20px;">
                    <span id="review-toggle-text">👁️ Review All Emails & Validate Selection</span>
                </button>
                
                <div id="review-panel" style="display: none; background: #f8fafc; padding: 25px; border-radius: 12px; border: 2px solid #e2e8f0;">
                    <h3 style="color: #1e3c72; margin-bottom: 20px;">📋 Complete Email Review</h3>
                    <p style="color: #64748b; margin-bottom: 20px;">
                        Review all {{ brief_stats.total_emails }} emails sorted by importance. 
                        <strong>Emails in the brief are highlighted in green.</strong> 
                        You can mark any email to help the system learn.
                    </p>
                    
                    <div style="max-height: 600px; overflow-y: auto; overflow-x: hidden;">
                        {% for email in all_emails %}
                        <div class="email-item-review {% if email.importance_score > brief_stats.threshold %}brief-included{% endif %}" 
                             style="background: {% if email.importance_score > brief_stats.threshold %}#f0fdf4{% else %}#ffffff{% endif %}; 
                                    padding: 15px; margin: 10px 0; border-radius: 8px; 
                                    border-left: 4px solid {% if email.importance_score > 0.7 %}#dc2626{% elif email.importance_score > 0.5 %}#f59e0b{% elif email.importance_score > 0.4 %}#3b82f6{% else %}#94a3b8{% endif %};
                                    {% if email.importance_score > brief_stats.threshold %}border: 2px solid #10b981;{% endif %}">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div style="flex: 1;">
                                    {% if email.importance_score > brief_stats.threshold %}
                                    <span style="background: #10b981; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-right: 10px;">IN BRIEF</span>
                                    {% endif %}
                                    {% if email.importance_score > 0.7 %}
                                    <span style="background: #dc2626; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-right: 10px; margin-top: 5px; display: inline-block;">🔴 CRITICAL</span>
                                    {% endif %}
                                    <strong style="color: #1e3c72;">{{ email.subject }}</strong><br>
                                    <span style="color: #64748b; font-size: 14px;">From: {{ email.sender }}</span><br>
                                    <span style="color: #94a3b8; font-size: 12px;">{{ email.date }}</span>
                                </div>
                                <div style="margin-left: 15px; display: flex; flex-direction: column; gap: 8px; align-items: flex-end;">
                                    <span data-score="{{ email.importance_score }}" style="background: {% if email.importance_score > 0.7 %}#fee2e2{% elif email.importance_score > 0.5 %}#fef3c7{% elif email.importance_score > 0.4 %}#dbeafe{% else %}#f1f5f9{% endif %}; 
                                        color: {% if email.importance_score > 0.7 %}#991b1b{% elif email.importance_score > 0.5 %}#92400e{% elif email.importance_score > 0.4 %}#1e40af{% else %}#475569{% endif %}; 
                                        padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                                        Score: {{ "%.2f"|format(email.importance_score) }}
                                    </span>
                                    {% if not email.has_feedback %}
                                    <div style="display: flex; gap: 5px;">
                                        <form method="POST" action="/dashboard/feedback" style="display: inline;">
                                            <input type="hidden" name="email_id" value="{{ email.id }}">
                                            <input type="hidden" name="is_important" value="true">
                                            <button type="submit" style="background: #10b981; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; font-weight: 600;">
                                                ✓
                                            </button>
                                        </form>
                                        <form method="POST" action="/dashboard/feedback" style="display: inline;">
                                            <input type="hidden" name="email_id" value="{{ email.id }}">
                                            <input type="hidden" name="is_important" value="false">
                                            <button type="submit" style="background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; font-weight: 600;">
                                                ✗
                                            </button>
                                        </form>
                                    </div>
                                    {% else %}
                                    <span style="background: {% if email.feedback_value == 1 %}#10b981{% else %}#ef4444{% endif %}; color: white; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">
                                        {% if email.feedback_value == 1 %}✓ Marked{% else %}✗ Marked{% endif %}
                                    </span>
                                    {% endif %}
                                </div>
                            </div>
                            {% if email.snippet %}
                            <p style="color: #64748b; font-size: 14px; margin-top: 8px;">{{ email.snippet[:150] }}{% if email.snippet|length > 150 %}...{% endif %}</p>
                            {% endif %}
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            
            <div class="info-box" style="margin-top: 20px;">
                <strong>💡 Tip:</strong> Click "Review All Emails" above to see the complete list and validate our selection. 
                Emails included in the brief are highlighted in green. You can mark any email to help the system learn your preferences.
            </div>
        </div>
        {% endif %}
        
        {% if has_emails %}
        <div class="section">
            <h2>📧 Your Emails by Category</h2>
            <p>Emails organized by category. Mark emails to help the AI learn your preferences!</p>
            
            {% if brief_stats.sender_categories %}
            {% for category, data in brief_stats.sender_categories.items() %}
            <div style="margin: 30px 0; background: #f8fafc; padding: 20px; border-radius: 12px; border-left: 4px solid {% if category == 'Security Alerts' %}#ef4444{% elif category == 'Work/Jobs' %}#f59e0b{% elif category == 'Financial' %}#3b82f6{% elif category == 'Healthcare' %}#10b981{% else %}#64748b{% endif %};">
                <h3 style="color: #1e3c72; margin-bottom: 15px;">
                    {{ category }} 
                    <span style="font-size: 14px; color: #64748b; font-weight: normal;">({{ data.count }} emails{% if data.in_brief > 0 %}, {{ data.in_brief }} important{% endif %})</span>
                </h3>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h4 style="color: #10b981; font-size: 14px; margin-bottom: 10px;">✓ Important ({{ data.in_brief }})</h4>
                        {% for email in all_emails %}
                        {% set email_category = categorize_sender(email.sender, email.subject) %}
                        {% if email_category == category and email.importance_score > brief_stats.threshold %}
                        <div style="background: white; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 3px solid #10b981;">
                            <strong style="color: #1e3c72; font-size: 13px;">{{ email.subject[:50] }}{% if email.subject|length > 50 %}...{% endif %}</strong><br>
                            <span style="color: #64748b; font-size: 12px;">{{ email.sender[:40] }}{% if email.sender|length > 40 %}...{% endif %}</span>
                            <span style="float: right; background: #10b981; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;">{{ "%.2f"|format(email.importance_score) }}</span>
                        </div>
                        {% endif %}
                        {% endfor %}
                    </div>
                    <div>
                        <h4 style="color: #94a3b8; font-size: 14px; margin-bottom: 10px;">✗ Filtered Out ({{ data.count - data.in_brief }})</h4>
                        {% for email in all_emails %}
                        {% set email_category = categorize_sender(email.sender, email.subject) %}
                        {% if email_category == category and email.importance_score <= brief_stats.threshold %}
                        <div style="background: white; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 3px solid #94a3b8; opacity: 0.7;">
                            <strong style="color: #64748b; font-size: 13px;">{{ email.subject[:50] }}{% if email.subject|length > 50 %}...{% endif %}</strong><br>
                            <span style="color: #94a3b8; font-size: 12px;">{{ email.sender[:40] }}{% if email.sender|length > 40 %}...{% endif %}</span>
                            <span style="float: right; background: #94a3b8; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;">{{ "%.2f"|format(email.importance_score) }}</span>
                        </div>
                        {% endif %}
                        {% endfor %}
                    </div>
                </div>
            </div>
            {% endfor %}
            {% endif %}
            
            <div style="margin-top: 30px;">
                <h3 style="color: #1e3c72; margin-bottom: 15px;">📋 All Emails ({{ total_emails }} total)</h3>
                <p style="color: #64748b; margin-bottom: 15px;">Mark emails as important or not important to help the AI learn your preferences. This improves future briefs!</p>
                <div style="max-height: 600px; overflow-y: auto; overflow-x: hidden; margin-top: 20px;">
                    {% for email in emails %}
                <div style="background: #f8fafc; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 3px solid {% if email.importance_score > 0.7 %}#dc2626{% elif email.importance_score > 0.5 %}#f59e0b{% elif email.importance_score > 0.4 %}#3b82f6{% else %}#94a3b8{% endif %};">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div style="flex: 1;">
                            <strong style="color: #1e3c72;">{{ email.subject }}</strong><br>
                            <span style="color: #64748b; font-size: 14px;">From: {{ email.sender }}</span><br>
                            <span style="color: #94a3b8; font-size: 12px;">{{ email.date }}</span>
                        </div>
                        <div style="margin-left: 15px; display: flex; flex-direction: column; gap: 8px; align-items: flex-end;">
                            <span style="background: {% if email.importance_score > 0.7 %}#fee2e2{% elif email.importance_score > 0.5 %}#fef3c7{% elif email.importance_score > 0.4 %}#dbeafe{% else %}#f1f5f9{% endif %}; 
                                color: {% if email.importance_score > 0.7 %}#991b1b{% elif email.importance_score > 0.5 %}#92400e{% elif email.importance_score > 0.4 %}#1e40af{% else %}#475569{% endif %}; 
                                padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                                Score: {{ "%.2f"|format(email.importance_score) }}
                                {% if email.importance_score > 0.7 %}<span style="margin-left: 5px;">🔴</span>{% endif %}
                            </span>
                            <div style="display: flex; gap: 5px;">
                                {% if email.has_feedback %}
                                    {% if email.feedback_value == 1 %}
                                    <span style="background: #10b981; color: white; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">
                                        ✓ Marked Important
                                    </span>
                                    {% else %}
                                    <span style="background: #ef4444; color: white; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">
                                        ✗ Marked Not Important
                                    </span>
                                    {% endif %}
                                {% else %}
                                <form method="POST" action="/dashboard/feedback" style="display: inline;">
                                    <input type="hidden" name="email_id" value="{{ email.id }}">
                                    <input type="hidden" name="is_important" value="true">
                                    <button type="submit" style="background: #10b981; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; font-weight: 600; transition: all 0.2s;" title="Mark as Important" onmouseover="this.style.background='#059669'" onmouseout="this.style.background='#10b981'">
                                        ✓ Important
                                    </button>
                                </form>
                                <form method="POST" action="/dashboard/feedback" style="display: inline;">
                                    <input type="hidden" name="email_id" value="{{ email.id }}">
                                    <input type="hidden" name="is_important" value="false">
                                    <button type="submit" style="background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; font-weight: 600; transition: all 0.2s;" title="Mark as Not Important" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'">
                                        ✗ Not Important
                                    </button>
                                </form>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    {% if email.snippet %}
                    <p style="color: #64748b; font-size: 14px; margin-top: 8px;">{{ email.snippet[:150] }}{% if email.snippet|length > 150 %}...{% endif %}</p>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% else %}
        <div class="section">
            <h2>📥 No Emails Yet</h2>
            <p>Click "Fetch Emails" to retrieve your emails from the last 48 hours.</p>
        </div>
        {% endif %}


        <div style="text-align: center; margin-top: 40px;">
            <a href="/?home=true" class="btn btn-secondary">← Back to Home</a>
            <a href="/setup/gmail" class="btn btn-secondary">⚙️ Settings</a>
        </div>
    </div>
</body>
</html>
"""


ONBOARDING_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Train Your Email Brief - Daily Email Brief</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #f5a623 100%);
            min-height: 100vh;
            padding: 20px;
            position: relative;
            overflow-x: hidden;
        }
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 50%, rgba(245, 166, 35, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(30, 60, 114, 0.2) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.98);
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 50px;
            position: relative;
            z-index: 1;
            backdrop-filter: blur(10px);
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 2px solid #f0f4f8;
        }
        h1 {
            color: #1e3c72;
            margin-bottom: 15px;
            font-size: 42px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        .subtitle {
            color: #64748b;
            font-size: 18px;
            margin-top: 10px;
        }
        .progress-bar {
            background: #e2e8f0;
            height: 8px;
            border-radius: 4px;
            margin: 30px 0;
            overflow: hidden;
        }
        .progress-fill {
            background: linear-gradient(90deg, #1e3c72 0%, #f5a623 100%);
            height: 100%;
            transition: width 0.3s;
        }
        .section {
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
            border-left: 4px solid #f5a623;
            padding: 30px;
            margin: 25px 0;
            border-radius: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }
        .section h2 {
            color: #1e3c72;
            margin-bottom: 15px;
            font-size: 24px;
            font-weight: 600;
        }
        .email-item {
            background: #ffffff;
            padding: 20px;
            margin: 15px 0;
            border-radius: 12px;
            border: 2px solid #e2e8f0;
            transition: all 0.3s;
        }
        .email-item:hover {
            border-color: #f5a623;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        .email-item.marked-important {
            border-color: #10b981;
            background: #f0fdf4;
        }
        .email-item.marked-not-important {
            border-color: #ef4444;
            background: #fef2f2;
        }
        .email-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 10px;
        }
        .email-subject {
            font-weight: 600;
            color: #1e3c72;
            font-size: 16px;
            flex: 1;
        }
        .email-sender {
            color: #64748b;
            font-size: 14px;
            margin-top: 5px;
        }
        .email-snippet {
            color: #475569;
            font-size: 14px;
            margin-top: 10px;
            line-height: 1.6;
        }
        .feedback-buttons {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .btn-feedback {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            flex: 1;
        }
        .btn-important {
            background: #10b981;
            color: white;
        }
        .btn-important:hover {
            background: #059669;
            transform: translateY(-2px);
        }
        .btn-important.selected {
            background: #059669;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
        }
        .btn-not-important {
            background: #ef4444;
            color: white;
        }
        .btn-not-important:hover {
            background: #dc2626;
            transform: translateY(-2px);
        }
        .btn-not-important.selected {
            background: #dc2626;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
        }
        .btn-continue {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 16px 40px;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin: 30px auto;
            display: block;
            box-shadow: 0 4px 12px rgba(30, 60, 114, 0.3);
        }
        .btn-continue:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(30, 60, 114, 0.4);
        }
        .btn-continue:disabled {
            background: #94a3b8;
            cursor: not-allowed;
            transform: none;
        }
        .info-box {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border-left: 4px solid #3b82f6;
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
        }
        .info-box strong {
            color: #1e40af;
        }
        .category-label {
            display: inline-block;
            background: #f5a623;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Train Your Email Brief</h1>
            <p class="subtitle">Help us learn what matters to you by reviewing a few sample emails</p>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {{ progress }}%"></div>
            </div>
            <p style="color: #64748b; font-size: 14px;">{{ marked_count }} of {{ total_emails }} emails reviewed</p>
        </div>

        <div class="info-box">
            <strong>💡 Why this matters:</strong> By marking a few sample emails, the AI learns your preferences. 
            This helps us prioritize what's truly important to you and skip promotional emails, newsletters, and other low-priority messages.
        </div>

        <div class="section">
            <h2>📧 Review These Sample Emails</h2>
            <p>Mark each email as <strong>Important</strong> or <strong>Not Important</strong>. We'll use this to personalize your daily brief.</p>
            
            <form id="training-form" method="POST" action="/onboarding/complete">
                {% for email in sample_emails %}
                <div class="email-item" id="email-{{ email.id }}" data-email-id="{{ email.id }}">
                    <div class="category-label">{{ email.category|default('Email') }}</div>
                    <div class="email-header">
                        <div style="flex: 1;">
                            <div class="email-subject">{{ email.subject }}</div>
                            <div class="email-sender">From: {{ email.sender }}</div>
                        </div>
                    </div>
                    {% if email.snippet %}
                    <div class="email-snippet">{{ email.snippet[:200] }}{% if email.snippet|length > 200 %}...{% endif %}</div>
                    {% endif %}
                    <div class="feedback-buttons">
                        <button type="button" class="btn-feedback btn-important" 
                                onclick="markEmail('{{ email.id }}', true, this)">
                            ✓ Important
                        </button>
                        <button type="button" class="btn-feedback btn-not-important" 
                                onclick="markEmail('{{ email.id }}', false, this)">
                            ✗ Not Important
                        </button>
                    </div>
                    <input type="hidden" name="email_{{ email.id }}" id="feedback-{{ email.id }}" value="">
                </div>
                {% endfor %}
                
                <button type="submit" class="btn-continue" id="continue-btn" disabled>
                    Continue to Dashboard →
                </button>
            </form>
        </div>
    </div>

    <script>
        let markedCount = 0;
        const totalEmails = {{ total_emails }};

        function markEmail(emailId, isImportant, buttonElement) {
            console.log('[ONBOARDING] Marking email:', emailId, 'as', isImportant ? 'Important' : 'Not Important');
            
            const emailItem = document.getElementById('email-' + emailId);
            const feedbackInput = document.getElementById('feedback-' + emailId);
            const buttons = emailItem.querySelectorAll('.btn-feedback');
            
            // Remove previous selections
            buttons.forEach(btn => btn.classList.remove('selected'));
            emailItem.classList.remove('marked-important', 'marked-not-important');
            
            // Mark current selection
            buttonElement.classList.add('selected');
            feedbackInput.value = isImportant ? 'true' : 'false';
            
            console.log('[ONBOARDING] Feedback input value set to:', feedbackInput.value);
            
            if (isImportant) {
                emailItem.classList.add('marked-important');
            } else {
                emailItem.classList.add('marked-not-important');
            }
            
            // Update count
            markedCount = document.querySelectorAll('.email-item.marked-important, .email-item.marked-not-important').length;
            console.log('[ONBOARDING] Marked count:', markedCount, 'of', totalEmails);
            
            // Update progress
            const progress = (markedCount / totalEmails) * 100;
            document.querySelector('.progress-fill').style.width = progress + '%';
            document.querySelector('.subtitle').nextElementSibling.nextElementSibling.textContent = 
                markedCount + ' of ' + totalEmails + ' emails reviewed';
            
            // Enable continue button when all marked
            const continueBtn = document.getElementById('continue-btn');
            if (markedCount === totalEmails) {
                continueBtn.disabled = false;
                continueBtn.textContent = '✓ Complete Training →';
                console.log('[ONBOARDING] All emails marked! Continue button enabled.');
            } else {
                continueBtn.disabled = true;
            }
        }
        
        // Log form submission
        document.getElementById('training-form').addEventListener('submit', function(e) {
            console.log('[ONBOARDING] Form submitting...');
            const formData = new FormData(this);
            console.log('[ONBOARDING] Form data:', Object.fromEntries(formData));
        });
    </script>
</body>
</html>
"""

PREFERENCES_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Configure Preferences - Daily Email Brief</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #f5a623 100%);
            min-height: 100vh;
            padding: 20px;
            position: relative;
            overflow-x: hidden;
        }
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 50%, rgba(245, 166, 35, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(30, 60, 114, 0.2) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.98);
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 50px;
            position: relative;
            z-index: 1;
            backdrop-filter: blur(10px);
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 2px solid #f0f4f8;
        }
        h1 {
            color: #1e3c72;
            margin-bottom: 15px;
            font-size: 42px;
            font-weight: 700;
        }
        .subtitle {
            color: #64748b;
            font-size: 18px;
        }
        .section {
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
            border-left: 4px solid #f5a623;
            padding: 30px;
            margin: 25px 0;
            border-radius: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }
        .section h2 {
            color: #1e3c72;
            margin-bottom: 15px;
            font-size: 24px;
        }
        .form-group {
            margin: 20px 0;
        }
        label {
            display: block;
            color: #1e3c72;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 15px;
        }
        input[type="text"], input[type="email"], input[type="number"], select {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 15px;
            transition: all 0.3s;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #f5a623;
            box-shadow: 0 0 0 3px rgba(245, 166, 35, 0.1);
        }
        .btn {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 14px 32px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin: 10px 10px 10px 0;
            display: inline-block;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(30, 60, 114, 0.4);
        }
        .btn-secondary {
            background: linear-gradient(135deg, #64748b 0%, #475569 100%);
        }
        .sender-item {
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border: 2px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .btn-remove {
            background: #ef4444;
            color: white;
            padding: 6px 12px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
        }
        .info-box {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border-left: 4px solid #3b82f6;
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚙️ Configure Your Preferences</h1>
            <p class="subtitle">Personalize your daily email brief</p>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="info-box" style="{% if category == 'success' %}background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); border-color: #10b981;{% elif category == 'error' %}background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border-color: #ef4444;{% endif %}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST" action="/preferences/save">
            <!-- Important Senders -->
            <div class="section">
                <h2>📧 Important Senders</h2>
                <p>Add email addresses or domains that should always be marked as important.</p>
                
                <div id="senders-list">
                    {% for sender in important_senders %}
                    <div class="sender-item">
                        <div>
                            <strong>{{ sender.sender }}</strong>
                            <span style="color: #64748b; font-size: 14px; margin-left: 10px;">
                                ({{ sender.priority }} priority, {{ sender.category }})
                            </span>
                        </div>
                        <button type="button" class="btn-remove" onclick="removeSender('{{ sender.sender }}')">Remove</button>
                    </div>
                    {% endfor %}
                </div>
                
                <div class="form-group" style="margin-top: 20px;">
                    <label>Add New Sender</label>
                    <input type="text" id="new-sender" placeholder="e.g., boss@company.com or *@family.com" style="margin-bottom: 10px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <select id="new-priority">
                            <option value="high">High Priority</option>
                            <option value="medium" selected>Medium Priority</option>
                            <option value="low">Low Priority</option>
                        </select>
                        <select id="new-category">
                            <option value="work" selected>Work</option>
                            <option value="personal">Personal</option>
                            <option value="urgent">Urgent</option>
                            <option value="other">Other</option>
                        </select>
                    </div>
                    <button type="button" class="btn" onclick="addSender()" style="margin-top: 10px;">Add Sender</button>
                </div>
            </div>

            <!-- Brief Settings -->
            <div class="section">
                <h2>📊 Brief Settings</h2>
                <div class="form-group">
                    <label>Number of top emails in brief</label>
                    <input type="number" name="brief_top_n" value="{{ brief_top_n }}" min="5" max="50" required>
                </div>
                <div class="form-group">
                    <label>Minimum importance score (0.0 - 1.0)</label>
                    <input type="number" name="min_score" value="{{ min_score }}" min="0" max="1" step="0.1" required>
                </div>
            </div>

            <!-- Delivery Preferences -->
            <div class="section">
                <h2>📬 Delivery Preferences</h2>
                <div class="form-group">
                    <label>How would you like to receive your brief?</label>
                    <select name="delivery_method" required>
                        <option value="web" {% if delivery_method == 'web' %}selected{% endif %}>Web Dashboard</option>
                        <option value="email" {% if delivery_method == 'email' %}selected{% endif %}>Email</option>
                        <option value="both" {% if delivery_method == 'both' %}selected{% endif %}>Both</option>
                        <option value="cli" {% if delivery_method == 'cli' %}selected{% endif %}>CLI Only</option>
                    </select>
                </div>
                <div class="form-group" id="email-delivery-group" style="display: {% if delivery_method in ['email', 'both'] %}block{% else %}none{% endif %};">
                    <label>Email address for brief delivery</label>
                    <input type="email" name="delivery_email" value="{{ delivery_email }}" placeholder="your-email@example.com">
                </div>
            </div>

            <div style="text-align: center; margin-top: 40px;">
                <button type="submit" class="btn">✅ Save Preferences & Continue</button>
            </div>
        </form>

        <div style="text-align: center; margin-top: 20px;">
            <a href="/dashboard" class="btn btn-secondary">Skip for Now →</a>
        </div>
    </div>

    <script>
        // Show/hide email delivery field
        document.querySelector('select[name="delivery_method"]').addEventListener('change', function() {
            const emailGroup = document.getElementById('email-delivery-group');
            if (this.value === 'email' || this.value === 'both') {
                emailGroup.style.display = 'block';
            } else {
                emailGroup.style.display = 'none';
            }
        });

        function addSender() {
            const sender = document.getElementById('new-sender').value.trim();
            const priority = document.getElementById('new-priority').value;
            const category = document.getElementById('new-category').value;
            
            if (!sender) {
                alert('Please enter a sender email or domain');
                return;
            }
            
            // Add hidden input to form
            const form = document.querySelector('form');
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'sender_' + Date.now();
            input.value = sender + '|' + priority + '|' + category;
            form.appendChild(input);
            
            // Add to display
            const list = document.getElementById('senders-list');
            const item = document.createElement('div');
            item.className = 'sender-item';
            item.innerHTML = `
                <div>
                    <strong>${sender}</strong>
                    <span style="color: #64748b; font-size: 14px; margin-left: 10px;">
                        (${priority} priority, ${category})
                    </span>
                </div>
                <button type="button" class="btn-remove" onclick="this.parentElement.remove(); input.remove();">Remove</button>
            `;
            list.appendChild(item);
            
            // Clear input
            document.getElementById('new-sender').value = '';
        }

        function removeSender(sender) {
            // This will be handled by the form submission
            if (confirm('Remove this sender?')) {
                event.target.closest('.sender-item').remove();
            }
        }
    </script>
</body>
</html>
"""


@app.route('/preferences')
def preferences():
    """Preferences configuration page."""
    if not os.path.exists(TOKEN_FILE):
        flash('Please connect your Gmail account first', 'error')
        return redirect(url_for('onboarding'))
    
    from src.storage.database import Database
    db = Database()
    
    # Get current preferences
    brief_top_n = db.get_user_preference('brief_top_n', '10')
    min_score = db.get_user_preference('min_importance_score', '0.3')
    delivery_method = db.get_user_preference('delivery_method', 'web')
    delivery_email = db.get_user_preference('delivery_email', '')
    
    # Get important senders
    important_senders = db.get_important_senders()
    
    return render_template_string(PREFERENCES_HTML,
                                 important_senders=important_senders,
                                 brief_top_n=brief_top_n,
                                 min_score=min_score,
                                 delivery_method=delivery_method,
                                 delivery_email=delivery_email)


@app.route('/preferences/save', methods=['POST'])
def preferences_save():
    """Save preferences."""
    if not os.path.exists(TOKEN_FILE):
        flash('Please connect your Gmail account first', 'error')
        return redirect(url_for('onboarding'))
    
    from src.storage.database import Database
    db = Database()
    
    # Save preferences
    db.save_user_preference('brief_top_n', request.form.get('brief_top_n', '10'))
    db.save_user_preference('min_importance_score', request.form.get('min_score', '0.3'))
    db.save_user_preference('delivery_method', request.form.get('delivery_method', 'web'))
    
    delivery_email = request.form.get('delivery_email', '')
    if delivery_email:
        db.save_user_preference('delivery_email', delivery_email)
    
    # Save important senders
    for key, value in request.form.items():
        if key.startswith('sender_'):
            parts = value.split('|')
            if len(parts) == 3:
                sender, priority, category = parts
                db.save_important_sender(sender, priority, category)
    
    flash('✅ Preferences saved successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/onboarding')
def onboarding():
    """Onboarding page - includes OAuth setup if needed, then email training."""
    # Check if credentials exist
    has_credentials = os.path.exists(CREDENTIALS_FILE)
    has_token = os.path.exists(TOKEN_FILE)
    
    # If no credentials, show setup instructions
    if not has_credentials:
        return render_template_string(SETUP_HTML,
                                    provider_name='Gmail',
                                    has_credentials=False,
                                    has_token=False)
    
    # If credentials but no token, show connection step
    if has_credentials and not has_token:
        return render_template_string(SETUP_HTML,
                                    provider_name='Gmail',
                                    has_credentials=True,
                                    has_token=False)
    
    # If connected, check if training already done
    if has_token:
        from src.storage.database import Database
        db = Database()
        try:
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM feedback')
            feedback_count = cursor.fetchone()[0]
            conn.close()
            print(f"\n[ONBOARDING] Loading onboarding page. Current feedback count: {feedback_count}")
            
            # If user already has feedback (training done), skip to dashboard
            if feedback_count >= 5:
                print(f"[ONBOARDING] User already completed training ({feedback_count} feedback entries). Redirecting to dashboard.")
                return redirect(url_for('dashboard'))
        except Exception as e:
            print(f"[ONBOARDING] Error checking feedback count: {e}")
            feedback_count = 0
        
        # Fetch some sample emails for training
        try:
            from src.email_connectors.gmail import GmailConnector
            from config.settings import EMAIL_FETCH_HOURS
            
            gmail = GmailConnector()
            if not gmail.authenticate():
                flash('Gmail authentication failed. Please reconnect.', 'error')
                return redirect(url_for('onboarding'))  # Will show setup again
            
            # Fetch emails
            emails = gmail.fetch_recent_emails(hours=EMAIL_FETCH_HOURS)
            
            # Save emails to database
            for email in emails:
                db.save_email(email, account_type='gmail')
            
            # Select diverse sample emails (different senders, different types)
            sample_emails = []
            seen_senders = set()
            
            # First, try to get diverse senders
            for email in emails[:50]:  # Look at first 50
                if len(sample_emails) >= 10:
                    break
                sender = email.get('sender', '').lower()
                sender_key = sender.split('<')[0].strip() if '<' in sender else sender
                if sender_key not in seen_senders or len(sample_emails) < 5:
                    sample_emails.append(email)
                    seen_senders.add(sender_key)
            
            # If we don't have enough, fill with remaining
            while len(sample_emails) < 10 and len(sample_emails) < len(emails):
                for email in emails:
                    if email not in sample_emails:
                        sample_emails.append(email)
                        break
                if len(sample_emails) >= 10:
                    break
            
            # Categorize emails (simple heuristic)
            for email in sample_emails:
                subject_lower = email.get('subject', '').lower()
                sender_lower = email.get('sender', '').lower()
                
                if any(word in subject_lower for word in ['promo', 'sale', 'deal', 'offer', 'discount', '$', 'fare']):
                    email['category'] = 'Promotion'
                elif any(word in sender_lower for word in ['newsletter', 'news', 'digest', 'update']):
                    email['category'] = 'Newsletter'
                elif any(word in subject_lower for word in ['security', 'alert', 'important', 'urgent', 'action']):
                    email['category'] = 'Important'
                elif any(word in sender_lower for word in ['noreply', 'no-reply', 'donotreply']):
                    email['category'] = 'Notification'
                else:
                    email['category'] = 'Email'
            
            return render_template_string(ONBOARDING_HTML,
                                         sample_emails=sample_emails[:10],
                                         total_emails=min(10, len(sample_emails)),
                                         marked_count=0,
                                         progress=0)
        except Exception as e:
            flash(f'Error loading training emails: {str(e)}', 'error')
            return redirect(url_for('dashboard'))


@app.route('/onboarding/complete', methods=['POST'])
def onboarding_complete():
    """Save training feedback and redirect to dashboard."""
    if not os.path.exists(TOKEN_FILE):
        flash('Please connect your Gmail account first', 'error')
        return redirect(url_for('onboarding'))
    
    print(f"\n[ONBOARDING] Training completion request received")
    print(f"[ONBOARDING] Form data: {dict(request.form)}")
    
    try:
        from src.storage.database import Database
        db = Database()
        
        # Save all feedback from form
        feedback_count = 0
        for key, value in request.form.items():
            if key.startswith('email_'):
                email_id = key.replace('email_', '')
                is_important = value.lower() == 'true'
                print(f"[ONBOARDING] Saving feedback for {email_id}: {is_important}")
                db.save_feedback(email_id, is_important)
                feedback_count += 1
        
        print(f"[ONBOARDING] Saved {feedback_count} feedback entries")
        
        # Don't re-score all emails here - it's too slow and expensive
        # Re-scoring will happen lazily when user clicks "Score Importance" or when dashboard loads
        # This makes the redirect much faster
        
        print(f"[ONBOARDING] Training complete! Saved {feedback_count} feedback entries. Redirecting to dashboard.")
        flash(f'✅ Training complete! We\'ve learned from {feedback_count} examples. Your personalized brief is ready!', 'success')
        
        # Always go to dashboard - preferences can be set later
        return redirect(url_for('dashboard'))
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ONBOARDING ERROR] {str(e)}")
        print(f"[ONBOARDING ERROR] Traceback: {error_trace}")
        flash(f'Error completing training: {str(e)}', 'error')
        return redirect(url_for('onboarding'))


@app.route('/dashboard')
def dashboard():
    """Dashboard page - main page with all actions."""
    # Check if user has connected Gmail
    if not os.path.exists(TOKEN_FILE):
        flash('Please connect your Gmail account first', 'error')
        return redirect(url_for('onboarding'))
    
    # Check if user needs training
    from src.storage.database import Database
    db = Database()
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM feedback')
        feedback_count = cursor.fetchone()[0]
        conn.close()
        print(f"[DASHBOARD] Feedback count: {feedback_count}")
        
        # If no feedback yet, redirect to onboarding for training
        if feedback_count < 5:
            print(f"[DASHBOARD] User needs training ({feedback_count} feedback entries). Redirecting to onboarding.")
            return redirect(url_for('onboarding'))
    except Exception as e:
        print(f"[DASHBOARD] Error checking feedback: {e}")
        feedback_count = 0
        # If error checking, still allow access but might redirect to onboarding
    
    # Import here to avoid circular imports
    from src.email_connectors.gmail import GmailConnector
    from src.storage.database import Database
    from src.ai.scorer import ImportanceScorer
    from src.ai.summarizer import BriefSummarizer
    from config.settings import EMAIL_FETCH_HOURS
    
    # Get recent emails from database
    db = Database()
    emails = db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
    
    # Don't re-score all emails on every dashboard load - it's too slow!
    # Only re-score if explicitly requested via "Score Importance" button
    # This makes dashboard loads much faster
    
    # Sort by existing scores
    emails.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
    
    # Get feedback for emails to show which ones have been marked
    feedback_map = {}
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT email_id, is_important FROM feedback')
        for row in cursor.fetchall():
            feedback_map[row[0]] = row[1]
        conn.close()
    except:
        pass
    
    # Add feedback status to emails
    for email in emails:
        email['has_feedback'] = email['id'] in feedback_map
        email['feedback_value'] = feedback_map.get(email['id'], None)
    
    # Generate brief if we have emails - prioritize high-scoring emails
    brief_text = None
    important_emails = []
    brief_stats = {
        'total_emails': len(emails),
        'important_count': 0,
        'filtered_count': 0,
        'avg_score': 0,
        'top_score': 0,
        'low_score': 0,
            'threshold': 0.65,  # Default threshold (more aggressive)
            'critical_count': 0,
            'category_breakdown': {},
            'sender_categories': {}
        }
    
    # Categorize senders
    def categorize_sender(sender, subject):
        """Categorize sender based on email content and sender name."""
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        
        # Newsletters
        if any(word in sender_lower for word in ['newsletter', 'digest', 'news', 'update', 'substack', 'medium']):
            return 'Newsletters'
        # Promotions
        if any(word in sender_lower or word in subject_lower for word in ['promo', 'sale', 'deal', 'offer', 'discount', 'coupon', '$', 'fare', 'airline', 'hotel', 'booking']):
            return 'Promotions'
        # Healthcare/Medical
        if any(word in sender_lower for word in ['hospital', 'clinic', 'medical', 'health', 'doctor', 'pharmacy', 'appointment']):
            return 'Healthcare'
        # Financial
        if any(word in sender_lower for word in ['bank', 'credit', 'payment', 'invoice', 'billing', 'paypal', 'stripe', 'financial']):
            return 'Financial'
        # Social Media
        if any(word in sender_lower for word in ['linkedin', 'twitter', 'facebook', 'instagram', 'social']):
            return 'Social Media'
        # Work/Professional
        if any(word in sender_lower for word in ['job', 'career', 'recruiter', 'hiring', 'interview', 'application']):
            return 'Work/Jobs'
        # Security/Alerts
        if any(word in subject_lower for word in ['security', 'alert', 'login', 'password', 'verify', 'suspicious']):
            return 'Security Alerts'
        # Shopping/Retail
        if any(word in sender_lower for word in ['amazon', 'ebay', 'shop', 'store', 'retail', 'delivery', 'shipping']):
            return 'Shopping'
        # Technology
        if any(word in sender_lower for word in ['github', 'stackoverflow', 'tech', 'software', 'developer', 'code']):
            return 'Technology'
        # Education
        if any(word in sender_lower for word in ['university', 'school', 'course', 'education', 'learning', 'coursera', 'udemy']):
            return 'Education'
        # Travel
        if any(word in sender_lower for word in ['travel', 'trip', 'flight', 'airline', 'hotel', 'booking', 'expedia']):
            return 'Travel'
        # Notifications
        if any(word in sender_lower for word in ['noreply', 'no-reply', 'notification', 'alert', 'reminder']):
            return 'Notifications'
        
        return 'Other'
    
    if emails:
        # Calculate statistics
        scores = [e.get('importance_score', 0) for e in emails]
        brief_stats['avg_score'] = sum(scores) / len(scores) if scores else 0
        brief_stats['top_score'] = max(scores) if scores else 0
        brief_stats['low_score'] = min(scores) if scores else 0
        
        # Categorize all senders
        sender_categories = {}
        for email in emails:
            category = categorize_sender(email.get('sender', ''), email.get('subject', ''))
            if category not in sender_categories:
                sender_categories[category] = {'count': 0, 'senders': set(), 'in_brief': 0}
            sender_categories[category]['count'] += 1
            sender_categories[category]['senders'].add(email.get('sender', 'Unknown'))
        
        # Calculate adaptive threshold based on feedback distribution
        def calculate_adaptive_threshold(emails, feedback_map):
            """Calculate threshold based on feedback patterns."""
            # Get feedback scores
            feedback_scores = []
            for email in emails:
                if email['id'] in feedback_map:
                    feedback_scores.append(email.get('importance_score', 0))
            
            if len(feedback_scores) >= 10:
                # Use 75th percentile of feedback scores as threshold (more aggressive)
                sorted_scores = sorted(feedback_scores)
                percentile_75 = sorted_scores[int(len(sorted_scores) * 0.75)]
                # Ensure threshold is at least 0.65 for aggressive filtering
                threshold = max(0.65, percentile_75)
            else:
                # Not enough feedback - use percentile-based approach
                scores = [e.get('importance_score', 0) for e in emails]
                if scores:
                    sorted_scores = sorted(scores, reverse=True)
                    # Top 15% or minimum 0.65, whichever is higher (more aggressive)
                    top_15_percent = sorted_scores[max(1, len(sorted_scores) // 7)]
                    threshold = max(0.65, top_15_percent)
                else:
                    threshold = 0.65
            
            return threshold
        
        # Calculate adaptive threshold - make it more aggressive
        threshold = calculate_adaptive_threshold(emails, feedback_map)
        # Ensure threshold is at least 0.65 for better filtering
        threshold = max(0.65, threshold)
        brief_stats['threshold'] = threshold
        
        # Filter to show only emails above adaptive threshold
        important_emails = [e for e in emails if e.get('importance_score', 0) > threshold]
        brief_stats['important_count'] = len(important_emails)
        brief_stats['filtered_count'] = len(emails) - len(important_emails)
        
        # Count critical emails (>0.7)
        critical_emails = [e for e in emails if e.get('importance_score', 0) > 0.7]
        brief_stats['critical_count'] = len(critical_emails)
        
        # Count how many from each category are in brief
        category_breakdown = {}
        for email in important_emails:
            category = categorize_sender(email.get('sender', ''), email.get('subject', ''))
            if category not in category_breakdown:
                category_breakdown[category] = 0
            category_breakdown[category] += 1
            if category in sender_categories:
                sender_categories[category]['in_brief'] += 1
        
        brief_stats['category_breakdown'] = category_breakdown
        
        # Convert sets to lists for template; add first_email_id per category for scroll-to-summary
        for cat in sender_categories:
            sender_categories[cat]['senders'] = list(sender_categories[cat]['senders'])[:5]  # Top 5 senders
            sender_categories[cat]['sender_count'] = len(sender_categories[cat]['senders'])
            sender_categories[cat]['first_email_id'] = None
        for email in important_emails:
            cat = categorize_sender(email.get('sender', ''), email.get('subject', ''))
            if cat in sender_categories and sender_categories[cat]['first_email_id'] is None:
                sender_categories[cat]['first_email_id'] = email.get('id')
        
        brief_stats['sender_categories'] = sender_categories
        
        if important_emails:
            summarizer = BriefSummarizer()
            brief_text = summarizer.generate_brief(important_emails, top_n=10)
        else:
            # If no high-scoring emails, show top ones anyway
            important_emails = emails[:10]
            summarizer = BriefSummarizer()
            brief_text = summarizer.generate_brief(important_emails, top_n=10)
            brief_stats['important_count'] = len(important_emails)
            brief_stats['filtered_count'] = len(emails) - len(important_emails)
    else:
        important_emails = []
    
    return render_template_string(DASHBOARD_HTML, 
                                 emails=emails[:20],  # Show top 20
                                 brief_text=brief_text,
                                 total_emails=len(emails),
                                 has_emails=len(emails) > 0,
                                 brief_stats=brief_stats,
                                 all_emails=emails,  # Pass all emails for review
                                 important_emails=important_emails,
                                 categorize_sender=categorize_sender)  # Pass function to template


@app.route('/dashboard/fetch', methods=['POST'])
def dashboard_fetch():
    """Fetch emails from dashboard."""
    if not os.path.exists(TOKEN_FILE):
        flash('Please connect your Gmail account first', 'error')
        return redirect(url_for('onboarding'))
    
    try:
        from src.email_connectors.gmail import GmailConnector
        from src.storage.database import Database
        from config.settings import EMAIL_FETCH_HOURS
        
        db = Database()
        gmail = GmailConnector()
        
        if not gmail.authenticate():
            flash('Gmail authentication failed. Please reconnect your account.', 'error')
            return redirect(url_for('dashboard'))
        
        emails = gmail.fetch_recent_emails(hours=EMAIL_FETCH_HOURS)
        
        # Save emails
        for email in emails:
            db.save_email(email, account_type='gmail')
        
        flash(f'✅ Fetched {len(emails)} emails successfully!', 'success')
    except Exception as e:
        flash(f'Error fetching emails: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))


@app.route('/dashboard/score', methods=['POST'])
def dashboard_score():
    """Score emails from dashboard."""
    if not os.path.exists(TOKEN_FILE):
        flash('Please connect your Gmail account first', 'error')
        return redirect(url_for('onboarding'))
    
    try:
        from src.storage.database import Database
        from src.ai.scorer import ImportanceScorer
        from config.settings import EMAIL_FETCH_HOURS
        
        db = Database()
        scorer = ImportanceScorer(db)
        
        emails = db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
        
        # Show progress message
        flash(f'⏳ Scoring {len(emails)} emails... This may take a minute. Please wait...', 'info')
        
        scored_count = 0
        for email in emails:
            try:
                score = scorer.score_email(email)
                db.update_importance_score(email['id'], score)
                scored_count += 1
            except Exception as e:
                print(f"[SCORE ERROR] Error scoring email {email.get('id', 'unknown')}: {e}")
                continue  # Skip this email and continue
        
        flash(f'✅ Scored {scored_count} emails successfully!', 'success')
    except Exception as e:
        flash(f'Error scoring emails: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))


@app.route('/dashboard/generate-brief', methods=['POST'])
def dashboard_generate_brief():
    """Generate brief from dashboard."""
    if not os.path.exists(TOKEN_FILE):
        flash('Please connect your Gmail account first', 'error')
        return redirect(url_for('onboarding'))
    
    # Just redirect to dashboard - brief will be generated on page load
    return redirect(url_for('dashboard'))


@app.route('/dashboard/reset-training', methods=['POST'])
def dashboard_reset_training():
    """Reset training data to allow re-onboarding."""
    if not os.path.exists(TOKEN_FILE):
        flash('Please connect your Gmail account first', 'error')
        return redirect(url_for('onboarding'))
    
    try:
        from src.storage.database import Database
        import sqlite3
        
        db = Database()
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # Clear all feedback
        cursor.execute('DELETE FROM feedback')
        cursor.execute('DELETE FROM feedback_enhanced')
        cursor.execute('DELETE FROM sender_patterns')
        
        conn.commit()
        conn.close()
        
        flash('✅ Training data reset successfully! You can now go through onboarding again.', 'success')
    except Exception as e:
        flash(f'Error resetting training: {str(e)}', 'error')
    
    return redirect(url_for('onboarding'))


@app.route('/dashboard/feedback', methods=['POST'])
def dashboard_feedback():
    """Save user feedback on email importance."""
    if not os.path.exists(TOKEN_FILE):
        flash('Please connect your Gmail account first', 'error')
        return redirect(url_for('onboarding'))
    
    email_id = request.form.get('email_id')
    is_important = request.form.get('is_important', 'false').lower() == 'true'
    
    print(f"\n[FEEDBACK] Received feedback request")
    print(f"[FEEDBACK] Email ID: {email_id}")
    print(f"[FEEDBACK] Is Important: {is_important}")
    
    if not email_id:
        print(f"[FEEDBACK ERROR] No email ID provided")
        flash('Email ID is required', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from src.storage.database import Database
        from src.utils.categories import categorize_sender
        
        db = Database()
        db.save_feedback(email_id, is_important)
        
        # Update category pattern so similar emails (e.g. same category) are auto-ranked
        email = db.get_email_by_id(email_id)
        if email:
            category = categorize_sender(email.get('sender', ''), email.get('subject', ''))
            db.update_category_feedback(category, is_important)
        
        # Re-score this email with new feedback
        from src.ai.scorer import ImportanceScorer
        scorer = ImportanceScorer(db)
        emails_list = db.get_recent_emails(hours=168)  # Get from last week
        for e in emails_list:
            if e['id'] == email_id:
                score = scorer.score_email(e)
                db.update_importance_score(email_id, score)
                print(f"[FEEDBACK] Re-scored email. New score: {score:.2f}")
                break
        
        status = "important" if is_important else "not important"
        print(f"[FEEDBACK] Successfully saved feedback: {status}")
        flash(f'✅ Marked email as {status}. The system will learn from this!', 'success')
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[FEEDBACK ERROR] {str(e)}")
        print(f"[FEEDBACK ERROR] Traceback: {error_trace}")
        flash(f'Error saving feedback: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))


@app.route('/setup')
@app.route('/setup/gmail')
def setup(provider='gmail'):
    """Gmail setup page."""
    has_credentials = os.path.exists(CREDENTIALS_FILE)
    has_token = os.path.exists(TOKEN_FILE)
    
    provider_name = provider.upper() if provider == 'gmail' else provider.capitalize()
    
    return render_template_string(SETUP_HTML, 
                                 has_credentials=has_credentials,
                                 has_token=has_token,
                                 provider_name=provider_name,
                                 provider=provider)


@app.route('/setup/outlook')
def setup_outlook():
    """Outlook setup page (placeholder)."""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Outlook Setup - Coming Soon</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #f5a623 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                position: relative;
            }
            body::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: 
                    radial-gradient(circle at 20% 50%, rgba(245, 166, 35, 0.15) 0%, transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(30, 60, 114, 0.2) 0%, transparent 50%);
                pointer-events: none;
                z-index: 0;
            }
            .container {
                background: rgba(255, 255, 255, 0.98);
                border-radius: 24px;
                padding: 60px 40px;
                text-align: center;
                max-width: 500px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                position: relative;
                z-index: 1;
                backdrop-filter: blur(10px);
            }
            h1 { 
                color: #1e3c72; 
                margin-bottom: 20px; 
                font-size: 32px;
                font-weight: 700;
            }
            p {
                color: #64748b;
                font-size: 18px;
                margin-bottom: 30px;
            }
            .btn {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 14px 32px;
                border: none;
                border-radius: 12px;
                text-decoration: none;
                display: inline-block;
                margin-top: 20px;
                font-weight: 600;
                box-shadow: 0 4px 12px rgba(30, 60, 114, 0.3);
                transition: all 0.3s;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(30, 60, 114, 0.4);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📮 Outlook Setup</h1>
            <p>Outlook integration is coming soon!</p>
            <a href="/" class="btn">← Back to Home</a>
        </div>
    </body>
    </html>
    """)


@app.route('/setup/credentials', methods=['POST'])
def save_credentials():
    """Save OAuth credentials from form."""
    client_id = request.form.get('client_id', '').strip()
    client_secret = request.form.get('client_secret', '').strip()
    
    if not client_id or not client_secret:
        flash('Please provide both Client ID and Client Secret', 'error')
        return redirect(url_for('onboarding'))
    
    # Create credentials.json structure
    # Use "web" instead of "installed" for Web application type
    redirect_uri = REDIRECT_URI.strip()
    print(f"[SAVE CREDENTIALS] Saving redirect URI: {redirect_uri}")
    
    credentials_data = {
        "web": {
            "client_id": client_id,
            "project_id": "daily-email-brief",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": [redirect_uri]
        }
    }
    
    try:
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials_data, f, indent=2)
        import sys
        msg = f"\n[SAVE CREDENTIALS] Credentials saved with redirect URI: {redirect_uri}\n"
        print(msg, flush=True)
        sys.stderr.write(msg)
        app.logger.error(msg)
        flash('✅ Credentials saved successfully!', 'success')
    except Exception as e:
        flash(f'Error saving credentials: {str(e)}', 'error')
    
    # Redirect to onboarding (which will show setup if no credentials)
    return redirect(url_for('onboarding'))


@app.route('/setup/reset-credentials', methods=['POST'])
def reset_credentials():
    """Reset/clear saved credentials and unlink Gmail."""
    try:
        # Delete credentials file if it exists
        if os.path.exists(CREDENTIALS_FILE):
            os.remove(CREDENTIALS_FILE)
        # Also delete token file to force re-authentication
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        flash('✅ Gmail account unlinked successfully! You can now reconnect or set up a new account.', 'success')
    except Exception as e:
        flash(f'Error unlinking account: {str(e)}', 'error')
    
    # Redirect to home page (which will show setup options)
    return redirect(url_for('home'))


@app.route('/oauth/authorize')
def oauth_authorize():
    """Start OAuth flow."""
    global _oauth_in_progress
    
    # Prevent multiple simultaneous OAuth flows
    if _oauth_in_progress:
        flash('OAuth flow already in progress. Please wait...', 'error')
        return redirect(url_for('onboarding'))
    
    if not os.path.exists(CREDENTIALS_FILE):
        flash('Please set up credentials first', 'error')
        return redirect(url_for('onboarding'))
    
    try:
        _oauth_in_progress = True
        # Read credentials file and handle both "web" and "installed" types
        with open(CREDENTIALS_FILE, 'r') as f:
            creds_data = json.load(f)
        
        # Extract client info (works for both web and installed types)
        if 'web' in creds_data:
            client_config = creds_data['web']
        elif 'installed' in creds_data:
            client_config = creds_data['installed']
        else:
            raise ValueError("Invalid credentials format")
        
        # Ensure redirect URI matches exactly - use the one from saved config or default
        saved_redirect_uris = client_config.get('redirect_uris', [])
        if saved_redirect_uris:
            redirect_uri = saved_redirect_uris[0].strip()
        else:
            redirect_uri = REDIRECT_URI.strip()
        
        print(f"[OAUTH] Using redirect URI: {redirect_uri}")
        print(f"[OAUTH] Client ID: {client_config['client_id']}")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_config['client_id'],
                    "client_secret": client_config['client_secret'],
                    "auth_uri": client_config.get('auth_uri', 'https://accounts.google.com/o/oauth2/auth'),
                    "token_uri": client_config.get('token_uri', 'https://oauth2.googleapis.com/token'),
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store flow in app config (will be reset in callback)
        app.config['OAUTH_FLOW'] = flow
        
        # Extract and log the redirect_uri from the authorization URL
        import urllib.parse
        import sys
        parsed_url = urllib.parse.urlparse(authorization_url)
        params = urllib.parse.parse_qs(parsed_url.query)
        redirect_uri_in_url = params.get('redirect_uri', [None])[0]
        
        debug_msg = f"""
{'='*60}
[OAUTH DEBUG] Redirect URI being sent to Google:
  {redirect_uri_in_url}
[OAUTH DEBUG] Expected in Google Cloud Console:
  http://127.0.0.1:5000/oauth/callback
{'='*60}
"""
        print(debug_msg, flush=True)
        sys.stderr.write(debug_msg)
        app.logger.error(debug_msg)  # Use error level so it shows up
        
        # Store state in session (simplified - in production use proper session)
        app.config['OAUTH_STATE'] = state
        app.config['OAUTH_FLOW'] = flow
        
        return redirect(authorization_url)
    except Exception as e:
        _oauth_in_progress = False
        import traceback
        print(f"[OAUTH ERROR] {e}\n{traceback.format_exc()}", flush=True)
        flash(f'OAuth error: {str(e)}', 'error')
        return redirect(url_for('onboarding'))


@app.route('/oauth/callback', methods=['GET', 'POST'])
def oauth_callback():
    """Handle OAuth callback."""
    global _oauth_in_progress
    
    # Log that we received the callback
    print(f"\n[OAUTH CALLBACK] Received callback with params: {dict(request.args)}")
    
    # Check for error in callback
    error = request.args.get('error')
    if error:
        _oauth_in_progress = False  # Reset flag on error
        error_description = request.args.get('error_description', 'Unknown error')
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>OAuth Error</title>
            <meta http-equiv="refresh" content="5;url=/setup/gmail">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif; 
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #f5a623 100%);
                    display: flex; align-items: center; justify-content: center; min-height: 100vh; 
                    padding: 20px;
                }
                .container {
                    background: rgba(255, 255, 255, 0.98);
                    border-radius: 24px;
                    padding: 50px;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                    max-width: 600px;
                }
                h1 { color: #dc2626; margin-bottom: 20px; font-size: 32px; }
                p { color: #64748b; font-size: 16px; margin-bottom: 15px; line-height: 1.6; }
                .error-details {
                    background: #fee2e2;
                    border: 2px solid #ef4444;
                    border-radius: 12px;
                    padding: 20px;
                    margin: 20px 0;
                    color: #991b1b;
                    font-size: 14px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>❌ OAuth Error</h1>
                <p><strong>Error:</strong> {{ error }}</p>
                <div class="error-details">{{ error_description }}</div>
                <p style="font-size: 14px; color: #94a3b8;">Redirecting to setup page in 5 seconds...</p>
            </div>
        </body>
        </html>
        """, error=error, error_description=error_description), 400
    
    if not os.path.exists(CREDENTIALS_FILE):
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - Credentials Not Found</title>
            <meta http-equiv="refresh" content="3;url=/setup/gmail">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                       background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #f5a623 100%);
                       display: flex; align-items: center; justify-content: center; min-height: 100vh; 
                       color: white; text-align: center; }
            </style>
        </head>
        <body>
            <div>
                <h2>❌ Credentials not found</h2>
                <p>Redirecting to setup page...</p>
            </div>
        </body>
        </html>
        """), 400
    
    try:
        # Read credentials file and handle both "web" and "installed" types
        with open(CREDENTIALS_FILE, 'r') as f:
            creds_data = json.load(f)
        
        # Extract client info (works for both web and installed types)
        if 'web' in creds_data:
            client_config = creds_data['web']
        elif 'installed' in creds_data:
            client_config = creds_data['installed']
        else:
            raise ValueError("Invalid credentials format. Expected 'web' or 'installed' key.")
        
        # Build client config for Flow
        client_config_dict = {
            "web": {
                "client_id": client_config['client_id'],
                "client_secret": client_config['client_secret'],
                "auth_uri": client_config.get('auth_uri', 'https://accounts.google.com/o/oauth2/auth'),
                "token_uri": client_config.get('token_uri', 'https://oauth2.googleapis.com/token'),
                "redirect_uris": [REDIRECT_URI]
            }
        }
        
        # Ensure redirect URI matches exactly
        redirect_uri = REDIRECT_URI.strip()
        print(f"[OAUTH CALLBACK] Using redirect URI: {redirect_uri}")
        
        flow = Flow.from_client_config(
            client_config_dict,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        # Get authorization code from callback
        authorization_response = request.url
        print(f"[OAUTH CALLBACK] Processing authorization code...")
        
        flow.fetch_token(authorization_response=authorization_response)
        print(f"[OAUTH CALLBACK] Token fetched successfully!")
        
        # Save credentials
        creds = flow.credentials
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print(f"[OAUTH CALLBACK] Token saved to {TOKEN_FILE}")
        
        # For now, always redirect to onboarding (we can make it conditional later)
        # Check if this is first time connection (no feedback yet)
        from src.storage.database import Database
        db = Database()
        try:
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM feedback')
            feedback_count = cursor.fetchone()[0]
            conn.close()
            print(f"[OAUTH CALLBACK] Feedback count: {feedback_count}")
        except Exception as e:
            print(f"[OAUTH CALLBACK] Error checking feedback: {e}")
            feedback_count = 0
        
        # Always redirect to onboarding for now (can make conditional later)
        redirect_url = '/onboarding'
        print(f"[OAUTH CALLBACK] Redirecting to: {redirect_url}")
        
        # Reset OAuth flag on success
        _oauth_in_progress = False
        
        # Show success page with auto-redirect
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Success - Gmail Connected</title>
            <meta http-equiv="refresh" content="2;url=""" + redirect_url + """">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif; 
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #f5a623 100%);
                    display: flex; align-items: center; justify-content: center; min-height: 100vh; 
                    padding: 20px;
                }
                .container {
                    background: rgba(255, 255, 255, 0.98);
                    border-radius: 24px;
                    padding: 50px;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                    max-width: 500px;
                }
                h1 { color: #1e3c72; margin-bottom: 20px; font-size: 32px; }
                p { color: #64748b; font-size: 18px; margin-bottom: 30px; }
                .spinner {
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #f5a623;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 20px auto;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ Success!</h1>
                <p>Your Gmail account has been connected successfully!</p>
                <div class="spinner"></div>
                <p style="font-size: 14px; color: #94a3b8;">Redirecting to setup page...</p>
            </div>
        </body>
        </html>
        """)
    except Exception as e:
        error_msg = str(e)
        import traceback
        error_trace = traceback.format_exc()
        
        # Provide more helpful error messages
        if 'invalid_grant' in error_msg.lower():
            error_display = 'The authorization code may have expired. Please try connecting again.'
        elif 'redirect_uri_mismatch' in error_msg.lower():
            error_display = 'Redirect URI mismatch. Please check your OAuth client settings and add: http://127.0.0.1:5000/oauth/callback'
        elif 'invalid_client' in error_msg.lower():
            error_display = 'Invalid client credentials. Please reset and enter your credentials again.'
        else:
            error_display = error_msg
        
        # Log error for debugging
        print(f"\n[OAUTH CALLBACK ERROR] {error_msg}")
        print(f"[OAUTH CALLBACK ERROR] Traceback: {error_trace}")
        print(f"[OAUTH CALLBACK ERROR] Request URL: {request.url}")
        print(f"[OAUTH CALLBACK ERROR] Request args: {dict(request.args)}")
        
        # Reset OAuth flag on error
        _oauth_in_progress = False
        
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - OAuth Failed</title>
            <meta http-equiv="refresh" content="5;url=/setup/gmail">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif; 
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #f5a623 100%);
                    display: flex; align-items: center; justify-content: center; min-height: 100vh; 
                    padding: 20px;
                }
                .container {
                    background: rgba(255, 255, 255, 0.98);
                    border-radius: 24px;
                    padding: 50px;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                    max-width: 600px;
                }
                h1 { color: #dc2626; margin-bottom: 20px; font-size: 32px; }
                p { color: #64748b; font-size: 16px; margin-bottom: 15px; line-height: 1.6; }
                .error-details {
                    background: #fee2e2;
                    border: 2px solid #ef4444;
                    border-radius: 12px;
                    padding: 20px;
                    margin: 20px 0;
                    color: #991b1b;
                    font-size: 14px;
                }
                .btn {
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    color: white;
                    padding: 14px 32px;
                    border: none;
                    border-radius: 12px;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 20px;
                    font-weight: 600;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>❌ Connection Failed</h1>
                <p>{{ error }}</p>
                <div class="error-details">
                    <strong>Error Details:</strong><br>
                    {{ error_details }}
                </div>
                <p style="font-size: 14px; color: #94a3b8;">Redirecting to setup page in 5 seconds...</p>
                <a href="/setup/gmail" class="btn">Go to Setup Page</a>
            </div>
        </body>
        </html>
        """, error=error_display, error_details=error_msg), 400


@app.route('/api/email/<email_id>')
def api_email(email_id):
    """Return a single email by ID (for lazy-loading full body)."""
    if not os.path.exists(TOKEN_FILE):
        return jsonify({'error': 'Not authenticated'}), 401
    try:
        from src.storage.database import Database
        db = Database()
        email = db.get_email_by_id(email_id)
        if not email:
            return jsonify({'error': 'Email not found'}), 404
        return jsonify({
            'id': email['id'],
            'subject': email['subject'],
            'sender': email['sender'],
            'date': email['date'],
            'snippet': email.get('snippet', ''),
            'body': email.get('body', '') or email.get('snippet', '')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def api_status():
    """API endpoint to check setup status."""
    return jsonify({
        'has_credentials': os.path.exists(CREDENTIALS_FILE),
        'has_token': os.path.exists(TOKEN_FILE)
    })


_browser_opened = False

def open_browser():
    """Open browser to home page (only once)."""
    global _browser_opened
    if not _browser_opened:
        _browser_opened = True
        webbrowser.open('http://127.0.0.1:5000/')


if __name__ == '__main__':
    # Open browser automatically after 1 second
    Timer(1, open_browser).start()
    print("\n🌐 Setup UI starting...")
    print("📱 Opening browser at http://127.0.0.1:5000/")
    print("⚠️  IMPORTANT: Keep this terminal window open while using the setup UI!")
    print("⚠️  If you close it, the server will stop and OAuth callbacks won't work.")
    print("Press Ctrl+C to stop\n")
    try:
        app.run(debug=False, port=5000, host='127.0.0.1', use_reloader=False)
    except OSError as e:
        if "Address already in use" in str(e):
            print("\n❌ Error: Port 5000 is already in use!")
            print("   Another application is using port 5000.")
            print("   Please stop that application or use a different port.\n")
        else:
            print(f"\n❌ Error starting server: {e}\n")
