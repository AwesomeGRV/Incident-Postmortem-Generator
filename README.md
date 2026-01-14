# Enterprise Incident Postmortem Generator

A production-ready, enterprise-grade web application for generating comprehensive incident postmortems from timeline data. Built for SRE teams with advanced features including authentication, analytics, SLA tracking, notifications, and role-based access control.

## **Enterprise Features**

### **Core Capabilities**
- **Web-based Interface**: Clean, responsive UI with modern design
- **Multiple Input Formats**: Accept both JSON and YAML incident data
- **Google SRE-style Postmortems**: Follow industry best practices
- **Contributing Factors Analysis**: Categorize technical, process, people, and external factors
- **Action Items Management**: Generate categorized action items with priorities
- **What Went Well/Wrong Analysis**: Structured analysis of incident response

### **Enterprise Features**
- **Authentication & Authorization**: JWT-based auth with role-based access control
- **User Management**: Admin, Editor, and Viewer roles with granular permissions
- **Analytics Dashboard**: Real-time metrics, trends, and SLA compliance reporting
- **SLA Tracking**: Automated SLA monitoring and breach alerts
- **Notification System**: Email, Slack, and webhook notifications
- **Audit Logging**: Complete audit trail for compliance and security
- **Advanced Search**: Full-text search with filtering capabilities
- **Database Storage**: Persistent storage with history and versioning
- **API Rate Limiting**: Protect against abuse and ensure performance
- **Production Ready**: Docker support, environment configuration, monitoring

### **Integrations**
- **Jira Integration**: Automatically create tickets for action items
- **Slack Notifications**: Real-time alerts and updates
- **Email Notifications**: Automated email reports and alerts
- **Webhook Support**: Custom integrations via webhooks
- **Prometheus Metrics**: Export metrics for monitoring

## **Quick Start**

### **Prerequisites**
- Python 3.8 or higher
- PostgreSQL (recommended) or SQLite for development
- Redis (for background tasks and caching)

### **Installation**

1. **Clone the repository:**
```bash
git clone <repository-url>
cd incident-postmortem-generator
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Initialize database:**
```bash
# For PostgreSQL
export DATABASE_URL="postgresql://user:password@localhost/incident_db"

# For SQLite (development)
export DATABASE_URL="sqlite:///./incident_postmortem.db"
```

5. **Run the application:**
```bash
python run.py
```

6. **Access the application:**
```
http://localhost:8000
```

## **Configuration**

### **Environment Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | false | Enable debug mode |
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 8000 | Server port |
| `DATABASE_URL` | sqlite:///./incident_postmortem.db | Database connection string |
| `SECRET_KEY` | - | JWT secret key (required) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Token expiration time |

#### **Authentication**
| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing secret (generate with: `openssl rand -hex 32`) |

#### **Email Configuration**
| Variable | Description |
|----------|-------------|
| `SMTP_SERVER` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (default: 587) |
| `SMTP_USERNAME` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `SMTP_FROM_EMAIL` | From email address |
| `SMTP_USE_TLS` | Use TLS (default: true) |

#### **Slack Integration**
| Variable | Description |
|----------|-------------|
| `SLACK_BOT_TOKEN` | Slack bot token for notifications |

#### **Jira Integration**
| Variable | Description |
|----------|-------------|
| `JIRA_URL` | Jira instance URL |
| `JIRA_USERNAME` | Jira username |
| `JIRA_TOKEN` | Jira API token |
| `JIRA_PROJECT_KEY` | Default project key (INC) |

#### **Notification Settings**
| Variable | Description |
|----------|-------------|
| `SLA_ALERT_RECIPIENTS` | Comma-separated list of SLA alert recipients |
| `ESCALATION_RECIPIENTS` | Comma-separated list of escalation recipients |

## **Usage Guide**

### **1. User Management**

#### **Creating Users (Admin only)**
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "grv",
    "email": "grv@company.com",
    "password": "securepassword",
    "full_name": "Awesome GRV",
    "role": "editor"
  }'
```

