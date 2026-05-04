"""
Enhanced Real-Time Collaboration System
Modern WebSocket-based collaboration with operational transforms
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque

# WebSocket imports
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

# Database imports
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
import redis.asyncio as redis

# Operational transform imports
import difflib
import hashlib

Base = declarative_base()

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of collaborative operations"""
    INSERT = "insert"
    DELETE = "delete"
    RETAIN = "retain"
    FORMAT = "format"


class CollaborationEventType(Enum):
    """Collaboration event types"""
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    CURSOR_MOVE = "cursor_move"
    SELECTION_CHANGE = "selection_change"
    TEXT_CHANGE = "text_change"
    COMMENT_ADD = "comment_add"
    COMMENT_RESOLVE = "comment_resolve"


@dataclass
class Operation:
    """Operational transform operation"""
    type: OperationType
    position: int
    content: Optional[str] = None
    length: Optional[int] = None
    attributes: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class UserPresence:
    """User presence information"""
    user_id: str
    username: str
    cursor_position: int = 0
    selection_start: int = 0
    selection_end: int = 0
    color: str = "#007bff"
    is_active: bool = True
    last_seen: datetime = None
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.utcnow()


@dataclass
class Comment:
    """Collaborative comment"""
    id: str
    user_id: str
    username: str
    content: str
    position: int
    created_at: datetime
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None


