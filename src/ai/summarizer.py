import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from typing import List, Dict
from openai import OpenAI
from config.settings import OPENAI_API_KEY, SUMMARY_MODEL


class BriefSummarizer:
    """Generates daily email brief using OpenAI."""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = SUMMARY_MODEL
    
    def generate_brief(self, emails: List[Dict], top_n: int = 10) -> str:
        """
        Generate a daily brief from top N important emails.
        
        Args:
            emails: List of emails sorted by importance
            top_n: Number of top emails to include
            
        Returns:
            Formatted brief text
        """
        if not emails:
            return "No emails found in the last 24-48 hours."
        
        # Get top N emails
        top_emails = emails[:top_n]
        
        # Format emails for prompt
        email_texts = []
        for i, email in enumerate(top_emails, 1):
            email_texts.append(
                f"{i}. From: {email['sender']}\n"
                f"   Subject: {email['subject']}\n"
                f"   Date: {email['date']}\n"
                f"   Preview: {email.get('snippet', '')[:200]}\n"
                f"   Importance Score: {email.get('importance_score', 0):.2f}\n"
            )
        
        prompt = f"""You are a helpful email assistant. Create a concise daily email brief from these important emails.

Emails:
{chr(10).join(email_texts)}

Create a brief that:
1. Highlights the most critical emails that need attention
2. Provides a brief summary of each important email
3. Groups related emails if applicable
4. Is concise and actionable

IMPORTANT: Format your response as clean HTML. Use:
- <h2> for main section titles (like "Critical Emails", "Other Updates")
- <h3> for individual email titles
- <p> for paragraphs and summaries
- <ul> and <li> for lists
- <strong> for emphasis
- <div class="email-item-brief"> to wrap each email entry
- Use class="critical" for urgent emails, class="important" for important ones

Do NOT use markdown. Use proper HTML tags only."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful email assistant that creates concise, actionable daily email briefs. Always format your response as clean HTML with proper structure. Use <h2> for main sections, <h3> for individual email titles, <p> for paragraphs, <ul> and <li> for lists, <strong> for emphasis, and <div class='email-item-brief'> to wrap each email. Never use markdown syntax."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            brief_html = response.choices[0].message.content.strip()
            
            # Clean up any markdown that might have slipped through
            import re
            # Remove markdown header separators
            brief_html = re.sub(r'^=+\s*$', '', brief_html, flags=re.MULTILINE)
            # Convert markdown headers to HTML if needed
            brief_html = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', brief_html, flags=re.MULTILINE)
            brief_html = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', brief_html, flags=re.MULTILINE)
            brief_html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', brief_html, flags=re.MULTILINE)
            # Convert markdown bold
            brief_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', brief_html)
            # Convert markdown lists (handle both - and *)
            brief_html = re.sub(r'^[-*]\s+(.+)$', r'<li>\1</li>', brief_html, flags=re.MULTILINE)
            # Convert numbered lists
            brief_html = re.sub(r'^\d+\.\s+(.+)$', r'<li>\1</li>', brief_html, flags=re.MULTILINE)
            
            # Wrap consecutive <li> in <ul>
            lines = brief_html.split('\n')
            result = []
            in_list = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('<li>'):
                    if not in_list:
                        result.append('<ul>')
                        in_list = True
                    result.append(line)
                elif stripped.startswith('</li>') or stripped.startswith('</ul>') or stripped.startswith('</ol>'):
                    if in_list:
                        result.append('</ul>')
                        in_list = False
                    result.append(line)
                else:
                    if in_list and not stripped.startswith('<'):
                        result.append('</ul>')
                        in_list = False
                    result.append(line)
            if in_list:
                result.append('</ul>')
            brief_html = '\n'.join(result)
            
            # Clean up extra whitespace
            brief_html = re.sub(r'\n{3,}', '\n\n', brief_html)
            
            # Don't add header - dashboard already has one
            # Just return the brief content directly
            
            return brief_html
            
        except Exception as e:
            return f"Error generating brief: {e}\n\nTop emails:\n" + "\n".join([f"- {e['subject']} ({e['sender']})" for e in top_emails[:5]])
