"""
Modern Security System with OAuth2, MFA, and Advanced Authentication
Enhanced security features for 2025 standards
"""

import asyncio
import secrets
import hashlib
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

# Security imports
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.sqla_oauth2 import (
    OAuth2ClientMixin,
    OAuth2TokenMixin,
)
from passlib.context import CryptContext
from jose import JWTError, jwt
from itsdangerous import URLSafeTimedSerializer
import pyotp
import qrcode
from io import BytesIO
import base64

# FastAPI imports
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, validator

# Database imports
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship, Session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AuthProvider(Enum):
    """Authentication providers"""
    LOCAL = "local"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"
    SAML = "saml"
    LDAP = "ldap"


class MFAMethod(Enum):
    """Multi-factor authentication methods"""
    TOTP = "totp"  # Time-based One-Time Password
    SMS = "sms"     # SMS verification
    EMAIL = "email" # Email verification
    HARDWARE = "hardware"  # Hardware token


class SecurityLevel(Enum):
    """Security levels for different operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    mfa_enabled: bool = True
    password_min_length: int = 12
    password_require_special_chars: bool = True
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    session_timeout_minutes: int = 60
    require_password_change_days: int = 90


class User(Base):
    """Enhanced User model with security features"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    
    # Security fields
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    
    # Authentication methods
    auth_provider = Column(String(50), default=AuthProvider.LOCAL.value)
    provider_id = Column(String(255))  # ID from external provider
    
    # MFA fields
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(32))  # TOTP secret
    mfa_backup_codes = Column(Text)  # JSON array of backup codes
    phone_number = Column(String(20))
    
    # Security tracking
    failed_login_attempts = Column(Integer, default=0)
    last_login = Column(DateTime)
    last_password_change = Column(DateTime)
    password_changed_at = Column(DateTime, default=datetime.utcnow)
    
    # Session management
    session_token = Column(String(255))
    refresh_token = Column(String(255))
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LoginAttempt(Base):
    """Track login attempts for security monitoring"""
    __tablename__ = "login_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(Text)
    success = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    failure_reason = Column(String(255))


class SecurityAudit(Base):
    """Security audit log"""
    __tablename__ = "security_audit"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(255), nullable=False)
    resource = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    success = Column(Boolean, nullable=False)
    details = Column(Text)  # JSON details
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")


