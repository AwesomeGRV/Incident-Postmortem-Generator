# Incident Postmortem Generator

A production-ready web application for generating comprehensive incident postmortems from timeline data. Built for SRE teams to create consistent, high-quality postmortems quickly and efficiently.

## Features

- **Web-based Interface**: Clean, responsive UI for inputting incident data
- **Multiple Input Formats**: Accept both JSON and YAML incident data
- **Google SRE-style Postmortems**: Follow industry best practices for incident analysis
- **Contributing Factors Analysis**: Categorize technical, process, people, and external factors
- **Action Items Management**: Generate categorized action items with priorities
- **What Went Well/Wrong Analysis**: Structured analysis of incident response
- **Jira Integration**: Automatically create Jira tickets for action items
- **Multiple Output Formats**: Generate Markdown and PDF outputs
- **Production Ready**: Docker support, environment configuration, and proper error handling

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd incident-postmortem-generator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python run.py
```

4. Open your browser and navigate to:
```
http://localhost:8000
```

## Usage

### 1. Prepare Incident Data

Create your incident data in JSON or YAML format. Here's a sample structure:

#### JSON Format
```json
{
  "title": "Database Connection Pool Exhaustion",
  "severity": "high",
  "start_time": "2024-01-15T10:30:00Z",
  "end_time": "2024-01-15T11:45:00Z",
  "description": "Application experienced database connection pool exhaustion",
  "timeline": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "event": "Alert triggered: High database connection usage",
      "severity": "medium",
      "source": "Prometheus"
    }
  ],
  "impact": [
    {
      "type": "availability",
      "description": "Service availability degraded to 70%",
      "affected_users": 5000,
      "affected_services": ["user-service", "order-service"],
      "duration_minutes": 75
    }
  ],
  "contributing_factors": [
    {
      "factor": "Connection leak in recent deployment",
      "category": "technical",
      "description": "Recent code changes introduced a database connection leak"
    }
  ],
  "action_items": [
    {
      "title": "Fix database connection leak",
      "description": "Identify and fix the root cause of the connection leak",
      "category": "immediate",
      "priority": "high",
      "assignee": "backend-team"
    }
  ],
  "what_went_well": [
    "Quick response from on-call engineer"
  ],
  "what_went_wrong": [
    "Connection leak was not caught in pre-deployment testing"
  ]
}
```

#### YAML Format
```yaml
title: Database Connection Pool Exhaustion
severity: high
start_time: 2024-01-15T10:30:00Z
end_time: 2024-01-15T11:45:00Z
description: Application experienced database connection pool exhaustion

timeline:
  - timestamp: 2024-01-15T10:30:00Z
    event: Alert triggered: High database connection usage
    severity: medium
    source: Prometheus

impact:
  - type: availability
    description: Service availability degraded to 70%
    affected_users: 5000
    affected_services: [user-service, order-service]
    duration_minutes: 75

contributing_factors:
  - factor: Connection leak in recent deployment
    category: technical
    description: Recent code changes introduced a database connection leak

action_items:
  - title: Fix database connection leak
    description: Identify and fix the root cause of the connection leak
    category: immediate
    priority: high
    assignee: backend-team

what_went_well:
  - Quick response from on-call engineer

what_went_wrong:
  - Connection leak was not caught in pre-deployment testing
