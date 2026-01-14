from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .enterprise_models import Incident, Analytics, SLAMetrics, UserRole
from .database import get_db


class AnalyticsService:
    """Enterprise analytics and metrics service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_incident_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        team_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get comprehensive incident metrics"""
        
        # Default to last 30 days
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        base_query = self.db.query(Incident).filter(
            Incident.created_at >= start_date,
            Incident.created_at <= end_date
        )
        
        if team_id:
            base_query = base_query.filter(Incident.created_by == team_id)
        
        # Total incidents
        total_incidents = base_query.count()
        
        # Incidents by severity
        severity_breakdown = self.db.query(
            Incident.severity,
            func.count(Incident.id).label('count')
        ).filter(
            Incident.created_at >= start_date,
            Incident.created_at <= end_date
        ).group_by(Incident.severity).all()
        
        # Incidents by status
        status_breakdown = self.db.query(
            Incident.status,
            func.count(Incident.id).label('count')
        ).filter(
            Incident.created_at >= start_date,
            Incident.created_at <= end_date
        ).group_by(Incident.status).all()
        
        # Average resolution time
        avg_resolution_time = self.db.query(
            func.avg(Incident.duration_minutes)
        ).filter(
            Incident.created_at >= start_date,
            Incident.created_at <= end_date,
            Incident.duration_minutes.isnot(None)
        ).scalar() or 0
        
        # SLA compliance rate
        sla_compliant = self.db.query(SLAMetrics).filter(
            SLAMetrics.achieved == True
        ).count()
        
        total_sla_checks = self.db.query(SLAMetrics).count()
        sla_compliance_rate = (sla_compliant / total_sla_checks * 100) if total_sla_checks > 0 else 0
        
        # Trend data (daily incidents)
        daily_trends = self.db.query(
            func.date(Incident.created_at).label('date'),
            func.count(Incident.id).label('count')
        ).filter(
            Incident.created_at >= start_date,
            Incident.created_at <= end_date
        ).group_by(func.date(Incident.created_at)).all()
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_incidents": total_incidents,
                "avg_resolution_time_minutes": round(avg_resolution_time, 2),
                "sla_compliance_rate": round(sla_compliance_rate, 2)
            },
            "severity_breakdown": [
                {"severity": item.severity, "count": item.count}
                for item in severity_breakdown
            ],
            "status_breakdown": [
                {"status": item.status.value, "count": item.count}
                for item in status_breakdown
            ],
            "daily_trends": [
                {"date": item.date.isoformat(), "count": item.count}
                for item in daily_trends
            ]
        }
    
    def get_team_performance(self, team_id: int) -> Dict[str, Any]:
        """Get team-specific performance metrics"""
        
        # Team incidents
        team_incidents = self.db.query(Incident).filter(
            Incident.created_by == team_id
        ).all()
        
        # Team metrics
        total_incidents = len(team_incidents)
        published_incidents = len([i for i in team_incidents if i.status.value == "published"])
        
        # Average time to publish
        publish_times = [
            (i.published_at - i.created_at).total_seconds() / 3600
            for i in team_incidents if i.published_at
        ]
        avg_time_to_publish = sum(publish_times) / len(publish_times) if publish_times else 0
        
        # Quality score (based on completeness)
        quality_scores = []
        for incident in team_incidents:
            score = 0
            if incident.executive_summary:
                score += 20
            if incident.contributing_factors:
                score += 20
            if incident.action_items:
                score += 20
            if incident.what_went_well:
                score += 20
            if incident.what_went_wrong:
                score += 20
            quality_scores.append(score)
        
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            "team_id": team_id,
            "total_incidents": total_incidents,
            "published_incidents": published_incidents,
            "publish_rate": (published_incidents / total_incidents * 100) if total_incidents > 0 else 0,
            "avg_time_to_publish_hours": round(avg_time_to_publish, 2),
            "avg_quality_score": round(avg_quality_score, 2)
        }
    
    def get_sla_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate SLA compliance report"""
        
        sla_metrics = self.db.query(SLAMetrics).join(Incident).filter(
            Incident.created_at >= start_date,
            Incident.created_at <= end_date
        ).all()
        
        # Group by SLA type
        sla_by_type = {}
        for metric in sla_metrics:
            if metric.sla_type not in sla_by_type:
                sla_by_type[metric.sla_type] = {
                    "total": 0,
                    "achieved": 0,
                    "breached": 0,
                    "total_breach_minutes": 0
                }
            
            sla_by_type[metric.sla_type]["total"] += 1
            if metric.achieved:
                sla_by_type[metric.sla_type]["achieved"] += 1
            else:
                sla_by_type[metric.sla_type]["breached"] += 1
                sla_by_type[metric.sla_type]["total_breach_minutes"] += metric.breach_minutes
        
        # Calculate compliance rates
        for sla_type, data in sla_by_type.items():
            data["compliance_rate"] = (data["achieved"] / data["total"] * 100) if data["total"] > 0 else 0
            data["avg_breach_minutes"] = (
                data["total_breach_minutes"] / data["breached"]
            ) if data["breached"] > 0 else 0
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "sla_metrics": sla_by_type,
            "overall_compliance": sum(
                data["compliance_rate"] for data in sla_by_type.values()
            ) / len(sla_by_type) if sla_by_type else 0
        }
    
    def get_incident_heatmap(self, days: int = 30) -> Dict[str, Any]:
        """Generate incident heatmap data by hour and day of week"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        incidents = self.db.query(Incident).filter(
            Incident.created_at >= start_date
        ).all()
        
        # Initialize heatmap data
        heatmap = {}
        for hour in range(24):
            for day in range(7):
                heatmap[f"{day}-{hour}"] = 0
        
        # Populate heatmap
        for incident in incidents:
            day_of_week = incident.created_at.weekday()
            hour = incident.created_at.hour
            key = f"{day_of_week}-{hour}"
            heatmap[key] += 1
        
        return {
            "period_days": days,
            "heatmap": heatmap,
            "peak_hour": max(
                heatmap.items(), key=lambda x: x[1]
            )[0] if heatmap else None
        }
    
    def record_metric(self, metric_name: str, metric_value: float, dimensions: Dict[str, Any] = None):
        """Record a custom metric"""
        analytics = Analytics(
            metric_name=metric_name,
            metric_value=metric_value,
            dimensions=dimensions or {}
        )
        
        self.db.add(analytics)
        self.db.commit()
    
    def get_custom_metrics(
        self,
        metric_name: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get custom metrics for a time range"""
        
        metrics = self.db.query(Analytics).filter(
            Analytics.metric_name == metric_name,
            Analytics.timestamp >= start_date,
            Analytics.timestamp <= end_date
        ).all()
        
        return [
            {
                "timestamp": metric.timestamp.isoformat(),
                "value": metric.metric_value,
                "dimensions": metric.dimensions
            }
            for metric in metrics
        ]