#### **Login**
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "grv",
    "password": "securepassword"
  }'
```

### **2. Incident Management**

#### **Create Incident**
```bash
curl -X POST "http://localhost:8000/api/incidents" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d @incident_data.json
```

#### **Search Incidents**
```bash
curl "http://localhost:8000/api/incidents?severity=high&status=published" \
  -H "Authorization: Bearer <token>"
```

#### **Export to PDF**
```bash
curl -X POST "http://localhost:8000/api/incidents/123/export/pdf" \
  -H "Authorization: Bearer <token>" \
  --output incident_123.pdf
```

### **3. Analytics and Reporting**

#### **Get Metrics**
```bash
curl "http://localhost:8000/api/analytics/metrics?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer <token>"
```

#### **SLA Report**
```bash
curl "http://localhost:8000/api/analytics/sla?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer <token>"
```

## **Architecture**

### **System Components**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend │    │   API Gateway   │    │   Auth Service │
│   (FastAPI)    │◄──►│   (FastAPI)    │◄──►│   (JWT)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Analytics     │    │   Notification  │    │   Audit Log     │
│   Service      │    │   Service      │    │   Service      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Database Layer                        │
│              (PostgreSQL / SQLite)                     │
└─────────────────────────────────────────────────────────────────┘
```

### **Data Models**

#### **User Management**
- **Users**: Authentication, roles, permissions
- **Roles**: Admin, Editor, Viewer with granular permissions

#### **Incident Management**
- **Incidents**: Core incident data with full history
- **Timeline**: Event timeline with timestamps and sources
- **Impact**: Business impact analysis with metrics
- **Action Items**: Trackable tasks with assignments and due dates

#### **Analytics & Compliance**
- **SLA Metrics**: Automated SLA tracking and compliance
- **Analytics**: Custom metrics and trend analysis
- **Audit Logs**: Complete audit trail for compliance

## **Security Features**

### **Authentication & Authorization**
- **JWT-based Authentication**: Secure token-based auth
- **Role-based Access Control**: Granular permissions by role
- **Session Management**: Secure session handling
- **Password Security**: Bcrypt hashing with salt

### **API Security**
- **Rate Limiting**: Prevent abuse and ensure availability
- **CORS Configuration**: Proper cross-origin resource sharing
- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Protection**: Parameterized queries

### **Audit & Compliance**
- **Complete Audit Trail**: Log all user actions
- **Data Retention**: Configurable retention policies
- **Compliance Reporting**: Generate compliance reports
- **Privacy Controls**: Data privacy and GDPR considerations

## **Monitoring & Observability**

### **Metrics Collection**
- **Application Metrics**: Response times, error rates, user activity
- **Business Metrics**: Incident volume, SLA compliance, resolution times
- **System Metrics**: Database performance, resource usage
- **Custom Metrics**: Extensible metric collection

### **Alerting**
- **SLA Breaches**: Automatic alerts for SLA violations
- **System Health**: Application and infrastructure health
- **Business Alerts**: Critical incidents and escalations
- **Custom Alerts**: Configurable alert rules

### **Integrations**
- **Prometheus**: Export metrics for monitoring
- **Grafana**: Pre-built dashboards
- **PagerDuty**: Critical incident escalation
- **Custom Webhooks**: Flexible integration options

## **Docker Deployment**

### **Development Environment**
```bash
docker-compose -f docker-compose.dev.yml up
```

### **Production Environment**
```bash
# Configure environment variables
export DATABASE_URL="postgresql://user:pass@db:5432/incident_db"
export SECRET_KEY="your-secret-key"
export SMTP_SERVER="smtp.company.com"

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### **Kubernetes Deployment**
```bash
# Apply configurations
kubectl apply -f k8s/
```

## **Testing**

### **Unit Tests**
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/ --cov=app --cov-report=html
```

### **Integration Tests**
```bash
# Run integration tests
pytest tests/integration/ --env=test
```

### **Load Testing**
```bash
# Install load testing tools
pip install locust

# Run load tests
locust -f tests/load_test.py --host=http://localhost:8000
```

