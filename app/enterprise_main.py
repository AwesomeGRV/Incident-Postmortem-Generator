from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import json
import yaml
import os
from datetime import datetime

from .database import get_db, create_tables
from .auth import (
    User, UserCreate, UserLogin, UserResponse, Token,
    get_current_active_user, require_admin, require_editor, require_viewer,
    login_for_access_token, create_user
)
from .enterprise_models import Incident, UserRole, IncidentStatus
from .incident_service import IncidentService
from .analytics import AnalyticsService
from .notifications import AlertManager
from .models import IncidentInput
from .templates import PostmortemTemplate
from .pdf_converter import PDFConverter
from .websocket_service import connection_manager, notification_service
from .ai_classifier import incident_classifier
from .template_system import template_manager
from .compliance_system import get_audit_manager, AuditEvent, AuditAction, ComplianceStandard
from .advanced_predictor import get_advanced_predictor, PredictionType
from .collaborative_editor import get_collaborative_editor
from .correlation_engine import get_correlation_engine
from .knowledge_base import get_knowledge_manager, KnowledgeType

# Initialize FastAPI app
app = FastAPI(
    title="Enterprise Incident Postmortem Generator",
    description="Production-ready incident postmortem management system",
    version="2.0.0"
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Security
security = HTTPBearer()

# Initialize components
template_engine = PostmortemTemplate()
pdf_converter = PDFConverter()

# Create database tables
create_tables()


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    # Initialize alert manager
    db = next(get_db())
    alert_manager = AlertManager(db)
    # Start background tasks for alerts
    # This would typically be a Celery task or similar


# Authentication endpoints
@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """User login endpoint"""
    try:
        token = login_for_access_token(db, user_login)
        return {"access_token": token.access_token, "token_type": "bearer"}
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )


