import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import click
from src.storage.database import Database
from src.email_connectors.gmail import GmailConnector
from src.ai.scorer import ImportanceScorer
from src.ai.summarizer import BriefSummarizer
from src.ui.onboarding import OnboardingWizard
from src.ui.feedback import InteractiveFeedback
from src.email_connectors.email_delivery import EmailDelivery
from config.settings import EMAIL_FETCH_HOURS
from datetime import datetime


class MainLauncher:
    """Unified UI launcher for all operations."""
    
    def __init__(self):
        self.db = Database()
    
    def run(self):
        """Main launcher menu."""
        # Check if first time setup needed
        if not self._is_setup_complete():
            self._first_time_setup()
            return
        
        # Main menu
        while True:
            self._show_main_menu()
            choice = click.prompt("\nSelect an option", type=int, default=1)
            
            if choice == 1:
                self._fetch_and_score()
            elif choice == 2:
                self._generate_brief()
            elif choice == 3:
                self._view_dashboard()
            elif choice == 4:
                self._provide_feedback()
            elif choice == 5:
                self._manage_preferences()
            elif choice == 6:
                self._view_emails()
            elif choice == 7:
                click.echo("\n👋 Goodbye!\n")
                break
            else:
                click.echo("❌ Invalid option. Please try again.")
    
    def _is_setup_complete(self):
        """Check if initial setup is complete."""
        # Check if Gmail token exists
        from config.settings import GMAIL_TOKEN_FILE
        token_exists = os.path.exists(GMAIL_TOKEN_FILE)
        
        # If token exists, just open web UI - let web handle everything
        if token_exists:
            return True  # Web UI will handle preferences
        
        return False
    
    def _first_time_setup(self):
        """First time setup flow - opens web UI for everything."""
        click.echo("\n" + "="*60)
        click.echo("🎉 Welcome to Daily Email Brief!")
        click.echo("="*60)
        click.echo("\nOpening web setup portal...")
        click.echo("⚠️  All configuration happens in your browser!")
        click.echo("⚠️  Keep this terminal window open!\n")
        
        from src.ui.web_setup import app, open_browser
        from threading import Timer
        
        Timer(1, open_browser).start()
        try:
            app.run(debug=False, port=5000, host='127.0.0.1', use_reloader=False)
        except KeyboardInterrupt:
            click.echo("\n✅ Setup complete!\n")
        except Exception as e:
            click.echo(f"\n❌ Error: {e}\n")
    
    def _show_main_menu(self):
        """Display main menu."""
        # Try to clear screen, but don't fail if it doesn't work
        try:
            click.clear()
        except:
            pass
        click.echo("\n" + "="*60)
        click.echo("📬 Daily Email Brief - Main Menu")
        click.echo("="*60)
        click.echo("\n1. 🔄 Fetch & Score Emails")
        click.echo("2. 📋 Generate Daily Brief")
        click.echo("3. 🌐 Open Web Dashboard")
        click.echo("4. 💬 Provide Feedback")
        click.echo("5. ⚙️  Manage Preferences")
        click.echo("6. 📧 View Emails List")
        click.echo("7. 🚪 Exit")
    
    def _fetch_and_score(self):
        """Fetch and score emails in one go."""
        click.echo("\n" + "="*60)
        click.echo("🔄 Fetching and Scoring Emails")
        click.echo("="*60 + "\n")
        
        # Fetch
        click.echo("📥 Fetching emails...")
        gmail = GmailConnector()
        
        if not gmail.authenticate():
            click.echo("❌ Gmail authentication failed.")
            click.echo("💡 Run setup again: python main.py launcher")
            click.pause("\nPress Enter to continue...")
            return
        
        hours = int(self.db.get_user_preference('email_fetch_hours', str(EMAIL_FETCH_HOURS)) or EMAIL_FETCH_HOURS)
        emails = gmail.fetch_recent_emails(hours=hours)
        click.echo(f"✅ Found {len(emails)} emails")
        
        # Save emails
        for email in emails:
            self.db.save_email(email, account_type='gmail')
        click.echo(f"✅ Saved {len(emails)} emails to database")
        
        # Score
        if emails:
            click.echo("\n🎯 Scoring email importance...")
            scorer = ImportanceScorer(self.db)
            
            for email in emails:
                score = scorer.score_email(email)
                self.db.update_importance_score(email['id'], score)
            
            click.echo("✅ Scoring complete")
        
        click.pause("\nPress Enter to continue...")
    
    def _generate_brief(self):
        """Generate and display brief."""
        click.echo("\n" + "="*60)
        click.echo("📋 Generating Daily Brief")
        click.echo("="*60 + "\n")
        
        # Check if emails exist
        emails = self.db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
        if not emails:
            click.echo("❌ No emails found. Please fetch emails first.")
            if click.confirm("Would you like to fetch emails now?", default=True):
                self._fetch_and_score()
                emails = self.db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
            else:
                click.pause("\nPress Enter to continue...")
                return
        
        # Generate brief
        click.echo("🤖 Generating brief with AI...")
        summarizer = BriefSummarizer()
        
        top_n = int(self.db.get_user_preference('brief_top_n', '10') or '10')
        emails.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
        
        brief_text = summarizer.generate_brief(emails, top_n=top_n)
        
        # Display brief
        click.echo("\n" + brief_text)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"brief_{timestamp}.txt"
        with open(filename, 'w') as f:
            f.write(brief_text)
        click.echo(f"\n✅ Brief saved to {filename}")
        
        # Delivery options
        click.echo("\n📬 Delivery Options:")
        click.echo("1. View in Web Dashboard")
        click.echo("2. Send via Email")
        click.echo("3. Skip")
        
        delivery_choice = click.prompt("Select option", type=int, default=3)
        
        if delivery_choice == 1:
            self._view_dashboard()
        elif delivery_choice == 2:
            delivery_email = self.db.get_user_preference('delivery_email')
            if delivery_email:
                delivery = EmailDelivery()
                if delivery.send_brief(brief_text, delivery_email):
                    self.db.save_brief_delivery(brief_text, 'email', 'sent')
                    click.echo(f"✅ Brief sent to {delivery_email}")
                else:
                    click.echo("❌ Failed to send email. Check email delivery configuration.")
            else:
                click.echo("❌ No delivery email configured. Set it up in preferences.")
        
        click.pause("\nPress Enter to continue...")
    
    def _view_dashboard(self):
        """Launch web dashboard."""
        click.echo("\n🌐 Starting web dashboard...")
        click.echo("📱 Opening browser at http://127.0.0.1:5001/dashboard")
        click.echo("⚠️  Keep this terminal window open!")
        click.echo("Press Ctrl+C to stop the server\n")
        
        from src.ui.web_dashboard import app
        import webbrowser
        from threading import Timer
        
        Timer(1, lambda: webbrowser.open('http://127.0.0.1:5001/dashboard')).start()
        
        try:
            app.run(debug=False, port=5001, host='127.0.0.1', use_reloader=False)
        except KeyboardInterrupt:
            click.echo("\n✅ Dashboard closed.\n")
        except OSError as e:
            if "Address already in use" in str(e):
                click.echo("\n❌ Port 5001 is already in use!")
                click.echo("   Dashboard might already be running.\n")
            else:
                click.echo(f"\n❌ Error: {e}\n")
            click.pause("Press Enter to continue...")
    
    def _provide_feedback(self):
        """Provide feedback on emails."""
        click.echo("\n" + "="*60)
        click.echo("💬 Provide Feedback")
        click.echo("="*60 + "\n")
        
        click.echo("1. Interactive feedback (single email)")
        click.echo("2. Batch feedback (multiple emails)")
        
        choice = click.prompt("Select option", type=int, default=1)
        
        feedback_system = InteractiveFeedback()
        
        if choice == 1:
            emails = self.db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
            emails.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
            
            if not emails:
                click.echo("❌ No emails found.")
                click.pause("\nPress Enter to continue...")
                return
            
            click.echo("\nRecent emails:")
            for i, email in enumerate(emails[:10], 1):
                click.echo(f"{i}. {email['subject'][:60]} (Score: {email.get('importance_score', 0):.2f})")
            
            email_idx = click.prompt("\nSelect email number", type=int) - 1
            if 0 <= email_idx < len(emails):
                feedback_system.interactive_feedback(emails[email_idx]['id'])
            else:
                click.echo("❌ Invalid selection.")
        else:
            feedback_system.interactive_feedback()
        
        click.pause("\nPress Enter to continue...")
    
    def _manage_preferences(self):
        """Manage user preferences."""
        click.echo("\n" + "="*60)
        click.echo("⚙️  Manage Preferences")
        click.echo("="*60 + "\n")
        
        wizard = OnboardingWizard()
        wizard.run()
        
        click.pause("\nPress Enter to continue...")
    
    def _view_emails(self):
        """View emails list."""
        click.echo("\n" + "="*60)
        click.echo("📧 Recent Emails")
        click.echo("="*60 + "\n")
        
        emails = self.db.get_recent_emails(hours=EMAIL_FETCH_HOURS)
        emails.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
        
        if not emails:
            click.echo("No emails found. Run 'Fetch & Score Emails' first.")
            click.pause("\nPress Enter to continue...")
            return
        
        click.echo(f"{'Score':<6} {'Subject':<50} {'Sender':<30}")
        click.echo("-" * 90)
        
        for email in emails[:50]:  # Show top 50
            score = email.get('importance_score', 0)
            subject = email['subject'][:48]
            sender = email['sender'][:28]
            click.echo(f"{score:.2f}  {subject:<50} {sender:<30}")
        
        click.pause("\nPress Enter to continue...")


def check_venv():
    """Check if running in virtual environment."""
    in_venv = (
        hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    )
    
    if not in_venv:
        click.echo("⚠️  WARNING: You're not in a virtual environment!")
        click.echo("   It's recommended to activate your venv first:")
        click.echo("   source venv/bin/activate")
        click.echo("")
        if not click.confirm("Continue anyway?", default=False):
            sys.exit(1)


if __name__ == '__main__':
    check_venv()
    launcher = MainLauncher()
    launcher.run()
