from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from typing import Optional, List
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
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


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
    incident = incident_service.create_incident(incident_data, current_user, request)
    return {"incident_id": incident.id, "status": "created"}


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