@dataclass
class CollaborationEvent:
    """Collaboration event"""
    type: CollaborationEventType
    user_id: str
    data: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class DocumentState:
    """Document state with operational transform support"""
    
    def __init__(self, document_id: str):
        self.document_id = document_id
        self.content = ""
        self.version = 0
        self.operations: List[Operation] = []
        self.presence: Dict[str, UserPresence] = {}
        self.comments: Dict[str, Comment] = {}
        self.last_modified = datetime.utcnow()
    
    def apply_operation(self, operation: Operation) -> bool:
        """Apply operation to document"""
        try:
            if operation.type == OperationType.INSERT:
                if operation.position <= len(self.content):
                    self.content = (
                        self.content[:operation.position] + 
                        operation.content + 
                        self.content[operation.position:]
                    )
                    self.operations.append(operation)
                    self.version += 1
                    self.last_modified = datetime.utcnow()
                    return True
            
            elif operation.type == OperationType.DELETE:
                if operation.position < len(self.content):
                    end_pos = min(operation.position + (operation.length or 1), len(self.content))
                    self.content = self.content[:operation.position] + self.content[end_pos:]
                    self.operations.append(operation)
                    self.version += 1
                    self.last_modified = datetime.utcnow()
                    return True
            
            elif operation.type == OperationType.FORMAT:
                # Handle formatting operations
                self.operations.append(operation)
                self.version += 1
                self.last_modified = datetime.utcnow()
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error applying operation: {e}")
            return False
    
    def transform_operation(self, operation: Operation, against_version: int) -> Operation:
        """Transform operation against document version"""
        if against_version >= self.version:
            return operation
        
        # Get operations to transform against
        ops_to_transform = self.operations[against_version:]
        
        transformed_op = operation
        
        for op in ops_to_transform:
            transformed_op = self._transform_pair(transformed_op, op)
        
        return transformed_op
    
    def _transform_pair(self, op1: Operation, op2: Operation) -> Operation:
        """Transform two operations"""
        # Simplified operational transform logic
        if op1.type == OperationType.INSERT and op2.type == OperationType.INSERT:
            if op1.position <= op2.position:
                return op1
            else:
                return Operation(
                    type=op1.type,
                    position=op1.position + len(op2.content or ""),
                    content=op1.content,
                    user_id=op1.user_id,
                    timestamp=op1.timestamp
                )
        
        elif op1.type == OperationType.DELETE and op2.type == OperationType.INSERT:
            if op1.position <= op2.position:
                return op1
            else:
                return Operation(
                    type=op1.type,
                    position=op1.position + len(op2.content or ""),
                    length=op1.length,
                    user_id=op1.user_id,
                    timestamp=op1.timestamp
                )
        
        # Add more transformation rules as needed
        return op1
    
    def update_presence(self, user_id: str, presence: UserPresence):
        """Update user presence"""
        presence.last_seen = datetime.utcnow()
        self.presence[user_id] = presence
    
    def add_comment(self, comment: Comment):
        """Add comment to document"""
        self.comments[comment.id] = comment
    
    def resolve_comment(self, comment_id: str, resolved_by: str):
        """Resolve a comment"""
        if comment_id in self.comments:
            self.comments[comment_id].resolved = True
            self.comments[comment_id].resolved_by = resolved_by
            self.comments[comment_id].resolved_at = datetime.utcnow()
    
    def cleanup_inactive_users(self, timeout_minutes: int = 5):
        """Remove inactive users"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        inactive_users = [
            user_id for user_id, presence in self.presence.items()
            if presence.last_seen < cutoff_time
        ]
        
        for user_id in inactive_users:
            del self.presence[user_id]
        
        return inactive_users


class CollaborationManager:
    """Real-time collaboration manager"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.documents: Dict[str, DocumentState] = {}
        self.connections: Dict[str, WebSocket] = {}
        self.user_documents: Dict[str, Set[str]] = defaultdict(set)
        self.event_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
    
    async def initialize(self):
        """Initialize collaboration manager"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            logger.info("Collaboration manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
    
    async def register_connection(self, websocket: WebSocket, user_id: str) -> str:
        """Register WebSocket connection"""
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = websocket
        
        # Store connection in Redis for scaling
        if self.redis_client:
            await self.redis_client.hset(
                f"connections:{user_id}",
                connection_id,
                json.dumps({"connected_at": datetime.utcnow().isoformat()})
            )
        
        return connection_id
    
    async def unregister_connection(self, connection_id: str, user_id: str):
        """Unregister WebSocket connection"""
        if connection_id in self.connections:
            del self.connections[connection_id]
        
        # Remove from Redis
        if self.redis_client:
            await self.redis_client.hdel(f"connections:{user_id}", connection_id)
        
        # Clean up user presence in all documents
        for document_id in self.user_documents[user_id]:
            if document_id in self.documents:
                if user_id in self.documents[document_id].presence:
                    del self.documents[document_id].presence[user_id]
                
                # Broadcast user leave event
                await self.broadcast_event(
                    document_id,
                    CollaborationEvent(
                        type=CollaborationEventType.USER_LEAVE,
                        user_id=user_id,
                        data={"username": user_id}
                    ),
                    exclude_user=user_id
                )
    
    async def join_document(self, connection_id: str, user_id: str, document_id: str, username: str):
        """Join a document for collaboration"""
        # Initialize document if not exists
        if document_id not in self.documents:
            self.documents[document_id] = DocumentState(document_id)
        
        # Add user to document
        self.user_documents[user_id].add(document_id)
        
        # Create user presence
        presence = UserPresence(
            user_id=user_id,
            username=username,
            color=self._generate_user_color(user_id)
        )
        
        self.documents[document_id].update_presence(user_id, presence)
        
        # Broadcast join event
        await self.broadcast_event(
            document_id,
            CollaborationEvent(
                type=CollaborationEventType.USER_JOIN,
                user_id=user_id,
                data={
                    "username": username,
                    "color": presence.color,
                    "cursor_position": presence.cursor_position
                }
            ),
            exclude_user=user_id
        )
        
        # Send current document state to user
        await self.send_document_state(connection_id, document_id)
    
    async def leave_document(self, user_id: str, document_id: str):
        """Leave a document"""
        if document_id in self.user_documents[user_id]:
            self.user_documents[user_id].remove(document_id)
        
        if document_id in self.documents:
            if user_id in self.documents[document_id].presence:
                del self.documents[document_id].presence[user_id]
            
            # Broadcast leave event
            await self.broadcast_event(
                document_id,
                CollaborationEvent(
                    type=CollaborationEventType.USER_LEAVE,
                    user_id=user_id,
                    data={"username": user_id}
                )
            )
    
    async def apply_operation(self, user_id: str, document_id: str, operation: Operation):
        """Apply operation to document"""
        if document_id not in self.documents:
            return False
        
        document = self.documents[document_id]
        
        # Transform operation if needed
        if operation.user_id != user_id:
            operation = document.transform_operation(operation, operation.timestamp)
        
        # Apply operation
        success = document.apply_operation(operation)
        
        if success:
            # Broadcast operation to other users
            await self.broadcast_operation(document_id, operation, exclude_user=user_id)
            
            # Store in event history
            self.event_history[document_id].append(
                CollaborationEvent(
                    type=CollaborationEventType.TEXT_CHANGE,
                    user_id=user_id,
                    data=asdict(operation)
                )
            )
        
        return success
    
    async def update_cursor(self, user_id: str, document_id: str, cursor_position: int, 
                          selection_start: int = 0, selection_end: int = 0):
        """Update user cursor position"""
        if document_id not in self.documents:
            return
        
        document = self.documents[document_id]
        
        if user_id in document.presence:
            document.presence[user_id].cursor_position = cursor_position
            document.presence[user_id].selection_start = selection_start
            document.presence[user_id].selection_end = selection_end
            document.presence[user_id].last_seen = datetime.utcnow()
            
            # Broadcast cursor update
            await self.broadcast_event(
                document_id,
                CollaborationEvent(
                    type=CollaborationEventType.CURSOR_MOVE,
                    user_id=user_id,
                    data={
                        "cursor_position": cursor_position,
                        "selection_start": selection_start,
                        "selection_end": selection_end
                    }
                ),
                exclude_user=user_id
            )
    
    async def add_comment(self, user_id: str, document_id: str, content: str, position: int):
        """Add comment to document"""
        if document_id not in self.documents:
            return
        
        document = self.documents[document_id]
        
        comment = Comment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            username=document.presence.get(user_id, UserPresence(user_id, user_id)).username,
            content=content,
            position=position,
            created_at=datetime.utcnow()
        )
        
        document.add_comment(comment)
        
        # Broadcast comment addition
        await self.broadcast_event(
            document_id,
            CollaborationEvent(
                type=CollaborationEventType.COMMENT_ADD,
                user_id=user_id,
                data=asdict(comment)
            )
        )
    
    async def resolve_comment(self, user_id: str, document_id: str, comment_id: str):
        """Resolve a comment"""
        if document_id not in self.documents:
            return
        
        document = self.documents[document_id]
        document.resolve_comment(comment_id, user_id)
        
        # Broadcast comment resolution
        await self.broadcast_event(
            document_id,
            CollaborationEvent(
                type=CollaborationEventType.COMMENT_RESOLVE,
                user_id=user_id,
                data={
                    "comment_id": comment_id,
                    "resolved_by": user_id,
                    "resolved_at": datetime.utcnow().isoformat()
                }
            )
        )
    
    async def broadcast_operation(self, document_id: str, operation: Operation, exclude_user: Optional[str] = None):
        """Broadcast operation to all users in document"""
        if document_id not in self.documents:
            return
        
        document = self.documents[document_id]
        
        for user_id, presence in document.presence.items():
            if user_id != exclude_user:
                # Find user's connections
                for connection_id, websocket in self.connections.items():
                    try:
                        if websocket.state == WebSocketState.CONNECTED:
                            await websocket.send_text(json.dumps({
                                "type": "operation",
                                "data": asdict(operation),
                                "version": document.version
                            }))
                    except Exception as e:
                        logger.error(f"Error broadcasting operation: {e}")
    
    async def broadcast_event(self, document_id: str, event: CollaborationEvent, exclude_user: Optional[str] = None):
        """Broadcast event to all users in document"""
        if document_id not in self.documents:
            return
        
        for user_id, presence in self.documents[document_id].presence.items():
            if user_id != exclude_user:
                for connection_id, websocket in self.connections.items():
                    try:
                        if websocket.state == WebSocketState.CONNECTED:
                            await websocket.send_text(json.dumps({
                                "type": "event",
                                "data": asdict(event)
                            }))
                    except Exception as e:
                        logger.error(f"Error broadcasting event: {e}")
    
    async def send_document_state(self, connection_id: str, document_id: str):
        """Send current document state to connection"""
        if document_id not in self.documents or connection_id not in self.connections:
            return
        
        document = self.documents[document_id]
        websocket = self.connections[connection_id]
        
        try:
            if websocket.state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps({
                    "type": "document_state",
                    "data": {
                        "content": document.content,
                        "version": document.version,
                        "presence": {uid: asdict(presence) for uid, presence in document.presence.items()},
                        "comments": {cid: asdict(comment) for cid, comment in document.comments.items()}
                    }
                }))
        except Exception as e:
            logger.error(f"Error sending document state: {e}")
    
    async def cleanup_inactive_users(self):
        """Periodic cleanup of inactive users"""
        for document_id, document in self.documents.items():
            inactive_users = document.cleanup_inactive_users()
            
            for user_id in inactive_users:
                await self.broadcast_event(
                    document_id,
                    CollaborationEvent(
                        type=CollaborationEventType.USER_LEAVE,
                        user_id=user_id,
                        data={"username": user_id}
                    )
                )
    
    def _generate_user_color(self, user_id: str) -> str:
        """Generate consistent color for user"""
        colors = [
            "#007bff", "#28a745", "#dc3545", "#ffc107", "#17a2b8",
            "#6f42c1", "#e83e8c", "#fd7e14", "#20c997", "#6c757d"
        ]
        
        hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        return colors[hash_value % len(colors)]
    
    async def get_document_stats(self, document_id: str) -> Dict[str, Any]:
        """Get document collaboration statistics"""
        if document_id not in self.documents:
            return {}
        
        document = self.documents[document_id]
        
        return {
            "document_id": document_id,
            "version": document.version,
            "active_users": len(document.presence),
            "total_operations": len(document.operations),
            "total_comments": len(document.comments),
            "resolved_comments": sum(1 for comment in document.comments.values() if comment.resolved),
            "last_modified": document.last_modified.isoformat(),
            "content_length": len(document.content)
        }


# Global collaboration manager instance
collaboration_manager = CollaborationManager()
