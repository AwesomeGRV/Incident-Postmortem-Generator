"""
Real-time WebSocket notifications service for incident updates
"""

import json
import asyncio
from typing import Dict, List, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from .models import User, Incident
from .notifications import AlertManager


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications"""
    
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.user_connections: Dict[WebSocket, int] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Connect a WebSocket for a user"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.user_connections[websocket] = user_id
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "message": "Connected to real-time notifications",
            "timestamp": datetime.now().isoformat()
        }, user_id)
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket"""
        user_id = self.user_connections.get(websocket)
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        if websocket in self.user_connections:
            del self.user_connections[websocket]
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)
    
    async def broadcast_to_role(self, message: dict, role: str, db: Session):
        """Broadcast message to all users with specific role"""
        users = db.query(User).filter(User.role == role).all()
        for user in users:
            await self.send_personal_message(message, user.id)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected users"""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)


class NotificationService:
    """Service for handling real-time notifications"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    async def notify_incident_created(self, incident: Incident, creator: User, db: Session):
        """Notify users when a new incident is created"""
        message = {
            "type": "incident_created",
            "incident_id": incident.id,
            "title": incident.title,
            "severity": incident.severity,
            "creator": creator.full_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Notify all editors and admins
        await self.connection_manager.broadcast_to_role(message, "editor", db)
        await self.connection_manager.broadcast_to_role(message, "admin", db)
    
    async def notify_incident_updated(self, incident: Incident, updater: User, db: Session):
        """Notify users when an incident is updated"""
        message = {
            "type": "incident_updated",
            "incident_id": incident.id,
            "title": incident.title,
            "updated_by": updater.full_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Notify all viewers, editors, and admins
        for role in ["viewer", "editor", "admin"]:
            await self.connection_manager.broadcast_to_role(message, role, db)
    
    async def notify_incident_published(self, incident: Incident, publisher: User, db: Session):
        """Notify users when an incident is published"""
        message = {
            "type": "incident_published",
            "incident_id": incident.id,
            "title": incident.title,
            "published_by": publisher.full_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Notify all users
        await self.connection_manager.broadcast_to_all(message)
    
    async def notify_sla_breach(self, incident: Incident, db: Session):
        """Notify users when SLA is breached"""
        message = {
            "type": "sla_breach",
            "incident_id": incident.id,
            "title": incident.title,
            "severity": incident.severity,
            "sla_breach_time": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Notify all editors and admins
        await self.connection_manager.broadcast_to_role(message, "editor", db)
        await self.connection_manager.broadcast_to_role(message, "admin", db)
    
    async def notify_critical_alert(self, alert_data: dict, db: Session):
        """Notify users of critical alerts"""
        message = {
            "type": "critical_alert",
            "alert": alert_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Notify all editors and admins immediately
        await self.connection_manager.broadcast_to_role(message, "editor", db)
        await self.connection_manager.broadcast_to_role(message, "admin", db)
    
    async def notify_action_item_assigned(self, incident_id: int, action_item: dict, assignee: User, db: Session):
        """Notify user when action item is assigned to them"""
        message = {
            "type": "action_item_assigned",
            "incident_id": incident_id,
            "action_item": action_item,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.connection_manager.send_personal_message(message, assignee.id)
    
    async def notify_deadline_reminder(self, incident_id: int, action_items: List[dict], db: Session):
        """Notify users of upcoming deadlines"""
        for item in action_items:
            if item.get("assigned_to"):
                user = db.query(User).filter(User.id == item["assigned_to"]).first()
                if user:
                    message = {
                        "type": "deadline_reminder",
                        "incident_id": incident_id,
                        "action_item": item,
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.connection_manager.send_personal_message(message, user.id)


# Global connection manager instance
connection_manager = ConnectionManager()
notification_service = NotificationService(connection_manager)
