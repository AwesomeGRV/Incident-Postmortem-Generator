"""
Intelligent Incident Correlation and Clustering System
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum
import json
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
from sqlalchemy.orm import Session
from .enterprise_models import Incident
import re
from collections import defaultdict


class CorrelationType(Enum):
    TEMPORAL = "temporal"  # Time-based correlation
    SEMANTIC = "semantic"  # Content similarity
    SYSTEM = "system"     # Same system/component
    CAUSAL = "causal"     # Cause-effect relationship
    IMPACT = "impact"     # Similar impact patterns


class ClusterType(Enum):
    RECURRING = "recurring"     # Recurring incidents
    CASCADE = "cascade"         # Cascade failures
    ROOT_CAUSE = "root_cause"   # Same root cause
    SYSTEM_WIDE = "system_wide" # System-wide issues


@dataclass
class IncidentCorrelation:
    correlation_id: str
    incident_1_id: int
    incident_2_id: int
    correlation_type: CorrelationType
    strength: float  # 0.0 to 1.0
    evidence: List[str]
    confidence: float
    timestamp: datetime


@dataclass
class IncidentCluster:
    cluster_id: str
    cluster_type: ClusterType
    incident_ids: List[int]
    central_incident_id: int
    correlation_strength: float
    time_span: timedelta
    affected_systems: Set[str]
    severity_trend: str
    description: str
    recommendations: List[str]


class IncidentCorrelationEngine:
    """Advanced incident correlation and clustering engine"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 3)
        )
        self.graph = nx.Graph()
        self.correlations: List[IncidentCorrelation] = []
        self.clusters: List[IncidentCluster] = []
        self.system_keywords = {
            'database': ['database', 'db', 'sql', 'mysql', 'postgres', 'oracle', 'mongodb'],
            'api': ['api', 'rest', 'graphql', 'endpoint', 'service'],
            'network': ['network', 'connection', 'latency', 'timeout', 'dns', 'firewall'],
            'storage': ['storage', 'disk', 'filesystem', 's3', 'blob'],
            'authentication': ['auth', 'login', 'password', 'token', 'oauth'],
            'cache': ['cache', 'redis', 'memcached', 'cdn'],
            'monitoring': ['monitoring', 'metrics', 'logging', 'alert'],
            'deployment': ['deploy', 'release', 'rollback', 'ci/cd']
        }
    
    def analyze_incidents(self, days_back: int = 30) -> Dict[str, Any]:
        """Perform comprehensive incident correlation analysis"""
        try:
            # Get recent incidents
            cutoff_date = datetime.now() - timedelta(days=days_back)
            incidents = self.db.query(Incident).filter(
                Incident.created_at >= cutoff_date
            ).all()
            
            if len(incidents) < 2:
                return {"error": "Insufficient incidents for correlation analysis"}
            
            # Clear previous analysis
            self.correlations.clear()
            self.clusters.clear()
            self.graph.clear()
            
            # Perform correlation analysis
            self._find_temporal_correlations(incidents)
            self._find_semantic_correlations(incidents)
            self._find_system_correlations(incidents)
            self._find_causal_correlations(incidents)
            self._find_impact_correlations(incidents)
            
            # Build correlation graph
            self._build_correlation_graph()
            
            # Perform clustering
            self._perform_incident_clustering()
            
            # Generate insights
            insights = self._generate_correlation_insights()
            
            return {
                "incidents_analyzed": len(incidents),
                "correlations_found": len(self.correlations),
                "clusters_identified": len(self.clusters),
                "analysis_period_days": days_back,
                "insights": insights,
                "high_impact_correlations": self._get_high_impact_correlations(),
                "recurring_patterns": self._identify_recurring_patterns()
            }
            
        except Exception as e:
            return {"error": f"Correlation analysis failed: {str(e)}"}
    
    def _find_temporal_correlations(self, incidents: List[Incident]):
        """Find time-based correlations between incidents"""
        for i, inc1 in enumerate(incidents):
            for inc2 in incidents[i+1:]:
                if not inc1.created_at or not inc2.created_at:
                    continue
                
                time_diff = abs((inc1.created_at - inc2.created_at).total_seconds())
                
                # Incidents within 1 hour might be related
                if time_diff <= 3600:  # 1 hour
                    strength = 1.0 - (time_diff / 3600)
                    
                    evidence = []
                    if time_diff <= 300:  # 5 minutes
                        evidence.append("Incidents occurred within 5 minutes")
                    elif time_diff <= 1800:  # 30 minutes
                        evidence.append("Incidents occurred within 30 minutes")
                    else:
                        evidence.append("Incidents occurred within 1 hour")
                    
                    correlation = IncidentCorrelation(
                        correlation_id=f"temporal_{inc1.id}_{inc2.id}",
                        incident_1_id=inc1.id,
                        incident_2_id=inc2.id,
                        correlation_type=CorrelationType.TEMPORAL,
                        strength=strength,
                        evidence=evidence,
                        confidence=0.7,
                        timestamp=datetime.now()
                    )
                    
                    self.correlations.append(correlation)
    
    def _find_semantic_correlations(self, incidents: List[Incident]):
        """Find content-based correlations using text similarity"""
        # Prepare text data
        texts = []
        incident_map = {}
        
        for i, incident in enumerate(incidents):
            text = f"{incident.title or ''} {incident.description or ''}"
            texts.append(text)
            incident_map[i] = incident
        
        if not texts or len(texts) < 2:
            return
        
        # Vectorize texts
        try:
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # Find highly similar pairs
            for i in range(len(incidents)):
                for j in range(i+1, len(incidents)):
                    similarity = similarity_matrix[i][j]
                    
                    if similarity > 0.3:  # Threshold for semantic similarity
                        evidence = []
                        if similarity > 0.7:
                            evidence.append("Very high content similarity")
                        elif similarity > 0.5:
                            evidence.append("High content similarity")
                        else:
                            evidence.append("Moderate content similarity")
                        
                        # Find common keywords
                        text1 = texts[i].lower()
                        text2 = texts[j].lower()
                        common_words = set(text1.split()) & set(text2.split())
                        common_words = [w for w in common_words if len(w) > 3]
                        
                        if common_words:
                            evidence.append(f"Common keywords: {', '.join(common_words[:5])}")
                        
                        correlation = IncidentCorrelation(
                            correlation_id=f"semantic_{incidents[i].id}_{incidents[j].id}",
                            incident_1_id=incidents[i].id,
                            incident_2_id=incidents[j].id,
                            correlation_type=CorrelationType.SEMANTIC,
                            strength=similarity,
                            evidence=evidence,
                            confidence=0.8,
                            timestamp=datetime.now()
                        )
                        
                        self.correlations.append(correlation)
        
        except Exception as e:
            print(f"Semantic correlation error: {e}")
    
    def _find_system_correlations(self, incidents: List[Incident]):
        """Find system-based correlations"""
        for i, inc1 in enumerate(incidents):
            for j, inc2 in enumerate(incidents[i+1:], i+1):
                systems1 = self._extract_systems(inc1)
                systems2 = self._extract_systems(inc2)
                
                common_systems = systems1 & systems2
                
                if common_systems:
                    strength = len(common_systems) / max(len(systems1), len(systems2), 1)
                    
                    evidence = [f"Common systems: {', '.join(common_systems)}"]
                    
                    correlation = IncidentCorrelation(
                        correlation_id=f"system_{inc1.id}_{inc2.id}",
                        incident_1_id=inc1.id,
                        incident_2_id=inc2.id,
                        correlation_type=CorrelationType.SYSTEM,
                        strength=strength,
                        evidence=evidence,
                        confidence=0.9,
                        timestamp=datetime.now()
                    )
                    
                    self.correlations.append(correlation)
    
    def _find_causal_correlations(self, incidents: List[Incident]):
        """Find potential cause-effect relationships"""
        # Sort incidents by time
        sorted_incidents = sorted([inc for inc in incidents if inc.created_at], 
                                key=lambda x: x.created_at)
        
        for i, inc1 in enumerate(sorted_incidents):
            for inc2 in sorted_incidents[i+1:]:
                if not inc1.created_at or not inc2.created_at:
                    continue
                
                time_diff = (inc2.created_at - inc1.created_at).total_seconds()
                
                # Only consider incidents where inc2 happened after inc1
                if time_diff <= 0 or time_diff > 7200:  # Within 2 hours
                    continue
                
                # Check for causal indicators
                causal_score = 0.0
                evidence = []
                
                # Severity progression (lower severity incident might cause higher severity)
                severity_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
                if (inc1.severity in severity_order and inc2.severity in severity_order and
                    severity_order[inc1.severity] < severity_order[inc2.severity]):
                    causal_score += 0.3
                    evidence.append("Severity escalation pattern")
                
                # System dependency (if inc1 affects infrastructure that inc2 depends on)
                systems1 = self._extract_systems(inc1)
                systems2 = self._extract_systems(inc2)
                
                if 'database' in systems1 and 'api' in systems2:
                    causal_score += 0.4
                    evidence.append("Database issue potentially causing API problems")
                
                if 'network' in systems1 and any(s in systems2 for s in ['api', 'database', 'storage']):
                    causal_score += 0.3
                    evidence.append("Network issue potentially affecting dependent services")
                
                if causal_score > 0.3:
                    correlation = IncidentCorrelation(
                        correlation_id=f"causal_{inc1.id}_{inc2.id}",
                        incident_1_id=inc1.id,
                        incident_2_id=inc2.id,
                        correlation_type=CorrelationType.CAUSAL,
                        strength=causal_score,
                        evidence=evidence,
                        confidence=0.6,
                        timestamp=datetime.now()
                    )
                    
                    self.correlations.append(correlation)
    
    def _find_impact_correlations(self, incidents: List[Incident]):
        """Find correlations based on similar impact patterns"""
        for i, inc1 in enumerate(incidents):
            for j, inc2 in enumerate(incidents[i+1:], i+1):
                impact_similarity = self._calculate_impact_similarity(inc1, inc2)
                
                if impact_similarity > 0.5:
                    evidence = []
                    if impact_similarity > 0.8:
                        evidence.append("Very similar impact patterns")
                    elif impact_similarity > 0.6:
                        evidence.append("Similar impact patterns")
                    else:
                        evidence.append("Moderately similar impact patterns")
                    
                    correlation = IncidentCorrelation(
                        correlation_id=f"impact_{inc1.id}_{inc2.id}",
                        incident_1_id=inc1.id,
                        incident_2_id=inc2.id,
                        correlation_type=CorrelationType.IMPACT,
                        strength=impact_similarity,
                        evidence=evidence,
                        confidence=0.7,
                        timestamp=datetime.now()
                    )
                    
                    self.correlations.append(correlation)
    
    def _extract_systems(self, incident: Incident) -> Set[str]:
        """Extract affected systems from incident"""
        systems = set()
        text = f"{incident.title or ''} {incident.description or ''}".lower()
        
        for system, keywords in self.system_keywords.items():
            if any(keyword in text for keyword in keywords):
                systems.add(system)
        
        return systems
    
    def _calculate_impact_similarity(self, inc1: Incident, inc2: Incident) -> float:
        """Calculate similarity between incident impacts"""
        similarity_factors = []
        
        # Severity similarity
        if inc1.severity == inc2.severity:
            similarity_factors.append(1.0)
        else:
            severity_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            s1 = severity_order.get(inc1.severity, 2)
            s2 = severity_order.get(inc2.severity, 2)
            similarity = 1.0 - abs(s1 - s2) / 3.0
            similarity_factors.append(similarity)
        
        # Impact count similarity
        impact1_count = len(inc1.impact) if inc1.impact else 0
        impact2_count = len(inc2.impact) if inc2.impact else 0
        
        if impact1_count == 0 and impact2_count == 0:
            similarity_factors.append(1.0)
        elif impact1_count == 0 or impact2_count == 0:
            similarity_factors.append(0.0)
        else:
            similarity = 1.0 - abs(impact1_count - impact2_count) / max(impact1_count, impact2_count)
            similarity_factors.append(similarity)
        
        # Timeline event similarity
        timeline1_count = len(inc1.timeline) if inc1.timeline else 0
        timeline2_count = len(inc2.timeline) if inc2.timeline else 0
        
        if timeline1_count == 0 and timeline2_count == 0:
            similarity_factors.append(1.0)
        elif timeline1_count == 0 or timeline2_count == 0:
            similarity_factors.append(0.0)
        else:
            similarity = 1.0 - abs(timeline1_count - timeline2_count) / max(timeline1_count, timeline2_count)
            similarity_factors.append(similarity)
        
        return np.mean(similarity_factors) if similarity_factors else 0.0
    
    def _build_correlation_graph(self):
        """Build graph from correlations"""
        self.graph.clear()
        
        # Add nodes (incidents)
        incident_ids = set()
        for corr in self.correlations:
            incident_ids.add(corr.incident_1_id)
            incident_ids.add(corr.incident_2_id)
        
        for incident_id in incident_ids:
            self.graph.add_node(incident_id)
        
        # Add edges (correlations)
        for corr in self.correlations:
            if corr.strength > 0.3:  # Only include strong correlations
                self.graph.add_edge(
                    corr.incident_1_id,
                    corr.incident_2_id,
                    weight=corr.strength,
                    type=corr.correlation_type.value,
                    evidence=corr.evidence
                )
    
    def _perform_incident_clustering(self):
        """Perform clustering on correlated incidents"""
        if len(self.graph.nodes) < 2:
            return
        
        # Use community detection for clustering
        try:
            # Find connected components
            connected_components = list(nx.connected_components(self.graph))
            
            for component in connected_components:
                if len(component) < 2:
                    continue
                
                subgraph = self.graph.subgraph(component)
                
                # Determine cluster type
                cluster_type = self._determine_cluster_type(subgraph)
                
                # Find central incident
                central_incident = max(subgraph.nodes(), 
                                     key=lambda n: subgraph.degree(n))
                
                # Calculate cluster metrics
                incident_ids = list(component)
                incidents = self.db.query(Incident).filter(
                    Incident.id.in_(incident_ids)
                ).all()
                
                time_span = self._calculate_time_span(incidents)
                affected_systems = set()
                for inc in incidents:
                    affected_systems.update(self._extract_systems(inc))
                
                severity_trend = self._calculate_severity_trend(incidents)
                
                # Generate cluster description and recommendations
                description, recommendations = self._generate_cluster_insights(
                    cluster_type, incidents, subgraph
                )
                
                cluster = IncidentCluster(
                    cluster_id=f"cluster_{len(self.clusters)}",
                    cluster_type=cluster_type,
                    incident_ids=incident_ids,
                    central_incident_id=central_incident,
                    correlation_strength=np.mean([
                        edge[2]['weight'] for edge in subgraph.edges(data=True)
                    ]),
                    time_span=time_span,
                    affected_systems=affected_systems,
                    severity_trend=severity_trend,
                    description=description,
                    recommendations=recommendations
                )
                
                self.clusters.append(cluster)
        
        except Exception as e:
            print(f"Clustering error: {e}")
    
    def _determine_cluster_type(self, subgraph) -> ClusterType:
        """Determine the type of cluster"""
        # Analyze edge types
        edge_types = defaultdict(int)
        for _, _, data in subgraph.edges(data=True):
            edge_types[data['type']] += 1
        
        total_edges = sum(edge_types.values())
        
        # Determine cluster type based on dominant correlation type
        if edge_types['causal'] / total_edges > 0.5:
            return ClusterType.CASCADE
        elif edge_types['temporal'] / total_edges > 0.6:
            return ClusterType.RECURRING
        elif edge_types['system'] / total_edges > 0.5:
            return ClusterType.SYSTEM_WIDE
        else:
            return ClusterType.ROOT_CAUSE
    
    def _calculate_time_span(self, incidents: List[Incident]) -> timedelta:
        """Calculate time span of incidents in cluster"""
        times = [inc.created_at for inc in incidents if inc.created_at]
        if len(times) < 2:
            return timedelta(0)
        
        return max(times) - min(times)
    
    def _calculate_severity_trend(self, incidents: List[Incident]) -> str:
        """Calculate severity trend in cluster"""
        if not incidents:
            return "unknown"
        
        # Sort by time
        sorted_incidents = sorted([inc for inc in incidents if inc.created_at and inc.severity],
                                key=lambda x: x.created_at)
        
        if len(sorted_incidents) < 2:
            return "stable"
        
        severity_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        
        first_severity = severity_order.get(sorted_incidents[0].severity, 2)
        last_severity = severity_order.get(sorted_incidents[-1].severity, 2)
        
        if last_severity > first_severity:
            return "escalating"
        elif last_severity < first_severity:
            return "decreasing"
        else:
            return "stable"
    
    def _generate_cluster_insights(self, cluster_type: ClusterType, 
                                 incidents: List[Incident], 
                                 subgraph) -> Tuple[str, List[str]]:
        """Generate insights and recommendations for cluster"""
        if cluster_type == ClusterType.CASCADE:
            description = "Cascade failure pattern detected - incidents appear to be causing each other"
            recommendations = [
                "Implement circuit breakers to prevent cascade failures",
                "Review system dependencies and add isolation",
                "Improve monitoring to detect early warning signs"
            ]
        elif cluster_type == ClusterType.RECURRING:
            description = "Recurring incident pattern - similar incidents happening repeatedly"
            recommendations = [
                "Investigate and fix root cause permanently",
                "Implement automated monitoring for early detection",
                "Create standard operating procedures for quick resolution"
            ]
        elif cluster_type == ClusterType.SYSTEM_WIDE:
            description = "System-wide issue affecting multiple components"
            recommendations = [
                "Perform comprehensive system health check",
                "Review shared infrastructure and dependencies",
                "Implement system-wide monitoring and alerting"
            ]
        else:  # ROOT_CAUSE
            description = "Incidents sharing common root cause"
            recommendations = [
                "Conduct root cause analysis for the entire cluster",
                "Implement preventive measures for the identified root cause",
                "Update knowledge base with cluster insights"
            ]
        
        return description, recommendations
    
    def _generate_correlation_insights(self) -> List[Dict[str, Any]]:
        """Generate insights from correlation analysis"""
        insights = []
        
        # Most common correlation types
        correlation_types = defaultdict(int)
        for corr in self.correlations:
            correlation_types[corr.correlation_type.value] += 1
        
        most_common = max(correlation_types.items(), key=lambda x: x[1])
        insights.append({
            "type": "correlation_pattern",
            "insight": f"Most common correlation type: {most_common[0]} ({most_common[1]} occurrences)",
            "priority": "medium"
        })
        
        # High-strength correlations
        high_strength = [c for c in self.correlations if c.strength > 0.8]
        if high_strength:
            insights.append({
                "type": "high_correlation",
                "insight": f"Found {len(high_strength)} high-strength correlations requiring immediate attention",
                "priority": "high"
            })
        
        # Cluster insights
        if self.clusters:
            insights.append({
                "type": "clustering",
                "insight": f"Identified {len(self.clusters)} incident clusters with common patterns",
                "priority": "medium"
            })
        
        return insights
    
    def _get_high_impact_correlations(self) -> List[Dict[str, Any]]:
        """Get high-impact correlations"""
        high_impact = []
        
        for corr in self.correlations:
            if corr.strength > 0.7 and corr.confidence > 0.7:
                high_impact.append({
                    "correlation_id": corr.correlation_id,
                    "incident_1_id": corr.incident_1_id,
                    "incident_2_id": corr.incident_2_id,
                    "type": corr.correlation_type.value,
                    "strength": corr.strength,
                    "evidence": corr.evidence
                })
        
        return sorted(high_impact, key=lambda x: x['strength'], reverse=True)[:10]
    
    def _identify_recurring_patterns(self) -> List[Dict[str, Any]]:
        """Identify recurring patterns in incidents"""
        patterns = []
        
        # Analyze clusters for recurring patterns
        for cluster in self.clusters:
            if cluster.cluster_type == ClusterType.RECURRING:
                patterns.append({
                    "pattern_id": cluster.cluster_id,
                    "type": "recurring_incidents",
                    "description": cluster.description,
                    "incident_count": len(cluster.incident_ids),
                    "time_span_hours": cluster.time_span.total_seconds() / 3600,
                    "affected_systems": list(cluster.affected_systems),
                    "recommendations": cluster.recommendations
                })
        
        return patterns
    
    def get_incident_correlations(self, incident_id: int) -> List[Dict[str, Any]]:
        """Get all correlations for a specific incident"""
        correlations = []
        
        for corr in self.correlations:
            if corr.incident_1_id == incident_id or corr.incident_2_id == incident_id:
                correlations.append({
                    "correlation_id": corr.correlation_id,
                    "related_incident_id": corr.incident_2_id if corr.incident_1_id == incident_id else corr.incident_1_id,
                    "type": corr.correlation_type.value,
                    "strength": corr.strength,
                    "confidence": corr.confidence,
                    "evidence": corr.evidence,
                    "timestamp": corr.timestamp.isoformat()
                })
        
        return sorted(correlations, key=lambda x: x['strength'], reverse=True)
    
    def get_incident_cluster(self, incident_id: int) -> Optional[Dict[str, Any]]:
        """Get cluster information for a specific incident"""
        for cluster in self.clusters:
            if incident_id in cluster.incident_ids:
                return {
                    "cluster_id": cluster.cluster_id,
                    "cluster_type": cluster.cluster_type.value,
                    "incident_ids": cluster.incident_ids,
                    "central_incident_id": cluster.central_incident_id,
                    "correlation_strength": cluster.correlation_strength,
                    "time_span_hours": cluster.time_span.total_seconds() / 3600,
                    "affected_systems": list(cluster.affected_systems),
                    "severity_trend": cluster.severity_trend,
                    "description": cluster.description,
                    "recommendations": cluster.recommendations
                }
        
        return None


# Global correlation engine instance
def get_correlation_engine(db: Session) -> IncidentCorrelationEngine:
    """Get correlation engine instance"""
    return IncidentCorrelationEngine(db)
