import sys
import os
import click
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.storage.database import Database


class InteractiveFeedback:
    """Interactive feedback system for emails."""
    
    def __init__(self):
        self.db = Database()
    
    def interactive_feedback(self, email_id: str = None):
        """Provide interactive feedback on emails."""
        if email_id:
            self._feedback_single(email_id)
        else:
            self._feedback_batch()
    
    def _feedback_single(self, email_id: str):
        """Provide feedback on a single email."""
        email = self.db.get_email_by_id(email_id)
        if not email:
            click.echo(f"❌ Email {email_id} not found.")
            return
        
        click.echo("\n" + "="*60)
        click.echo("📧 Email Feedback")
        click.echo("="*60)
        click.echo(f"From: {email['sender']}")
        click.echo(f"Subject: {email['subject']}")
        click.echo(f"Date: {email['date']}")
        click.echo(f"Preview: {email.get('snippet', '')[:200]}...")
        click.echo(f"Current Score: {email.get('importance_score', 0):.2f}\n")
        
        # Is important?
        is_important = click.confirm("Is this email important?", default=True)
        
        # Priority
        priority = None
        if is_important:
            priority = click.prompt(
                "Priority level",
                type=click.Choice(['high', 'medium', 'low']),
                default='medium'
            )
        
        # Category
        category = click.prompt(
            "Category",
            type=click.Choice(['work', 'personal', 'urgent', 'newsletter', 'notification', 'other']),
            default='other'
        )
        
        # Optional notes
        notes = click.prompt("Optional notes (press Enter to skip)", default='', show_default=False)
        if not notes:
            notes = None
        
        # Save feedback
        self.db.save_enhanced_feedback(email_id, is_important, priority, category, notes)
        
        click.echo(f"\n✅ Feedback saved! The system will learn from this.")
    
    def _feedback_batch(self):
        """Provide feedback on multiple emails."""
        emails = self.db.get_recent_emails(hours=48)
        emails.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
        
        if not emails:
            click.echo("No emails found. Run 'fetch' first.")
            return
        
        click.echo("\n" + "="*60)
        click.echo("📧 Batch Email Feedback")
        click.echo("="*60)
        click.echo(f"Found {len(emails)} emails. Let's review the top ones.\n")
        
        for i, email in enumerate(emails[:20], 1):  # Top 20
            click.echo(f"\n[{i}/{min(20, len(emails))}]")
            click.echo(f"From: {email['sender']}")
            click.echo(f"Subject: {email['subject'][:60]}")
            click.echo(f"Score: {email.get('importance_score', 0):.2f}")
            
            action = click.prompt(
                "Action (important/not-important/skip/quit)",
                type=click.Choice(['important', 'not-important', 'skip', 'quit']),
                default='skip'
            )
            
            if action == 'quit':
                break
            elif action == 'skip':
                continue
            elif action == 'important':
                priority = click.prompt(
                    "Priority (high/medium/low)",
                    type=click.Choice(['high', 'medium', 'low']),
                    default='medium'
                )
                category = click.prompt(
                    "Category",
                    type=click.Choice(['work', 'personal', 'urgent', 'other']),
                    default='other'
                )
                self.db.save_enhanced_feedback(email['id'], True, priority, category)
                click.echo("✅ Marked as important")
            else:  # not-important
                self.db.save_enhanced_feedback(email['id'], False, None, 'other')
                click.echo("✅ Marked as not important")
        
        click.echo("\n✅ Batch feedback complete!")
    
    def quick_feedback(self, email_id: str, important: bool):
        """Quick feedback without interaction."""
        self.db.save_enhanced_feedback(email_id, important)
        status = "important" if important else "not important"
        click.echo(f"✅ Marked email {email_id} as {status}")
