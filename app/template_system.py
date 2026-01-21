"""
Incident templates system for standardized incident reporting
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class TemplateCategory(Enum):
    """Template categories"""
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    DATABASE = "database"
    NETWORK = "network"
    SECURITY = "security"
    PERFORMANCE = "performance"
    AVAILABILITY = "availability"
    HUMAN_ERROR = "human_error"


@dataclass
class TemplateField:
    """Template field definition"""
    name: str
    label: str
    type: str  # text, textarea, select, multiselect, datetime, number
    required: bool = True
    options: Optional[List[str]] = None
    default_value: Optional[str] = None
    placeholder: Optional[str] = None
    validation: Optional[Dict] = None


@dataclass
class IncidentTemplate:
    """Incident template definition"""
    id: str
    name: str
    description: str
    category: TemplateCategory
    severity: str
    fields: List[TemplateField]
    suggested_actions: List[str]
    contributing_factors: List[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime


class TemplateManager:
    """Manages incident templates"""
    
    def __init__(self):
        self.templates: Dict[str, IncidentTemplate] = {}
        self.templates_dir = "app/templates/incidents"
        self._load_default_templates()
        self._load_custom_templates()
    
    def _load_default_templates(self):
        """Load default incident templates"""
        default_templates = [
            {
                "id": "database_outage",
                "name": "Database Outage",
                "description": "Template for database-related incidents",
                "category": TemplateCategory.DATABASE,
                "severity": "high",
                "fields": [
                    TemplateField(
                        name="title",
                        label="Incident Title",
                        type="text",
                        placeholder="Brief description of the database issue"
                    ),
                    TemplateField(
                        name="database_type",
                        label="Database Type",
                        type="select",
                        options=["PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Other"],
                        required=True
                    ),
                    TemplateField(
                        name="issue_type",
                        label="Issue Type",
                        type="select",
                        options=["Connection Pool Exhaustion", "Slow Queries", "Deadlock", "Replication Lag", "Data Corruption", "Other"],
                        required=True
                    ),
                    TemplateField(
                        name="affected_databases",
                        label="Affected Databases",
                        type="multiselect",
                        options=["Primary", "Replica", "Cache", "Analytics", "Logging"],
                        required=True
                    ),
                    TemplateField(
                        name="error_rate",
                        label="Error Rate (%)",
                        type="number",
                        placeholder="Percentage of failed queries"
                    ),
                    TemplateField(
                        name="impact_description",
                        label="Impact Description",
                        type="textarea",
                        placeholder="Describe the impact on services and users"
                    ),
                    TemplateField(
                        name="timeline",
                        label="Timeline",
                        type="textarea",
                        placeholder="Chronological events during the incident"
                    )
                ],
                "suggested_actions": [
                    "Review database connection pooling configuration",
                    "Analyze slow query logs and optimize indexes",
                    "Implement database monitoring and alerting",
                    "Review failover and replication setup",
                    "Document database capacity planning"
                ],
                "contributing_factors": [
                    "Insufficient connection pool size",
                    "Missing database monitoring",
                    "Lack of query optimization",
                    "Inadequate capacity planning",
                    "Missing failover mechanisms"
                ],
                "tags": ["database", "outage", "performance"],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "id": "application_crash",
                "name": "Application Crash",
                "description": "Template for application crash incidents",
                "category": TemplateCategory.APPLICATION,
                "severity": "high",
                "fields": [
                    TemplateField(
                        name="title",
                        label="Incident Title",
                        type="text",
                        placeholder="Brief description of the application crash"
                    ),
                    TemplateField(
                        name="application_name",
                        label="Application Name",
                        type="text",
                        required=True
                    ),
                    TemplateField(
                        name="crash_type",
                        label="Crash Type",
                        type="select",
                        options=["OutOfMemoryError", "NullPointerException", "StackOverflow", "Segmentation Fault", "Other"],
                        required=True
                    ),
                    TemplateField(
                        name="error_logs",
                        label="Error Logs",
                        type="textarea",
                        placeholder="Relevant error messages and stack traces"
                    ),
                    TemplateField(
                        name="affected_endpoints",
                        label="Affected Endpoints",
                        type="multiselect",
                        options=["API", "Web UI", "Background Jobs", "WebSocket", "Other"],
                        required=True
                    ),
                    TemplateField(
                        name="memory_usage",
                        label="Memory Usage at Crash",
                        type="text",
                        placeholder="Memory utilization percentage or absolute value"
                    ),
                    TemplateField(
                        name="recent_deployments",
                        label="Recent Deployments",
                        type="textarea",
                        placeholder="List recent code changes or deployments"
                    )
                ],
                "suggested_actions": [
                    "Analyze application logs and stack traces",
                    "Review memory usage patterns and leaks",
                    "Implement better error handling",
                    "Add comprehensive monitoring",
                    "Review deployment process and rollback procedures"
                ],
                "contributing_factors": [
                    "Memory leak in application code",
                    "Insufficient memory allocation",
                    "Poor error handling",
                    "Missing monitoring and alerting",
                    "Inadequate testing before deployment"
                ],
                "tags": ["application", "crash", "memory"],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "id": "network_connectivity",
                "name": "Network Connectivity Issue",
                "description": "Template for network-related incidents",
                "category": TemplateCategory.NETWORK,
                "severity": "medium",
                "fields": [
                    TemplateField(
                        name="title",
                        label="Incident Title",
                        type="text",
                        placeholder="Brief description of the network issue"
                    ),
                    TemplateField(
                        name="network_area",
                        label="Network Area",
                        type="select",
                        options=["Internal Network", "External Connectivity", "Load Balancer", "CDN", "DNS", "VPN"],
                        required=True
                    ),
                    TemplateField(
                        name="issue_type",
                        label="Issue Type",
                        type="select",
                        options=["High Latency", "Packet Loss", "Connection Timeout", "DNS Resolution", "Bandwidth Saturation", "Other"],
                        required=True
                    ),
                    TemplateField(
                        name="affected_services",
                        label="Affected Services",
                        type="multiselect",
                        options=["Web Servers", "API Servers", "Database", "Cache", "External APIs", "Monitoring"],
                        required=True
                    ),
                    TemplateField(
                        name="latency_increase",
                        label="Latency Increase",
                        type="text",
                        placeholder="e.g., 50ms to 500ms"
                    ),
                    TemplateField(
                        name="packet_loss_rate",
                        label="Packet Loss Rate (%)",
                        type="number",
                        placeholder="Percentage of packets lost"
                    ),
                    TemplateField(
                        name="network_diagnostics",
                        label="Network Diagnostics",
                        type="textarea",
                        placeholder="Ping, traceroute, and other diagnostic results"
                    )
                ],
                "suggested_actions": [
                    "Analyze network traffic patterns",
                    "Check network device configurations",
                    "Review load balancer settings",
                    "Implement network monitoring",
                    "Document network topology and dependencies"
                ],
                "contributing_factors": [
                    "Network device misconfiguration",
                    "Insufficient bandwidth",
                    "Load balancer issues",
                    "DNS configuration problems",
                    "Missing network monitoring"
                ],
                "tags": ["network", "connectivity", "latency"],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "id": "security_incident",
                "name": "Security Incident",
                "description": "Template for security-related incidents",
                "category": TemplateCategory.SECURITY,
                "severity": "critical",
                "fields": [
                    TemplateField(
                        name="title",
                        label="Incident Title",
                        type="text",
                        placeholder="Brief description of the security incident"
                    ),
                    TemplateField(
                        name="incident_type",
                        label="Incident Type",
                        type="select",
                        options=["Unauthorized Access", "Data Breach", "DDoS Attack", "Malware", "Phishing", "Vulnerability Exploit", "Other"],
                        required=True
                    ),
                    TemplateField(
                        name="severity_level",
                        label="Security Severity",
                        type="select",
                        options=["Critical", "High", "Medium", "Low"],
                        required=True
                    ),
                    TemplateField(
                        name="affected_systems",
                        label="Affected Systems",
                        type="multiselect",
                        options=["Web Servers", "Database", "Authentication", "API", "Customer Data", "Internal Systems"],
                        required=True
                    ),
                    TemplateField(
                        name="data_compromised",
                        label="Data Compromised",
                        type="select",
                        options=["None", "Personal Data", "Financial Data", "Health Data", "Intellectual Property", "Other"],
                        required=True
                    ),
                    TemplateField(
                        name="attack_vector",
                        label="Attack Vector",
                        type="textarea",
                        placeholder="How the attacker gained access"
                    ),
                    TemplateField(
                        name="immediate_actions",
                        label="Immediate Actions Taken",
                        type="textarea",
                        placeholder="Steps taken to contain the incident"
                    ),
                    TemplateField(
                        name="forensic_evidence",
                        label="Forensic Evidence",
                        type="textarea",
                        placeholder="Logs, screenshots, and other evidence collected"
                    )
                ],
                "suggested_actions": [
                    "Conduct security audit and penetration testing",
                    "Review and update security policies",
                    "Implement security monitoring and alerting",
                    "Provide security awareness training",
                    "Document incident response procedures"
                ],
                "contributing_factors": [
                    "Weak authentication mechanisms",
                    "Missing security patches",
                    "Insufficient security monitoring",
                    "Lack of employee training",
                    "Inadequate access controls"
                ],
                "tags": ["security", "breach", "attack"],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "id": "performance_degradation",
                "name": "Performance Degradation",
                "description": "Template for performance-related incidents",
                "category": TemplateCategory.PERFORMANCE,
                "severity": "medium",
                "fields": [
                    TemplateField(
                        name="title",
                        label="Incident Title",
                        type="text",
                        placeholder="Brief description of the performance issue"
                    ),
                    TemplateField(
                        name="performance_metric",
                        label="Affected Metric",
                        type="select",
                        options=["Response Time", "Throughput", "CPU Usage", "Memory Usage", "Disk I/O", "Network I/O"],
                        required=True
                    ),
                    TemplateField(
                        name="baseline_value",
                        label="Baseline Value",
                        type="text",
                        placeholder="Normal performance value"
                    ),
                    TemplateField(
                        name="degraded_value",
                        label="Degraded Value",
                        type="text",
                        placeholder="Current degraded performance value"
                    ),
                    TemplateField(
                        name="affected_components",
                        label="Affected Components",
                        type="multiselect",
                        options=["Web Servers", "Application Servers", "Database", "Cache", "Load Balancer", "CDN"],
                        required=True
                    ),
                    TemplateField(
                        name="user_impact",
                        label="User Impact",
                        type="select",
                        options=["None", "Minor", "Moderate", "Severe", "Critical"],
                        required=True
                    ),
                    TemplateField(
                        name="performance_analysis",
                        label="Performance Analysis",
                        type="textarea",
                        placeholder="Analysis of performance metrics and bottlenecks"
                    )
                ],
                "suggested_actions": [
                    "Analyze performance metrics and bottlenecks",
                    "Optimize database queries and indexes",
                    "Implement caching strategies",
                    "Review application architecture",
                    "Add performance monitoring and alerting"
                ],
                "contributing_factors": [
                    "Inefficient code or algorithms",
                    "Database performance issues",
                    "Insufficient resources",
                    "Poor caching strategy",
                    "Missing performance monitoring"
                ],
                "tags": ["performance", "degradation", "optimization"],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]
        
        for template_data in default_templates:
            template = IncidentTemplate(**template_data)
            self.templates[template.id] = template
    
    def _load_custom_templates(self):
        """Load custom templates from file system"""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            return
        
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(self.templates_dir, filename), 'r') as f:
                        template_data = json.load(f)
                    
                    # Convert string category back to enum
                    if 'category' in template_data:
                        template_data['category'] = TemplateCategory(template_data['category'])
                    
                    # Convert field data to TemplateField objects
                    if 'fields' in template_data:
                        template_data['fields'] = [
                            TemplateField(**field) for field in template_data['fields']
                        ]
                    
                    # Convert datetime strings back to datetime objects
                    if 'created_at' in template_data:
                        template_data['created_at'] = datetime.fromisoformat(template_data['created_at'])
                    if 'updated_at' in template_data:
                        template_data['updated_at'] = datetime.fromisoformat(template_data['updated_at'])
                    
                    template = IncidentTemplate(**template_data)
                    self.templates[template.id] = template
                    
                except Exception as e:
                    print(f"Error loading template {filename}: {e}")
    
    def get_template(self, template_id: str) -> Optional[IncidentTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def get_templates_by_category(self, category: TemplateCategory) -> List[IncidentTemplate]:
        """Get all templates in a category"""
        return [template for template in self.templates.values() if template.category == category]
    
    def get_all_templates(self) -> List[IncidentTemplate]:
        """Get all templates"""
        return list(self.templates.values())
    
    def create_template(self, template_data: Dict) -> IncidentTemplate:
        """Create a new template"""
        template_id = template_data.get('id')
        if not template_id:
            template_id = f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            template_data['id'] = template_id
        
        # Convert field data to TemplateField objects
        if 'fields' in template_data:
            template_data['fields'] = [
                TemplateField(**field) for field in template_data['fields']
            ]
        
        # Convert category string to enum
        if isinstance(template_data.get('category'), str):
            template_data['category'] = TemplateCategory(template_data['category'])
        
        template_data['created_at'] = datetime.now()
        template_data['updated_at'] = datetime.now()
        
        template = IncidentTemplate(**template_data)
        self.templates[template.id] = template
        
        # Save to file system
        self._save_template(template)
        
        return template
    
    def update_template(self, template_id: str, updates: Dict) -> Optional[IncidentTemplate]:
        """Update an existing template"""
        if template_id not in self.templates:
            return None
        
        template = self.templates[template_id]
        
        # Update fields
        for key, value in updates.items():
            if hasattr(template, key):
                if key == 'category' and isinstance(value, str):
                    setattr(template, key, TemplateCategory(value))
                elif key == 'fields' and isinstance(value, list):
                    setattr(template, key, [TemplateField(**field) for field in value])
                else:
                    setattr(template, key, value)
        
        template.updated_at = datetime.now()
        
        # Save to file system
        self._save_template(template)
        
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template"""
        if template_id not in self.templates:
            return False
        
        del self.templates[template_id]
        
        # Remove from file system
        template_file = os.path.join(self.templates_dir, f"{template_id}.json")
        if os.path.exists(template_file):
            os.remove(template_file)
        
        return True
    
    def _save_template(self, template: IncidentTemplate):
        """Save template to file system"""
        os.makedirs(self.templates_dir, exist_ok=True)
        
        template_data = asdict(template)
        
        # Convert enum to string for JSON serialization
        template_data['category'] = template.category.value
        
        # Convert datetime to string for JSON serialization
        template_data['created_at'] = template.created_at.isoformat()
        template_data['updated_at'] = template.updated_at.isoformat()
        
        with open(os.path.join(self.templates_dir, f"{template.id}.json"), 'w') as f:
            json.dump(template_data, f, indent=2)
    
    def apply_template(self, template_id: str) -> Dict:
        """Apply a template and return initial incident data"""
        template = self.get_template(template_id)
        if not template:
            return {}
        
        incident_data = {
            "title": "",
            "severity": template.severity,
            "category": template.category.value,
            "contributing_factors": template.contributing_factors,
            "action_items": [
                {"title": action, "description": "", "category": "immediate", "priority": "high"}
                for action in template.suggested_actions[:3]
            ],
            "tags": template.tags
        }
        
        # Add default values from template fields
        for field in template.fields:
            if field.default_value:
                incident_data[field.name] = field.default_value
        
        return incident_data


# Global template manager instance
template_manager = TemplateManager()
