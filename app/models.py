from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str = "viewer"


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    roles: list = []


class User(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactType(str, Enum):
    AVAILABILITY = "availability"
    PERFORMANCE = "performance"
    FUNCTIONALITY = "functionality"
    DATA = "data"
    SECURITY = "security"


class Alert(BaseModel):
    name: str
    timestamp: datetime
    severity: SeverityLevel
    description: str
    source: str


class TimelineEvent(BaseModel):
    timestamp: datetime
    event: str
    severity: SeverityLevel = SeverityLevel.MEDIUM
    source: Optional[str] = None


class Impact(BaseModel):
    type: ImpactType
    description: str
    affected_users: Optional[int] = None
    affected_services: List[str] = []
    duration_minutes: Optional[int] = None


class ContributingFactor(BaseModel):
    factor: str
    category: str  # technical, process, people, external
    description: str


class ActionItem(BaseModel):
    title: str
    description: str
    category: str  # immediate, short_term, long_term, preventive
    priority: SeverityLevel
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None


class IncidentInput(BaseModel):
    title: str
    severity: SeverityLevel
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    description: str
    timeline: List[TimelineEvent]
    alerts: List[Alert] = []
    impact: List[Impact]
    contributing_factors: List[ContributingFactor] = []
    action_items: List[ActionItem] = []
    what_went_well: List[str] = []
    what_went_wrong: List[str] = []


class PostmortemOutput(BaseModel):
    title: str
    incident_id: str
    date_generated: datetime
    severity: SeverityLevel
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: int
    executive_summary: str
    timeline: List[TimelineEvent]
    impact: List[Impact]
    contributing_factors: List[ContributingFactor]
    action_items: List[ActionItem]
    what_went_well: List[str]
    what_went_wrong: List[str]
    lessons_learned: List[str]
    next_steps: List[str]


class JiraTicket(BaseModel):
    project_key: str
    summary: str
    description: str
    issue_type: str = "Task"
    priority: str
    assignee: Optional[str] = None
    labels: List[str] = []
    due_date: Optional[str] = None
