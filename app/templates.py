from jinja2 import Template
from .models import PostmortemOutput


class PostmortemTemplate:
    def __init__(self):
        self.markdown_template = """
# Incident Postmortem: {{ postmortem.title }}

**Incident ID:** {{ postmortem.incident_id }}  
**Date Generated:** {{ postmortem.date_generated.strftime('%Y-%m-%d %H:%M UTC') }}  
**Severity:** {{ postmortem.severity.value.upper() }}  
**Duration:** {{ postmortem.duration_minutes }} minutes  
**Start Time:** {{ postmortem.start_time.strftime('%Y-%m-%d %H:%M UTC') }}  
{% if postmortem.end_time %}**End Time:** {{ postmortem.end_time.strftime('%Y-%m-%d %H:%M UTC') }}{% endif %}

---

## Executive Summary

{{ postmortem.executive_summary }}

---

## Timeline

{% for event in postmortem.timeline %}
- **{{ event.timestamp.strftime('%Y-%m-%d %H:%M UTC') }}** - {{ event.event }}{% if event.source %} (Source: {{ event.source }}){% endif %}
{% endfor %}

---

## Impact Analysis

{% for impact in postmortem.impact %}
### {{ impact.type.value.title() }} Impact
{{ impact.description }}
{% if impact.affected_users %}- **Affected Users:** {{ impact.affected_users }}{% endif %}
{% if impact.affected_services %}- **Affected Services:** {{ impact.affected_services | join(', ') }}{% endif %}
{% if impact.duration_minutes %}- **Duration:** {{ impact.duration_minutes }} minutes{% endif %}

{% endfor %}

---

## Contributing Factors

{% for factor in postmortem.contributing_factors %}
### {{ factor.category.title() }} Factor
**Factor:** {{ factor.factor }}  
**Description:** {{ factor.description }}

{% endfor %}

---

## What Went Well

{% for item in postmortem.what_went_well %}
- {{ item }}
{% endfor %}

---

## What Went Wrong

{% for item in postmortem.what_went_wrong %}
- {{ item }}
{% endfor %}

---

## Lessons Learned

{% for lesson in postmortem.lessons_learned %}
- {{ lesson }}
{% endfor %}

---

## Action Items

{% for item in postmortem.action_items %}
### {{ item.title }} ({{ item.category.replace('_', ' ').title() }})
- **Priority:** {{ item.priority.value.upper() }}
- **Description:** {{ item.description }}
{% if item.assignee %}- **Assignee:** {{ item.assignee }}{% endif %}
{% if item.due_date %}- **Due Date:** {{ item.due_date.strftime('%Y-%m-%d') }}{% endif %}

{% endfor %}

---

## Next Steps

{% for step in postmortem.next_steps %}
{{ loop.index }}. {{ step }}
{% endfor %}

---

*This postmortem was generated automatically using the Incident Postmortem Generator.*
"""

    def render_markdown(self, postmortem: PostmortemOutput) -> str:
        template = Template(self.markdown_template)
        return template.render(postmortem=postmortem)
