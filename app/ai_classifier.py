"""
AI-powered incident classification and analysis service
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import pickle
import os


class IncidentCategory(Enum):
    """Incident categories for classification"""
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    DATABASE = "database"
    NETWORK = "network"
    SECURITY = "security"
    PERFORMANCE = "performance"
    AVAILABILITY = "availability"
    DATA = "data"
    THIRD_PARTY = "third_party"
    HUMAN_ERROR = "human_error"


class IncidentSeverity(Enum):
    """Incident severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class IncidentClassification:
    """Incident classification result"""
    category: IncidentCategory
    severity: IncidentSeverity
    confidence: float
    factors: List[str]
    recommended_actions: List[str]
    estimated_resolution_time: int  # in minutes
    business_impact: str


class IncidentClassifier:
    """AI-powered incident classification system"""
    
    def __init__(self):
        self.severity_model = None
        self.category_model = None
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Initialize NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
        
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            nltk.download('vader_lexicon')
        
        # Load or train models
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models or train new ones"""
        model_path = "app/models/classification_models.pkl"
        
        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                models = pickle.load(f)
                self.severity_model = models['severity']
                self.category_model = models['category']
                self.vectorizer = models['vectorizer']
        else:
            # Initialize with basic training data
            self._train_basic_models()
    
    def _train_basic_models(self):
        """Train basic classification models with sample data"""
        # Sample training data for severity classification
        severity_texts = [
            ("critical system outage complete failure", "critical"),
            ("major degradation service unavailable", "critical"),
            ("high error rates performance issues", "high"),
            ("significant impact user experience", "high"),
            ("minor issues some users affected", "medium"),
            ("partial degradation slow response", "medium"),
            ("low impact minimal disruption", "low"),
            ("cosmetic issues minor bugs", "low")
        ]
        
        # Sample training data for category classification
        category_texts = [
            ("database connection pool exhaustion sql timeout", "database"),
            ("server crash memory leak cpu spike", "infrastructure"),
            ("application error exception bug", "application"),
            ("network latency packet loss connection timeout", "network"),
            ("security breach unauthorized access vulnerability", "security"),
            ("slow response time performance degradation", "performance"),
            ("service unavailable outage downtime", "availability"),
            ("data corruption loss inconsistency", "data"),
            ("third party api external service failure", "third_party"),
            ("human error misconfiguration deployment", "human_error")
        ]
        
        # Train severity model
        severity_x = [text for text, _ in severity_texts]
        severity_y = [label for _, label in severity_texts]
        
        severity_vectors = self.vectorizer.fit_transform(severity_x)
        self.severity_model = MultinomialNB()
        self.severity_model.fit(severity_vectors, severity_y)
        
        # Train category model
        category_x = [text for text, _ in category_texts]
        category_y = [label for _, label in category_texts]
        
        category_vectors = self.vectorizer.transform(category_x)
        self.category_model = MultinomialNB()
        self.category_model.fit(category_vectors, category_y)
        
        # Save models
        os.makedirs("app/models", exist_ok=True)
        with open("app/models/classification_models.pkl", 'wb') as f:
            pickle.dump({
                'severity': self.severity_model,
                'category': self.category_model,
                'vectorizer': self.vectorizer
            }, f)
    
    def classify_incident(self, incident_data: Dict) -> IncidentClassification:
        """Classify an incident based on its data"""
        # Extract text features from incident
        text_features = self._extract_text_features(incident_data)
        
        # Predict severity
        severity_prediction = self._predict_severity(text_features)
        
        # Predict category
        category_prediction = self._predict_category(text_features)
        
        # Calculate confidence
        confidence = self._calculate_confidence(severity_prediction, category_prediction)
        
        # Identify contributing factors
        factors = self._identify_factors(incident_data)
        
        # Generate recommended actions
        recommended_actions = self._generate_recommendations(
            category_prediction[0], 
            severity_prediction[0], 
            factors
        )
        
        # Estimate resolution time
        estimated_time = self._estimate_resolution_time(
            severity_prediction[0], 
            category_prediction[0]
        )
        
        # Assess business impact
        business_impact = self._assess_business_impact(
            severity_prediction[0], 
            incident_data
        )
        
        return IncidentClassification(
            category=IncidentCategory(category_prediction[0]),
            severity=IncidentSeverity(severity_prediction[0]),
            confidence=confidence,
            factors=factors,
            recommended_actions=recommended_actions,
            estimated_resolution_time=estimated_time,
            business_impact=business_impact
        )
    
    def _extract_text_features(self, incident_data: Dict) -> str:
        """Extract text features from incident data"""
        text_parts = []
        
        # Add title and description
        if incident_data.get('title'):
            text_parts.append(incident_data['title'])
        if incident_data.get('description'):
            text_parts.append(incident_data['description'])
        
        # Add timeline events
        if incident_data.get('timeline'):
            for event in incident_data['timeline']:
                if isinstance(event, dict) and event.get('event'):
                    text_parts.append(event['event'])
        
        # Add impact descriptions
        if incident_data.get('impact'):
            for impact in incident_data['impact']:
                if isinstance(impact, dict) and impact.get('description'):
                    text_parts.append(impact['description'])
        
        return ' '.join(text_parts).lower()
    
    def _predict_severity(self, text: str) -> Tuple[str, float]:
        """Predict incident severity"""
        if not self.severity_model:
            return "medium", 0.5
        
        vector = self.vectorizer.transform([text])
        prediction = self.severity_model.predict(vector)[0]
        probabilities = self.severity_model.predict_proba(vector)[0]
        
        # Get confidence for predicted class
        class_names = self.severity_model.classes_
        confidence_idx = list(class_names).index(prediction)
        confidence = probabilities[confidence_idx]
        
        return prediction, confidence
    
    def _predict_category(self, text: str) -> Tuple[str, float]:
        """Predict incident category"""
        if not self.category_model:
            return "application", 0.5
        
        vector = self.vectorizer.transform([text])
        prediction = self.category_model.predict(vector)[0]
        probabilities = self.category_model.predict_proba(vector)[0]
        
        # Get confidence for predicted class
        class_names = self.category_model.classes_
        confidence_idx = list(class_names).index(prediction)
        confidence = probabilities[confidence_idx]
        
        return prediction, confidence
    
    def _calculate_confidence(self, severity_pred: Tuple, category_pred: Tuple) -> float:
        """Calculate overall classification confidence"""
        severity_conf = severity_pred[1]
        category_conf = category_pred[1]
        return (severity_conf + category_conf) / 2
    
    def _identify_factors(self, incident_data: Dict) -> List[str]:
        """Identify contributing factors from incident data"""
        factors = []
        text = self._extract_text_features(incident_data)
        
        # Define patterns for different factors
        factor_patterns = {
            "Configuration issue": r"(config|configuration|misconfig|setting)",
            "Resource exhaustion": r"(memory|cpu|disk|resource|exhausted|full)",
            "Network problem": r"(network|connection|timeout|latency|packet)",
            "Database issue": r"(database|sql|query|connection pool|deadlock)",
            "Code bug": r"(bug|error|exception|crash|fault)",
            "Human error": r"(human|manual|mistake|accident|operator)",
            "Third party": r"(third party|external|vendor|api|service)",
            "Security": r"(security|breach|attack|unauthorized|vulnerability)",
            "Performance": r"(performance|slow|degradation|response time)",
            "Hardware failure": r"(hardware|server|disk|memory|cpu failure)"
        }
        
        for factor, pattern in factor_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                factors.append(factor)
        
        return factors[:5]  # Return top 5 factors
    
    def _generate_recommendations(self, category: str, severity: str, factors: List[str]) -> List[str]:
        """Generate recommended actions based on classification"""
        recommendations = []
        
        # Base recommendations by category
        category_recommendations = {
            "database": [
                "Review database connection pooling configuration",
                "Analyze slow queries and optimize indexes",
                "Implement database monitoring and alerting"
            ],
            "infrastructure": [
                "Check system resource utilization",
                "Review infrastructure monitoring setup",
                "Implement auto-scaling policies"
            ],
            "application": [
                "Review application logs for errors",
                "Implement better error handling",
                "Add comprehensive monitoring"
            ],
            "network": [
                "Check network connectivity and latency",
                "Review network configuration",
                "Implement network monitoring"
            ],
            "security": [
                "Conduct security audit",
                "Review access controls",
                "Implement security monitoring"
            ]
        }
        
        # Add category-specific recommendations
        if category in category_recommendations:
            recommendations.extend(category_recommendations[category][:2])
        
        # Add severity-specific recommendations
        if severity == "critical":
            recommendations.append("Implement incident response playbook")
            recommendations.append("Schedule post-incident review")
        elif severity == "high":
            recommendations.append("Review monitoring thresholds")
            recommendations.append("Update documentation")
        
        # Add factor-specific recommendations
        if "Configuration issue" in factors:
            recommendations.append("Review change management process")
        if "Human error" in factors:
            recommendations.append("Provide additional training")
            recommendations.append("Implement peer review process")
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def _estimate_resolution_time(self, severity: str, category: str) -> int:
        """Estimate resolution time in minutes"""
        base_times = {
            "critical": 240,  # 4 hours
            "high": 120,      # 2 hours
            "medium": 60,     # 1 hour
            "low": 30         # 30 minutes
        }
        
        category_multipliers = {
            "infrastructure": 1.5,
            "database": 1.3,
            "network": 1.2,
            "security": 2.0,
            "application": 1.0,
            "performance": 1.1,
            "availability": 1.4,
            "data": 1.6,
            "third_party": 2.5,
            "human_error": 0.8
        }
        
        base_time = base_times.get(severity, 60)
        multiplier = category_multipliers.get(category, 1.0)
        
        return int(base_time * multiplier)
    
    def _assess_business_impact(self, severity: str, incident_data: Dict) -> str:
        """Assess business impact based on severity and incident data"""
        impact_descriptions = {
            "critical": "Severe business impact with significant revenue loss and customer dissatisfaction",
            "high": "Major business impact affecting core operations and customer experience",
            "medium": "Moderate business impact with some operational disruption",
            "low": "Minimal business impact with limited operational effect"
        }
        
        base_impact = impact_descriptions.get(severity, impact_descriptions["medium"])
        
        # Check for specific impact indicators
        text = self._extract_text_features(incident_data).lower()
        
        if any(word in text for word in ["revenue", "sales", "transaction"]):
            base_impact += " Financial systems affected."
        if any(word in text for word in ["customer", "user", "client"]):
            base_impact += " Customer experience impacted."
        if any(word in text for word in ["production", "live", "operational"]):
            base_impact += " Production systems affected."
        
        return base_impact


# Global classifier instance
incident_classifier = IncidentClassifier()
