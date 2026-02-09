import sqlite3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from datetime import datetime
from typing import List, Dict, Optional
from config.settings import DATABASE_PATH


class Database:
    """Local SQLite database for storing emails, embeddings, and feedback."""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Emails table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                subject TEXT,
                sender TEXT,
                date TEXT,
                snippet TEXT,
                body TEXT,
                thread_id TEXT,
                account_type TEXT,
                importance_score REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Embeddings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS embeddings (
                email_id TEXT PRIMARY KEY,
                embedding TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails(id)
            )
        ''')
        
        # Feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                is_important INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails(id)
            )
        ''')
        
        # Sender patterns table (for learning)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sender_patterns (
                sender TEXT PRIMARY KEY,
                important_count INTEGER DEFAULT 0,
                not_important_count INTEGER DEFAULT 0,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Enhanced feedback table with categories and priorities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_enhanced (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                is_important INTEGER,
                priority TEXT,
                category TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails(id)
            )
        ''')
        
        # Email categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_categories (
                email_id TEXT PRIMARY KEY,
                category TEXT,
                confidence REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails(id)
            )
        ''')
        
        # Brief delivery history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS brief_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brief_text TEXT,
                delivery_method TEXT,
                delivery_status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Important senders (user-defined)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS important_senders (
                sender TEXT PRIMARY KEY,
                priority TEXT,
                category TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Category patterns (learn from feedback: e.g. "Promotions" often not important)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS category_patterns (
                category TEXT PRIMARY KEY,
                important_count INTEGER DEFAULT 0,
                not_important_count INTEGER DEFAULT 0,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_email(self, email: Dict, account_type: str = 'gmail'):
        """Save or update an email."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO emails 
            (id, subject, sender, date, snippet, body, thread_id, account_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            email['id'],
            email['subject'],
            email['sender'],
            email['date'],
            email.get('snippet', ''),
            email.get('body', ''),
            email.get('thread_id', ''),
            account_type
        ))
        
        conn.commit()
        conn.close()
    
    def save_embedding(self, email_id: str, embedding: List[float]):
        """Save embedding for an email."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        embedding_str = ','.join(map(str, embedding))
        
        cursor.execute('''
            INSERT OR REPLACE INTO embeddings (email_id, embedding)
            VALUES (?, ?)
        ''', (email_id, embedding_str))
        
        conn.commit()
        conn.close()
    
    def get_embedding(self, email_id: str) -> Optional[List[float]]:
        """Get embedding for an email."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT embedding FROM embeddings WHERE email_id = ?', (email_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return [float(x) for x in result[0].split(',')]
        return None
    
    def get_important_emails_embeddings(self) -> List[tuple]:
        """Get embeddings of emails marked as important."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT e.email_id, e.embedding
            FROM embeddings e
            JOIN feedback f ON e.email_id = f.email_id
            WHERE f.is_important = 1
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        embeddings = []
        for email_id, embedding_str in results:
            embedding = [float(x) for x in embedding_str.split(',')]
            embeddings.append((email_id, embedding))
        
        return embeddings
    
    def save_feedback(self, email_id: str, is_important: bool):
        """Save user feedback for an email."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feedback (email_id, is_important)
            VALUES (?, ?)
        ''', (email_id, 1 if is_important else 0))
        
        # Update sender pattern
        cursor.execute('SELECT sender FROM emails WHERE id = ?', (email_id,))
        result = cursor.fetchone()
        if result:
            sender = result[0]
            cursor.execute('''
                INSERT OR REPLACE INTO sender_patterns 
                (sender, important_count, not_important_count, last_updated)
                VALUES (
                    ?,
                    COALESCE((SELECT important_count FROM sender_patterns WHERE sender = ?), 0) + ?,
                    COALESCE((SELECT not_important_count FROM sender_patterns WHERE sender = ?), 0) + ?,
                    CURRENT_TIMESTAMP
                )
            ''', (sender, sender, 1 if is_important else 0, sender, 0 if is_important else 1))
        
        conn.commit()
        conn.close()
    
    def update_category_feedback(self, category: str, is_important: bool):
        """Update category pattern from feedback (e.g. mark Promotions as not important)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO category_patterns
            (category, important_count, not_important_count, last_updated)
            VALUES (
                ?,
                COALESCE((SELECT important_count FROM category_patterns WHERE category = ?), 0) + ?,
                COALESCE((SELECT not_important_count FROM category_patterns WHERE category = ?), 0) + ?,
                CURRENT_TIMESTAMP
            )
        ''', (category, category, 1 if is_important else 0, category, 0 if is_important else 1))
        conn.commit()
        conn.close()
    
    def get_category_reputation(self, category: str) -> float:
        """Get category reputation (0-1) from feedback history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT important_count, not_important_count FROM category_patterns WHERE category = ?
        ''', (category,))
        result = cursor.fetchone()
        conn.close()
        if not result:
            return 0.5
        important, not_important = result
        total = important + not_important
        if total == 0:
            return 0.5
        return important / total
    
    def get_email_by_id(self, email_id: str) -> Optional[Dict]:
        """Get a single email by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, subject, sender, date, snippet, body, importance_score
            FROM emails WHERE id = ?
        ''', (email_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {
            'id': row[0], 'subject': row[1], 'sender': row[2], 'date': row[3],
            'snippet': row[4], 'body': row[5], 'importance_score': row[6]
        }
    
    def update_importance_score(self, email_id: str, score: float):
        """Update importance score for an email."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE emails SET importance_score = ? WHERE id = ?
        ''', (score, email_id))
        
        conn.commit()
        conn.close()
    
    def get_recent_emails(self, hours: int = 48) -> List[Dict]:
        """Get emails from the last N hours."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = datetime.now().isoformat()
        cursor.execute('''
            SELECT id, subject, sender, date, snippet, body, importance_score
            FROM emails
            WHERE datetime(date) >= datetime('now', '-' || ? || ' hours')
            ORDER BY importance_score DESC, date DESC
        ''', (hours,))
        
        rows = cursor.fetchall()
        conn.close()
        
        emails = []
        for row in rows:
            emails.append({
                'id': row[0],
                'subject': row[1],
                'sender': row[2],
                'date': row[3],
                'snippet': row[4],
                'body': row[5],
                'importance_score': row[6]
            })
        
        return emails
    
    def get_sender_reputation(self, sender: str) -> float:
        """Get sender reputation score based on feedback history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT important_count, not_important_count
            FROM sender_patterns
            WHERE sender = ?
        ''', (sender,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return 0.5  # Neutral
        
        important, not_important = result
        total = important + not_important
        
        if total == 0:
            return 0.5
        
        return important / total
    
    def save_user_preference(self, key: str, value: str):
        """Save user preference."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, value))
        
        conn.commit()
        conn.close()
    
    def get_user_preference(self, key: str, default: str = None) -> Optional[str]:
        """Get user preference."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM user_preferences WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else default
    
    def save_enhanced_feedback(self, email_id: str, is_important: bool, 
                              priority: str = None, category: str = None, notes: str = None):
        """Save enhanced feedback with priority and category."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save to enhanced feedback table
        cursor.execute('''
            INSERT INTO feedback_enhanced (email_id, is_important, priority, category, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (email_id, 1 if is_important else 0, priority, category, notes))
        
        # Also save to regular feedback for backward compatibility
        self.save_feedback(email_id, is_important)
        
        # Update sender pattern
        cursor.execute('SELECT sender FROM emails WHERE id = ?', (email_id,))
        result = cursor.fetchone()
        if result:
            sender = result[0]
            cursor.execute('''
                INSERT OR REPLACE INTO sender_patterns 
                (sender, important_count, not_important_count, last_updated)
                VALUES (
                    ?,
                    COALESCE((SELECT important_count FROM sender_patterns WHERE sender = ?), 0) + ?,
                    COALESCE((SELECT not_important_count FROM sender_patterns WHERE sender = ?), 0) + ?,
                    CURRENT_TIMESTAMP
                )
            ''', (sender, sender, 1 if is_important else 0, sender, 0 if is_important else 1))
        
        conn.commit()
        conn.close()
    
    def save_important_sender(self, sender: str, priority: str = 'high', 
                             category: str = None, notes: str = None):
        """Save important sender configuration."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO important_senders (sender, priority, category, notes, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (sender, priority, category, notes))
        
        conn.commit()
        conn.close()
    
    def get_important_senders(self) -> List[Dict]:
        """Get list of important senders."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT sender, priority, category, notes FROM important_senders')
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'sender': row[0],
            'priority': row[1],
            'category': row[2],
            'notes': row[3]
        } for row in rows]
    
    def save_brief_delivery(self, brief_text: str, delivery_method: str, 
                            delivery_status: str = 'sent'):
        """Save brief delivery record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO brief_deliveries (brief_text, delivery_method, delivery_status)
            VALUES (?, ?, ?)
        ''', (brief_text, delivery_method, delivery_status))
        
        conn.commit()
        conn.close()
    
    def get_email_by_id(self, email_id: str) -> Optional[Dict]:
        """Get email by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, subject, sender, date, snippet, body, importance_score
            FROM emails WHERE id = ?
        ''', (email_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'subject': row[1],
                'sender': row[2],
                'date': row[3],
                'snippet': row[4],
                'body': row[5],
                'importance_score': row[6]
            }
        return None
