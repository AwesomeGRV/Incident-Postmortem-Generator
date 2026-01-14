from typing import List
from datetime import datetime, timedelta
import uuid
from .models import (
    IncidentInput, 
    PostmortemOutput, 
    TimelineEvent, 
    ContributingFactor,
    ActionItem,
    SeverityLevel
)


class PostmortemGenerator:
    def __init__(self):
        pass
    
    def generate_postmortem(self, incident: IncidentInput) -> PostmortemOutput:
        # Generate unique incident ID
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Calculate duration if not provided
        duration = incident.duration_minutes
        if duration is None and incident.end_time:
            duration = int((incident.end_time - incident.start_time).total_seconds() / 60)
        elif duration is None:
            duration = 0
        
        # Sort timeline by timestamp
        sorted_timeline = sorted(incident.timeline, key=lambda x: x.timestamp)
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(incident)
        
        # Generate lessons learned
        lessons_learned = self._generate_lessons_learned(incident)
        
        # Generate next steps
        next_steps = self._generate_next_steps(incident.action_items)
        
        return PostmortemOutput(
            title=incident.title,
            incident_id=incident_id,
            date_generated=datetime.now(),
            severity=incident.severity,
            start_time=incident.start_time,
            end_time=incident.end_time,
            duration_minutes=duration,
            executive_summary=executive_summary,
            timeline=sorted_timeline,
            impact=incident.impact,
            contributing_factors=incident.contributing_factors,
            action_items=incident.action_items,
            what_went_well=incident.what_went_well,
            what_went_wrong=incident.what_went_wrong,
            lessons_learned=lessons_learned,
            next_steps=next_steps
        )
    
    def _generate_executive_summary(self, incident: IncidentInput) -> str:
        summary_parts = []
        
        # Basic incident info
        summary_parts.append(f"On {incident.start_time.strftime('%B %d, %Y at %H:%M UTC')}, "
                           f"we experienced a {incident.severity.value} severity incident: {incident.title}.")
        
        # Duration
        if incident.duration_minutes:
            hours = incident.duration_minutes // 60
            minutes = incident.duration_minutes % 60
            duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            summary_parts.append(f"The incident lasted for {duration_str}.")
        
        # Impact
        if incident.impact:
            impact_descriptions = [imp.description for imp in incident.impact]
            summary_parts.append(f"Primary impacts included: {', '.join(impact_descriptions)}.")
        
        # Resolution status
        if incident.end_time:
            summary_parts.append(f"The incident was resolved at {incident.end_time.strftime('%H:%M UTC')}.")
        else:
            summary_parts.append("The incident is currently ongoing.")
        
        return " ".join(summary_parts)
    
    def _generate_lessons_learned(self, incident: IncidentInput) -> List[str]:
        lessons = []
        
        # Extract lessons from contributing factors
        for factor in incident.contributing_factors:
            if factor.category == "technical":
                lessons.append(f"Technical improvements needed: {factor.factor}")
            elif factor.category == "process":
                lessons.append(f"Process gaps identified: {factor.factor}")
            elif factor.category == "people":
                lessons.append(f"Training/coordination opportunities: {factor.factor}")
            elif factor.category == "external":
                lessons.append(f"External dependency considerations: {factor.factor}")
        
        # Extract lessons from what went wrong
        for wrong_item in incident.what_went_wrong:
            lessons.append(f"Area for improvement: {wrong_item}")
        
        return lessons
    
    def _generate_next_steps(self, action_items: List[ActionItem]) -> List[str]:
        next_steps = []
        
        # Group action items by category and priority
        immediate_actions = [item for item in action_items if item.category == "immediate"]
        short_term_actions = [item for item in action_items if item.category == "short_term"]
        long_term_actions = [item for item in action_items if item.category == "long_term"]
        preventive_actions = [item for item in action_items if item.category == "preventive"]
        
        if immediate_actions:
            next_steps.append(f"Immediate actions ({len(immediate_actions)} items): "
                            f"Implement critical fixes to prevent recurrence.")
        
        if short_term_actions:
            next_steps.append(f"Short-term improvements ({len(short_term_actions)} items): "
                            f"Address identified gaps within the next 30 days.")
        
        if long_term_actions:
            next_steps.append(f"Long-term initiatives ({len(long_term_actions)} items): "
                            f"Strategic improvements to enhance resilience.")
        
        if preventive_actions:
            next_steps.append(f"Preventive measures ({len(preventive_actions)} items): "
                            f"Strengthen monitoring and detection capabilities.")
        
        return next_steps