## **Development Guide**

### **Setting Up Development Environment**
```bash
# Clone repository
git clone <repository-url>
cd incident-postmortem-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup database
createdb incident_dev
export DATABASE_URL="postgresql://localhost/incident_dev"

# Run migrations
alembic upgrade head

# Start development server
python run.py
```

### **Code Style**
```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint code
flake8 app/ tests/
mypy app/

# Run pre-commit hooks
pre-commit run --all-files
```

### **Database Migrations**
```bash
# Create migration
alembic revision --autogenerate -m "Add new feature"

# Apply migration
alembic upgrade head

# Downgrade migration
alembic downgrade -1
```

## **Troubleshooting**

### **Common Issues**

#### **Database Connection Issues**
```bash
# Check database connection
python -c "from app.database import engine; print(engine.execute('SELECT 1').scalar())"

# Reset database
alembic downgrade base
alembic upgrade head
```

#### **Authentication Issues**
```bash
# Generate new secret key
openssl rand -hex 32

# Test JWT token
python -c "
import jwt
token = jwt.encode({'test': 'data'}, 'your-secret', algorithm='HS256')
print(jwt.decode(token, 'your-secret', algorithms=['HS256']))
"
```

#### **Performance Issues**
```bash
# Check database performance
python -c "
from app.database import engine
print(engine.execute('EXPLAIN ANALYZE SELECT * FROM incidents LIMIT 10').fetchall())
"
```

### **Monitoring Issues**
```bash
# Check application logs
docker-compose logs app

# Check database logs
docker-compose logs db

# Check system resources
docker stats
```

## **API Reference**

### **Authentication Endpoints**
- `POST /auth/login` - User login
- `POST /auth/register` - User registration (admin only)
- `GET /auth/me` - Get current user info

### **Incident Endpoints**
- `GET /api/incidents` - List incidents with filtering
- `POST /api/incidents` - Create new incident
- `GET /api/incidents/{id}` - Get incident details
- `PUT /api/incidents/{id}` - Update incident
- `DELETE /api/incidents/{id}` - Delete incident
- `POST /api/incidents/{id}/publish` - Publish incident
- `GET /api/incidents/{id}/history` - Get audit history
- `POST /api/incidents/{id}/export/pdf` - Export to PDF

### **Analytics Endpoints**
- `GET /api/analytics/metrics` - Get incident metrics
- `GET /api/analytics/sla` - Get SLA compliance report
- `GET /api/analytics/heatmap` - Get incident heatmap

### **System Endpoints**
- `GET /api/health` - Health check
- `GET /api/version` - Version information

## **Contributing**

### **Development Workflow**
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `pytest`
6. Commit your changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open Pull Request

### **Code Standards**
- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation
- Use meaningful commit messages
- Ensure CI/CD pipeline passes

## **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## **Support**

### **Documentation**
- [User Guide](docs/user-guide.md)
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Troubleshooting](docs/troubleshooting.md)

### **Community**
- [GitHub Issues](https://github.com/company/incident-postmortem-generator/issues)
- [Discussions](https://github.com/company/incident-postmortem-generator/discussions)
- [Wiki](https://github.com/company/incident-postmortem-generator/wiki)

### **Enterprise Support**
For enterprise support, custom development, or consulting:
- Email: enterprise@company.com
- Phone: +1-555-0123
- Website: https://company.com/enterprise-support

## **Changelog**

### **Version 2.0.0** (Enterprise Release)
- Added user authentication and role-based access control
- Implemented database storage with full history
- Added advanced search and filtering capabilities
- Built analytics dashboard with real-time metrics
- Implemented SLA tracking and compliance reporting
- Added multi-channel notification system (Email, Slack, Webhooks)
- Implemented comprehensive audit logging
- Added API rate limiting and security features
- Created enterprise-grade configuration management
- Added Docker and Kubernetes deployment support

### **Version 1.0.0** (Initial Release)
- Basic incident postmortem generation
- JSON/YAML input support
- Markdown and PDF output
- Jira integration
- Web-based interface
