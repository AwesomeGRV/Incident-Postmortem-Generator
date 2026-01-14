import requests
import json
from typing import List, Optional
from .models import ActionItem, JiraTicket, PostmortemOutput


class JiraIntegration:
    def __init__(self, base_url: str, username: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.auth = (username, api_token)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def create_action_item_tickets(self, action_items: List[ActionItem], 
                                 project_key: str, 
                                 postmortem: PostmortemOutput) -> List[dict]:
        """Create Jira tickets for action items"""
        created_tickets = []
        
        for item in action_items:
            ticket = self._create_action_item_ticket(item, project_key, postmortem)
            if ticket:
                created_tickets.append(ticket)
        
        return created_tickets
    
    def _create_action_item_ticket(self, action_item: ActionItem, 
                                 project_key: str, 
                                 postmortem: PostmortemOutput) -> Optional[dict]:
        """Create a single Jira ticket for an action item"""
        
        # Map priority levels
        priority_map = {
            "low": "Low",
            "medium": "Medium",
            "high": "High",
            "critical": "Highest"
        }
        
        # Map issue types
        issue_type_map = {
            "immediate": "Bug",
            "short_term": "Task", 
            "long_term": "Story",
            "preventive": "Task"
        }
        
        issue_type = issue_type_map.get(action_item.category, "Task")
        priority = priority_map.get(action_item.priority.value, "Medium")
        
        # Build ticket description
        description = f"""h2. Incident Context
*Incident ID:* {postmortem.incident_id}
*Incident Title:* {postmortem.title}
*Severity:* {postmortem.severity.value.upper()}
*Date:* {postmortem.start_time.strftime('%Y-%m-%d')}

h2. Action Item Details
*Category:* {action_item.category.replace('_', ' ').title()}
*Priority:* {action_item.priority.value.upper()}

h2. Description
{action_item.description}

h2. Acceptance Criteria
- [ ] Action item is fully implemented
- [ ] Testing completed and verified
- [ ] Documentation updated if required
- [ ] Post-implementation review conducted

---
*This ticket was automatically generated from incident postmortem {postmortem.incident_id}*
"""
        
        ticket_data = {
            "fields": {
                "project": {"key": project_key},
                "summary": f"[{postmortem.incident_id}] {action_item.title}",
                "description": description,
                "issuetype": {"name": issue_type},
                "priority": {"name": priority},
                "labels": [f"incident-{postmortem.incident_id}", "postmortem-action", action_item.category]
            }
        }
        
        # Add assignee if specified
        if action_item.assignee:
            ticket_data["fields"]["assignee"] = {"name": action_item.assignee}
        
        # Add due date if specified
        if action_item.due_date:
            ticket_data["fields"]["duedate"] = action_item.due_date.strftime('%Y-%m-%d')
        
        try:
            response = requests.post(
                f"{self.base_url}/rest/api/2/issue",
                auth=self.auth,
                headers=self.headers,
                data=json.dumps(ticket_data)
            )
            
            if response.status_code == 201:
                ticket_info = response.json()
                return {
                    "key": ticket_info["key"],
                    "url": f"{self.base_url}/browse/{ticket_info['key']}",
                    "title": action_item.title,
                    "status": "created"
                }
            else:
                return {
                    "title": action_item.title,
                    "status": "error",
                    "error": response.text
                }
                
        except Exception as e:
            return {
                "title": action_item.title,
                "status": "error", 
                "error": str(e)
            }
    
    def test_connection(self) -> bool:
        """Test connection to Jira instance"""
        try:
            response = requests.get(
                f"{self.base_url}/rest/api/2/myself",
                auth=self.auth,
                headers=self.headers
            )
            return response.status_code == 200
        except:
            return False
