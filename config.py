import os
from typing import Optional


class Config:
    # Application settings
    APP_NAME = "Incident Postmortem Generator"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # Server settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
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
    
    # PDF generation settings
    PDF_TIMEOUT = int(os.getenv("PDF_TIMEOUT", "30"))  # seconds
    
    @classmethod
    def get_jira_config(cls) -> Optional[dict]:
        """Get Jira configuration if all required fields are set"""
        if all([cls.JIRA_URL, cls.JIRA_USERNAME, cls.JIRA_TOKEN]):
            return {
                "url": cls.JIRA_URL,
                "username": cls.JIRA_USERNAME,
                "token": cls.JIRA_TOKEN,
                "project_key": cls.JIRA_PROJECT_KEY
            }
        return None
