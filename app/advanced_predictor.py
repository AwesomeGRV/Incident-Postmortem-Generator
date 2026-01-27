"""
Advanced AI Incident Prediction and Prevention System
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import pickle
import os
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from sklearn.metrics import classification_report, confusion_matrix
from sqlalchemy.orm import Session
from .enterprise_models import Incident
import warnings
warnings.filterwarnings('ignore')


class PredictionType(Enum):
    INCIDENT_LIKELIHOOD = "incident_likelihood"
    SEVERITY_PREDICTION = "severity_prediction"
    RESOLUTION_TIME = "resolution_time"
    ROOT_CAUSE = "root_cause"
    PREVENTION_RECOMMENDATION = "prevention_recommendation"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PredictionResult:
    prediction_type: PredictionType
    confidence: float
    result: Any
    factors: List[str]
    recommendations: List[str]
    timestamp: datetime
    model_version: str


@dataclass
class IncidentPattern:
    pattern_id: str
    frequency: int
    time_pattern: str
    affected_systems: List[str]
    severity_trend: str
    related_incidents: List[int]
    prevention_score: float


class AdvancedPredictor:
    """Advanced AI-powered incident prediction and prevention system"""
    
    def __init__(self, db: Session):
        self.db = db
        self.models_dir = "models/advanced"
        self.scaler = StandardScaler()
        self.incident_predictor = RandomForestClassifier(n_estimators=100, random_state=42)
        self.severity_predictor = RandomForestClassifier(n_estimators=100, random_state=42)
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.clustering_model = DBSCAN(eps=0.5, min_samples=5)
        self.model_version = "2.1.0"
        self._ensure_models_directory()
        self._load_models()
    
    def _ensure_models_directory(self):
        """Ensure models directory exists"""
        os.makedirs(self.models_dir, exist_ok=True)
    
    def _load_models(self):
        """Load pre-trained models if available"""
        try:
            if os.path.exists(f"{self.models_dir}/incident_predictor.pkl"):
                with open(f"{self.models_dir}/incident_predictor.pkl", 'rb') as f:
                    self.incident_predictor = pickle.load(f)
            
            if os.path.exists(f"{self.models_dir}/severity_predictor.pkl"):
                with open(f"{self.models_dir}/severity_predictor.pkl", 'rb') as f:
                    self.severity_predictor = pickle.load(f)
            
            if os.path.exists(f"{self.models_dir}/scaler.pkl"):
                with open(f"{self.models_dir}/scaler.pkl", 'rb') as f:
                    self.scaler = pickle.load(f)
                    
        except Exception as e:
            print(f"Could not load models: {e}")
    
    def _save_models(self):
        """Save trained models"""
        try:
            with open(f"{self.models_dir}/incident_predictor.pkl", 'wb') as f:
                pickle.dump(self.incident_predictor, f)
            
            with open(f"{self.models_dir}/severity_predictor.pkl", 'wb') as f:
                pickle.dump(self.severity_predictor, f)
            
            with open(f"{self.models_dir}/scaler.pkl", 'wb') as f:
                pickle.dump(self.scaler, f)
                
        except Exception as e:
            print(f"Could not save models: {e}")
    
    def _extract_features(self, incidents: List[Incident]) -> np.ndarray:
        """Extract features from incidents for ML models"""
        features = []
        
        for incident in incidents:
            # Time-based features
            hour = incident.created_at.hour if incident.created_at else 0
            day_of_week = incident.created_at.weekday() if incident.created_at else 0
            day_of_month = incident.created_at.day if incident.created_at else 0
            
            # Incident features
            severity_map = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            severity = severity_map.get(incident.severity.lower(), 2)
            
            # Text-based features (simplified)
            title_length = len(incident.title) if incident.title else 0
            desc_length = len(incident.description) if incident.description else 0
            
            # Timeline features
            timeline_events = len(incident.timeline) if incident.timeline else 0
            
            # Impact features
            impact_score = len(incident.impact) if incident.impact else 0
            
            # Action items features
            action_items = len(incident.action_items) if incident.action_items else 0
            
            feature_vector = [
                hour, day_of_week, day_of_month,
                severity, title_length, desc_length,
                timeline_events, impact_score, action_items
            ]
            
            features.append(feature_vector)
        
        return np.array(features)
    
    def train_models(self) -> Dict[str, float]:
        """Train prediction models with historical data"""
        try:
            # Get historical incidents
            incidents = self.db.query(Incident).all()
            
            if len(incidents) < 10:
                return {"error": "Insufficient data for training"}
            
            # Extract features
            features = self._extract_features(incidents)
            
            # Create labels for training
            # Incident likelihood (based on frequency patterns)
            incident_labels = []
            severity_labels = []
            
            for incident in incidents:
                # Simple heuristic for incident likelihood
                incident_labels.append(1 if incident.severity in ['high', 'critical'] else 0)
                
                # Severity prediction labels
                severity_map = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
                severity_labels.append(severity_map.get(incident.severity.lower(), 1))
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features)
            
            # Train incident predictor
            self.incident_predictor.fit(features_scaled, incident_labels)
            
            # Train severity predictor
            self.severity_predictor.fit(features_scaled, severity_labels)
            
            # Train anomaly detector
            self.anomaly_detector.fit(features_scaled)
            
            # Save models
            self._save_models()
            
            return {
                "models_trained": True,
                "incidents_used": len(incidents),
                "features_extracted": features.shape[1],
                "model_version": self.model_version
            }
            
        except Exception as e:
            return {"error": f"Training failed: {str(e)}"}
    
    def predict_incident_likelihood(self, system_metrics: Dict[str, Any]) -> PredictionResult:
        """Predict likelihood of incident based on system metrics"""
        try:
            # Convert system metrics to feature vector
            features = self._metrics_to_features(system_metrics)
            features_scaled = self.scaler.transform([features])
            
            # Predict likelihood
            probability = self.incident_predictor.predict_proba(features_scaled)[0]
            likelihood_score = probability[1]  # Probability of incident
            
            # Determine risk level
            if likelihood_score < 0.3:
                risk_level = RiskLevel.LOW
            elif likelihood_score < 0.6:
                risk_level = RiskLevel.MEDIUM
            elif likelihood_score < 0.8:
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.CRITICAL
            
            # Generate factors and recommendations
            factors = self._analyze_risk_factors(system_metrics)
            recommendations = self._generate_prevention_recommendations(risk_level, factors)
            
            return PredictionResult(
                prediction_type=PredictionType.INCIDENT_LIKELIHOOD,
                confidence=likelihood_score,
                result={
                    "risk_level": risk_level.value,
                    "probability": likelihood_score,
                    "system_health": self._calculate_system_health(system_metrics)
                },
                factors=factors,
                recommendations=recommendations,
                timestamp=datetime.now(),
                model_version=self.model_version
            )
            
        except Exception as e:
            return PredictionResult(
                prediction_type=PredictionType.INCIDENT_LIKELIHOOD,
                confidence=0.0,
                result={"error": str(e)},
                factors=[],
                recommendations=["Unable to predict due to model error"],
                timestamp=datetime.now(),
                model_version=self.model_version
            )
    
    def predict_severity(self, incident_data: Dict[str, Any]) -> PredictionResult:
        """Predict incident severity based on initial data"""
        try:
            # Convert incident data to features
            features = self._incident_to_features(incident_data)
            features_scaled = self.scaler.transform([features])
            
            # Predict severity
            severity_prediction = self.severity_predictor.predict(features_scaled)[0]
            severity_probabilities = self.severity_predictor.predict_proba(features_scaled)[0]
            
            severity_map = {0: 'low', 1: 'medium', 2: 'high', 3: 'critical'}
            predicted_severity = severity_map[severity_prediction]
            confidence = max(severity_probabilities)
            
            # Generate factors and recommendations
            factors = self._analyze_severity_factors(incident_data)
            recommendations = self._generate_severity_recommendations(predicted_severity, factors)
            
            return PredictionResult(
                prediction_type=PredictionType.SEVERITY_PREDICTION,
                confidence=confidence,
                result={
                    "predicted_severity": predicted_severity,
                    "severity_probabilities": {
                        severity_map[i]: prob for i, prob in enumerate(severity_probabilities)
                    }
                },
                factors=factors,
                recommendations=recommendations,
                timestamp=datetime.now(),
                model_version=self.model_version
            )
            
        except Exception as e:
            return PredictionResult(
                prediction_type=PredictionType.SEVERITY_PREDICTION,
                confidence=0.0,
                result={"error": str(e)},
                factors=[],
                recommendations=["Unable to predict severity due to model error"],
                timestamp=datetime.now(),
                model_version=self.model_version
            )
    
    def detect_anomalies(self, system_metrics: Dict[str, Any]) -> PredictionResult:
        """Detect anomalies in system metrics"""
        try:
            features = self._metrics_to_features(system_metrics)
            features_scaled = self.scaler.transform([features])
            
            # Detect anomalies
            anomaly_score = self.anomaly_detector.decision_function(features_scaled)[0]
            is_anomaly = self.anomaly_detector.predict(features_scaled)[0] == -1
            
            # Analyze anomaly factors
            factors = self._analyze_anomaly_factors(system_metrics)
            recommendations = self._generate_anomaly_recommendations(is_anomaly, factors)
            
            return PredictionResult(
                prediction_type=PredictionType.ROOT_CAUSE,
                confidence=abs(anomaly_score),
                result={
                    "is_anomaly": is_anomaly,
                    "anomaly_score": float(anomaly_score),
                    "anomaly_level": "high" if abs(anomaly_score) > 0.5 else "medium" if abs(anomaly_score) > 0.2 else "low"
                },
                factors=factors,
                recommendations=recommendations,
                timestamp=datetime.now(),
                model_version=self.model_version
            )
            
        except Exception as e:
            return PredictionResult(
                prediction_type=PredictionType.ROOT_CAUSE,
                confidence=0.0,
                result={"error": str(e)},
                factors=[],
                recommendations=["Unable to detect anomalies due to model error"],
                timestamp=datetime.now(),
                model_version=self.model_version
            )
    
    def find_incident_patterns(self, days_back: int = 30) -> List[IncidentPattern]:
        """Find patterns in historical incidents"""
        try:
            # Get recent incidents
            cutoff_date = datetime.now() - timedelta(days=days_back)
            incidents = self.db.query(Incident).filter(
                Incident.created_at >= cutoff_date
            ).all()
            
            if len(incidents) < 5:
                return []
            
            # Extract features for clustering
            features = self._extract_features(incidents)
            features_scaled = self.scaler.fit_transform(features)
            
            # Cluster incidents
            clusters = self.clustering_model.fit_predict(features_scaled)
            
            # Analyze patterns
            patterns = []
            unique_clusters = set(clusters)
            
            for cluster_id in unique_clusters:
                if cluster_id == -1:  # Noise points
                    continue
                
                cluster_incidents = [incidents[i] for i in range(len(incidents)) if clusters[i] == cluster_id]
                
                if len(cluster_incidents) >= 3:  # Only consider significant patterns
                    pattern = self._analyze_cluster_pattern(cluster_incidents, cluster_id)
                    patterns.append(pattern)
            
            return sorted(patterns, key=lambda p: p.frequency, reverse=True)
            
        except Exception as e:
            print(f"Error finding patterns: {e}")
            return []
    
    def _metrics_to_features(self, metrics: Dict[str, Any]) -> List[float]:
        """Convert system metrics to feature vector"""
        # Extract relevant metrics
        cpu_usage = metrics.get('cpu_usage', 0)
        memory_usage = metrics.get('memory_usage', 0)
        disk_usage = metrics.get('disk_usage', 0)
        network_latency = metrics.get('network_latency', 0)
        error_rate = metrics.get('error_rate', 0)
        response_time = metrics.get('response_time', 0)
        
        # Time-based features
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()
        
        return [
            cpu_usage, memory_usage, disk_usage, network_latency,
            error_rate, response_time, hour, day_of_week
        ]
    
    def _incident_to_features(self, incident_data: Dict[str, Any]) -> List[float]:
        """Convert incident data to feature vector"""
        title = incident_data.get('title', '')
        description = incident_data.get('description', '')
        
        # Basic features
        title_length = len(title)
        desc_length = len(description)
        
        # Time features
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()
        
        # Text analysis (simplified)
        urgent_keywords = ['critical', 'urgent', 'down', 'failure', 'crash']
        urgent_count = sum(1 for keyword in urgent_keywords if keyword in title.lower() or keyword in description.lower())
        
        return [
            title_length, desc_length, hour, day_of_week, urgent_count
        ]
    
    def _calculate_system_health(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall system health score"""
        cpu = metrics.get('cpu_usage', 0)
        memory = metrics.get('memory_usage', 0)
        disk = metrics.get('disk_usage', 0)
        error_rate = metrics.get('error_rate', 0)
        
        # Weighted health score
        health_score = 100 - (cpu * 0.3 + memory * 0.3 + disk * 0.2 + error_rate * 0.2)
        return max(0, min(100, health_score))
    
    def _analyze_risk_factors(self, metrics: Dict[str, Any]) -> List[str]:
        """Analyze risk factors from system metrics"""
        factors = []
        
        if metrics.get('cpu_usage', 0) > 80:
            factors.append("High CPU usage detected")
        
        if metrics.get('memory_usage', 0) > 85:
            factors.append("Memory usage approaching limits")
        
        if metrics.get('disk_usage', 0) > 90:
            factors.append("Disk space critically low")
        
        if metrics.get('error_rate', 0) > 5:
            factors.append("Elevated error rate")
        
        if metrics.get('response_time', 0) > 1000:
            factors.append("Response time degradation")
        
        return factors
    
    def _generate_prevention_recommendations(self, risk_level: RiskLevel, factors: List[str]) -> List[str]:
        """Generate prevention recommendations based on risk level and factors"""
        recommendations = []
        
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            recommendations.extend([
                "Immediate system health check required",
                "Consider scaling resources",
                "Enable additional monitoring"
            ])
        
        if "High CPU usage" in str(factors):
            recommendations.append("Optimize CPU-intensive processes")
        
        if "Memory usage" in str(factors):
            recommendations.append("Investigate memory leaks and optimize usage")
        
        if "error rate" in str(factors):
            recommendations.append("Review error logs and fix root causes")
        
        return recommendations
    
    def _analyze_severity_factors(self, incident_data: Dict[str, Any]) -> List[str]:
        """Analyze factors affecting incident severity"""
        factors = []
        title = incident_data.get('title', '').lower()
        description = incident_data.get('description', '').lower()
        
        critical_keywords = ['critical', 'emergency', 'outage', 'down', 'crash']
        if any(keyword in title or keyword in description for keyword in critical_keywords):
            factors.append("Critical keywords detected in incident description")
        
        if len(description) > 500:
            factors.append("Detailed description suggests complex incident")
        
        return factors
    
    def _generate_severity_recommendations(self, severity: str, factors: List[str]) -> List[str]:
        """Generate recommendations based on predicted severity"""
        recommendations = []
        
        if severity == 'critical':
            recommendations.extend([
                "Escalate immediately to senior team",
                "Activate incident response protocol",
                "Prepare customer communication"
            ])
        elif severity == 'high':
            recommendations.extend([
                "Assign senior engineer",
                "Monitor closely for escalation",
                "Prepare rollback plan"
            ])
        elif severity == 'medium':
            recommendations.extend([
                "Standard incident response",
                "Monitor resolution progress",
                "Document lessons learned"
            ])
        else:
            recommendations.extend([
                "Handle during regular operations",
                "Monitor for changes",
                "Update knowledge base"
            ])
        
        return recommendations
    
    def _analyze_anomaly_factors(self, metrics: Dict[str, Any]) -> List[str]:
        """Analyze factors contributing to anomalies"""
        factors = []
        
        for metric, value in metrics.items():
            if isinstance(value, (int, float)) and value > 90:
                factors.append(f"Unusual high {metric}: {value}")
        
        return factors
    
    def _generate_anomaly_recommendations(self, is_anomaly: bool, factors: List[str]) -> List[str]:
        """Generate recommendations for anomaly detection"""
        if not is_anomaly:
            return ["System operating within normal parameters"]
        
        recommendations = [
            "Investigate anomalous metrics immediately",
            "Check for recent system changes",
            "Review logs for unusual activity"
        ]
        
        return recommendations
    
    def _analyze_cluster_pattern(self, incidents: List[Incident], cluster_id: int) -> IncidentPattern:
        """Analyze pattern within a cluster of incidents"""
        # Time pattern analysis
        hours = [inc.created_at.hour for inc in incidents if inc.created_at]
        common_hour = max(set(hours), key=hours.count) if hours else 0
        
        # Affected systems
        systems = set()
        for inc in incidents:
            if inc.title:
                # Simple system extraction from titles
                if 'database' in inc.title.lower():
                    systems.add('database')
                if 'api' in inc.title.lower():
                    systems.add('api')
                if 'network' in inc.title.lower():
                    systems.add('network')
        
        # Severity trend
        severities = [inc.severity for inc in incidents]
        severity_counts = {s: severities.count(s) for s in set(severities)}
        most_common_severity = max(severity_counts, key=severity_counts.get)
        
        # Prevention score (simplified)
        prevention_score = 1.0 - (len(incidents) / 100.0)  # More incidents = lower prevention score
        
        return IncidentPattern(
            pattern_id=f"pattern_{cluster_id}",
            frequency=len(incidents),
            time_pattern=f"Common hour: {common_hour}:00",
            affected_systems=list(systems),
            severity_trend=most_common_severity,
            related_incidents=[inc.id for inc in incidents],
            prevention_score=max(0, prevention_score)
        )


# Global predictor instance
def get_advanced_predictor(db: Session) -> AdvancedPredictor:
    """Get advanced predictor instance"""
    return AdvancedPredictor(db)
