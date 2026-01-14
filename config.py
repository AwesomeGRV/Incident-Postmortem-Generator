import os
from typing import Optional


class Config:
    # Application settings
    APP_NAME = "Enterprise Incident Postmortem Generator"
    VERSION = "2.0.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # Server settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    # Database settings
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./incident_postmortem.db")
    
    # Security settings
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Email settings
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    # Slack settings
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    
    # Notification settings
    SLA_ALERT_RECIPIENTS = os.getenv("SLA_ALERT_RECIPIENTS", "").split(",") if os.getenv("SLA_ALERT_RECIPIENTS") else []
    ESCALATION_RECIPIENTS = os.getenv("ESCALATION_RECIPIENTS", "").split(",") if os.getenv("ESCALATION_RECIPIENTS") else []
    
    # File upload settings
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    
    # Jira settings (optional)
    JIRA_URL = os.getenv("JIRA_URL")
    JIRA_USERNAME = os.getenv("JIRA_USERNAME")
    JIRA_TOKEN = os.getenv("JIRA_TOKEN")
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "INC")
    
    # Output settings
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
    TEMP_DIR = os.getenv("TEMP_DIR", "temp")
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
