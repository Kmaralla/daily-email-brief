import sys
import os
import click
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.storage.database import Database


class OnboardingWizard:
    """Interactive onboarding wizard for setting up preferences."""
    
    def __init__(self):
        self.db = Database()
    
    def run(self):
        """Run the onboarding wizard."""
        click.echo("\n" + "="*60)
        click.echo("🎯 Welcome to Daily Email Brief Setup!")
        click.echo("="*60 + "\n")
        
        click.echo("Let's configure your email preferences to personalize your briefs.\n")
        
        # Step 1: Important senders
        self._setup_important_senders()
        
        # Step 2: Email categories
        self._setup_categories()
        
        # Step 3: Priority preferences
        self._setup_priorities()
        
        # Step 4: Delivery preferences
        self._setup_delivery()
        
        click.echo("\n✅ Onboarding complete! Your preferences have been saved.")
        click.echo("💡 You can update these anytime with: python main.py preferences\n")
    
    def _setup_important_senders(self):
        """Setup important senders."""
        click.echo("📧 Step 1: Important Senders")
        click.echo("-" * 60)
        click.echo("Add email addresses or domains that should always be marked as important.")
        click.echo("Examples: boss@company.com, notifications@github.com, *@family.com\n")
        
        senders = []
        while True:
            sender = click.prompt("Enter sender email/domain (or 'done' to finish)", default='done')
            if sender.lower() == 'done':
                break
            
            priority = click.prompt("Priority (high/medium/low)", default='high', 
                                  type=click.Choice(['high', 'medium', 'low']))
            category = click.prompt("Category (work/personal/urgent/other)", default='work',
                                   type=click.Choice(['work', 'personal', 'urgent', 'other']))
            
            senders.append({
                'sender': sender,
                'priority': priority,
                'category': category
            })
            
            self.db.save_important_sender(sender, priority, category)
            click.echo(f"✅ Added {sender} as {priority} priority in {category} category\n")
        
        if senders:
            click.echo(f"✅ Configured {len(senders)} important sender(s)\n")
        else:
            click.echo("ℹ️  No important senders configured. You can add them later.\n")
    
    def _setup_categories(self):
        """Setup email categories."""
        click.echo("📁 Step 2: Email Categories")
        click.echo("-" * 60)
        click.echo("Configure how emails should be categorized.\n")
        
        categories = ['work', 'personal', 'newsletters', 'notifications', 'social', 'other']
        click.echo("Available categories: " + ", ".join(categories))
        
        # Save default categories
        self.db.save_user_preference('categories', ','.join(categories))
        click.echo("✅ Default categories configured\n")
    
    def _setup_priorities(self):
        """Setup priority preferences."""
        click.echo("⚡ Step 3: Priority Settings")
        click.echo("-" * 60)
        
        default_top_n = click.prompt("How many top emails should appear in your brief?", 
                                     default=10, type=int)
        self.db.save_user_preference('brief_top_n', str(default_top_n))
        
        min_score = click.prompt("Minimum importance score to include (0.0-1.0)", 
                                default=0.3, type=float)
        self.db.save_user_preference('min_importance_score', str(min_score))
        
        click.echo("✅ Priority settings configured\n")
    
    def _setup_delivery(self):
        """Setup delivery preferences."""
        click.echo("📬 Step 4: Delivery Preferences")
        click.echo("-" * 60)
        
        delivery_method = click.prompt(
            "How would you like to receive your brief?",
            type=click.Choice(['cli', 'email', 'both', 'web']),
            default='cli'
        )
        self.db.save_user_preference('delivery_method', delivery_method)
        
        if delivery_method in ['email', 'both']:
            email_address = click.prompt("Enter your email address for brief delivery")
            self.db.save_user_preference('delivery_email', email_address)
            click.echo("✅ Email delivery configured")
        
        if delivery_method in ['web', 'both']:
            click.echo("✅ Web dashboard will be available at http://localhost:5000/dashboard")
        
        click.echo("")
