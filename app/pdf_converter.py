import markdown
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from .models import PostmortemOutput
from .templates import PostmortemTemplate


class PDFConverter:
    def __init__(self):
        self.template = PostmortemTemplate()
    
    def convert_to_pdf(self, postmortem: PostmortemOutput, output_path: str) -> bool:
        """Convert postmortem to PDF"""
        try:
            # Generate markdown content
            markdown_content = self.template.render_markdown(postmortem)
            
            # Convert markdown to HTML
            html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
            
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
            
            # Get styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                textColor=HexColor('#2c3e50'),
                alignment=1  # Center
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor=HexColor('#2c3e50')
            )
            
            normal_style = styles['Normal']
            normal_style.fontSize = 10
            normal_style.spaceAfter = 6
            
            # Build story (content)
            story = []
            
            # Title
            story.append(Paragraph(postmortem.title, title_style))
            story.append(Spacer(1, 12))
            
            # Metadata
            story.append(Paragraph(f"<b>Incident ID:</b> {postmortem.incident_id}", normal_style))
            story.append(Paragraph(f"<b>Date Generated:</b> {postmortem.date_generated.strftime('%Y-%m-%d %H:%M UTC')}", normal_style))
            story.append(Paragraph(f"<b>Severity:</b> {postmortem.severity.value.upper()}", normal_style))
            story.append(Paragraph(f"<b>Duration:</b> {postmortem.duration_minutes} minutes", normal_style))
            story.append(Spacer(1, 20))
            
            # Executive Summary
            story.append(Paragraph("Executive Summary", heading_style))
            story.append(Paragraph(postmortem.executive_summary, normal_style))
            story.append(Spacer(1, 20))
            
            # Timeline
            story.append(Paragraph("Timeline", heading_style))
            for event in postmortem.timeline:
                event_text = f"<b>{event.timestamp.strftime('%Y-%m-%d %H:%M UTC')}</b> - {event.event}"
                if event.source:
                    event_text += f" (Source: {event.source})"
                story.append(Paragraph(event_text, normal_style))
            story.append(Spacer(1, 20))
            
            # Impact
            story.append(Paragraph("Impact Analysis", heading_style))
            for impact in postmortem.impact:
                story.append(Paragraph(f"<b>{impact.type.value.title()} Impact</b>", normal_style))
                story.append(Paragraph(impact.description, normal_style))
                if impact.affected_users:
                    story.append(Paragraph(f"<b>Affected Users:</b> {impact.affected_users}", normal_style))
                if impact.affected_services:
                    story.append(Paragraph(f"<b>Affected Services:</b> {', '.join(impact.affected_services)}", normal_style))
                if impact.duration_minutes:
                    story.append(Paragraph(f"<b>Duration:</b> {impact.duration_minutes} minutes", normal_style))
                story.append(Spacer(1, 12))
            story.append(Spacer(1, 20))
            
            # Contributing Factors
            if postmortem.contributing_factors:
                story.append(Paragraph("Contributing Factors", heading_style))
                for factor in postmortem.contributing_factors:
                    story.append(Paragraph(f"<b>{factor.category.title()} Factor</b>", normal_style))
                    story.append(Paragraph(f"<b>Factor:</b> {factor.factor}", normal_style))
                    story.append(Paragraph(f"<b>Description:</b> {factor.description}", normal_style))
                    story.append(Spacer(1, 12))
                story.append(Spacer(1, 20))
            
            # What Went Well
            if postmortem.what_went_well:
                story.append(Paragraph("What Went Well", heading_style))
                for item in postmortem.what_went_well:
                    story.append(Paragraph(f"• {item}", normal_style))
                story.append(Spacer(1, 20))
            
            # What Went Wrong
            if postmortem.what_went_wrong:
                story.append(Paragraph("What Went Wrong", heading_style))
                for item in postmortem.what_went_wrong:
                    story.append(Paragraph(f"• {item}", normal_style))
                story.append(Spacer(1, 20))
            
            # Lessons Learned
            if postmortem.lessons_learned:
                story.append(Paragraph("Lessons Learned", heading_style))
                for lesson in postmortem.lessons_learned:
                    story.append(Paragraph(f"• {lesson}", normal_style))
                story.append(Spacer(1, 20))
            
            # Action Items
            if postmortem.action_items:
                story.append(Paragraph("Action Items", heading_style))
                for item in postmortem.action_items:
                    story.append(Paragraph(f"<b>{item.title}</b> ({item.category.replace('_', ' ').title()})", normal_style))
                    story.append(Paragraph(f"<b>Priority:</b> {item.priority.value.upper()}", normal_style))
                    story.append(Paragraph(f"<b>Description:</b> {item.description}", normal_style))
                    if item.assignee:
                        story.append(Paragraph(f"<b>Assignee:</b> {item.assignee}", normal_style))
                    if item.due_date:
                        story.append(Paragraph(f"<b>Due Date:</b> {item.due_date.strftime('%Y-%m-%d')}", normal_style))
                    story.append(Spacer(1, 12))
                story.append(Spacer(1, 20))
            
            # Next Steps
            if postmortem.next_steps:
                story.append(Paragraph("Next Steps", heading_style))
                for i, step in enumerate(postmortem.next_steps, 1):
                    story.append(Paragraph(f"{i}. {step}", normal_style))
            
            # Build PDF
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"Error converting to PDF: {e}")
            return False
