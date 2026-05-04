"""
Enhanced AI/ML Service with Modern Models and Techniques
Integrates OpenAI, Anthropic, and Transformer models for advanced incident analysis
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import os
from pathlib import Path

# Modern ML/AI imports
import openai
import anthropic
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from sentence_transformers import SentenceTransformer
import torch
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """AI providers for different capabilities"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL_TRANSFORMER = "local_transformer"
    ENSEMBLE = "ensemble"


class IncidentCategory(Enum):
    """Enhanced incident categories with subcategories"""
    INFRASTRUCTURE = {
        "main": "infrastructure",
        "subcategories": ["compute", "storage", "networking", "cdn", "load_balancer"]
    }
    APPLICATION = {
        "main": "application",
        "subcategories": ["backend", "frontend", "api", "microservices", "monolith"]
    }
    DATABASE = {
        "main": "database",
        "subcategories": ["sql", "nosql", "cache", "data_warehouse", "replication"]
    }
    SECURITY = {
        "main": "security",
        "subcategories": ["authentication", "authorization", "encryption", "vulnerability", "breach"]
    }
    PERFORMANCE = {
        "main": "performance",
        "subcategories": ["latency", "throughput", "memory", "cpu", "scalability"]
    }
    THIRD_PARTY = {
        "main": "third_party",
        "subcategories": ["api_failure", "service_outage", "rate_limit", "dependency"]
    }
    HUMAN_ERROR = {
        "main": "human_error",
        "subcategories": ["misconfiguration", "deployment", "process", "training"]
    }


@dataclass
class AIAnalysisResult:
    """Enhanced AI analysis result"""
    category: Dict[str, str]
    severity: str
    confidence: float
    root_cause_analysis: List[str]
    contributing_factors: List[str]
    recommended_actions: List[str]
    prediction_confidence: float
    similar_incidents: List[Dict]
    estimated_resolution_time: Optional[timedelta]
    business_impact: Dict[str, Any]
    compliance_risks: List[str]