```

### 2. Generate Postmortem

1. Paste your incident data into the web interface
2. Select output format (Markdown, PDF, or both)
3. Optionally configure Jira integration
4. Click "Generate Postmortem"

### 3. Review and Export

- Preview the generated postmortem
- Copy Markdown content
- Download PDF version
- View created Jira tickets (if configured)

## Data Model Reference

### Incident Fields

- **title**: String - Incident title
- **severity**: Enum - low, medium, high, critical
- **start_time**: ISO 8601 datetime - When incident started
- **end_time**: ISO 8601 datetime - When incident ended (optional)
- **description**: String - Detailed incident description
- **timeline**: Array of TimelineEvent objects
- **alerts**: Array of Alert objects (optional)
- **impact**: Array of Impact objects
- **contributing_factors**: Array of ContributingFactor objects (optional)
- **action_items**: Array of ActionItem objects (optional)
- **what_went_well**: Array of strings (optional)
- **what_went_wrong**: Array of strings (optional)

### TimelineEvent

- **timestamp**: ISO 8601 datetime
- **event**: String - Description of the event
- **severity**: Enum - low, medium, high, critical (default: medium)
- **source**: String - Source of the event (optional)

### Alert

- **name**: String - Alert name
- **timestamp**: ISO 8601 datetime
- **severity**: Enum - low, medium, high, critical
- **description**: String - Alert description
- **source**: String - Alert source

### Impact

- **type**: Enum - availability, performance, functionality, data, security
- **description**: String - Impact description
- **affected_users**: Integer - Number of affected users (optional)
- **affected_services**: Array of strings - Affected service names (optional)
- **duration_minutes**: Integer - Impact duration in minutes (optional)

### ContributingFactor

- **factor**: String - Factor description
- **category**: String - technical, process, people, external
- **description**: String - Detailed description

### ActionItem

- **title**: String - Action item title
- **description**: String - Detailed description
- **category**: String - immediate, short_term, long_term, preventive
- **priority**: Enum - low, medium, high, critical
- **assignee**: String - Assigned person or team (optional)
- **due_date**: ISO 8601 date - Due date (optional)

## Jira Integration

### Setup

1. Configure Jira credentials using environment variables:

```bash
export JIRA_URL="https://your-company.atlassian.net"
export JIRA_USERNAME="your-email@company.com"
export JIRA_TOKEN="your-api-token"
export JIRA_PROJECT_KEY="INC"
```

2. Generate an API token in Jira:
   - Go to Account Settings > Security > API tokens
   - Create and copy the token

### Features

- Automatic ticket creation for action items
- Proper issue type mapping (Bug, Task, Story)
- Priority mapping based on action item priority
- Automatic labeling and assignment
- Links back to incident postmortem

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DEBUG | false | Enable debug mode |
| HOST | 0.0.0.0 | Server host |
| PORT | 8000 | Server port |
| JIRA_URL | - | Jira instance URL |
| JIRA_USERNAME | - | Jira username |
| JIRA_TOKEN | - | Jira API token |
| JIRA_PROJECT_KEY | INC | Default Jira project key |
| OUTPUT_DIR | outputs | Directory for generated files |
| TEMP_DIR | temp | Directory for temporary files |

### Docker Deployment

1. Build the Docker image:
```bash
docker build -t incident-postmortem-generator .
```

2. Run with environment variables:
```bash
docker run -p 8000:8000 \
  -e JIRA_URL="https://your-company.atlassian.net" \
  -e JIRA_USERNAME="your-email@company.com" \
  -e JIRA_TOKEN="your-api-token" \
  incident-postmortem-generator
```

3. Or use docker-compose:
```yaml
version: '3.8'
services:
  postmortem-generator:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - JIRA_URL=https://your-company.atlassian.net
      - JIRA_USERNAME=your-email@company.com
      - JIRA_TOKEN=your-api-token
      - JIRA_PROJECT_KEY=INC
    volumes:
      - ./outputs:/app/outputs
```

## API Usage

### Generate Postmortem

```bash
curl -X POST "http://localhost:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "incident_data": {
      "title": "Sample Incident",
      "severity": "high",
      "start_time": "2024-01-15T10:30:00Z",
      "description": "Sample incident description",
      "timeline": [],
      "impact": [],
      "contributing_factors": [],
      "action_items": [],
      "what_went_well": [],
      "what_went_wrong": []
    },
    "format": "markdown",
    "jira_config": {
      "url": "https://your-company.atlassian.net",
      "username": "your-email@company.com",
      "token": "your-api-token",
      "project_key": "INC"
    }
  }'
```

### Health Check

```bash
curl "http://localhost:8000/api/health"
```

## Development

### Project Structure

```
incident-postmortem-generator/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic data models
│   ├── generator.py         # Postmortem generation logic
│   ├── templates.py         # Jinja2 templates
│   ├── pdf_converter.py     # PDF generation
│   └── jira_integration.py  # Jira API integration
├── templates/
│   ├── index.html           # Main web interface
│   └── result.html          # Results display
├── static/
│   └── style.css            # Static styles
├── config.py                # Configuration management
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

### Running in Development Mode

```bash
export DEBUG=true
python run.py
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

## Troubleshooting

### PDF Generation Issues

If PDF generation fails, ensure you have the required system dependencies:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
```

**macOS:**
```bash
brew install pango
```

**Windows:**
PDF generation should work out of the box with the included dependencies.

### Jira Integration Issues

1. Verify your Jira URL and credentials
2. Ensure you have proper permissions in the Jira project
3. Check that the project key exists
4. Verify API token has the necessary permissions

### Common Errors

- **Validation errors**: Check that your incident data matches the required schema
- **Connection timeouts**: Increase timeout values for slow systems
- **Memory issues**: Reduce the size of incident data or increase system memory

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Search existing GitHub issues
3. Create a new issue with detailed information

## Changelog

### Version 1.0.0
- Initial release
- Web-based interface
- JSON/YAML input support
- Markdown and PDF output
- Jira integration
- Google SRE-style postmortem generation