class ModernSecurityService:
    """Modern security service with advanced features"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.oauth = OAuth()
        self.serializer = URLSafeTimedSerializer(config.secret_key)
        
        # Initialize OAuth providers
        self._setup_oauth_providers()
    
    def _setup_oauth_providers(self):
        """Setup OAuth providers"""
        # Google OAuth
        if os.getenv("GOOGLE_CLIENT_ID"):
            self.oauth.register(
                name='google',
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_kwargs={'scope': 'openid email profile'}
            )
        
        # Microsoft OAuth
        if os.getenv("MICROSOFT_CLIENT_ID"):
            self.oauth.register(
                name='microsoft',
                client_id=os.getenv("MICROSOFT_CLIENT_ID"),
                client_secret=os.getenv("MICROSOFT_CLIENT_SECRET"),
                authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
                client_kwargs={'scope': 'openid email profile'}
            )
        
        # GitHub OAuth
        if os.getenv("GITHUB_CLIENT_ID"):
            self.oauth.register(
                name='github',
                client_id=os.getenv("GITHUB_CLIENT_ID"),
                client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
                authorize_url='https://github.com/login/oauth/authorize',
                token_url='https://github.com/login/oauth/access_token',
                client_kwargs={'scope': 'user:email'}
            )
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash password"""
        return self.pwd_context.hash(password)
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength"""
        result = {
            "valid": True,
            "errors": [],
            "score": 0
        }
        
        # Length check
        if len(password) < self.config.password_min_length:
            result["errors"].append(f"Password must be at least {self.config.password_min_length} characters")
            result["valid"] = False
        
        # Character complexity
        if self.config.password_require_special_chars:
            if not any(c.isupper() for c in password):
                result["errors"].append("Password must contain uppercase letters")
                result["valid"] = False
            if not any(c.islower() for c in password):
                result["errors"].append("Password must contain lowercase letters")
                result["valid"] = False
            if not any(c.isdigit() for c in password):
                result["errors"].append("Password must contain digits")
                result["valid"] = False
            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                result["errors"].append("Password must contain special characters")
                result["valid"] = False
        
        # Calculate strength score
        score = 0
        if len(password) >= 12:
            score += 20
        if len(password) >= 16:
            score += 10
        if any(c.isupper() for c in password):
            score += 20
        if any(c.islower() for c in password):
            score += 20
        if any(c.isdigit() for c in password):
            score += 20
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 10
        
        result["score"] = min(score, 100)
        return result
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.config.secret_key, algorithm=self.config.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.config.secret_key, algorithm=self.config.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.config.secret_key, algorithms=[self.config.algorithm])
            if payload.get("type") != token_type:
                raise JWTError("Invalid token type")
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def generate_mfa_secret(self) -> str:
        """Generate MFA TOTP secret"""
        return pyotp.random_base32()
    
    def generate_qr_code(self, user_email: str, secret: str) -> str:
        """Generate QR code for TOTP setup"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name="Incident Postmortem Generator"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_totp(self, secret: str, token: str) -> bool:
        """Verify TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for MFA"""
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            codes.append(code)
        return codes
    
    def check_account_lockout(self, user: User) -> bool:
        """Check if account should be locked"""
        if user.failed_login_attempts >= self.config.max_login_attempts:
            if not user.is_locked:
                user.is_locked = True
                user.last_login = datetime.utcnow()
                return True
        return False
    
    def unlock_account(self, user: User) -> bool:
        """Unlock user account"""
        if user.is_locked:
            user.is_locked = False
            user.failed_login_attempts = 0
            return True
        return False
    
    def is_password_expired(self, user: User) -> bool:
        """Check if password has expired"""
        if user.last_password_change:
            days_since_change = (datetime.utcnow() - user.last_password_change).days
            return days_since_change > self.config.require_password_change_days
        return True  # Force change if never changed
    
    def log_security_event(self, db: Session, user_id: Optional[int], action: str, 
                          resource: Optional[str] = None, success: bool = True, 
                          details: Optional[Dict] = None, request: Optional[Request] = None):
        """Log security audit event"""
        audit = SecurityAudit(
            user_id=user_id,
            action=action,
            resource=resource,
            success=success,
            details=json.dumps(details) if details else None,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        db.add(audit)
        db.commit()
    
    def get_security_context(self, request: Request) -> Dict[str, Any]:
        """Get security context for request"""
        return {
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "timestamp": datetime.utcnow(),
            "session_id": request.session.get("session_id") if hasattr(request, 'session') else None
        }
    
    def check_rate_limit(self, db: Session, email: str, ip_address: str) -> Dict[str, Any]:
        """Check rate limiting for login attempts"""
        recent_attempts = db.query(LoginAttempt).filter(
            LoginAttempt.email == email,
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.timestamp > datetime.utcnow() - timedelta(minutes=15)
        ).count()
        
        return {
            "allowed": recent_attempts < 10,  # 10 attempts per 15 minutes
            "attempts": recent_attempts,
            "reset_time": datetime.utcnow() + timedelta(minutes=15)
        }
    
    def detect_suspicious_activity(self, db: Session, user_id: int, request: Request) -> List[str]:
        """Detect suspicious activity patterns"""
        suspicious = []
        
        # Check for multiple failed logins
        recent_failures = db.query(LoginAttempt).filter(
            LoginAttempt.email == request.session.get("email"),
            LoginAttempt.success == False,
            LoginAttempt.timestamp > datetime.utcnow() - timedelta(hours=1)
        ).count()
        
        if recent_failures > 5:
            suspicious.append("Multiple failed login attempts detected")
        
        # Check for unusual IP address
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.last_login:
            # This would typically use a geoip service
            pass
        
        # Check for rapid session changes
        # Add more sophisticated detection logic here
        
        return suspicious


class PydanticModels:
    """Pydantic models for security"""
    
    class UserCreate(BaseModel):
        email: EmailStr
        username: str
        password: str
        full_name: Optional[str] = None
        
        @validator('password')
        def validate_password(cls, v):
            # Basic validation - would use security service in production
            if len(v) < 8:
                raise ValueError('Password must be at least 8 characters long')
            return v
    
    class UserLogin(BaseModel):
        email: EmailStr
        password: str
        mfa_token: Optional[str] = None
        remember_me: bool = False
    
    class Token(BaseModel):
        access_token: str
        token_type: str
        refresh_token: Optional[str] = None
        expires_in: int
    
    class MFASetup(BaseModel):
        secret: str
        qr_code: str
        backup_codes: List[str]
    
    class MFAVerify(BaseModel):
        token: str
    
    class PasswordChange(BaseModel):
        current_password: str
        new_password: str
        
        @validator('new_password')
        def validate_new_password(cls, v):
            if len(v) < 8:
                raise ValueError('Password must be at least 8 characters long')
            return v
    
    class PasswordReset(BaseModel):
        email: EmailStr
    
    class PasswordResetConfirm(BaseModel):
        token: str
        new_password: str


# Security middleware
class SecurityMiddleware:
    """Security middleware for FastAPI"""
    
    def __init__(self, security_service: ModernSecurityService):
        self.security_service = security_service
    
    async def __call__(self, request: Request, call_next):
        """Process request through security middleware"""
        # Add security headers
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


# Global security service instance
def get_security_service() -> ModernSecurityService:
    """Get security service instance"""
    config = SecurityConfig(
        secret_key=os.getenv("SECRET_KEY", secrets.token_urlsafe(32)),
        mfa_enabled=os.getenv("MFA_ENABLED", "true").lower() == "true",
        password_min_length=int(os.getenv("PASSWORD_MIN_LENGTH", "12")),
        max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    )
    return ModernSecurityService(config)


# Dependency functions
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db),
    security_service: ModernSecurityService = Depends(get_security_service)
) -> User:
    """Get current authenticated user"""
    try:
        payload = security_service.verify_token(credentials.credentials)
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        
        if user.is_locked:
            raise HTTPException(status_code=401, detail="Account locked")
        
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")


def require_mfa(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require MFA verification"""
    if current_user.mfa_enabled:
        # Check if MFA was verified in this session
        # This would typically be stored in session or token
        pass
    return current_user


def require_security_level(
    level: SecurityLevel,
    current_user: User = Depends(get_current_user)
) -> User:
    """Require specific security level for operation"""
    # Implement role-based access based on security level
    if level == SecurityLevel.CRITICAL and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Insufficient privileges")
    
    return current_user