class EnhancedAIService:
    """Enhanced AI service with multiple model capabilities"""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.sentence_model = None
        self.classifier_pipeline = None
        self.embedding_cache = {}
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize AI models and clients"""
        try:
            # Initialize OpenAI
            if os.getenv("OPENAI_API_KEY"):
                self.openai_client = openai.OpenAI()
                logger.info("OpenAI client initialized")
            
            # Initialize Anthropic
            if os.getenv("ANTHROPIC_API_KEY"):
                self.anthropic_client = anthropic.Anthropic()
                logger.info("Anthropic client initialized")
            
            # Initialize local transformer models
            self._load_local_models()
            
        except Exception as e:
            logger.error(f"Error initializing AI models: {e}")
    
    def _load_local_models(self):
        """Load local transformer models"""
        try:
            # Load sentence transformer for embeddings
            model_name = "all-MiniLM-L6-v2"
            self.sentence_model = SentenceTransformer(model_name)
            logger.info(f"Sentence transformer loaded: {model_name}")
            
            # Load classification pipeline
            model_name = "microsoft/DialoGPT-medium"  # Example model
            self.classifier_pipeline = pipeline(
                "text-classification",
                model=model_name,
                device=0 if torch.cuda.is_available() else -1
            )
            logger.info(f"Classification pipeline loaded: {model_name}")
            
        except Exception as e:
            logger.error(f"Error loading local models: {e}")
    
    async def analyze_incident(self, incident_data: Dict[str, Any], provider: AIProvider = AIProvider.ENSEMBLE) -> AIAnalysisResult:
        """
        Analyze incident using enhanced AI capabilities
        """
        try:
            # Extract incident text for analysis
            incident_text = self._extract_incident_text(incident_data)
            
            # Get embeddings for similarity search
            embeddings = await self._get_embeddings(incident_text)
            
            # Perform analysis based on provider
            if provider == AIProvider.OPENAI and self.openai_client:
                return await self._analyze_with_openai(incident_data, incident_text, embeddings)
            elif provider == AIProvider.ANTHROPIC and self.anthropic_client:
                return await self._analyze_with_anthropic(incident_data, incident_text, embeddings)
            elif provider == AIProvider.LOCAL_TRANSFORMER:
                return await self._analyze_with_local_models(incident_data, incident_text, embeddings)
            else:
                # Ensemble approach
                return await self._ensemble_analysis(incident_data, incident_text, embeddings)
                
        except Exception as e:
            logger.error(f"Error in incident analysis: {e}")
            raise
    
    def _extract_incident_text(self, incident_data: Dict[str, Any]) -> str:
        """Extract relevant text from incident data"""
        text_parts = []
        
        # Add title and description
        if "title" in incident_data:
            text_parts.append(f"Title: {incident_data['title']}")
        if "description" in incident_data:
            text_parts.append(f"Description: {incident_data['description']}")
        
        # Add timeline events
        if "timeline" in incident_data:
            for event in incident_data["timeline"]:
                if "description" in event:
                    text_parts.append(f"Event: {event['description']}")
        
        # Add contributing factors
        if "contributing_factors" in incident_data:
            for factor in incident_data["contributing_factors"]:
                text_parts.append(f"Factor: {factor}")
        
        return " ".join(text_parts)
    
    async def _get_embeddings(self, text: str) -> np.ndarray:
        """Get text embeddings using sentence transformer"""
        try:
            # Check cache first
            if text in self.embedding_cache:
                return self.embedding_cache[text]
            
            # Generate embeddings
            embeddings = self.sentence_model.encode([text])[0]
            
            # Cache result
            self.embedding_cache[text] = embeddings
            
            return embeddings
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            return np.zeros(384)  # Default embedding size
    
    async def _analyze_with_openai(self, incident_data: Dict, incident_text: str, embeddings: np.ndarray) -> AIAnalysisResult:
        """Analyze incident using OpenAI GPT models"""
        try:
            prompt = self._build_analysis_prompt(incident_data, incident_text)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert incident analyst. Provide detailed, structured analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            analysis_text = response.choices[0].message.content
            return self._parse_analysis_result(analysis_text, embeddings)
            
        except Exception as e:
            logger.error(f"Error in OpenAI analysis: {e}")
            raise
    
    async def _analyze_with_anthropic(self, incident_data: Dict, incident_text: str, embeddings: np.ndarray) -> AIAnalysisResult:
        """Analyze incident using Anthropic Claude"""
        try:
            prompt = self._build_analysis_prompt(incident_data, incident_text)
            
            response = self.anthropic_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            analysis_text = response.content[0].text
            return self._parse_analysis_result(analysis_text, embeddings)
            
        except Exception as e:
            logger.error(f"Error in Anthropic analysis: {e}")
            raise
    
    async def _analyze_with_local_models(self, incident_data: Dict, incident_text: str, embeddings: np.ndarray) -> AIAnalysisResult:
        """Analyze incident using local transformer models"""
        try:
            # Use classification pipeline for category and severity
            classification = self.classifier_pipeline(incident_text)
            
            # Generate analysis based on classification
            category = self._map_to_category(classification[0]['label'])
            severity = self._estimate_severity(incident_data)
            
            # Generate recommendations using rule-based approach
            recommendations = self._generate_recommendations(category, severity, incident_data)
            
            return AIAnalysisResult(
                category=category,
                severity=severity,
                confidence=classification[0]['score'],
                root_cause_analysis=self._extract_root_causes(incident_data),
                contributing_factors=self._extract_contributing_factors(incident_data),
                recommended_actions=recommendations,
                prediction_confidence=classification[0]['score'],
                similar_incidents=await self._find_similar_incidents(embeddings),
                estimated_resolution_time=self._estimate_resolution_time(category, severity),
                business_impact=self._assess_business_impact(incident_data),
                compliance_risks=self._assess_compliance_risks(incident_data)
            )
            
        except Exception as e:
            logger.error(f"Error in local model analysis: {e}")
            raise
    
    async def _ensemble_analysis(self, incident_data: Dict, incident_text: str, embeddings: np.ndarray) -> AIAnalysisResult:
        """Combine results from multiple AI providers"""
        results = []
        
        # Collect results from available providers
        if self.openai_client:
            try:
                result = await self._analyze_with_openai(incident_data, incident_text, embeddings)
                results.append(("openai", result))
            except Exception as e:
                logger.warning(f"OpenAI analysis failed: {e}")
        
        if self.anthropic_client:
            try:
                result = await self._analyze_with_anthropic(incident_data, incident_text, embeddings)
                results.append(("anthropic", result))
            except Exception as e:
                logger.warning(f"Anthropic analysis failed: {e}")
        
        # Always include local models as fallback
        try:
            result = await self._analyze_with_local_models(incident_data, incident_text, embeddings)
            results.append(("local", result))
        except Exception as e:
            logger.warning(f"Local model analysis failed: {e}")
        
        # Ensemble the results
        return self._ensemble_results(results)
    
    def _ensemble_results(self, results: List[Tuple[str, AIAnalysisResult]]) -> AIAnalysisResult:
        """Combine multiple analysis results"""
        if not results:
            raise ValueError("No analysis results to ensemble")
        
        if len(results) == 1:
            return results[0][1]
        
        # Weight voting based on provider confidence
        weights = {"openai": 0.4, "anthropic": 0.4, "local": 0.2}
        
        # Ensemble category (most common)
        categories = [result.category["main"] for _, result in results]
        main_category = max(set(categories), key=categories.count)
        
        # Find subcategory for main category
        subcategories = []
        for _, result in results:
            if result.category["main"] == main_category:
                subcategories.append(result.category.get("subcategory", ""))
        
        subcategory = max(set(subcategories), key=subcategories.count) if subcategories else ""
        
        # Average confidence scores
        avg_confidence = sum(result.confidence for _, result in results) / len(results)
        
        # Combine all recommendations
        all_recommendations = []
        for _, result in results:
            all_recommendations.extend(result.recommended_actions)
        
        # Remove duplicates while preserving order
        unique_recommendations = list(dict.fromkeys(all_recommendations))
        
        # Combine similar incidents
        all_similar = []
        for _, result in results:
            all_similar.extend(result.similar_incidents)
        
        return AIAnalysisResult(
            category={"main": main_category, "subcategory": subcategory},
            severity=results[0][1].severity,  # Use first result's severity
            confidence=avg_confidence,
            root_cause_analysis=results[0][1].root_cause_analysis,
            contributing_factors=results[0][1].contributing_factors,
            recommended_actions=unique_recommendations[:10],  # Limit to top 10
            prediction_confidence=avg_confidence,
            similar_incidents=all_similar[:5],  # Limit to top 5
            estimated_resolution_time=results[0][1].estimated_resolution_time,
            business_impact=results[0][1].business_impact,
            compliance_risks=results[0][1].compliance_risks
        )
    
    def _build_analysis_prompt(self, incident_data: Dict, incident_text: str) -> str:
        """Build comprehensive analysis prompt for AI models"""
        prompt = f"""
