"""
Real-time Collaborative Incident Editing System
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from .enterprise_models import Incident, User
import uuid


class EditOperation(Enum):
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"
    FORMAT = "format"


class CursorPosition:
    def __init__(self, user_id: int, line: int, column: int, selection: Optional[Dict] = None):
        self.user_id = user_id
        self.line = line
        self.column = column
        self.selection = selection
        self.timestamp = datetime.now()


@dataclass
class EditEvent:
    operation_id: str
    incident_id: int
    user_id: int
    operation: EditOperation
    position: int
    content: str
    timestamp: datetime
    user_name: str
    field_name: str  # title, description, etc.


@dataclass
class UserPresence:
    user_id: int
    user_name: str
    incident_id: int
    cursor: CursorPosition
    is_typing: bool
    last_activity: datetime
    color: str  # User color for highlighting


class CollaborativeEditor:
    """Manages real-time collaborative editing of incidents"""
    
    def __init__(self):
        self.active_sessions: Dict[int, Set[WebSocket]] = {}  # incident_id -> websockets
        self.user_sessions: Dict[WebSocket, UserPresence] = {}  # websocket -> user presence
        self.edit_history: Dict[int, List[EditEvent]] = {}  # incident_id -> edit events
        self.user_colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
            "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E2"
        ]
        self.color_index = 0
    
    async def connect_user(self, websocket: WebSocket, incident_id: int, user: User) -> str:
        """Connect a user to collaborative editing session"""
        await websocket.accept()
        
        # Add to active sessions
        if incident_id not in self.active_sessions:
            self.active_sessions[incident_id] = set()
        self.active_sessions[incident_id].add(websocket)
        
        # Assign color to user
        user_color = self.user_colors[self.color_index % len(self.user_colors)]
        self.color_index += 1
        
        # Create user presence
        presence = UserPresence(
            user_id=user.id,
            user_name=user.full_name,
            incident_id=incident_id,
            cursor=CursorPosition(user.id, 0, 0),
            is_typing=False,
            last_activity=datetime.now(),
            color=user_color
        )
        
        self.user_sessions[websocket] = presence
        
        # Initialize edit history for this incident
        if incident_id not in self.edit_history:
            self.edit_history[incident_id] = []
        
        # Notify other users
        await self.broadcast_user_joined(incident_id, presence)
        
        # Send current state to new user
        await self.send_current_state(websocket, incident_id)
        
        return f"Connected to incident {incident_id} collaborative editing"
    
    async def disconnect_user(self, websocket: WebSocket):
        """Disconnect user from collaborative editing"""
        if websocket in self.user_sessions:
            presence = self.user_sessions[websocket]
            incident_id = presence.incident_id
            
            # Remove from active sessions
            if incident_id in self.active_sessions:
                self.active_sessions[incident_id].discard(websocket)
                if not self.active_sessions[incident_id]:
                    del self.active_sessions[incident_id]
            
            # Notify other users
            await self.broadcast_user_left(incident_id, presence)
            
            # Clean up
            del self.user_sessions[websocket]
    
    async def handle_edit_operation(self, websocket: WebSocket, operation_data: Dict[str, Any]):
        """Handle edit operation from user"""
        if websocket not in self.user_sessions:
            return
        
        presence = self.user_sessions[websocket]
        incident_id = presence.incident_id
        
        # Create edit event
        edit_event = EditEvent(
            operation_id=str(uuid.uuid4()),
            incident_id=incident_id,
            user_id=presence.user_id,
            operation=EditOperation(operation_data.get('operation', 'insert')),
            position=operation_data.get('position', 0),
            content=operation_data.get('content', ''),
            timestamp=datetime.now(),
            user_name=presence.user_name,
            field_name=operation_data.get('field_name', 'description')
        )
        
        # Add to edit history
        self.edit_history[incident_id].append(edit_event)
        
        # Keep only last 100 operations per incident
        if len(self.edit_history[incident_id]) > 100:
            self.edit_history[incident_id] = self.edit_history[incident_id][-100:]
        
        # Broadcast to other users
        await self.broadcast_edit_operation(incident_id, edit_event, exclude_websocket=websocket)
        
        # Update user activity
        presence.last_activity = datetime.now()
        presence.is_typing = True
        
        # Schedule typing indicator reset
        asyncio.create_task(self.reset_typing_indicator(websocket))
    
    async def handle_cursor_update(self, websocket: WebSocket, cursor_data: Dict[str, Any]):
        """Handle cursor position update"""
        if websocket not in self.user_sessions:
            return
        
        presence = self.user_sessions[websocket]
        presence.cursor = CursorPosition(
            user_id=presence.user_id,
            line=cursor_data.get('line', 0),
            column=cursor_data.get('column', 0),
            selection=cursor_data.get('selection')
        )
        presence.last_activity = datetime.now()
        
        # Broadcast cursor position to other users
        await self.broadcast_cursor_update(presence.incident_id, presence, exclude_websocket=websocket)
    
    async def reset_typing_indicator(self, websocket: WebSocket):
        """Reset typing indicator after delay"""
        await asyncio.sleep(1.0)  # Wait 1 second
        
        if websocket in self.user_sessions:
            presence = self.user_sessions[websocket]
            if presence.is_typing:
                presence.is_typing = False
                await self.broadcast_user_activity(presence.incident_id, presence)
    
    async def send_current_state(self, websocket: WebSocket, incident_id: int):
        """Send current state to newly connected user"""
        # Get current incident data
        from .database import get_db
        db = next(get_db())
        
        try:
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            if not incident:
                return
            
            # Send incident data
            await websocket.send_text(json.dumps({
                'type': 'incident_data',
                'data': {
                    'id': incident.id,
                    'title': incident.title,
                    'description': incident.description,
                    'severity': incident.severity,
                    'status': incident.status.value if incident.status else 'draft'
                }
            }))
            
            # Send active users
            active_users = []
            for ws, presence in self.user_sessions.items():
                if presence.incident_id == incident_id and ws != websocket:
                    active_users.append({
                        'user_id': presence.user_id,
                        'user_name': presence.user_name,
                        'cursor': {
                            'line': presence.cursor.line,
                            'column': presence.cursor.column,
                            'selection': presence.cursor.selection
                        },
                        'is_typing': presence.is_typing,
                        'color': presence.color
                    })
            
            await websocket.send_text(json.dumps({
                'type': 'active_users',
                'users': active_users
            }))
            
            # Send recent edit history
            recent_edits = self.edit_history.get(incident_id, [])[-20:]  # Last 20 edits
            edit_data = []
            for edit in recent_edits:
                edit_data.append({
                    'operation_id': edit.operation_id,
                    'user_name': edit.user_name,
                    'operation': edit.operation.value,
                    'position': edit.position,
                    'content': edit.content,
                    'field_name': edit.field_name,
                    'timestamp': edit.timestamp.isoformat()
                })
            
            await websocket.send_text(json.dumps({
                'type': 'edit_history',
                'edits': edit_data
            }))
            
        finally:
            db.close()
    
    async def broadcast_edit_operation(self, incident_id: int, edit_event: EditEvent, exclude_websocket: WebSocket = None):
        """Broadcast edit operation to all users in incident session"""
        message = {
            'type': 'edit_operation',
            'data': {
                'operation_id': edit_event.operation_id,
                'user_id': edit_event.user_id,
                'user_name': edit_event.user_name,
                'operation': edit_event.operation.value,
                'position': edit_event.position,
                'content': edit_event.content,
                'field_name': edit_event.field_name,
                'timestamp': edit_event.timestamp.isoformat()
            }
        }
        
        await self.broadcast_to_incident(incident_id, message, exclude_websocket)
    
    async def broadcast_cursor_update(self, incident_id: int, presence: UserPresence, exclude_websocket: WebSocket = None):
        """Broadcast cursor position update"""
        message = {
            'type': 'cursor_update',
            'data': {
                'user_id': presence.user_id,
                'user_name': presence.user_name,
                'cursor': {
                    'line': presence.cursor.line,
                    'column': presence.cursor.column,
                    'selection': presence.cursor.selection
                },
                'color': presence.color
            }
        }
        
        await self.broadcast_to_incident(incident_id, message, exclude_websocket)
    
    async def broadcast_user_joined(self, incident_id: int, presence: UserPresence):
        """Broadcast user joined notification"""
        message = {
            'type': 'user_joined',
            'data': {
                'user_id': presence.user_id,
                'user_name': presence.user_name,
                'color': presence.color
            }
        }
        
        await self.broadcast_to_incident(incident_id, message)
    
    async def broadcast_user_left(self, incident_id: int, presence: UserPresence):
        """Broadcast user left notification"""
        message = {
            'type': 'user_left',
            'data': {
                'user_id': presence.user_id,
                'user_name': presence.user_name
            }
        }
        
        await self.broadcast_to_incident(incident_id, message)
    
    async def broadcast_user_activity(self, incident_id: int, presence: UserPresence):
        """Broadcast user activity update"""
        message = {
            'type': 'user_activity',
            'data': {
                'user_id': presence.user_id,
                'user_name': presence.user_name,
                'is_typing': presence.is_typing,
                'cursor': {
                    'line': presence.cursor.line,
                    'column': presence.cursor.column
                }
            }
        }
        
        await self.broadcast_to_incident(incident_id, message)
    
    async def broadcast_to_incident(self, incident_id: int, message: Dict[str, Any], exclude_websocket: WebSocket = None):
        """Broadcast message to all users in incident session"""
        if incident_id not in self.active_sessions:
            return
        
        message_text = json.dumps(message)
        disconnected = set()
        
        for websocket in self.active_sessions[incident_id]:
            if websocket != exclude_websocket:
                try:
                    await websocket.send_text(message_text)
                except:
                    disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            await self.disconnect_user(websocket)
    
    def get_active_users(self, incident_id: int) -> List[Dict[str, Any]]:
        """Get list of active users for an incident"""
        active_users = []
        
        for presence in self.user_sessions.values():
            if presence.incident_id == incident_id:
                active_users.append({
                    'user_id': presence.user_id,
                    'user_name': presence.user_name,
                    'cursor': {
                        'line': presence.cursor.line,
                        'column': presence.cursor.column,
                        'selection': presence.cursor.selection
                    },
                    'is_typing': presence.is_typing,
                    'last_activity': presence.last_activity.isoformat(),
                    'color': presence.color
                })
        
        return active_users
    
    def get_edit_history(self, incident_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get edit history for an incident"""
        edits = self.edit_history.get(incident_id, [])
        
        edit_data = []
        for edit in edits[-limit:]:
            edit_data.append({
                'operation_id': edit.operation_id,
                'user_id': edit.user_id,
                'user_name': edit.user_name,
                'operation': edit.operation.value,
                'position': edit.position,
                'content': edit.content,
                'field_name': edit.field_name,
                'timestamp': edit.timestamp.isoformat()
            })
        
        return edit_data


# Global collaborative editor instance
collaborative_editor = CollaborativeEditor()


def get_collaborative_editor() -> CollaborativeEditor:
    """Get collaborative editor instance"""
    return collaborative_editor
