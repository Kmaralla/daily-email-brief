import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import click
from datetime import datetime
from src.email_connectors.gmail import GmailConnector
from src.storage.database import Database
from src.ai.scorer import ImportanceScorer
from src.ai.summarizer import BriefSummarizer
from src.ui.onboarding import OnboardingWizard
from src.ui.feedback import InteractiveFeedback
from src.email_connectors.email_delivery import EmailDelivery
from config.settings import EMAIL_FETCH_HOURS


@click.group()
def cli():
    """Daily Email Brief - AI-powered email summary tool."""
    pass


@cli.command()
def launcher():
    """Launch interactive UI launcher (recommended for new users)."""
    from src.ui.main_launcher import MainLauncher
    launcher = MainLauncher()
    launcher.run()


@cli.command()
def setup():
    """Launch web UI for easy email account setup."""
    click.echo("🌐 Starting setup UI...")
    click.echo("📱 Opening browser at http://127.0.0.1:5000/")
    click.echo("⚠️  IMPORTANT: Keep this terminal window open while using the setup UI!")
    click.echo("⚠️  If you close it, the server will stop and OAuth callbacks won't work.")
    click.echo("Press Ctrl+C to stop the server\n")
    
    from src.ui.web_setup import app, open_browser
    from threading import Timer
    
    # Open browser after 1 second
    Timer(1, open_browser).start()
    
    try:
        app.run(debug=False, port=5000, host='127.0.0.1', use_reloader=False)
    except OSError as e:
        if "Address already in use" in str(e):
            click.echo("\n❌ Error: Port 5000 is already in use!")
            click.echo("   Another application is using port 5000.")
            click.echo("   Please stop that application or use a different port.\n")
        else:
            click.echo(f"\n❌ Error starting server: {e}\n")


@cli.command()
@click.option('--hours', default=EMAIL_FETCH_HOURS, help='Hours to look back for emails')
def fetch(hours):
    """Fetch emails from connected accounts."""
    click.echo(f"Fetching emails from last {hours} hours...")
    
    db = Database()
    gmail = GmailConnector()
    
    if not gmail.authenticate():
        click.echo("❌ Gmail authentication failed.")
        click.echo("💡 Run 'python main.py setup' to configure your account through the web UI")
        return
    
    emails = gmail.fetch_recent_emails(hours=hours)
    click.echo(f"Found {len(emails)} emails")
    
    # Save emails
    for email in emails:
        db.save_email(email, account_type='gmail')
    
    click.echo(f"✅ Saved {len(emails)} emails to database")


@cli.command()
def score():
    """Score importance of fetched emails."""
    click.echo("Scoring email importance...")
    
    db = Database()
    scorer = ImportanceScorer(db)
    
    emails = db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
    click.echo(f"Scoring {len(emails)} emails...")
    
    for email in emails:
        score = scorer.score_email(email)
        db.update_importance_score(email['id'], score)
        click.echo(f"  {email['subject'][:50]:50} | Score: {score:.2f}")
    
    click.echo("✅ Scoring complete")


@cli.command()
@click.option('--top', default=None, help='Number of top emails to include')
@click.option('--send-email', is_flag=True, help='Send brief via email')
@click.option('--web', is_flag=True, help='Open brief in web dashboard')
def brief(top, send_email, web):
    """Generate daily email brief."""
    click.echo("Generating daily brief...")
    
    db = Database()
    summarizer = BriefSummarizer()
    
    # Get user preference for top N
    if top is None:
        top_pref = db.get_user_preference('brief_top_n', '10')
        top = int(top_pref) if top_pref else 10
    
    # Get emails sorted by importance
    emails = db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
    emails.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
    
    if not emails:
        click.echo("No emails found. Run 'fetch' first.")
        return
    
    brief_text = summarizer.generate_brief(emails, top_n=top)
    
    click.echo("\n" + brief_text)
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"brief_{timestamp}.txt"
    with open(filename, 'w') as f:
        f.write(brief_text)
    
    click.echo(f"\n✅ Brief saved to {filename}")
    
    # Email delivery
    if send_email:
        delivery_email = db.get_user_preference('delivery_email')
        if delivery_email:
            delivery = EmailDelivery()
            if delivery.send_brief(brief_text, delivery_email):
                db.save_brief_delivery(brief_text, 'email', 'sent')
                click.echo(f"✅ Brief sent to {delivery_email}")
            else:
                click.echo("❌ Failed to send email. Check email delivery configuration.")
        else:
            click.echo("❌ No delivery email configured. Run 'python main.py preferences'")
    
    # Web dashboard
    if web:
        click.echo("🌐 Starting web dashboard...")
        click.echo("📱 Opening browser at http://127.0.0.1:5001/dashboard")
        click.echo("⚠️  Keep this terminal window open!\n")
        from src.ui.web_dashboard import app
        import webbrowser
        from threading import Timer
        Timer(1, lambda: webbrowser.open('http://127.0.0.1:5001/dashboard')).start()
        try:
            app.run(debug=False, port=5001, host='127.0.0.1', use_reloader=False)
        except OSError as e:
            if "Address already in use" in str(e):
                click.echo("\n❌ Error: Port 5001 is already in use!")
                click.echo("   Please stop the other application or use: python main.py dashboard\n")
            else:
                click.echo(f"\n❌ Error starting server: {e}\n")


