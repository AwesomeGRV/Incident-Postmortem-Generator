import smtplib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from sqlalchemy.orm import Session

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .enterprise_models import Notification, NotificationType, Incident
from config import Config


class NotificationService:
    """Enterprise notification service with multiple channels"""
    
    def __init__(self, db: Session):
        self.db = db
        self.smtp_server = None
        self.slack_client = None
        
        # Initialize email server
        if Config.SMTP_SERVER:
            self.smtp_server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
            if Config.SMTP_USE_TLS:
                self.smtp_server.starttls()
            if Config.SMTP_USERNAME and Config.SMTP_PASSWORD:
                self.smtp_server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        
        # Initialize Slack client
        if Config.SLACK_BOT_TOKEN:
            self.slack_client = WebClient(token=Config.SLACK_BOT_TOKEN)
    
    def send_incident_notification(
        self,
        incident: Incident,
        notification_type: NotificationType,
        recipients: List[str],
        message: str,
        subject: Optional[str] = None
    ):
        """Send notification for incident"""
        
        for recipient in recipients:
            notification = Notification(
                incident_id=incident.id,
                type=notification_type,
                recipient=recipient,
                subject=subject or f"Incident Update: {incident.title}",
                message=message
            )
            
            try:
                if notification_type == NotificationType.EMAIL:
                    self._send_email(notification)
                elif notification_type == NotificationType.SLACK:
                    self._send_slack(notification)
                elif notification_type == NotificationType.WEBHOOK:
                    self._send_webhook(notification)
                
                notification.status = "sent"
                notification.sent_at = datetime.utcnow()
                
            except Exception as e:
                notification.status = "failed"
                notification.message = f"{message}\n\nError: {str(e)}"
            
            self.db.add(notification)
        
        self.db.commit()
    
    def _send_email(self, notification: Notification):
        """Send email notification"""
        if not self.smtp_server:
            raise Exception("SMTP server not configured")
        
        msg = MimeMultipart()
        msg['From'] = Config.SMTP_FROM_EMAIL
        msg['To'] = notification.recipient
        msg['Subject'] = notification.subject
        
        msg.attach(MimeText(notification.message, 'plain'))
        
        self.smtp_server.send_message(msg)
    
    def _send_slack(self, notification: Notification):
        """Send Slack notification"""
        if not self.slack_client:
            raise Exception("Slack client not configured")
        
        try:
            self.slack_client.chat_postMessage(
                channel=notification.recipient,
                text=notification.message,
                username="Incident Postmortem Bot"
            )
        except SlackApiError as e:
            raise Exception(f"Slack API error: {e.response['error']}")
    
    def _send_webhook(self, notification: Notification):
        """Send webhook notification"""
        import requests
        
        webhook_url = notification.recipient  # In this case, recipient is the webhook URL
        
        payload = {
            "incident_id": notification.incident_id,
            "subject": notification.subject,
            "message": notification.message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = requests.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()
    
    def send_sla_breach_alert(self, incident: Incident, sla_type: str, breach_minutes: int):
        """Send SLA breach notification"""
        message = f"""
SLA Breach Alert!

Incident: {incident.title}
Incident ID: {incident.incident_id}
SLA Type: {sla_type}
Breach Duration: {breach_minutes} minutes

Immediate attention required.
        """.strip()
        
        # Send to configured alert recipients
        alert_recipients = Config.SLA_ALERT_RECIPIENTS or []
        
        for recipient in alert_recipients:
            if "@" in recipient:
                self.send_incident_notification(
                    incident, NotificationType.EMAIL, [recipient], message,
                    f"SLA BREACH: {incident.title}"
                )
            elif recipient.startswith("#"):
                self.send_incident_notification(
                    incident, NotificationType.SLACK, [recipient], message,
                    f"SLA BREACH: {incident.title}"
                )
    
    def send_review_reminder(self, incident: Incident, days_overdue: int):
        """Send review reminder for draft incidents"""
        message = f"""
Review Reminder

Incident: {incident.title}
Incident ID: {incident.incident_id}
Status: Draft
Days Overdue: {days_overdue}

Please complete the postmortem review and publish.
        """.strip()
        
        # Send to incident creator
        if incident.created_by_user:
            self.send_incident_notification(
                incident, NotificationType.EMAIL,
                [incident.created_by_user.email], message,
                f"Review Required: {incident.title}"
            )


class AlertManager:
    """Manage different types of alerts and notifications"""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
    
    def check_and_send_alerts(self):
        """Check for conditions that require alerts"""
        # Check for SLA breaches
        self._check_sla_breaches()
        
        # Check for overdue reviews
        self._check_overdue_reviews()
        
        # Check for critical incidents requiring escalation
        self._check_critical_incidents()
    
    def _check_sla_breaches(self):
        """Check for SLA breaches"""
        from .enterprise_models import SLAMetrics
        
        breaches = self.db.query(SLAMetrics).filter(
            SLAMetrics.achieved == False
        ).all()
        
        for breach in breaches:
            if breach.incident:
                self.notification_service.send_sla_breach_alert(
                    breach.incident,
                    breach.sla_type,
                    breach.breach_minutes
                )
    
    def _check_overdue_reviews(self):
        """Check for incidents overdue for review"""
        from datetime import timedelta
        from .enterprise_models import IncidentStatus
        
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        overdue_incidents = self.db.query(Incident).filter(
            Incident.status == IncidentStatus.DRAFT,
            Incident.created_at < cutoff_date
        ).all()
        
        for incident in overdue_incidents:
            days_overdue = (datetime.utcnow() - incident.created_at).days
            self.notification_service.send_review_reminder(incident, days_overdue)
    
    def _check_critical_incidents(self):
        """Check for critical incidents requiring escalation"""
        from .enterprise_models import IncidentStatus
        
        critical_incidents = self.db.query(Incident).filter(
            Incident.severity == "critical",
            Incident.status == IncidentStatus.DRAFT
        ).all()
        
        for incident in critical_incidents:
            # Escalate critical incidents
            escalation_message = f"""
CRITICAL INCIDENT ESCALATION

Incident: {incident.title}
Incident ID: {incident.incident_id}
Severity: Critical
Status: Draft

Immediate management attention required.
            """.strip()
            
            # Send to escalation recipients
            escalation_recipients = Config.ESCALATION_RECIPIENTS or []
            
            for recipient in escalation_recipients:
                self.notification_service.send_incident_notification(
                    incident, NotificationType.EMAIL,
                    [recipient], escalation_message,
                    f"CRITICAL ESCALATION: {incident.title}"
                )
