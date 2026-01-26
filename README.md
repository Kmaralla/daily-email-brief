# 📬 Daily Email Brief

> **Stop drowning in your inbox. Get AI-powered email summaries that help you focus on what matters.**

Daily Email Brief is an intelligent email assistant that learns your preferences and delivers personalized daily summaries. **No more opening Gmail/Outlook to check every email** - get the gist instantly and only log in when you need to respond.

## 🎯 The Problem & Solution

**The Problem:**
- 📧 Opening Gmail/Outlook multiple times daily
- 🔍 Scanning through dozens of emails to find what's important
- ⏰ Wasting 30-60 minutes/day on newsletters, promotions, and low-priority messages
- 😰 Missing critical emails buried in the noise

**The Solution:**
- ✅ **AI-powered importance scoring** - Automatically identifies what matters to YOU
- ✅ **Personalized daily summaries** - Get the gist without opening your inbox
- ✅ **Learns from your feedback** - Gets smarter over time
- ✅ **Beautiful web dashboard** - View everything in one place
- ✅ **Only open email when needed** - Respond only to what requires action

### 💡 Time Savings

```
Traditional Approach          Daily Email Brief
───────────────────          ──────────────────
📧 Open Gmail                📊 Open Dashboard
👀 Scan 50 emails            🤖 AI shows top 10
⏰ 30-60 min/day             ⏰ 2-5 min/day
😰 High stress               😊 Low stress
🔄 Repeat 3-5x/day           ✅ Done once
```

**Result: 2-4 hours saved per week!** 🎉

## ✨ Key Features

- 🧠 **AI-Powered Intelligence** - Smart importance scoring using embeddings and machine learning
- 📊 **Personalized Daily Briefs** - Top priority emails with context-rich AI summaries
- 🎯 **Smart Onboarding** - Guided web-based setup, no CLI configuration needed
- 🌐 **Beautiful Web Dashboard** - One-click actions: Fetch, Score, Generate Brief
- 🔄 **Learns Your Preferences** - Gets smarter from your feedback over time

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- Gmail account

### Installation

1. **Clone and setup**
   ```bash
   git clone https://github.com/Kmaralla/daily-email-brief.git
   cd daily-email-brief
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure API key**
   ```bash
   echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
   ```

3. **Run the application**
   ```bash
   python main.py
   ```
   The web UI will open automatically in your browser! 🎉

### First-Time Setup

The web UI guides you through everything:
1. **Connect Gmail** - OAuth setup with step-by-step instructions
2. **Train the AI** - Review 10 sample emails to teach preferences
3. **Configure Preferences** (optional) - Set important senders, categories
4. **Start Using** - Fetch, score, and generate your first brief!

**That's it!** No complex configuration needed.

## 📖 Usage

### Daily Workflow

1. **Open Dashboard** - `http://127.0.0.1:5000/dashboard`
2. **Click "Fetch Emails"** - Retrieves emails from last 48 hours
3. **Click "Score Importance"** - AI scores each email
4. **Click "Generate Brief"** - Get your personalized summary
5. **Review & Act** - See what needs attention, only open Gmail to respond

### Dashboard Features

- **📥 Fetch Emails** - Get latest emails from your inbox
- **⭐ Score Importance** - AI-powered importance scoring
- **📊 Generate Brief** - Create personalized daily summary
- **💬 Provide Feedback** - Mark emails as important/not important
- **📧 View All Emails** - Browse with importance scores
- **📈 Statistics** - See email patterns and insights


### 📊 Main Dashboard

![Dashboard](docs/screenshots/dashboard.png)

*Your command center - see everything at a glance without opening Gmail*

---

### 🎯 Onboarding Flow

![Onboarding](docs/screenshots/onboarding.png)

*Guided setup with OAuth configuration and email training*

---

### 💬 Feedback Interface

![Feedback](docs/screenshots/feedback.png)

*Mark emails as important/not important to help the AI learn your preferences*

---

### 📬 Daily Brief

![Brief](docs/screenshots/brief.png)

*AI-generated summary with top important emails and actionable insights*

## 📐 Architecture

```
┌──────────────┐      ┌──────────────┐      ┌────────────┐
│   Gmail API  │─────▶│  Email Fetch │─────▶│  Database  │
│  (OAuth 2.0) │      │   Connector  │      │  (SQLite)  │
└──────────────┘      └──────────────┘      └────────────┘
         │                     │
         ▼                     ▼
┌──────────────┐      ┌──────────────┐
│ AI Scorer    │      │ AI Summarizer│
│ (Embeddings) │      │ GPT-4 (or custom))│
└──────────────┘      └──────────────┘
         │                     │
         └───────────┬─────────┘
                     ▼
              ┌──────────────┐
              │   Dashboard  │
              │  (Web UI)    │
              └──────────────┘
```

## 🔒 Privacy & Security

- **100% Local** - All data stays on your computer
- **Read-Only Access** - Only requests read permission for emails
- **No Cloud Storage** - Emails stored locally in SQLite database
- **Open Source** - Full transparency, you control your data

## 🛠️ Technical Stack

- **Python 3.8+** - Core language
- **Flask** - Web framework
- **OpenAI API** - AI-powered scoring and summarization
- **Gmail API** - Email fetching
- **SQLite** - Local data storage

See `requirements.txt` for full dependency list.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is open source and available under the MIT License.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Kmaralla/daily-email-brief/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Kmaralla/daily-email-brief/discussions)

---

**Made with ❤️ to help you focus on what matters**
**If you find it useful and productive, ⭐ this repository**