@cli.command()
@click.argument('email_id', required=False)
@click.option('--important', type=click.BOOL, help='Mark as important (true/false)')
@click.option('--interactive', '-i', is_flag=True, help='Interactive feedback mode')
@click.option('--batch', '-b', is_flag=True, help='Batch feedback mode for multiple emails')
def feedback(email_id, important, interactive, batch):
    """Provide feedback on email importance.
    
    Use --interactive or -i for guided feedback with categories and priorities.
    Use --batch or -b to review multiple emails at once.
    """
    feedback_system = InteractiveFeedback()
    
    if batch:
        feedback_system.interactive_feedback()
    elif interactive or email_id:
        if email_id:
            if important is not None:
                feedback_system.quick_feedback(email_id, important)
            else:
                feedback_system.interactive_feedback(email_id)
        else:
            click.echo("❌ Please provide an email_id or use --batch mode")
    else:
        click.echo("Usage: feedback [EMAIL_ID] [--important true/false] [--interactive] [--batch]")
        click.echo("Examples:")
        click.echo("  python main.py feedback --interactive <email_id>")
        click.echo("  python main.py feedback --batch")
        click.echo("  python main.py feedback <email_id> --important true")


@cli.command()
@click.option('--min-score', default=0.0, help='Minimum importance score to show')
@click.option('--limit', default=50, help='Maximum number of emails to show')
def list_emails(min_score, limit):
    """List recent emails with their importance scores."""
    db = Database()
    emails = db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
    emails.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
    
    if not emails:
        click.echo("No emails found. Run 'fetch' first.")
        return
    
    # Filter by min score
    filtered_emails = [e for e in emails if e.get('importance_score', 0) >= min_score]
    filtered_emails = filtered_emails[:limit]
    
    click.echo(f"\n{'Score':<6} {'Subject':<50} {'Sender':<30} {'ID':<20}")
    click.echo("-" * 110)
    
    for email in filtered_emails:
        score = email.get('importance_score', 0)
        subject = email['subject'][:48]
        sender = email['sender'][:28]
        email_id = email['id'][:18]
        click.echo(f"{score:.2f}  {subject:<50} {sender:<30} {email_id:<20}")


@cli.command()
def onboarding():
    """Run interactive onboarding wizard to set up preferences."""
    wizard = OnboardingWizard()
    wizard.run()


@cli.command()
def preferences():
    """View and edit user preferences."""
    db = Database()
    
    click.echo("\n" + "="*60)
    click.echo("⚙️  User Preferences")
    click.echo("="*60 + "\n")
    
    # Show current preferences
    delivery_method = db.get_user_preference('delivery_method', 'cli')
    delivery_email = db.get_user_preference('delivery_email', 'Not set')
    brief_top_n = db.get_user_preference('brief_top_n', '10')
    min_score = db.get_user_preference('min_importance_score', '0.0')
    
    click.echo("Current Settings:")
    click.echo(f"  Delivery Method: {delivery_method}")
    click.echo(f"  Delivery Email: {delivery_email}")
    click.echo(f"  Brief Top N: {brief_top_n}")
    click.echo(f"  Min Importance Score: {min_score}\n")
    
    # Show important senders
    important_senders = db.get_important_senders()
    if important_senders:
        click.echo("Important Senders:")
        for sender_info in important_senders:
            click.echo(f"  • {sender_info['sender']} ({sender_info['priority']} priority, {sender_info['category']})")
    else:
        click.echo("No important senders configured.\n")
    
    # Edit option
    if click.confirm("\nWould you like to edit preferences?", default=False):
        wizard = OnboardingWizard()
        wizard.run()


@cli.command()
@click.option('--sender', required=True, help='Sender email or domain')
@click.option('--priority', type=click.Choice(['high', 'medium', 'low']), default='high')
@click.option('--category', type=click.Choice(['work', 'personal', 'urgent', 'other']), default='work')
def add_sender(sender, priority, category):
    """Add an important sender."""
    db = Database()
    db.save_important_sender(sender, priority, category)
    click.echo(f"✅ Added {sender} as {priority} priority in {category} category")


@cli.command()
def dashboard():
    """Launch web dashboard to view briefs and emails."""
    click.echo("🌐 Starting web dashboard...")
    click.echo("📱 Opening browser at http://127.0.0.1:5001/dashboard")
    click.echo("⚠️  Keep this terminal window open!\n")
    
    from src.ui.web_dashboard import app
    import webbrowser
    from threading import Timer
    
    Timer(1, lambda: webbrowser.open('http://127.0.0.1:5001/dashboard')).start()
    
    try:
        app.run(debug=False, port=5001, host='127.0.0.1', use_reloader=False)
    except OSError as e:
        if "Address already in use" in str(e):
            click.echo("\n❌ Error: Port 5001 is already in use!")
            click.echo("   Please stop the other application or use a different port.\n")
        else:
            click.echo(f"\n❌ Error starting server: {e}\n")


if __name__ == '__main__':
    cli()
