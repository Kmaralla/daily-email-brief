import numpy as np
from typing import List, Dict
from openai import OpenAI
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config.settings import OPENAI_API_KEY, EMBEDDING_MODEL
from src.storage.database import Database


class ImportanceScorer:
    """Scores email importance using embeddings and user feedback patterns."""
    
    def __init__(self, db: Database):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.db = db
        self.embedding_model = EMBEDDING_MODEL
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI."""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def score_email(self, email: Dict) -> float:
        """
        Score email importance (0.0 to 1.0).
        
        Factors:
        1. Sender reputation (from feedback history)
        2. Similarity to previously marked important emails
        3. Subject keywords (basic heuristics)
        """
        score = 0.0
        
        # Factor 1: Sender reputation (0-0.4 weight)
        sender = email.get('sender', '')
        sender_reputation = self.db.get_sender_reputation(sender)
        score += sender_reputation * 0.4
        
        # Factor 2: Similarity to important emails (0-0.4 weight)
        email_text = f"{email.get('subject', '')} {email.get('snippet', '')}"
        embedding = self.get_embedding(email_text)
        
        if embedding:
            # Save embedding
            self.db.save_embedding(email['id'], embedding)
            
            # Compare with important emails
            important_embeddings = self.db.get_important_emails_embeddings()
            if important_embeddings:
                max_similarity = 0.0
                for _, imp_embedding in important_embeddings:
                    similarity = self.cosine_similarity(embedding, imp_embedding)
                    max_similarity = max(max_similarity, similarity)
                
                score += max_similarity * 0.4
            else:
                # No feedback yet, use neutral score
                score += 0.2
        else:
            score += 0.2
        
        # Factor 3: Basic keyword heuristics (0-0.2 weight)
        subject_lower = email.get('subject', '').lower()
        important_keywords = ['urgent', 'important', 'action required', 'deadline', 'meeting']
        not_important_keywords = ['unsubscribe', 'newsletter', 'promotion', 'spam']
        
        keyword_score = 0.0
        for keyword in important_keywords:
            if keyword in subject_lower:
                keyword_score += 0.1
                break
        
        for keyword in not_important_keywords:
            if keyword in subject_lower:
                keyword_score -= 0.1
                break
        
        score += max(0, min(0.2, keyword_score + 0.1))
        
        # Normalize to 0-1 range
        score = max(0.0, min(1.0, score))
        
        return score