Analyze the following incident and provide a detailed structured analysis:

Incident Information:
{json.dumps(incident_data, indent=2)}

Full Text:
{incident_text}

Please provide analysis in the following format:
1. Category: [main_category/subcategory]
2. Severity: [critical/high/medium/low]
3. Root Cause Analysis: [list of root causes]
4. Contributing Factors: [list of factors]
5. Recommended Actions: [specific, actionable recommendations]
6. Business Impact: [assessment of business impact]
7. Compliance Risks: [any compliance or regulatory risks]
8. Estimated Resolution Time: [time estimate in hours/days]

Be specific, actionable, and focus on prevention and improvement.
"""
        return prompt
    
    def _parse_analysis_result(self, analysis_text: str, embeddings: np.ndarray) -> AIAnalysisResult:
        """Parse AI model response into structured result"""
        # This is a simplified parser - in production, use more sophisticated parsing
        lines = analysis_text.split('\n')
        
        category = {"main": "application", "subcategory": "api"}
        severity = "medium"
        confidence = 0.8
        
        root_causes = []
        contributing_factors = []
        recommendations = []
        business_impact = {}
        compliance_risks = []
        
        for line in lines:
            if "Category:" in line:
                parts = line.split("Category:")[1].strip().split("/")
                category = {"main": parts[0].strip(), "subcategory": parts[1].strip() if len(parts) > 1 else ""}
            elif "Severity:" in line:
                severity = line.split("Severity:")[1].strip().lower()
            elif "Root Cause Analysis:" in line:
                # Parse following lines as root causes
                pass
            elif "Contributing Factors:" in line:
                # Parse following lines as factors
                pass
            elif "Recommended Actions:" in line:
                # Parse following lines as recommendations
                pass
        
        return AIAnalysisResult(
            category=category,
            severity=severity,
            confidence=confidence,
            root_cause_analysis=root_causes,
            contributing_factors=contributing_factors,
            recommended_actions=recommendations,
            prediction_confidence=confidence,
            similar_incidents=[],  # Would be populated separately
            estimated_resolution_time=None,
            business_impact=business_impact,
            compliance_risks=compliance_risks
        )
    
    async def _find_similar_incidents(self, embeddings: np.ndarray, limit: int = 5) -> List[Dict]:
        """Find similar incidents using embedding similarity"""
        # This would query a vector database of past incidents
        # For now, return empty list
        return []
    
    def _estimate_resolution_time(self, category: Dict, severity: str) -> timedelta:
        """Estimate resolution time based on category and severity"""
        base_times = {
            "critical": timedelta(hours=8),
            "high": timedelta(hours=24),
            "medium": timedelta(hours=72),
            "low": timedelta(hours=168)
        }
        
        category_multipliers = {
            "infrastructure": 1.2,
            "application": 1.0,
            "database": 1.5,
            "security": 2.0,
            "performance": 0.8,
            "third_party": 1.3,
            "human_error": 0.5
        }
        
        base_time = base_times.get(severity, timedelta(hours=24))
        multiplier = category_multipliers.get(category["main"], 1.0)
        
        return timedelta(hours=int(base_time.total_seconds() / 3600 * multiplier))
    
    def _assess_business_impact(self, incident_data: Dict) -> Dict[str, Any]:
        """Assess business impact of incident"""
        impact = {
            "revenue_impact": "low",
            "customer_impact": "medium",
            "operational_impact": "medium",
            "reputation_impact": "low"
        }
        
        # Analyze incident data to determine impact
        if "affected_users" in incident_data:
            users = incident_data["affected_users"]
            if users > 10000:
                impact["customer_impact"] = "high"
                impact["revenue_impact"] = "high"
            elif users > 1000:
                impact["customer_impact"] = "medium"
        
        return impact
    
    def _assess_compliance_risks(self, incident_data: Dict) -> List[str]:
        """Assess compliance and regulatory risks"""
        risks = []
        
        # Check for data exposure
        if "data_exposed" in incident_data and incident_data["data_exposed"]:
            risks.append("GDPR - Data breach notification required")
            risks.append("Data privacy violation")
        
        # Check for availability issues
        if "downtime_hours" in incident_data and incident_data["downtime_hours"] > 4:
            risks.append("SLA violation potential")
            risks.append("Service availability compliance")
        
        return risks
    
    def _map_to_category(self, label: str) -> Dict[str, str]:
        """Map model label to incident category"""
        # Simplified mapping - would be more sophisticated in production
        category_mapping = {
            "LABEL_0": {"main": "infrastructure", "subcategory": "compute"},
            "LABEL_1": {"main": "application", "subcategory": "api"},
            "LABEL_2": {"main": "database", "subcategory": "sql"},
            "LABEL_3": {"main": "security", "subcategory": "authentication"},
        }
        
        return category_mapping.get(label, {"main": "application", "subcategory": "api"})
    
    def _estimate_severity(self, incident_data: Dict) -> str:
        """Estimate incident severity based on data"""
        severity = "medium"
        
        # Check for severity indicators
        if "downtime_hours" in incident_data:
            downtime = incident_data["downtime_hours"]
            if downtime > 8:
                severity = "critical"
            elif downtime > 2:
                severity = "high"
            elif downtime < 0.5:
                severity = "low"
        
        if "affected_users" in incident_data:
            users = incident_data["affected_users"]
            if users > 50000:
                severity = "critical"
            elif users > 10000:
                severity = "high"
        
        return severity
    
    def _generate_recommendations(self, category: Dict, severity: str, incident_data: Dict) -> List[str]:
        """Generate specific recommendations based on category and severity"""
        recommendations = []
        
        # Category-specific recommendations
        if category["main"] == "infrastructure":
            recommendations.extend([
                "Review infrastructure monitoring and alerting",
                "Implement automated failover mechanisms",
                "Conduct capacity planning review"
            ])
        elif category["main"] == "application":
            recommendations.extend([
                "Review application error handling",
                "Implement better logging and observability",
                "Conduct code review for similar patterns"
            ])
        elif category["main"] == "security":
            recommendations.extend([
                "Conduct security audit",
                "Review access controls and permissions",
                "Implement security monitoring"
            ])
        
        # Severity-specific recommendations
        if severity in ["critical", "high"]:
            recommendations.extend([
                "Schedule incident review meeting",
                "Update incident response procedures",
                "Consider post-incident testing"
            ])
        
        return recommendations[:10]  # Limit to 10 recommendations
    
    def _extract_root_causes(self, incident_data: Dict) -> List[str]:
        """Extract root causes from incident data"""
        root_causes = []
        
        if "timeline" in incident_data:
            for event in incident_data["timeline"]:
                if "root_cause" in event and event["root_cause"]:
                    root_causes.append(event["description"])
        
        return root_causes
    
    def _extract_contributing_factors(self, incident_data: Dict) -> List[str]:
        """Extract contributing factors from incident data"""
        return incident_data.get("contributing_factors", [])


# Global instance
enhanced_ai_service = EnhancedAIService()
