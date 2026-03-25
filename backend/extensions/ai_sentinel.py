import logging
import re
from typing import Dict, List, Tuple
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

class AISentinel:
    """
    AI Sentinel: A lightweight Phishing & Threat Detection Module.
    
    Uses heuristics and a pre-trained (mock) model to analyze email content
    for suspicious patterns, urgency, and known phishing indicators.
    """
    
    def __init__(self):
        self._keywords_urgency = [
            "urgent", "immediate", "action required", "suspended", "verify your account",
            "password expiration", "unauthorized access", "click here", "login now"
        ]
        
        self._keywords_finance = [
            "bank", "transfer", "invoice", "payment", "credit card", "social security",
            "crypto", "bitcoin", "ethereum", "wallet"
        ]
        
        # Initialize a simple ML pipeline
        # In a real system, this would load a saved model artifact.
        # Here we train a tiny model on initialization for demonstration.
        self._model = self._train_mock_model()
        logger.info("AI Sentinel initialized and model loaded.")

    def _train_mock_model(self) -> Pipeline:
        """
        Trains a lightweight model on typical phishing phrases vs normal phrases.
        This provides the 'AI' portion of the detection.
        """
        X_train = [
            "Please verify your account immediately",
            "Your account has been suspended",
            "Click here to claim your prize",
            "Meeting at 3 PM tomorrow",
            "Attached is the project report",
            "Lunch details for friday",
            "Urgent: Payment overdue",
            "Happy birthday!"
        ]
        y_train = [1, 1, 1, 0, 0, 0, 1, 0]  # 1 = Phishing, 0 = Safe
        
        pipeline = Pipeline([
            ('vectorizer', CountVectorizer()),
            ('classifier', LogisticRegression())
        ])
        
        pipeline.fit(X_train, y_train)
        return pipeline

    def analyze_email(self, subject: str, body: str, sender: str) -> Dict[str, Any]:
        """
        Analyzes an email for threats.
        Returns a dict with 'safe', 'score', 'reasons'.
        """
        score = 0
        reasons = []
        
        text_content = f"{subject} {body}".lower()
        
        # 1. ML Model Prediction
        try:
            # Probability of being phishing (class 1)
            probs = self._model.predict_proba([text_content])[0]
            ml_score = probs[1] * 100  # Convert to 0-100 scale
            if ml_score > 60:
                score += ml_score * 0.5
                reasons.append(f"AI Pattern Analysis detected suspicious content ({int(ml_score)}% confidence)")
        except Exception as e:
            logger.warning(f"AI Model prediction failed: {e}")
        
        # 2. Heuristic Checks
        urgency_count = sum(1 for k in self._keywords_urgency if k in text_content)
        if urgency_count > 0:
            score += urgency_count * 15
            reasons.append(f"Detected {urgency_count} urgency triggers")
            
        finance_count = sum(1 for k in self._keywords_finance if k in text_content)
        if finance_count > 0:
            score += finance_count * 10
            reasons.append(f"Detected {finance_count} financial keywords")
        
        # 3. Sender Analysis (Basic)
        if "admin" in sender.lower() or "support" in sender.lower():
            if "gmail.com" in sender.lower() or "yahoo.com" in sender.lower():
                score += 30
                reasons.append("Sender claims to be support/admin but uses public domain")

        # Cap score
        score = min(100, score)
        
        is_safe = score < 50
        
        return {
            "is_safe": is_safe,
            "score": round(score, 1),
            "reasons": reasons,
            "version": "1.0 (Sentinel)"
        }

# Global instance
ai_sentinel = AISentinel()
