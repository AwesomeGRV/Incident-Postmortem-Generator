#!/usr/bin/env python3
"""
Incident Postmortem Generator - Main Entry Point

This script starts the web application for generating incident postmortems.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.main import app
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
    print(f"Server will be available at: http://{Config.HOST}:{Config.PORT}")
    
    # Create necessary directories
    create_directories()
    
    # Start the server
    uvicorn.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="info" if not Config.DEBUG else "debug"
    )


if __name__ == "__main__":
    main()
