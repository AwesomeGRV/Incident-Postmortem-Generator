"""
Advanced Knowledge Base and Learning System
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import pickle
from sqlalchemy.orm import Session
from .enterprise_models import Incident
import re
from collections import defaultdict, Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class KnowledgeType(Enum):
    SOLUTION = "solution"
    PREVENTION = "prevention"
    BEST_PRACTICE = "best_practice"
    TROUBLESHOOTING = "troubleshooting"
    ROOT_CAUSE = "root_cause"
    LESSON_LEARNED = "lesson_learned"


class LearningSourceType(Enum):
    INCIDENT = "incident"
    POSTMORTEM = "postmortem"
    USER_FEEDBACK = "user_feedback"
    AUTOMATIC_EXTRACTION = "automatic_extraction"
    MANUAL_ENTRY = "manual_entry"


@dataclass
class KnowledgeEntry:
    entry_id: str
    title: str
    content: str
    knowledge_type: KnowledgeType
    source_type: LearningSourceType
    source_id: Optional[str]
    tags: List[str]
    confidence_score: float
    usefulness_score: float
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    related_incidents: List[int]
    metadata: Dict[str, Any]


@dataclass
class LearningPattern:
    pattern_id: str
    pattern_type: str
    frequency: int
    confidence: float
    description: str
    examples: List[str]
    recommendations: List[str]
    last_seen: datetime


class KnowledgeBaseManager:
    """Advanced knowledge base and learning system"""
    
    def __init__(self, db: Session):
        self.db = db
        self.knowledge_dir = "knowledge_base"
        self.entries_file = os.path.join(self.knowledge_dir, "entries.json")
        self.patterns_file = os.path.join(self.knowledge_dir, "patterns.json")
        self.vectorizer_file = os.path.join(self.knowledge_dir, "vectorizer.pkl")
        self.tfidf_matrix_file = os.path.join(self.knowledge_dir, "tfidf_matrix.pkl")
        
        self.entries: List[KnowledgeEntry] = []
        self.patterns: List[LearningPattern] = []
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        
        self._ensure_knowledge_directory()
        self._load_knowledge_base()
        self._load_patterns()
        self._build_search_index()
    
    def _ensure_knowledge_directory(self):
        """Ensure knowledge base directory exists"""
        os.makedirs(self.knowledge_dir, exist_ok=True)
    
    def _load_knowledge_base(self):
        """Load existing knowledge entries"""
        try:
            if os.path.exists(self.entries_file):
                with open(self.entries_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = []
                    for entry_data in data:
                        entry = KnowledgeEntry(
                            entry_id=entry_data['entry_id'],
                            title=entry_data['title'],
                            content=entry_data['content'],
                            knowledge_type=KnowledgeType(entry_data['knowledge_type']),
                            source_type=LearningSourceType(entry_data['source_type']),
                            source_id=entry_data.get('source_id'),
                            tags=entry_data['tags'],
                            confidence_score=entry_data['confidence_score'],
                            usefulness_score=entry_data['usefulness_score'],
                            created_at=datetime.fromisoformat(entry_data['created_at']),
                            updated_at=datetime.fromisoformat(entry_data['updated_at']),
                            created_by=entry_data.get('created_by'),
                            related_incidents=entry_data['related_incidents'],
                            metadata=entry_data.get('metadata', {})
                        )
                        self.entries.append(entry)
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            self.entries = []
    
    def _load_patterns(self):
        """Load existing learning patterns"""
        try:
            if os.path.exists(self.patterns_file):
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.patterns = []
                    for pattern_data in data:
                        pattern = LearningPattern(
                            pattern_id=pattern_data['pattern_id'],
                            pattern_type=pattern_data['pattern_type'],
                            frequency=pattern_data['frequency'],
                            confidence=pattern_data['confidence'],
                            description=pattern_data['description'],
                            examples=pattern_data['examples'],
                            recommendations=pattern_data['recommendations'],
                            last_seen=datetime.fromisoformat(pattern_data['last_seen'])
                        )
                        self.patterns.append(pattern)
        except Exception as e:
            print(f"Error loading patterns: {e}")
            self.patterns = []
    
    def _save_knowledge_base(self):
        """Save knowledge entries to file"""
        try:
            data = []
            for entry in self.entries:
                entry_data = asdict(entry)
                entry_data['knowledge_type'] = entry.knowledge_type.value
                entry_data['source_type'] = entry.source_type.value
                entry_data['created_at'] = entry.created_at.isoformat()
                entry_data['updated_at'] = entry.updated_at.isoformat()
                data.append(entry_data)
            
            with open(self.entries_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving knowledge base: {e}")
    
    def _save_patterns(self):
        """Save learning patterns to file"""
        try:
            data = []
            for pattern in self.patterns:
                pattern_data = asdict(pattern)
                pattern_data['last_seen'] = pattern.last_seen.isoformat()
                data.append(pattern_data)
            
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving patterns: {e}")
    
    def _build_search_index(self):
        """Build TF-IDF search index"""
        try:
            # Load existing vectorizer if available
            if (os.path.exists(self.vectorizer_file) and 
                os.path.exists(self.tfidf_matrix_file)):
                
                with open(self.vectorizer_file, 'rb') as f:
                    self.tfidf_vectorizer = pickle.load(f)
                with open(self.tfidf_matrix_file, 'rb') as f:
                    self.tfidf_matrix = pickle.load(f)
            else:
                # Build new index
                self._rebuild_search_index()
        except Exception as e:
            print(f"Error loading search index: {e}")
            self._rebuild_search_index()
    
    def _rebuild_search_index(self):
        """Rebuild TF-IDF search index"""
        if not self.entries:
            return
        
        # Prepare documents
        documents = []
        for entry in self.entries:
            doc = f"{entry.title} {entry.content} {' '.join(entry.tags)}"
            documents.append(doc)
        
        # Build TF-IDF matrix
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)
        
        # Save index
        try:
            with open(self.vectorizer_file, 'wb') as f:
                pickle.dump(self.tfidf_vectorizer, f)
            with open(self.tfidf_matrix_file, 'wb') as f:
                pickle.dump(self.tfidf_matrix, f)
        except Exception as e:
            print(f"Error saving search index: {e}")
    
    def extract_knowledge_from_incident(self, incident: Incident) -> List[KnowledgeEntry]:
        """Extract knowledge from a resolved incident"""
        entries = []
        
        if not incident.description:
            return entries
        
        # Extract solutions from action items
        if incident.action_items:
            for action_item in incident.action_items:
                if hasattr(action_item, 'description') and action_item.description:
                    solution_entry = KnowledgeEntry(
                        entry_id=self._generate_entry_id(),
                        title=f"Solution: {action_item.title}",
                        content=action_item.description,
                        knowledge_type=KnowledgeType.SOLUTION,
                        source_type=LearningSourceType.INCIDENT,
                        source_id=str(incident.id),
                        tags=self._extract_tags(f"{action_item.title} {action_item.description}"),
                        confidence_score=0.8,
                        usefulness_score=0.0,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        created_by="system",
                        related_incidents=[incident.id],
                        metadata={
                            "action_item_priority": getattr(action_item, 'priority', 'unknown'),
                            "incident_severity": incident.severity
                        }
                    )
                    entries.append(solution_entry)
        
        # Extract prevention measures from contributing factors
        if incident.contributing_factors:
            for factor in incident.contributing_factors:
                if hasattr(factor, 'description') and factor.description:
                    prevention_entry = KnowledgeEntry(
                        entry_id=self._generate_entry_id(),
                        title=f"Prevention: {factor.factor}",
                        content=f"Contributing factor: {factor.description}",
                        knowledge_type=KnowledgeType.PREVENTION,
                        source_type=LearningSourceType.INCIDENT,
                        source_id=str(incident.id),
                        tags=self._extract_tags(f"{factor.factor} {factor.description}"),
                        confidence_score=0.7,
                        usefulness_score=0.0,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        created_by="system",
                        related_incidents=[incident.id],
                        metadata={
                            "factor_category": getattr(factor, 'category', 'unknown'),
                            "incident_severity": incident.severity
                        }
                    )
                    entries.append(prevention_entry)
        
        # Extract lessons learned
        if incident.what_went_well:
            lessons_well = " ".join(incident.what_went_well) if isinstance(incident.what_went_well, list) else str(incident.what_went_well)
            lessons_entry = KnowledgeEntry(
                entry_id=self._generate_entry_id(),
                title="Lessons Learned: What Went Well",
                content=lessons_well,
                knowledge_type=KnowledgeType.LESSON_LEARNED,
                source_type=LearningSourceType.INCIDENT,
                source_id=str(incident.id),
                tags=self._extract_tags(lessons_well),
                confidence_score=0.6,
                usefulness_score=0.0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by="system",
                related_incidents=[incident.id],
                metadata={
                    "lesson_type": "positive",
                    "incident_severity": incident.severity
                }
            )
            entries.append(lessons_entry)
        
        if incident.what_went_wrong:
            lessons_wrong = " ".join(incident.what_went_wrong) if isinstance(incident.what_went_wrong, list) else str(incident.what_went_wrong)
            lessons_entry = KnowledgeEntry(
                entry_id=self._generate_entry_id(),
                title="Lessons Learned: What Went Wrong",
                content=lessons_wrong,
                knowledge_type=KnowledgeType.LESSON_LEARNED,
                source_type=LearningSourceType.INCIDENT,
                source_id=str(incident.id),
                tags=self._extract_tags(lessons_wrong),
                confidence_score=0.6,
                usefulness_score=0.0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by="system",
                related_incidents=[incident.id],
                metadata={
                    "lesson_type": "negative",
                    "incident_severity": incident.severity
                }
            )
            entries.append(lessons_entry)
        
        # Add entries to knowledge base
        for entry in entries:
            self.add_knowledge_entry(entry)
        
        return entries
    
    def add_knowledge_entry(self, entry: KnowledgeEntry):
        """Add a knowledge entry to the base"""
        # Check for duplicates
        existing = self._find_duplicate_entry(entry)
        if existing:
            # Update existing entry
            existing.updated_at = datetime.now()
            existing.usefulness_score = max(existing.usefulness_score, entry.usefulness_score)
            existing.confidence_score = (existing.confidence_score + entry.confidence_score) / 2
            if entry.related_incidents:
                existing.related_incidents.extend(entry.related_incidents)
                existing.related_incidents = list(set(existing.related_incidents))
        else:
            # Add new entry
            self.entries.append(entry)
        
        # Rebuild search index
        self._rebuild_search_index()
        self._save_knowledge_base()
    
    def search_knowledge(self, query: str, knowledge_type: Optional[KnowledgeType] = None, 
                        limit: int = 10) -> List[Dict[str, Any]]:
        """Search knowledge base"""
        if not self.entries or not self.tfidf_vectorizer:
            return []
        
        # Transform query
        query_vector = self.tfidf_vectorizer.transform([query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        
        # Get top results
        top_indices = similarities.argsort()[-limit:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Threshold
                entry = self.entries[idx]
                
                # Filter by knowledge type if specified
                if knowledge_type and entry.knowledge_type != knowledge_type:
                    continue
                
                result = {
                    "entry_id": entry.entry_id,
                    "title": entry.title,
                    "content": entry.content[:200] + "..." if len(entry.content) > 200 else entry.content,
                    "knowledge_type": entry.knowledge_type.value,
                    "tags": entry.tags,
                    "confidence_score": entry.confidence_score,
                    "usefulness_score": entry.usefulness_score,
                    "similarity_score": float(similarities[idx]),
                    "created_at": entry.created_at.isoformat(),
                    "related_incidents": entry.related_incidents,
                    "metadata": entry.metadata
                }
                results.append(result)
        
        return results
    
    def get_relevant_knowledge_for_incident(self, incident: Incident) -> List[Dict[str, Any]]:
        """Get relevant knowledge for a specific incident"""
        if not incident.title and not incident.description:
            return []
        
        # Create search query from incident
        query = f"{incident.title or ''} {incident.description or ''}"
        
        # Search for relevant knowledge
        relevant_knowledge = self.search_knowledge(query, limit=5)
        
        # Boost scores based on similarity to incident characteristics
        for knowledge in relevant_knowledge:
            boost = 0.0
            
            # Boost if same severity level
            if knowledge.get('metadata', {}).get('incident_severity') == incident.severity:
                boost += 0.1
            
            # Boost if recent
            created_at = datetime.fromisoformat(knowledge['created_at'])
            if datetime.now() - created_at < timedelta(days=30):
                boost += 0.1
            
            # Boost if high usefulness score
            if knowledge['usefulness_score'] > 0.7:
                boost += 0.1
            
            knowledge['similarity_score'] += boost
        
        # Re-sort by boosted score
        relevant_knowledge.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return relevant_knowledge
    
    def update_usefulness_score(self, entry_id: str, feedback_score: float):
        """Update usefulness score based on user feedback"""
        for entry in self.entries:
            if entry.entry_id == entry_id:
                # Update with weighted average
                if entry.usefulness_score == 0.0:
                    entry.usefulness_score = feedback_score
                else:
                    entry.usefulness_score = (entry.usefulness_score * 0.8 + feedback_score * 0.2)
                
                entry.updated_at = datetime.now()
                self._save_knowledge_base()
                break
    
    def learn_from_patterns(self) -> Dict[str, Any]:
        """Learn patterns from historical data"""
        try:
            # Get recent incidents
            recent_incidents = self.db.query(Incident).filter(
                Incident.created_at >= datetime.now() - timedelta(days=90)
            ).all()
            
            if len(recent_incidents) < 10:
                return {"error": "Insufficient data for pattern learning"}
            
            # Analyze patterns
            patterns = []
            
            # Common root causes
            root_cause_patterns = self._analyze_root_cause_patterns(recent_incidents)
            patterns.extend(root_cause_patterns)
            
            # Common solutions
            solution_patterns = self._analyze_solution_patterns(recent_incidents)
            patterns.extend(solution_patterns)
            
            # Recurring issues
            recurring_patterns = self._analyze_recurring_patterns(recent_incidents)
            patterns.extend(recurring_patterns)
            
            # Update patterns
            self.patterns.extend(patterns)
            self._save_patterns()
            
            return {
                "patterns_learned": len(patterns),
                "total_patterns": len(self.patterns),
                "pattern_types": list(set(p.pattern_type for p in patterns))
            }
            
        except Exception as e:
            return {"error": f"Pattern learning failed: {str(e)}"}
    
    def _analyze_root_cause_patterns(self, incidents: List[Incident]) -> List[LearningPattern]:
        """Analyze root cause patterns"""
        patterns = []
        
        # Collect contributing factors
        factor_counts = defaultdict(int)
        factor_examples = defaultdict(list)
        
        for incident in incidents:
            if incident.contributing_factors:
                for factor in incident.contributing_factors:
                    if hasattr(factor, 'factor'):
                        factor_name = factor.factor.lower()
                        factor_counts[factor_name] += 1
                        if incident.description:
                            factor_examples[factor_name].append(incident.description[:100])
        
        # Find common factors
        for factor, count in factor_counts.items():
            if count >= 3:  # Appeared in at least 3 incidents
                pattern = LearningPattern(
                    pattern_id=self._generate_pattern_id(),
                    pattern_type="root_cause",
                    frequency=count,
                    confidence=min(0.9, count / len(incidents)),
                    description=f"Common contributing factor: {factor}",
                    examples=factor_examples[factor][:3],
                    recommendations=[
                        f"Implement preventive measures for {factor}",
                        f"Add monitoring for {factor} indicators",
                        f"Create SOP for handling {factor} issues"
                    ],
                    last_seen=datetime.now()
                )
                patterns.append(pattern)
        
        return patterns
    
    def _analyze_solution_patterns(self, incidents: List[Incident]) -> List[LearningPattern]:
        """Analyze solution patterns"""
        patterns = []
        
        # Collect action items
        action_counts = defaultdict(int)
        action_examples = defaultdict(list)
        
        for incident in incidents:
            if incident.action_items:
                for action in incident.action_items:
                    if hasattr(action, 'title'):
                        action_title = action.title.lower()
                        action_counts[action_title] += 1
                        if hasattr(action, 'description') and action.description:
                            action_examples[action_title].append(action.description[:100])
        
        # Find common solutions
        for action, count in action_counts.items():
            if count >= 3:
                pattern = LearningPattern(
                    pattern_id=self._generate_pattern_id(),
                    pattern_type="solution",
                    frequency=count,
                    confidence=min(0.9, count / len(incidents)),
                    description=f"Common solution pattern: {action}",
                    examples=action_examples[action][:3],
                    recommendations=[
                        f"Standardize {action} procedure",
                        f"Create template for {action}",
                        f"Automate {action} where possible"
                    ],
                    last_seen=datetime.now()
                )
                patterns.append(pattern)
        
        return patterns
    
    def _analyze_recurring_patterns(self, incidents: List[Incident]) -> List[LearningPattern]:
        """Analyze recurring incident patterns"""
        patterns = []
        
        # Time-based patterns
        hour_counts = Counter(inc.created_at.hour for inc in incidents if inc.created_at)
        day_counts = Counter(inc.created_at.weekday() for inc in incidents if inc.created_at)
        
        # Peak hours
        peak_hours = [hour for hour, count in hour_counts.most_common(3) if count >= 3]
        if peak_hours:
            pattern = LearningPattern(
                pattern_id=self._generate_pattern_id(),
                pattern_type="temporal",
                frequency=sum(hour_counts[h] for h in peak_hours),
                confidence=0.7,
                description=f"Incidents frequently occur during hours: {', '.join(map(str, peak_hours))}",
                examples=[f"Hour {hour}: {hour_counts[hour]} incidents" for hour in peak_hours],
                recommendations=[
                    "Increase monitoring during peak hours",
                    "Schedule preventive maintenance before peak hours",
                    "Ensure adequate staffing during high-risk periods"
                ],
                last_seen=datetime.now()
            )
            patterns.append(pattern)
        
        return patterns
    
    def _generate_entry_id(self) -> str:
        """Generate unique entry ID"""
        return f"kb_entry_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(os.urandom(4)) & 0xffffffff}"
    
    def _generate_pattern_id(self) -> str:
        """Generate unique pattern ID"""
        return f"pattern_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(os.urandom(4)) & 0xffffffff}"
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract tags from text"""
        # Simple keyword extraction
        text = text.lower()
        
        # Common technical terms
        tech_keywords = [
            'database', 'api', 'network', 'server', 'cloud', 'security',
            'performance', 'memory', 'cpu', 'disk', 'backup', 'monitoring',
            'deployment', 'configuration', 'authentication', 'authorization',
            'cache', 'load balancer', 'firewall', 'ssl', 'tls', 'https'
        ]
        
        tags = []
        for keyword in tech_keywords:
            if keyword in text:
                tags.append(keyword)
        
        # Extract severity indicators
        severity_words = ['critical', 'high', 'medium', 'low', 'urgent', 'emergency']
        for word in severity_words:
            if word in text:
                tags.append(word)
        
        return list(set(tags))
    
    def _find_duplicate_entry(self, new_entry: KnowledgeEntry) -> Optional[KnowledgeEntry]:
        """Find potential duplicate entry"""
        for entry in self.entries:
            # Check exact title match
            if entry.title.lower() == new_entry.title.lower():
                return entry
            
            # Check high content similarity
            content_similarity = self._calculate_content_similarity(entry.content, new_entry.content)
            if content_similarity > 0.8:
                return entry
        
        return None
    
    def _calculate_content_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def get_knowledge_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        stats = {
            "total_entries": len(self.entries),
            "total_patterns": len(self.patterns),
            "entries_by_type": defaultdict(int),
            "entries_by_source": defaultdict(int),
            "average_usefulness": 0.0,
            "most_common_tags": [],
            "recent_entries": 0
        }
        
        # Calculate statistics
        for entry in self.entries:
            stats["entries_by_type"][entry.knowledge_type.value] += 1
            stats["entries_by_source"][entry.source_type.value] += 1
            stats["average_usefulness"] += entry.usefulness_score
            
            # Recent entries (last 30 days)
            if datetime.now() - entry.created_at < timedelta(days=30):
                stats["recent_entries"] += 1
        
        if self.entries:
            stats["average_usefulness"] /= len(self.entries)
        
        # Most common tags
        tag_counts = defaultdict(int)
        for entry in self.entries:
            for tag in entry.tags:
                tag_counts[tag] += 1
        
        stats["most_common_tags"] = [
            {"tag": tag, "count": count} 
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        return stats


# Global knowledge base manager instance
def get_knowledge_manager(db: Session) -> KnowledgeBaseManager:
    """Get knowledge base manager instance"""
    return KnowledgeBaseManager(db)
