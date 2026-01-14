#!/usr/bin/env python3
"""
Enterprise Incident Postmortem Generator - Main Entry Point

This script starts the enterprise-grade web application for generating incident postmortems.
Features include authentication, analytics, SLA tracking, notifications, and more.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.enterprise_main import app
from config import Config


def create_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        Config.OUTPUT_DIR,
        Config.TEMP_DIR,
        Config.UPLOAD_DIR,
        "static",
        "templates"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def main():
    """Main entry point for the application"""
    print(f"Starting {Config.APP_NAME} v{Config.VERSION}")
    print(f"Debug mode: {Config.DEBUG}")
    print(f"Database: {Config.DATABASE_URL}")
    print(f"Server will be available at: http://{Config.HOST}:{Config.PORT}")
    
    # Create necessary directories
    create_directories()
    
    # Start the server
    uvicorn.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="info" if not Config.DEBUG else "debug",
        access_log=True
    )


if __name__ == "__main__":
    main()
