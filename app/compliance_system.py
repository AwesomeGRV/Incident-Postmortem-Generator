"""
Comprehensive audit trail and compliance reporting system
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from sqlalchemy.orm import Session
from .models import User
from .enterprise_models import Incident
from .audit import AuditLog


class AuditAction(Enum):
    """Audit action types"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    PUBLISH = "publish"
    VIEW = "view"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"
    ASSIGN = "assign"
    COMMENT = "comment"
    APPROVE = "approve"
    REJECT = "reject"


class ComplianceStandard(Enum):
    """Compliance standards"""
    SOX = "sox"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    ISO27001 = "iso27001"
    PCI_DSS = "pci_dss"
    SOC2 = "soc2"


@dataclass
class AuditEvent:
    """Audit event data structure"""
    id: Optional[str] = None
    timestamp: datetime = None
    user_id: int = None
    user_name: str = ""
    action: AuditAction = None
    resource_type: str = ""
    resource_id: str = ""
    details: Dict[str, Any] = None
    ip_address: str = ""
    user_agent: str = ""
    session_id: str = ""
    compliance_tags: List[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.details is None:
            self.details = {}
        if self.compliance_tags is None:
            self.compliance_tags = []


@dataclass
class ComplianceReport:
    """Compliance report data structure"""
    id: str
    standard: ComplianceStandard
    period_start: datetime
    period_end: datetime
    total_events: int
    compliance_score: float
    violations: List[Dict[str, Any]]
    recommendations: List[str]
    generated_at: datetime
    generated_by: str


class AuditManager:
    """Manages audit trails and compliance reporting"""
    
    def __init__(self, db: Session):
        self.db = db
        self.audit_log_file = "logs/audit.jsonl"
        self._ensure_audit_directory()
    
    def _ensure_audit_directory(self):
        """Ensure audit directory exists"""
        os.makedirs("logs", exist_ok=True)
    
    def log_event(self, event: AuditEvent) -> bool:
        """Log an audit event"""
        try:
            # Create database audit log entry
            db_audit = AuditLog(
                user_id=event.user_id,
                action=event.action.value,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                details=json.dumps(event.details),
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                session_id=event.session_id,
                timestamp=event.timestamp
            )
            
            self.db.add(db_audit)
            self.db.commit()
            
            # Also log to file for backup and analysis
            event.id = str(db_audit.id)
            self._log_to_file(event)
            
            return True
        except Exception as e:
            print(f"Failed to log audit event: {e}")
            self.db.rollback()
            return False
    
    def _log_to_file(self, event: AuditEvent):
        """Log event to file"""
        try:
            with open(self.audit_log_file, 'a') as f:
                event_data = asdict(event)
                event_data['timestamp'] = event.timestamp.isoformat()
                event_data['action'] = event.action.value
                f.write(json.dumps(event_data) + '\n')
        except Exception as e:
            print(f"Failed to write audit log to file: {e}")
    
    def get_audit_trail(self, 
                      resource_type: Optional[str] = None,
                      resource_id: Optional[str] = None,
                      user_id: Optional[int] = None,
                      action: Optional[AuditAction] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      limit: int = 100) -> List[AuditEvent]:
        """Get audit trail with filters"""
        try:
            query = self.db.query(AuditLog)
            
            if resource_type:
                query = query.filter(AuditLog.resource_type == resource_type)
            if resource_id:
                query = query.filter(AuditLog.resource_id == resource_id)
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            if action:
                query = query.filter(AuditLog.action == action.value)
            if start_date:
                query = query.filter(AuditLog.timestamp >= start_date)
            if end_date:
                query = query.filter(AuditLog.timestamp <= end_date)
            
            audit_logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
            
            events = []
            for log in audit_logs:
                user = self.db.query(User).filter(User.id == log.user_id).first()
                event = AuditEvent(
                    id=str(log.id),
                    timestamp=log.timestamp,
                    user_id=log.user_id,
                    user_name=user.full_name if user else "Unknown",
                    action=AuditAction(log.action),
                    resource_type=log.resource_type,
                    resource_id=log.resource_id,
                    details=json.loads(log.details) if log.details else {},
                    ip_address=log.ip_address,
                    user_agent=log.user_agent,
                    session_id=log.session_id
                )
                events.append(event)
            
            return events
        except Exception as e:
            print(f"Failed to get audit trail: {e}")
            return []
    
    def generate_compliance_report(self, 
                                standard: ComplianceStandard,
                                period_start: datetime,
                                period_end: datetime,
                                generated_by: str) -> ComplianceReport:
        """Generate compliance report for a specific standard"""
        try:
            # Get all audit events in the period
            events = self.get_audit_trail(
                start_date=period_start,
                end_date=period_end,
                limit=10000
            )
            
            # Apply standard-specific rules
            violations = []
            compliance_score = 100.0
            
            if standard == ComplianceStandard.GDPR:
                violations, score = self._check_gdpr_compliance(events)
            elif standard == ComplianceStandard.SOX:
                violations, score = self._check_sox_compliance(events)
            elif standard == ComplianceStandard.HIPAA:
                violations, score = self._check_hipaa_compliance(events)
            elif standard == ComplianceStandard.ISO27001:
                violations, score = self._check_iso27001_compliance(events)
            elif standard == ComplianceStandard.PCI_DSS:
                violations, score = self._check_pci_dss_compliance(events)
            elif standard == ComplianceStandard.SOC2:
                violations, score = self._check_soc2_compliance(events)
            else:
                violations, score = [], 100.0
            
            compliance_score = score
            
            # Generate recommendations
            recommendations = self._generate_recommendations(standard, violations)
            
            report = ComplianceReport(
                id=f"{standard.value}_{period_start.strftime('%Y%m%d')}",
                standard=standard,
                period_start=period_start,
                period_end=period_end,
                total_events=len(events),
                compliance_score=compliance_score,
                violations=violations,
                recommendations=recommendations,
                generated_at=datetime.now(),
                generated_by=generated_by
            )
            
            # Save report
            self._save_compliance_report(report)
            
            return report
            
        except Exception as e:
            print(f"Failed to generate compliance report: {e}")
            raise
    
    def _check_gdpr_compliance(self, events: List[AuditEvent]) -> tuple:
        """Check GDPR compliance"""
        violations = []
        score = 100.0
        
        # Check for data access logging
        data_access_events = [e for e in events if e.resource_type in ["user_data", "personal_data"]]
        if not data_access_events:
            violations.append({
                "type": "missing_access_logs",
                "description": "No data access events logged",
                "severity": "high",
                "recommendation": "Ensure all personal data access is logged"
            })
            score -= 20
        
        # Check for data retention
        delete_events = [e for e in events if e.action == AuditAction.DELETE]
        if len(delete_events) == 0:
            violations.append({
                "type": "no_data_deletion",
                "description": "No data deletion events found",
                "severity": "medium",
                "recommendation": "Implement data retention policies"
            })
            score -= 10
        
        # Check for consent management
        consent_events = [e for e in events if "consent" in e.details.get("tags", [])]
        if len(consent_events) == 0:
            violations.append({
                "type": "missing_consent_logs",
                "description": "No consent management events logged",
                "severity": "high",
                "recommendation": "Log all consent-related activities"
            })
            score -= 15
        
        return violations, max(0, score)
    
    def _check_sox_compliance(self, events: List[AuditEvent]) -> tuple:
        """Check SOX compliance"""
        violations = []
        score = 100.0
        
        # Check for financial data access
        financial_events = [e for e in events if "financial" in e.resource_type]
        if not financial_events:
            violations.append({
                "type": "missing_financial_logs",
                "description": "No financial data access logged",
                "severity": "critical",
                "recommendation": "Ensure all financial data access is logged"
            })
            score -= 30
        
        # Check for segregation of duties
        user_actions = {}
        for event in events:
            if event.user_id not in user_actions:
                user_actions[event.user_id] = set()
            user_actions[event.user_id].add(event.action.value)
        
        for user_id, actions in user_actions.items():
            if len(actions) > 5:  # User has too many different action types
                violations.append({
                    "type": "segregation_of_duties",
                    "description": f"User {user_id} has too many permissions",
                    "severity": "high",
                    "recommendation": "Review user permissions and implement segregation of duties"
                })
                score -= 10
        
        return violations, max(0, score)
    
    def _check_hipaa_compliance(self, events: List[AuditEvent]) -> tuple:
        """Check HIPAA compliance"""
        violations = []
        score = 100.0
        
        # Check for PHI access logging
        phi_events = [e for e in events if "phi" in e.resource_type or "health" in e.resource_type]
        if not phi_events:
            violations.append({
                "type": "missing_phi_logs",
                "description": "No PHI access events logged",
                "severity": "critical",
                "recommendation": "Ensure all PHI access is logged"
            })
            score -= 25
        
        # Check for minimum necessary access
        for event in phi_events:
            if event.details.get("access_level") == "full":
                violations.append({
                    "type": "excessive_access",
                    "description": f"Full PHI access by user {event.user_name}",
                    "severity": "medium",
                    "recommendation": "Implement minimum necessary access principle"
                })
                score -= 5
        
        return violations, max(0, score)
    
    def _check_iso27001_compliance(self, events: List[AuditEvent]) -> tuple:
        """Check ISO 27001 compliance"""
        violations = []
        score = 100.0
        
        # Check for security incident logging
        security_events = [e for e in events if "security" in e.resource_type or e.action == AuditAction.DELETE]
        if len(security_events) < len(events) * 0.1:  # Less than 10% security events
            violations.append({
                "type": "insufficient_security_logging",
                "description": "Insufficient security event logging",
                "severity": "medium",
                "recommendation": "Increase security event logging coverage"
            })
            score -= 15
        
        # Check for access control
        access_events = [e for e in events if e.action in [AuditAction.LOGIN, AuditAction.LOGOUT]]
        if len(access_events) == 0:
            violations.append({
                "type": "missing_access_control_logs",
                "description": "No access control events logged",
                "severity": "high",
                "recommendation": "Log all access control events"
            })
            score -= 20
        
        return violations, max(0, score)
    
    def _check_pci_dss_compliance(self, events: List[AuditEvent]) -> tuple:
        """Check PCI DSS compliance"""
        violations = []
        score = 100.0
        
        # Check for cardholder data access
        card_events = [e for e in events if "card" in e.resource_type or "payment" in e.resource_type]
        if not card_events:
            violations.append({
                "type": "missing_card_data_logs",
                "description": "No cardholder data access logged",
                "severity": "critical",
                "recommendation": "Ensure all cardholder data access is logged"
            })
            score -= 35
        
        # Check for encryption usage
        for event in events:
            if "card" in event.resource_type and not event.details.get("encrypted"):
                violations.append({
                    "type": "unencrypted_card_data",
                    "description": f"Unencrypted card data access by {event.user_name}",
                    "severity": "critical",
                    "recommendation": "Ensure all cardholder data is encrypted"
                })
                score -= 20
        
        return violations, max(0, score)
    
    def _check_soc2_compliance(self, events: List[AuditEvent]) -> tuple:
        """Check SOC 2 compliance"""
        violations = []
        score = 100.0
        
        # Check for system change logging
        change_events = [e for e in events if e.action in [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.DELETE]]
        if len(change_events) == 0:
            violations.append({
                "type": "missing_change_logs",
                "description": "No system change events logged",
                "severity": "high",
                "recommendation": "Log all system changes"
            })
            score -= 25
        
        # Check for user access reviews
        review_events = [e for e in events if "access_review" in e.details.get("tags", [])]
        if len(review_events) == 0:
            violations.append({
                "type": "missing_access_reviews",
                "description": "No access review events logged",
                "severity": "medium",
                "recommendation": "Conduct regular access reviews"
            })
            score -= 15
        
        return violations, max(0, score)
    
    def _generate_recommendations(self, standard: ComplianceStandard, violations: List[Dict]) -> List[str]:
        """Generate recommendations based on violations"""
        recommendations = []
        
        for violation in violations:
            recommendations.append(violation.get("recommendation", ""))
        
        # Add standard-specific recommendations
        if standard == ComplianceStandard.GDPR:
            recommendations.extend([
                "Implement privacy by design principles",
                "Conduct regular data protection impact assessments",
                "Establish data breach notification procedures"
            ])
        elif standard == ComplianceStandard.SOX:
            recommendations.extend([
                "Implement robust internal controls",
                "Conduct regular financial statement audits",
                "Maintain proper documentation retention"
            ])
        elif standard == ComplianceStandard.HIPAA:
            recommendations.extend([
                "Implement comprehensive security awareness training",
                "Conduct regular risk assessments",
                "Establish business associate agreements"
            ])
        
        return list(set(recommendations))  # Remove duplicates
    
    def _save_compliance_report(self, report: ComplianceReport):
        """Save compliance report to file"""
        try:
            os.makedirs("reports/compliance", exist_ok=True)
            
            report_data = asdict(report)
            report_data['standard'] = report.standard.value
            report_data['period_start'] = report.period_start.isoformat()
            report_data['period_end'] = report.period_end.isoformat()
            report_data['generated_at'] = report.generated_at.isoformat()
            
            filename = f"reports/compliance/{report.id}.json"
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2)
                
        except Exception as e:
            print(f"Failed to save compliance report: {e}")
    
    def get_compliance_reports(self, standard: Optional[ComplianceStandard] = None) -> List[ComplianceReport]:
        """Get all compliance reports"""
        try:
            reports_dir = "reports/compliance"
            if not os.path.exists(reports_dir):
                return []
            
            reports = []
            for filename in os.listdir(reports_dir):
                if filename.endswith('.json'):
                    with open(os.path.join(reports_dir, filename), 'r') as f:
                        report_data = json.load(f)
                    
                    # Filter by standard if specified
                    if standard and report_data['standard'] != standard.value:
                        continue
                    
                    report = ComplianceReport(
                        id=report_data['id'],
                        standard=ComplianceStandard(report_data['standard']),
                        period_start=datetime.fromisoformat(report_data['period_start']),
                        period_end=datetime.fromisoformat(report_data['period_end']),
                        total_events=report_data['total_events'],
                        compliance_score=report_data['compliance_score'],
                        violations=report_data['violations'],
                        recommendations=report_data['recommendations'],
                        generated_at=datetime.fromisoformat(report_data['generated_at']),
                        generated_by=report_data['generated_by']
                    )
                    reports.append(report)
            
            return sorted(reports, key=lambda r: r.generated_at, reverse=True)
            
        except Exception as e:
            print(f"Failed to get compliance reports: {e}")
            return []
    
    def export_audit_trail(self, 
                         format: str = "json",
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> str:
        """Export audit trail in specified format"""
        try:
            events = self.get_audit_trail(
                start_date=start_date,
                end_date=end_date,
                limit=10000
            )
            
            if format == "json":
                return json.dumps([asdict(event) for event in events], indent=2, default=str)
            elif format == "csv":
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow([
                    'timestamp', 'user_id', 'user_name', 'action', 
                    'resource_type', 'resource_id', 'ip_address', 'details'
                ])
                
                # Write events
                for event in events:
                    writer.writerow([
                        event.timestamp.isoformat(),
                        event.user_id,
                        event.user_name,
                        event.action.value,
                        event.resource_type,
                        event.resource_id,
                        event.ip_address,
                        json.dumps(event.details)
                    ])
                
                return output.getvalue()
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            print(f"Failed to export audit trail: {e}")
            raise


# Global audit manager instance
def get_audit_manager(db: Session) -> AuditManager:
    """Get audit manager instance"""
    return AuditManager(db)