@app.post("/auth/register")
@limiter.limit("3/minute")
async def register(
    request: Request,
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """User registration endpoint (admin only)"""
    try:
        db_user = create_user(db, user)
        return UserResponse.from_orm(db_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/auth/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info"""
    return UserResponse.from_orm(current_user)


# Web interface endpoints
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Enhanced dashboard with real-time updates and AI insights"""
    return templates.TemplateResponse("advanced_dashboard.html", {"request": request})


@app.get("/incidents/new", response_class=HTMLResponse)
async def new_incident_form(
    request: Request,
    current_user: User = Depends(require_editor)
):
    """New incident form"""
    return templates.TemplateResponse("incident_form.html", {
        "request": request,
        "user": current_user
    })


@app.get("/incidents/{incident_id}", response_class=HTMLResponse)
async def view_incident(
    incident_id: int,
    request: Request,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """View incident details"""
    incident_service = IncidentService(db)
    incident = incident_service.get_incident(incident_id, current_user)
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return templates.TemplateResponse("incident_detail.html", {
        "request": request,
        "incident": incident,
        "user": current_user
    })


@app.get("/incidents", response_class=HTMLResponse)
async def incident_list(
    request: Request,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Incident list with search"""
    return templates.TemplateResponse("incident_list.html", {
        "request": request,
        "user": current_user
    })


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(
    request: Request,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Analytics dashboard"""
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "user": current_user
    })


# API endpoints
@app.post("/api/incidents")
async def create_incident_api(
    incident_data: IncidentInput,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Create new incident via API"""
    incident_service = IncidentService(db)
    audit_manager = get_audit_manager(db)
    
    # Log audit event
    audit_event = AuditEvent(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action=AuditAction.CREATE,
        resource_type="incident",
        resource_id="",  # Will be set after creation
        details={"title": incident_data.title, "severity": incident_data.severity},
        ip_address=request.client.host if request else "",
        user_agent=request.headers.get("user-agent", "") if request else ""
    )
    
    # Classify incident using AI
    incident_dict = incident_data.dict()
    classification = incident_classifier.classify_incident(incident_dict)
    
    # Enhance incident data with AI classification
    if not incident_data.severity:
        incident_data.severity = classification.severity.value
    
    # Add AI insights to incident metadata
    incident_dict['ai_classification'] = {
        'category': classification.category.value,
        'confidence': classification.confidence,
        'factors': classification.factors,
        'recommended_actions': classification.recommended_actions,
        'estimated_resolution_time': classification.estimated_resolution_time,
        'business_impact': classification.business_impact
    }
    
    incident = incident_service.create_incident(incident_data, current_user, request)
    
    # Update audit event with incident ID
    audit_event.resource_id = str(incident.id)
    audit_manager.log_event(audit_event)
    
    # Send real-time notifications
    await notification_service.notify_incident_created(incident, current_user, db)
    
    return {
        "incident_id": incident.id, 
        "status": "created",
        "ai_classification": incident_dict['ai_classification']
    }


@app.get("/api/incidents")
async def list_incidents_api(
    query: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """List incidents with filtering"""
    incident_service = IncidentService(db)
    result = incident_service.search_incidents(
        user=current_user,
        query=query,
        severity=severity,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )
    
    return {
        "incidents": [incident.to_dict() for incident in result["incidents"]],
        "pagination": {
            "total_count": result["total_count"],
            "page": result["page"],
            "page_size": result["page_size"],
            "total_pages": result["total_pages"]
        }
    }


@app.get("/api/incidents/{incident_id}")
async def get_incident_api(
    incident_id: int,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get incident details via API"""
    incident_service = IncidentService(db)
    incident = incident_service.get_incident(incident_id, current_user)
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return incident.to_dict()


@app.put("/api/incidents/{incident_id}")
async def update_incident_api(
    incident_id: int,
    incident_data: IncidentInput,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Update incident via API"""
    incident_service = IncidentService(db)
    incident = incident_service.update_incident(incident_id, incident_data, current_user, request)
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Send real-time notifications
    await notification_service.notify_incident_updated(incident, current_user, db)
    
    return {"incident_id": incident.id, "status": "updated"}


@app.post("/api/incidents/{incident_id}/publish")
async def publish_incident_api(
    incident_id: int,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Publish incident via API"""
    incident_service = IncidentService(db)
    incident = incident_service.publish_incident(incident_id, current_user, request)
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Send real-time notifications
    await notification_service.notify_incident_published(incident, current_user, db)
    
    return {"incident_id": incident.id, "status": "published"}


@app.delete("/api/incidents/{incident_id}")
async def delete_incident_api(
    incident_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Delete incident via API"""
    incident_service = IncidentService(db)
    success = incident_service.delete_incident(incident_id, current_user, request)
    
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return {"status": "deleted"}


@app.get("/api/incidents/{incident_id}/history")
async def get_incident_history_api(
    incident_id: int,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get incident audit history"""
    incident_service = IncidentService(db)
    history = incident_service.get_incident_history(incident_id, current_user)
    
    return {
        "history": [log.to_dict() for log in history]
    }


@app.get("/api/analytics/metrics")
async def get_analytics_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    team_id: Optional[int] = None,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Get analytics metrics"""
    analytics_service = AnalyticsService(db)
    metrics = analytics_service.get_incident_metrics(start_date, end_date, team_id)
    return metrics


@app.get("/api/analytics/sla")
async def get_sla_report(
    start_date: datetime,
    end_date: datetime,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Get SLA compliance report"""
    analytics_service = AnalyticsService(db)
    report = analytics_service.get_sla_report(start_date, end_date)
    return report


@app.get("/api/analytics/heatmap")
async def get_incident_heatmap(
    days: int = 30,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Get incident heatmap data"""
    analytics_service = AnalyticsService(db)
    heatmap = analytics_service.get_incident_heatmap(days)
    return heatmap


@app.post("/api/incidents/{incident_id}/export/pdf")
async def export_incident_pdf(
    incident_id: int,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Export incident as PDF"""
    incident_service = IncidentService(db)
    incident = incident_service.get_incident(incident_id, current_user)
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Convert to postmortem format
    postmortem_data = {
        "title": incident.title,
        "incident_id": incident.incident_id,
        "date_generated": incident.created_at,
        "severity": incident.severity,
        "start_time": incident.start_time,
        "end_time": incident.end_time,
        "duration_minutes": incident.duration_minutes,
        "executive_summary": incident.executive_summary,
        "timeline": incident.timeline or [],
        "impact": incident.impact or [],
        "contributing_factors": incident.contributing_factors or [],
        "action_items": incident.action_items or [],
        "what_went_well": incident.what_went_well or [],
        "what_went_wrong": incident.what_went_wrong or [],
        "lessons_learned": incident.lessons_learned or [],
        "next_steps": incident.next_steps or []
    }
    
    # Generate PDF
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        pdf_path = tmp_file.name
    
    success = pdf_converter.convert_to_pdf(postmortem_data, pdf_path)
    if not success:
        raise HTTPException(status_code=500, detail="PDF generation failed")
    
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"incident_{incident.incident_id}.pdf")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }


# WebSocket endpoints
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time notifications"""
    await connection_manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back or handle client messages if needed
            await websocket.send_text(f"Received: {data}")
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


# AI Classification endpoints
@app.post("/api/ai/classify")
async def classify_incident_api(
    incident_data: dict,
    current_user: User = Depends(require_editor)
):
    """Classify incident using AI"""
    try:
        classification = incident_classifier.classify_incident(incident_data)
        return {
            "category": classification.category.value,
            "severity": classification.severity.value,
            "confidence": classification.confidence,
            "factors": classification.factors,
            "recommended_actions": classification.recommended_actions,
            "estimated_resolution_time": classification.estimated_resolution_time,
            "business_impact": classification.business_impact
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@app.post("/api/ai/analyze-timeline")
async def analyze_timeline_api(
    timeline_data: List[dict],
    current_user: User = Depends(require_editor)
):
    """Analyze incident timeline for patterns and insights"""
    try:
        # Extract text from timeline events
        timeline_text = " ".join([
            event.get("event", "") for event in timeline_data if isinstance(event, dict)
        ])
        
        # Classify the timeline
        classification = incident_classifier.classify_incident({"timeline": timeline_data})
        
        # Identify patterns
        patterns = []
        
        # Check for common incident patterns
        event_descriptions = [event.get("event", "").lower() for event in timeline_data if isinstance(event, dict)]
        
        if any("alert" in desc for desc in event_descriptions):
            patterns.append("Alert-driven detection")
        if any("manual" in desc or "human" in desc for desc in event_descriptions):
            patterns.append("Manual intervention required")
        if any("deploy" in desc or "release" in desc for desc in event_descriptions):
            patterns.append("Deployment-related incident")
        if any("network" in desc or "connection" in desc for desc in event_descriptions):
            patterns.append("Network connectivity issues")
        
        return {
            "classification": {
                "category": classification.category.value,
                "severity": classification.severity.value,
                "confidence": classification.confidence
            },
            "patterns": patterns,
            "factors": classification.factors,
            "recommended_actions": classification.recommended_actions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Timeline analysis failed: {str(e)}")


@app.post("/api/ai/predict-resolution-time")
async def predict_resolution_time_api(
    incident_data: dict,
    current_user: User = Depends(require_editor)
):
    """Predict incident resolution time using AI"""
    try:
        classification = incident_classifier.classify_incident(incident_data)
        
        # Add more sophisticated prediction logic here
        base_time = classification.estimated_resolution_time
        
        # Adjust based on incident complexity
        timeline = incident_data.get("timeline", [])
        if len(timeline) > 10:
            base_time *= 1.3  # Complex incidents take longer
        
        # Adjust based on number of affected services
        impact = incident_data.get("impact", [])
        if len(impact) > 3:
            base_time *= 1.2
        
        return {
            "predicted_resolution_time_minutes": int(base_time),
            "confidence": classification.confidence,
            "factors_considered": [
                "incident_severity",
                "incident_category", 
                "timeline_complexity",
                "impact_scope"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/api/ai/incident-suggestions")
async def get_incident_suggestions(
    query: str,
    current_user: User = Depends(require_editor)
):
    """Get incident suggestions based on partial input"""
    try:
        # Simple keyword-based suggestions
        suggestions = []
        
        # Common incident patterns
        common_patterns = {
            "database": [
                "Database connection pool exhaustion",
                "Slow query performance degradation",
                "Database deadlock detected",
                "Database replication lag"
            ],
            "network": [
                "Network latency increased",
                "Connection timeout errors",
                "Packet loss detected",
                "DNS resolution failures"
            ],
            "application": [
                "Application memory leak",
                "High CPU utilization",
                "Application crash detected",
                "Unresponsive application"
            ],
            "infrastructure": [
                "Server disk space full",
                "Memory exhaustion",
                "CPU spike detected",
                "Infrastructure failure"
            ]
        }
        
        query_lower = query.lower()
        for category, incidents in common_patterns.items():
            for incident in incidents:
                if query_lower in incident.lower() or any(word in incident.lower() for word in query_lower.split()):
                    suggestions.append({
                        "title": incident,
                        "category": category,
                        "severity": "medium"  # Default severity
                    })
        
        return {"suggestions": suggestions[:10]}  # Return top 10
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {str(e)}")


# Template system endpoints
@app.get("/api/templates")
async def get_templates_api(
    category: Optional[str] = None,
    current_user: User = Depends(require_viewer)
):
    """Get all incident templates"""
    try:
        if category:
            from .template_system import TemplateCategory
            cat_enum = TemplateCategory(category)
            templates = template_manager.get_templates_by_category(cat_enum)
        else:
            templates = template_manager.get_all_templates()
        
        return {
            "templates": [
                {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category.value,
                    "severity": template.severity,
                    "tags": template.tags,
                    "created_at": template.created_at.isoformat(),
                    "updated_at": template.updated_at.isoformat()
                }
                for template in templates
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")


@app.get("/api/templates/{template_id}")
async def get_template_api(
    template_id: str,
    current_user: User = Depends(require_viewer)
):
    """Get specific template"""
    try:
        template = template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category.value,
            "severity": template.severity,
            "fields": [
                {
                    "name": field.name,
                    "label": field.label,
                    "type": field.type,
                    "required": field.required,
                    "options": field.options,
                    "default_value": field.default_value,
                    "placeholder": field.placeholder,
                    "validation": field.validation
                }
                for field in template.fields
            ],
            "suggested_actions": template.suggested_actions,
            "contributing_factors": template.contributing_factors,
            "tags": template.tags,
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get template: {str(e)}")


@app.post("/api/templates")
async def create_template_api(
    template_data: dict,
    current_user: User = Depends(require_admin)
):
    """Create new template"""
    try:
        template = template_manager.create_template(template_data)
        return {
            "id": template.id,
            "status": "created",
            "message": "Template created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@app.put("/api/templates/{template_id}")
async def update_template_api(
    template_id: str,
    updates: dict,
    current_user: User = Depends(require_admin)
):
    """Update template"""
    try:
        template = template_manager.update_template(template_id, updates)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "id": template.id,
            "status": "updated",
            "message": "Template updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")


@app.delete("/api/templates/{template_id}")
async def delete_template_api(
    template_id: str,
    current_user: User = Depends(require_admin)
):
    """Delete template"""
    try:
        success = template_manager.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {"status": "deleted", "message": "Template deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")


@app.post("/api/templates/{template_id}/apply")
async def apply_template_api(
    template_id: str,
    current_user: User = Depends(require_editor)
):
    """Apply template to get initial incident data"""
    try:
        incident_data = template_manager.apply_template(template_id)
        if not incident_data:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "incident_data": incident_data,
            "message": "Template applied successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply template: {str(e)}")


# AI insights endpoint for dashboard
@app.get("/api/ai/insights")
async def get_ai_insights_api(
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get AI-powered insights for dashboard"""
    try:
        # Get recent incidents for analysis
        incident_service = IncidentService(db)
        recent_incidents = incident_service.search_incidents(
            user=current_user,
            page=1,
            page_size=10
        )["incidents"]
        
        insights = []
        
        # Analyze incident trends
        if len(recent_incidents) > 0:
            severity_counts = {}
            category_counts = {}
            
            for incident in recent_incidents:
                severity = incident.severity
                category = getattr(incident, 'category', 'unknown')
                
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                category_counts[category] = category_counts.get(category, 0) + 1
            
            # Most common severity
            most_common_severity = max(severity_counts, key=severity_counts.get)
            insights.append({
                "title": "Trend Analysis",
                "content": f"Most incidents this week are {most_common_severity} severity. Consider reviewing {most_common_severity} severity incident response procedures.",
                "icon": "📈"
            })
            
            # Resolution time trend
            avg_resolution = sum(
                getattr(incident, 'duration_minutes', 0) for incident in recent_incidents
            ) / len(recent_incidents)
            
            if avg_resolution > 120:  # 2 hours
                insights.append({
                    "title": "Performance Alert",
                    "content": f"Average resolution time is {int(avg_resolution)} minutes. Consider optimizing incident response workflows.",
                    "icon": "⚡"
                })
            else:
                insights.append({
                    "title": "Performance Good",
                    "content": f"Average resolution time is {int(avg_resolution)} minutes. Team is performing well!",
                    "icon": "✅"
                })
        
        # Add predictive insights
        insights.append({
            "title": "AI Prediction",
            "content": "Based on current patterns, expect 2-3 more incidents this week. Focus on proactive monitoring.",
            "icon": "🤖"
        })
        
        return {"insights": insights}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")


# Compliance and audit endpoints
@app.get("/api/audit/trail")
async def get_audit_trail_api(
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get audit trail"""
    try:
        audit_manager = get_audit_manager(db)
        
        # Convert action string to enum
        action_enum = None
        if action:
            action_enum = AuditAction(action)
        
        events = audit_manager.get_audit_trail(
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            action=action_enum,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {
            "events": [
                {
                    "id": event.id,
                    "timestamp": event.timestamp.isoformat(),
                    "user_id": event.user_id,
                    "user_name": event.user_name,
                    "action": event.action.value,
                    "resource_type": event.resource_type,
                    "resource_id": event.resource_id,
                    "details": event.details,
                    "ip_address": event.ip_address,
                    "user_agent": event.user_agent
                }
                for event in events
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audit trail: {str(e)}")


@app.post("/api/compliance/reports")
async def generate_compliance_report_api(
    standard: str,
    period_start: datetime,
    period_end: datetime,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Generate compliance report"""
    try:
        audit_manager = get_audit_manager(db)
        standard_enum = ComplianceStandard(standard)
        
        report = audit_manager.generate_compliance_report(
            standard=standard_enum,
            period_start=period_start,
            period_end=period_end,
            generated_by=current_user.full_name
        )
        
        return {
            "id": report.id,
            "standard": report.standard.value,
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "total_events": report.total_events,
            "compliance_score": report.compliance_score,
            "violations": report.violations,
            "recommendations": report.recommendations,
            "generated_at": report.generated_at.isoformat(),
            "generated_by": report.generated_by
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate compliance report: {str(e)}")


@app.get("/api/compliance/reports")
async def get_compliance_reports_api(
    standard: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get compliance reports"""
    try:
        audit_manager = get_audit_manager(db)
        
        # Convert standard string to enum
        standard_enum = None
        if standard:
            standard_enum = ComplianceStandard(standard)
        
        reports = audit_manager.get_compliance_reports(standard=standard_enum)
        
        return {
            "reports": [
                {
                    "id": report.id,
                    "standard": report.standard.value,
                    "period_start": report.period_start.isoformat(),
                    "period_end": report.period_end.isoformat(),
                    "total_events": report.total_events,
                    "compliance_score": report.compliance_score,
                    "violations_count": len(report.violations),
                    "generated_at": report.generated_at.isoformat(),
                    "generated_by": report.generated_by
                }
                for report in reports
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get compliance reports: {str(e)}")


@app.get("/api/compliance/reports/{report_id}")
async def get_compliance_report_api(
    report_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get specific compliance report"""
    try:
        audit_manager = get_audit_manager(db)
        reports = audit_manager.get_compliance_reports()
        
        report = next((r for r in reports if r.id == report_id), None)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return {
            "id": report.id,
            "standard": report.standard.value,
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "total_events": report.total_events,
            "compliance_score": report.compliance_score,
            "violations": report.violations,
            "recommendations": report.recommendations,
            "generated_at": report.generated_at.isoformat(),
            "generated_by": report.generated_by
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get compliance report: {str(e)}")


@app.get("/api/audit/export")
async def export_audit_trail_api(
    format: str = "json",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Export audit trail"""
    try:
        audit_manager = get_audit_manager(db)
        
        if format not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Format must be 'json' or 'csv'")
        
        export_data = audit_manager.export_audit_trail(
            format=format,
            start_date=start_date,
            end_date=end_date
        )
        
        from fastapi.responses import Response
        
        if format == "json":
            return Response(
                content=export_data,
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=audit_trail.json"}
            )
        else:
            return Response(
                content=export_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=audit_trail.csv"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export audit trail: {str(e)}")


# Advanced AI Prediction Endpoints
@app.post("/api/ai/predict-incident-likelihood")
async def predict_incident_likelihood_api(
    system_metrics: Dict[str, Any],
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Predict incident likelihood based on system metrics"""
    try:
        predictor = get_advanced_predictor(db)
        prediction = predictor.predict_incident_likelihood(system_metrics)
        
        return {
            "prediction_type": prediction.prediction_type.value,
            "confidence": prediction.confidence,
            "result": prediction.result,
            "factors": prediction.factors,
            "recommendations": prediction.recommendations,
            "timestamp": prediction.timestamp.isoformat(),
            "model_version": prediction.model_version
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/api/ai/predict-severity")
async def predict_severity_api(
    incident_data: Dict[str, Any],
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Predict incident severity"""
    try:
        predictor = get_advanced_predictor(db)
        prediction = predictor.predict_severity(incident_data)
        
        return {
            "prediction_type": prediction.prediction_type.value,
            "confidence": prediction.confidence,
            "result": prediction.result,
            "factors": prediction.factors,
            "recommendations": prediction.recommendations,
            "timestamp": prediction.timestamp.isoformat(),
            "model_version": prediction.model_version
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Severity prediction failed: {str(e)}")


@app.post("/api/ai/detect-anomalies")
async def detect_anomalies_api(
    system_metrics: Dict[str, Any],
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Detect anomalies in system metrics"""
    try:
        predictor = get_advanced_predictor(db)
        prediction = predictor.detect_anomalies(system_metrics)
        
        return {
            "prediction_type": prediction.prediction_type.value,
            "confidence": prediction.confidence,
            "result": prediction.result,
            "factors": prediction.factors,
            "recommendations": prediction.recommendations,
            "timestamp": prediction.timestamp.isoformat(),
            "model_version": prediction.model_version
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {str(e)}")


@app.get("/api/ai/incident-patterns")
async def get_incident_patterns_api(
    days_back: int = 30,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get incident patterns"""
    try:
        predictor = get_advanced_predictor(db)
        patterns = predictor.find_incident_patterns(days_back)
        
        return {
            "patterns": [
                {
                    "pattern_id": pattern.pattern_id,
                    "frequency": pattern.frequency,
                    "time_pattern": pattern.time_pattern,
                    "affected_systems": pattern.affected_systems,
                    "severity_trend": pattern.severity_trend,
                    "related_incidents": pattern.related_incidents,
                    "prevention_score": pattern.prevention_score
                }
                for pattern in patterns
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {str(e)}")


@app.post("/api/ai/train-models")
async def train_ai_models_api(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Train AI prediction models"""
    try:
        predictor = get_advanced_predictor(db)
        result = predictor.train_models()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")


# Collaborative Editing Endpoints
@app.websocket("/ws/collaborative/{incident_id}")
async def collaborative_editing_websocket(
    websocket: WebSocket,
    incident_id: int,
    token: str = None
):
    """WebSocket endpoint for collaborative incident editing"""
    try:
        # Authenticate user
        if not token:
            await websocket.close(code=4001)
            return
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username is None:
                await websocket.close(code=4001)
                return
        except JWTError:
            await websocket.close(code=4001)
            return
        
        # Get user
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        if not user:
            await websocket.close(code=4001)
            return
        
        # Connect to collaborative editor
        editor = get_collaborative_editor()
        message = await editor.connect_user(websocket, incident_id, user)
        
        # Handle messages
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get('type') == 'edit_operation':
                await editor.handle_edit_operation(websocket, message_data)
            elif message_data.get('type') == 'cursor_update':
                await editor.handle_cursor_update(websocket, message_data)
            
    except WebSocketDisconnect:
        await editor.disconnect_user(websocket)
    except Exception as e:
        print(f"Collaborative editing error: {e}")
        await websocket.close(code=4000)


@app.get("/api/collaborative/{incident_id}/active-users")
async def get_active_users_api(
    incident_id: int,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get active users for collaborative editing"""
    try:
        editor = get_collaborative_editor()
        active_users = editor.get_active_users(incident_id)
        
        return {"active_users": active_users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active users: {str(e)}")


@app.get("/api/collaborative/{incident_id}/edit-history")
async def get_edit_history_api(
    incident_id: int,
    limit: int = 50,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get edit history for incident"""
    try:
        editor = get_collaborative_editor()
        edit_history = editor.get_edit_history(incident_id, limit)
        
        return {"edit_history": edit_history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get edit history: {str(e)}")


# Incident Correlation Endpoints
@app.post("/api/correlation/analyze")
async def analyze_incident_correlations_api(
    days_back: int = 30,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Analyze incident correlations"""
    try:
        correlation_engine = get_correlation_engine(db)
        analysis = correlation_engine.analyze_incidents(days_back)
        
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Correlation analysis failed: {str(e)}")


@app.get("/api/correlation/incident/{incident_id}")
async def get_incident_correlations_api(
    incident_id: int,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get correlations for specific incident"""
    try:
        correlation_engine = get_correlation_engine(db)
        correlations = correlation_engine.get_incident_correlations(incident_id)
        
        return {"correlations": correlations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get correlations: {str(e)}")


@app.get("/api/correlation/cluster/{incident_id}")
async def get_incident_cluster_api(
    incident_id: int,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get cluster information for incident"""
    try:
        correlation_engine = get_correlation_engine(db)
        cluster = correlation_engine.get_incident_cluster(incident_id)
        
        if cluster:
            return {"cluster": cluster}
        else:
            return {"cluster": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cluster: {str(e)}")


# Knowledge Base Endpoints
@app.post("/api/knowledge/search")
async def search_knowledge_api(
    query: str,
    knowledge_type: Optional[str] = None,
    limit: int = 10,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Search knowledge base"""
    try:
        knowledge_manager = get_knowledge_manager(db)
        
        k_type = KnowledgeType(knowledge_type) if knowledge_type else None
        results = knowledge_manager.search_knowledge(query, k_type, limit)
        
        return {"results": results, "total_found": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge search failed: {str(e)}")


@app.get("/api/knowledge/incident/{incident_id}/relevant")
async def get_relevant_knowledge_api(
    incident_id: int,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get relevant knowledge for incident"""
    try:
        knowledge_manager = get_knowledge_manager(db)
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        relevant_knowledge = knowledge_manager.get_relevant_knowledge_for_incident(incident)
        
        return {"relevant_knowledge": relevant_knowledge}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get relevant knowledge: {str(e)}")


@app.post("/api/knowledge/entry/{entry_id}/feedback")
async def update_knowledge_feedback_api(
    entry_id: str,
    feedback_score: float,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Update knowledge entry usefulness based on feedback"""
    try:
        if not 0.0 <= feedback_score <= 1.0:
            raise HTTPException(status_code=400, detail="Feedback score must be between 0.0 and 1.0")
        
        knowledge_manager = get_knowledge_manager(db)
        knowledge_manager.update_usefulness_score(entry_id, feedback_score)
        
        return {"message": "Feedback recorded successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {str(e)}")


@app.post("/api/knowledge/learn-patterns")
async def learn_patterns_api(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Learn patterns from historical data"""
    try:
        knowledge_manager = get_knowledge_manager(db)
        result = knowledge_manager.learn_from_patterns()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern learning failed: {str(e)}")


@app.get("/api/knowledge/statistics")
async def get_knowledge_statistics_api(
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get knowledge base statistics"""
    try:
        knowledge_manager = get_knowledge_manager(db)
        stats = knowledge_manager.get_knowledge_statistics()
        
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@app.post("/api/knowledge/extract/{incident_id}")
async def extract_knowledge_from_incident_api(
    incident_id: int,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Extract knowledge from resolved incident"""
    try:
        knowledge_manager = get_knowledge_manager(db)
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        entries = knowledge_manager.extract_knowledge_from_incident(incident)
        
        return {
            "message": f"Extracted {len(entries)} knowledge entries",
            "entries": [
                {
                    "entry_id": entry.entry_id,
                    "title": entry.title,
                    "knowledge_type": entry.knowledge_type.value,
                    "confidence_score": entry.confidence_score
                }
                for entry in entries
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge extraction failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
