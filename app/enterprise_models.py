from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum as PyEnum
from .database import Base


class UserRole(PyEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class IncidentStatus(PyEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class NotificationType(PyEnum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


class AuditAction(PyEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    EXPORT = "export"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    incidents = relationship("Incident", back_populates="created_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")


class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    severity = Column(String(20), nullable=False)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.DRAFT)
    
    # Timeline
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)
    
    # JSON fields for complex data
    timeline = Column(JSON)
    alerts = Column(JSON)
    impact = Column(JSON)
    contributing_factors = Column(JSON)
    action_items = Column(JSON)
    what_went_well = Column(JSON)
    what_went_wrong = Column(JSON)
    
    # Generated content
    executive_summary = Column(Text)
    lessons_learned = Column(JSON)
    next_steps = Column(JSON)
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True))
    
    # Relationships
    created_by_user = relationship("User", back_populates="incidents")
    audit_logs = relationship("AuditLog", back_populates="incident")
    notifications = relationship("Notification", back_populates="incident")
    sla_metrics = relationship("SLAMetrics", back_populates="incident")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    action = Column(Enum(AuditAction), nullable=False)
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    incident = relationship("Incident", back_populates="audit_logs")


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    type = Column(Enum(NotificationType), nullable=False)
    recipient = Column(String(200), nullable=False)
    subject = Column(String(200))
    message = Column(Text)
    status = Column(String(20), default="pending")  # pending, sent, failed
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    incident = relationship("Incident", back_populates="notifications")


class SLAMetrics(Base):
    __tablename__ = "sla_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    sla_type = Column(String(50), nullable=False)  # response_time, resolution_time, etc.
    target_minutes = Column(Integer, nullable=False)
    actual_minutes = Column(Integer, nullable=False)
    achieved = Column(Boolean, nullable=False)
    breach_minutes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    incident = relationship("Incident", back_populates="sla_metrics")


class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    dimensions = Column(JSON)  # For filtering/grouping
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class IntegrationConfig(Base):
    __tablename__ = "integration_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    type = Column(String(50), nullable=False)  # jira, slack, email, webhook
    config = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
