from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from .enterprise_models import (
    Incident, IncidentStatus, User, AuditLog, AuditAction,
    SLAMetrics, Notification
)
from .models import IncidentInput, PostmortemOutput
from .generator import PostmortemGenerator
from .audit import AuditLogger
from .notifications import AlertManager
from .analytics import AnalyticsService


class IncidentService:
    """Enterprise incident management service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.generator = PostmortemGenerator()
        self.audit_logger = AuditLogger(db)
        self.alert_manager = AlertManager(db)
        self.analytics_service = AnalyticsService(db)
    
    def create_incident(
        self,
        incident_data: IncidentInput,
        user: User,
        request=None
    ) -> Incident:
        """Create a new incident"""
        
        # Generate postmortem
        postmortem = self.generator.generate_postmortem(incident_data)
        
        # Create incident record
        incident = Incident(
            incident_id=postmortem.incident_id,
            title=postmortem.title,
            description=incident_data.description,
            severity=postmortem.severity.value,
            start_time=postmortem.start_time,
            end_time=postmortem.end_time,
            duration_minutes=postmortem.duration_minutes,
            timeline=[event.dict() for event in postmortem.timeline],
            alerts=[alert.dict() for alert in incident_data.alerts],
            impact=[impact.dict() for impact in postmortem.impact],
            contributing_factors=[factor.dict() for factor in postmortem.contributing_factors],
            action_items=[item.dict() for item in postmortem.action_items],
            what_went_well=postmortem.what_went_well,
            what_went_wrong=postmortem.what_went_wrong,
            executive_summary=postmortem.executive_summary,
            lessons_learned=postmortem.lessons_learned,
            next_steps=postmortem.next_steps,
            created_by=user.id,
            status=IncidentStatus.DRAFT
        )
        
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        
        # Log creation
        self.audit_logger.log_action(
            user=user,
            action=AuditAction.CREATE,
            incident_id=incident.id,
            details={"incident_id": incident.incident_id},
            request=request
        )
        
        # Check for alerts
        self.alert_manager.check_and_send_alerts()
        
        # Record analytics
        self.analytics_service.record_metric(
            "incident_created",
            1.0,
            {"severity": incident.severity, "user_id": user.id}
        )
        
        return incident
    
    def update_incident(
        self,
        incident_id: int,
        incident_data: IncidentInput,
        user: User,
        request=None
    ) -> Optional[Incident]:
        """Update an existing incident"""
        
        incident = self.db.query(Incident).filter(
            Incident.id == incident_id
        ).first()
        
        if not incident:
            return None
        
        # Check permissions
        if user.role.value not in ["admin", "editor"] and incident.created_by != user.id:
            raise PermissionError("Insufficient permissions to update this incident")
        
        # Generate updated postmortem
        postmortem = self.generator.generate_postmortem(incident_data)
        
        # Update incident
        incident.title = postmortem.title
        incident.description = incident_data.description
        incident.severity = postmortem.severity.value
        incident.start_time = postmortem.start_time
        incident.end_time = postmortem.end_time
        incident.duration_minutes = postmortem.duration_minutes
        incident.timeline = [event.dict() for event in postmortem.timeline]
        incident.alerts = [alert.dict() for alert in incident_data.alerts]
        incident.impact = [impact.dict() for impact in postmortem.impact]
        incident.contributing_factors = [factor.dict() for factor in postmortem.contributing_factors]
        incident.action_items = [item.dict() for item in postmortem.action_items]
        incident.what_went_well = postmortem.what_went_well
        incident.what_went_wrong = postmortem.what_went_wrong
        incident.executive_summary = postmortem.executive_summary
        incident.lessons_learned = postmortem.lessons_learned
        incident.next_steps = postmortem.next_steps
        
        self.db.commit()
        
        # Log update
        self.audit_logger.log_action(
            user=user,
            action=AuditAction.UPDATE,
            incident_id=incident.id,
            details={"incident_id": incident.incident_id},
            request=request
        )
        
        return incident
    
    def publish_incident(
        self,
        incident_id: int,
        user: User,
        request=None
    ) -> Optional[Incident]:
        """Publish an incident"""
        
        incident = self.db.query(Incident).filter(
            Incident.id == incident_id
        ).first()
        
        if not incident:
            return None
        
        # Check permissions
        if user.role.value not in ["admin", "editor"]:
            raise PermissionError("Insufficient permissions to publish incidents")
        
        incident.status = IncidentStatus.PUBLISHED
        incident.published_at = datetime.utcnow()
        
        self.db.commit()
        
        # Log publication
        self.audit_logger.log_action(
            user=user,
            action=AuditAction.UPDATE,
            incident_id=incident.id,
            details={
                "incident_id": incident.incident_id,
                "status": "published"
            },
            request=request
        )
        
        # Record analytics
        self.analytics_service.record_metric(
            "incident_published",
            1.0,
            {"severity": incident.severity, "user_id": user.id}
        )
        
        return incident
    
    def delete_incident(
        self,
        incident_id: int,
        user: User,
        request=None
    ) -> bool:
        """Delete an incident"""
        
        incident = self.db.query(Incident).filter(
            Incident.id == incident_id
        ).first()
        
        if not incident:
            return False
        
        # Check permissions
        if user.role.value != "admin" and incident.created_by != user.id:
            raise PermissionError("Insufficient permissions to delete this incident")
        
        incident_id_str = incident.incident_id
        
        self.db.delete(incident)
        self.db.commit()
        
        # Log deletion
        self.audit_logger.log_action(
            user=user,
            action=AuditAction.DELETE,
            incident_id=incident_id,
            details={"incident_id": incident_id_str},
            request=request
        )
        
        return True
    
    def get_incident(
        self,
        incident_id: int,
        user: User
    ) -> Optional[Incident]:
        """Get a specific incident"""
        
        incident = self.db.query(Incident).filter(
            Incident.id == incident_id
        ).first()
        
        if not incident:
            return None
        
        # Check permissions
        if user.role.value == "viewer" and incident.status != IncidentStatus.PUBLISHED:
            if incident.created_by != user.id:
                return None
        
        # Log view
        self.audit_logger.log_action(
            user=user,
            action=AuditAction.VIEW,
            incident_id=incident.id
        )
        
        return incident
    
    def search_incidents(
        self,
        user: User,
        query: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        created_by: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Search incidents with advanced filtering"""
        
        # Build base query
        base_query = self.db.query(Incident)
        
        # Apply user permissions
        if user.role.value == "viewer":
            base_query = base_query.filter(
                or_(
                    Incident.status == IncidentStatus.PUBLISHED,
                    Incident.created_by == user.id
                )
            )
        
        # Apply filters
        if query:
            base_query = base_query.filter(
                or_(
                    Incident.title.ilike(f"%{query}%"),
                    Incident.description.ilike(f"%{query}%"),
                    Incident.executive_summary.ilike(f"%{query}%")
                )
            )
        
        if severity:
            base_query = base_query.filter(Incident.severity == severity)
        
        if status:
            base_query = base_query.filter(Incident.status == IncidentStatus(status))
        
        if start_date:
            base_query = base_query.filter(Incident.created_at >= start_date)
        
        if end_date:
            base_query = base_query.filter(Incident.created_at <= end_date)
        
        if created_by:
            base_query = base_query.filter(Incident.created_by == created_by)
        
        # Get total count
        total_count = base_query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        incidents = base_query.order_by(desc(Incident.created_at)).offset(offset).limit(page_size).all()
        
        return {
            "incidents": incidents,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    
    def get_incident_history(
        self,
        incident_id: int,
        user: User
    ) -> List[AuditLog]:
        """Get incident audit history"""
        
        # Check if user can access this incident
        incident = self.get_incident(incident_id, user)
        if not incident:
            return []
        
        return self.db.query(AuditLog).filter(
            AuditLog.incident_id == incident_id
        ).order_by(desc(AuditLog.timestamp)).all()
    
    def calculate_sla_metrics(self, incident: Incident):
        """Calculate and store SLA metrics for an incident"""
        
        # Define SLA targets (could be configurable)
        sla_targets = {
            "response_time": {
                "critical": 15,  # minutes
                "high": 30,
                "medium": 60,
                "low": 120
            },
            "resolution_time": {
                "critical": 240,  # 4 hours
                "high": 480,    # 8 hours
                "medium": 1440,  # 24 hours
                "low": 2880     # 48 hours
            }
        }
        
        severity = incident.severity
        duration = incident.duration_minutes or 0
        
        # Calculate response time SLA
        response_target = sla_targets["response_time"].get(severity, 60)
        response_achieved = duration <= response_target
        response_breach = max(0, duration - response_target) if not response_achieved else 0
        
        response_sla = SLAMetrics(
            incident_id=incident.id,
            sla_type="response_time",
            target_minutes=response_target,
            actual_minutes=duration,
            achieved=response_achieved,
            breach_minutes=response_breach
        )
        
        # Calculate resolution time SLA
        resolution_target = sla_targets["resolution_time"].get(severity, 1440)
        resolution_achieved = duration <= resolution_target
        resolution_breach = max(0, duration - resolution_target) if not resolution_achieved else 0
        
        resolution_sla = SLAMetrics(
            incident_id=incident.id,
            sla_type="resolution_time",
            target_minutes=resolution_target,
            actual_minutes=duration,
            achieved=resolution_achieved,
            breach_minutes=resolution_breach
        )
        
        self.db.add(response_sla)
        self.db.add(resolution_sla)
        self.db.commit()
        
        # Record SLA metrics
        self.analytics_service.record_metric(
            "sla_compliance",
            1.0 if response_achieved and resolution_achieved else 0.0,
            {
                "severity": severity,
                "response_achieved": response_achieved,
                "resolution_achieved": resolution_achieved
            }
        )
