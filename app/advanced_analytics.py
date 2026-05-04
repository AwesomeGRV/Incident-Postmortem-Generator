"""
Advanced Analytics and Business Intelligence System
Modern analytics with ML insights and predictive analytics
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from collections import defaultdict, Counter

# ML and analytics imports
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, silhouette_score
from sklearn.decomposition import PCA
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

# Database imports
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

logger = logging.getLogger(__name__)


class AnalyticsMetric(Enum):
    """Analytics metric types"""
    INCIDENT_VOLUME = "incident_volume"
    MTTR = "mttr"  # Mean Time To Resolution
    MTBF = "mtbf"  # Mean Time Between Failures
    SLA_COMPLIANCE = "sla_compliance"
    SEVERITY_DISTRIBUTION = "severity_distribution"
    CATEGORY_TRENDS = "category_trends"
    USER_PRODUCTIVITY = "user_productivity"
    SYSTEM_HEALTH = "system_health"
    BUSINESS_IMPACT = "business_impact"
    PREDICTIVE_RISK = "predictive_risk"


class TimeGranularity(Enum):
    """Time granularity for analytics"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class AlertLevel(Enum):
    """Alert levels for analytics"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class MetricData:
    """Metric data point"""
    metric: AnalyticsMetric
    value: float
    timestamp: datetime
    granularity: TimeGranularity
    dimensions: Dict[str, Any] = None
    metadata: Dict[str, Any] = None


@dataclass
class TrendAnalysis:
    """Trend analysis results"""
    metric: AnalyticsMetric
    trend_direction: str  # "up", "down", "stable"
    trend_strength: float  # 0-1
    seasonal_pattern: bool
    forecast_values: List[float]
    confidence_intervals: List[Tuple[float, float]]
    anomalies: List[datetime]


@dataclass
class RiskAssessment:
    """Risk assessment results"""
    risk_score: float  # 0-100
    risk_level: AlertLevel
    contributing_factors: List[str]
    predicted_incidents: int
    time_horizon: timedelta
    recommendations: List[str]


@dataclass
class BusinessImpact:
    """Business impact analysis"""
    revenue_impact: float
    customer_impact: int
    productivity_loss: float
    reputation_score: float
    compliance_risk: float
    total_cost: float


@dataclass
class AnalyticsAlert:
    """Analytics alert"""
    id: str
    metric: AnalyticsMetric
    level: AlertLevel
    message: str
    timestamp: datetime
    resolved: bool = False
    assigned_to: Optional[str] = None


class AdvancedAnalyticsEngine:
    """Advanced analytics engine with ML capabilities"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.alerts: Dict[str, AnalyticsAlert] = {}
        self.metrics_cache: Dict[str, List[MetricData]] = defaultdict(list)
        self.prediction_models = {}
        
        # Initialize ML models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize ML models"""
        # Anomaly detection
        self.models['anomaly'] = IsolationForest(
            contamination=0.1,
            random_state=42
        )
        
        # Incident volume prediction
        self.models['volume_prediction'] = RandomForestRegressor(
            n_estimators=100,
            random_state=42
        )
        
        # MTTR prediction
        self.models['mttr_prediction'] = RandomForestRegressor(
            n_estimators=100,
            random_state=42
        )
        
        # Clustering for incident patterns
        self.models['clustering'] = KMeans(
            n_clusters=5,
            random_state=42
        )
        
        # Data scalers
        self.scalers['standard'] = StandardScaler()
    
    async def calculate_metrics(self, db: Session, start_date: datetime, 
                             end_date: datetime, granularity: TimeGranularity = TimeGranularity.DAILY) -> List[MetricData]:
        """Calculate analytics metrics for time period"""
        metrics = []
        
        # Incident volume metrics
        volume_metrics = await self._calculate_incident_volume(db, start_date, end_date, granularity)
        metrics.extend(volume_metrics)
        
        # MTTR metrics
        mttr_metrics = await self._calculate_mttr(db, start_date, end_date, granularity)
        metrics.extend(mttr_metrics)
        
        # SLA compliance metrics
        sla_metrics = await self._calculate_sla_compliance(db, start_date, end_date, granularity)
        metrics.extend(sla_metrics)
        
        # Severity distribution
        severity_metrics = await self._calculate_severity_distribution(db, start_date, end_date, granularity)
        metrics.extend(severity_metrics)
        
        # Category trends
        category_metrics = await self._calculate_category_trends(db, start_date, end_date, granularity)
        metrics.extend(category_metrics)
        
        # Business impact
        impact_metrics = await self._calculate_business_impact(db, start_date, end_date, granularity)
        metrics.extend(impact_metrics)
        
        # Cache metrics
        for metric in metrics:
            self.metrics_cache[metric.metric.value].append(metric)
        
        return metrics
    
    async def _calculate_incident_volume(self, db: Session, start_date: datetime, 
                                      end_date: datetime, granularity: TimeGranularity) -> List[MetricData]:
        """Calculate incident volume metrics"""
        from .enterprise_models import Incident
        
        # Group incidents by time granularity
        if granularity == TimeGranularity.HOURLY:
            time_group = func.date_trunc('hour', Incident.created_at)
        elif granularity == TimeGranularity.DAILY:
            time_group = func.date_trunc('day', Incident.created_at)
        elif granularity == TimeGranularity.WEEKLY:
            time_group = func.date_trunc('week', Incident.created_at)
        elif granularity == TimeGranularity.MONTHLY:
            time_group = func.date_trunc('month', Incident.created_at)
        else:
            time_group = func.date_trunc('day', Incident.created_at)
        
        results = db.query(
            time_group.label('period'),
            func.count(Incident.id).label('count')
        ).filter(
            Incident.created_at >= start_date,
            Incident.created_at <= end_date
        ).group_by(time_group).all()
        
        metrics = []
        for period, count in results:
            metric = MetricData(
                metric=AnalyticsMetric.INCIDENT_VOLUME,
                value=float(count),
                timestamp=period,
                granularity=granularity,
                dimensions={"incident_count": count}
            )
            metrics.append(metric)
        
        return metrics
    
    async def _calculate_mttr(self, db: Session, start_date: datetime, 
                           end_date: datetime, granularity: TimeGranularity) -> List[MetricData]:
        """Calculate Mean Time To Resolution"""
        from .enterprise_models import Incident
        
        # Get resolved incidents
        results = db.query(
            func.date_trunc('day', Incident.created_at).label('period'),
            func.avg(
                func.extract('epoch', Incident.resolved_at - Incident.created_at)
            ).label('avg_resolution_time')
        ).filter(
            Incident.created_at >= start_date,
            Incident.created_at <= end_date,
            Incident.status == 'resolved',
            Incident.resolved_at.isnot(None)
        ).group_by(
            func.date_trunc('day', Incident.created_at)
        ).all()
        
        metrics = []
        for period, avg_time in results:
            if avg_time:
                metric = MetricData(
                    metric=AnalyticsMetric.MTTR,
                    value=float(avg_time / 3600),  # Convert to hours
                    timestamp=period,
                    granularity=granularity,
                    dimensions={"resolution_time_hours": float(avg_time / 3600)}
                )
                metrics.append(metric)
        
        return metrics
    
    async def _calculate_sla_compliance(self, db: Session, start_date: datetime, 
                                     end_date: datetime, granularity: TimeGranularity) -> List[MetricData]:
        """Calculate SLA compliance metrics"""
        from .enterprise_models import Incident
        
        # Get incidents with SLA information
        results = db.query(
            func.date_trunc('day', Incident.created_at).label('period'),
            func.count(Incident.id).label('total'),
            func.sum(
                func.case(
                    (Incident.resolved_at <= Incident.sla_deadline, 1),
                    else_=0
                )
            ).label('compliant')
        ).filter(
            Incident.created_at >= start_date,
            Incident.created_at <= end_date,
            Incident.sla_deadline.isnot(None)
        ).group_by(
            func.date_trunc('day', Incident.created_at)
        ).all()
        
        metrics = []
        for period, total, compliant in results:
            if total > 0:
                compliance_rate = (compliant / total) * 100
                metric = MetricData(
                    metric=AnalyticsMetric.SLA_COMPLIANCE,
                    value=compliance_rate,
                    timestamp=period,
                    granularity=granularity,
                    dimensions={
                        "total_incidents": total,
                        "compliant_incidents": compliant,
                        "compliance_rate": compliance_rate
                    }
                )
                metrics.append(metric)
        
        return metrics
    
    async def _calculate_severity_distribution(self, db: Session, start_date: datetime, 
                                            end_date: datetime, granularity: TimeGranularity) -> List[MetricData]:
        """Calculate severity distribution metrics"""
        from .enterprise_models import Incident
        
        results = db.query(
            Incident.severity,
            func.count(Incident.id).label('count')
        ).filter(
            Incident.created_at >= start_date,
            Incident.created_at <= end_date
        ).group_by(Incident.severity).all()
        
        metrics = []
        total_incidents = sum(count for _, count in results)
        
        for severity, count in results:
            if total_incidents > 0:
                percentage = (count / total_incidents) * 100
                metric = MetricData(
                    metric=AnalyticsMetric.SEVERITY_DISTRIBUTION,
                    value=percentage,
                    timestamp=end_date,
                    granularity=granularity,
                    dimensions={
                        "severity": severity,
                        "count": count,
                        "percentage": percentage
                    }
                )
                metrics.append(metric)
        
        return metrics
    
    async def _calculate_category_trends(self, db: Session, start_date: datetime, 
                                      end_date: datetime, granularity: TimeGranularity) -> List[MetricData]:
        """Calculate category trends"""
        from .enterprise_models import Incident
        
        results = db.query(
            Incident.category,
            func.date_trunc('day', Incident.created_at).label('period'),
            func.count(Incident.id).label('count')
        ).filter(
            Incident.created_at >= start_date,
            Incident.created_at <= end_date
        ).group_by(
            Incident.category,
            func.date_trunc('day', Incident.created_at)
        ).all()
        
        metrics = []
        for category, period, count in results:
            metric = MetricData(
                metric=AnalyticsMetric.CATEGORY_TRENDS,
                value=float(count),
                timestamp=period,
                granularity=granularity,
                dimensions={
                    "category": category,
                    "incident_count": count
                }
            )
            metrics.append(metric)
        
        return metrics
    
    async def _calculate_business_impact(self, db: Session, start_date: datetime, 
                                      end_date: datetime, granularity: TimeGranularity) -> List[MetricData]:
        """Calculate business impact metrics"""
        from .enterprise_models import Incident
        
        # Calculate various impact metrics
        results = db.query(
            func.date_trunc('day', Incident.created_at).label('period'),
            func.sum(Incident.affected_users).label('total_affected_users'),
            func.avg(Incident.downtime_minutes).label('avg_downtime'),
            func.count(Incident.id).label('incident_count')
        ).filter(
            Incident.created_at >= start_date,
            Incident.created_at <= end_date
        ).group_by(
            func.date_trunc('day', Incident.created_at)
        ).all()
        
        metrics = []
        for period, affected_users, avg_downtime, incident_count in results:
            # Calculate business impact score
            impact_score = 0
            if affected_users:
                impact_score += min(affected_users / 1000, 100)  # User impact
            if avg_downtime:
                impact_score += min(avg_downtime / 60, 50)  # Downtime impact
            if incident_count:
                impact_score += min(incident_count * 10, 50)  # Volume impact
            
            metric = MetricData(
                metric=AnalyticsMetric.BUSINESS_IMPACT,
                value=impact_score,
                timestamp=period,
                granularity=granularity,
                dimensions={
                    "affected_users": affected_users or 0,
                    "avg_downtime": float(avg_downtime or 0),
                    "incident_count": incident_count,
                    "impact_score": impact_score
                }
            )
            metrics.append(metric)
        
        return metrics
    
    async def analyze_trends(self, metric: AnalyticsMetric, 
                           forecast_periods: int = 30) -> TrendAnalysis:
        """Analyze trends and generate forecasts"""
        # Get historical data
        historical_data = self.metrics_cache.get(metric.value, [])
        
        if len(historical_data) < 10:
            # Not enough data for trend analysis
            return TrendAnalysis(
                metric=metric,
                trend_direction="stable",
                trend_strength=0.0,
                seasonal_pattern=False,
                forecast_values=[],
                confidence_intervals=[],
                anomalies=[]
            )
        
        # Convert to pandas for analysis
        df = pd.DataFrame([asdict(m) for m in historical_data])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Simple trend analysis
        values = df['value'].values
        time_index = np.arange(len(values))
        
        # Linear regression for trend
        trend_coef = np.polyfit(time_index, values, 1)
        trend_direction = "up" if trend_coef[0] > 0.1 else "down" if trend_coef[0] < -0.1 else "stable"
        trend_strength = min(abs(trend_coef[0]) * 10, 1.0)
        
        # Simple forecasting (linear extrapolation)
        forecast_values = []
        for i in range(1, forecast_periods + 1):
            forecast_value = trend_coef[0] * (len(values) + i) + trend_coef[1]
            forecast_values.append(max(0, forecast_value))  # Ensure non-negative
        
        # Calculate confidence intervals (simplified)
        std_error = np.std(values)
        confidence_intervals = [
            (max(0, val - 1.96 * std_error), val + 1.96 * std_error)
            for val in forecast_values
        ]
        
        # Detect anomalies (simplified)
        anomalies = []
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        for i, (timestamp, value) in enumerate(zip(df['timestamp'], values)):
            if abs(value - mean_val) > 2 * std_val:
                anomalies.append(timestamp)
        
        return TrendAnalysis(
            metric=metric,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            seasonal_pattern=False,  # Simplified
            forecast_values=forecast_values,
            confidence_intervals=confidence_intervals,
            anomalies=anomalies
        )
    
    async def assess_risk(self, db: Session, time_horizon: timedelta = timedelta(days=30)) -> RiskAssessment:
        """Assess predictive risk"""
        # Get recent incident data
        from .enterprise_models import Incident
        
        recent_date = datetime.utcnow() - timedelta(days=90)
        incidents = db.query(Incident).filter(
            Incident.created_at >= recent_date
        ).all()
        
        if not incidents:
            return RiskAssessment(
                risk_score=0.0,
                risk_level=AlertLevel.INFO,
                contributing_factors=[],
                predicted_incidents=0,
                time_horizon=time_horizon,
                recommendations=[]
            )
        
        # Calculate risk factors
        risk_factors = []
        risk_score = 0.0
        
        # Volume trend
        recent_volume = len([i for i in incidents if i.created_at >= datetime.utcnow() - timedelta(days=30)])
        if recent_volume > 50:
            risk_score += 20
            risk_factors.append("High incident volume")
        
        # Critical incidents
        critical_count = len([i for i in incidents if i.severity == 'critical'])
        if critical_count > 5:
            risk_score += 25
            risk_factors.append("Multiple critical incidents")
        
        # SLA breaches
        sla_breaches = len([i for i in incidents if i.sla_deadline and i.resolved_at and i.resolved_at > i.sla_deadline])
        if sla_breaches > 10:
            risk_score += 15
            risk_factors.append("SLA compliance issues")
        
        # Repeat incidents (same category/system)
        category_counts = Counter([i.category for i in incidents])
        repeat_categories = [cat for cat, count in category_counts.items() if count > 10]
        if repeat_categories:
            risk_score += 20
            risk_factors.append(f"Recurring issues in: {', '.join(repeat_categories)}")
        
        # System health indicators
        avg_resolution_time = np.mean([
            (i.resolved_at - i.created_at).total_seconds() / 3600 
            for i in incidents if i.resolved_at
        ])
        if avg_resolution_time > 24:
            risk_score += 10
            risk_factors.append("Slow resolution times")
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = AlertLevel.EMERGENCY
        elif risk_score >= 50:
            risk_level = AlertLevel.CRITICAL
        elif risk_score >= 30:
            risk_level = AlertLevel.WARNING
        else:
            risk_level = AlertLevel.INFO
        
        # Predict incidents (simplified linear prediction)
        predicted_incidents = int(recent_volume * (1 + risk_score / 100))
        
        # Generate recommendations
        recommendations = []
        if "High incident volume" in risk_factors:
            recommendations.append("Implement proactive monitoring and alerting")
        if "Multiple critical incidents" in risk_factors:
            recommendations.append("Review and improve incident response procedures")
        if "SLA compliance issues" in risk_factors:
            recommendations.append("Optimize resource allocation and escalation paths")
        if repeat_categories:
            recommendations.append(f"Investigate root causes for {', '.join(repeat_categories)}")
        if "Slow resolution times" in risk_factors:
            recommendations.append("Enhance team training and tooling")
        
        return RiskAssessment(
            risk_score=min(risk_score, 100),
            risk_level=risk_level,
            contributing_factors=risk_factors,
            predicted_incidents=predicted_incidents,
            time_horizon=time_horizon,
            recommendations=recommendations
        )
    
    async def generate_dashboard_data(self, db: Session) -> Dict[str, Any]:
        """Generate comprehensive dashboard data"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # Calculate metrics
        metrics = await self.calculate_metrics(db, start_date, end_date)
        
        # Analyze trends
        trend_analyses = {}
        for metric in AnalyticsMetric:
            if metric.value in self.metrics_cache:
                trend_analyses[metric.value] = await self.analyze_trends(metric)
        
        # Risk assessment
        risk_assessment = await self.assess_risk(db)
        
        # Generate charts
        charts = await self._generate_charts(metrics)
        
        # Active alerts
        active_alerts = [alert for alert in self.alerts.values() if not alert.resolved]
        
        return {
            "metrics": [asdict(m) for m in metrics],
            "trends": {k: asdict(v) for k, v in trend_analyses.items()},
            "risk_assessment": asdict(risk_assessment),
            "charts": charts,
            "alerts": [asdict(a) for a in active_alerts],
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def _generate_charts(self, metrics: List[MetricData]) -> Dict[str, Any]:
        """Generate chart data for dashboard"""
        charts = {}
        
        # Group metrics by type
        metrics_by_type = defaultdict(list)
        for metric in metrics:
            metrics_by_type[metric.metric.value].append(metric)
        
        # Incident volume chart
        if AnalyticsMetric.INCIDENT_VOLUME.value in metrics_by_type:
            volume_data = metrics_by_type[AnalyticsMetric.INCIDENT_VOLUME.value]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[m.timestamp for m in volume_data],
                y=[m.value for m in volume_data],
                mode='lines+markers',
                name='Incident Volume'
            ))
            fig.update_layout(
                title='Incident Volume Trend',
                xaxis_title='Date',
                yaxis_title='Number of Incidents'
            )
            charts['incident_volume'] = json.dumps(fig, cls=PlotlyJSONEncoder)
        
        # MTTR chart
        if AnalyticsMetric.MTTR.value in metrics_by_type:
            mttr_data = metrics_by_type[AnalyticsMetric.MTTR.value]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[m.timestamp for m in mttr_data],
                y=[m.value for m in mttr_data],
                mode='lines+markers',
                name='MTTR (hours)'
            ))
            fig.update_layout(
                title='Mean Time To Resolution',
                xaxis_title='Date',
                yaxis_title='Hours'
            )
            charts['mttr'] = json.dumps(fig, cls=PlotlyJSONEncoder)
        
        # Severity distribution pie chart
        if AnalyticsMetric.SEVERITY_DISTRIBUTION.value in metrics_by_type:
            severity_data = metrics_by_type[AnalyticsMetric.SEVERITY_DISTRIBUTION.value]
            labels = [m.dimensions.get('severity', 'Unknown') for m in severity_data]
            values = [m.value for m in severity_data]
            
            fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
            fig.update_layout(title='Severity Distribution')
            charts['severity_distribution'] = json.dumps(fig, cls=PlotlyJSONEncoder)
        
        # Category trends
        if AnalyticsMetric.CATEGORY_TRENDS.value in metrics_by_type:
            category_data = metrics_by_type[AnalyticsMetric.CATEGORY_TRENDS.value]
            categories = list(set([m.dimensions.get('category', 'Unknown') for m in category_data]))
            
            fig = go.Figure()
            for category in categories:
                cat_data = [m for m in category_data if m.dimensions.get('category') == category]
                if cat_data:
                    fig.add_trace(go.Scatter(
                        x=[m.timestamp for m in cat_data],
                        y=[m.value for m in cat_data],
                        mode='lines+markers',
                        name=category
                    ))
            
            fig.update_layout(
                title='Incident Trends by Category',
                xaxis_title='Date',
                yaxis_title='Number of Incidents'
            )
            charts['category_trends'] = json.dumps(fig, cls=PlotlyJSONEncoder)
        
        return charts
    
    async def create_alert(self, metric: AnalyticsMetric, level: AlertLevel, message: str) -> str:
        """Create analytics alert"""
        alert_id = str(uuid.uuid4())
        alert = AnalyticsAlert(
            id=alert_id,
            metric=metric,
            level=level,
            message=message,
            timestamp=datetime.utcnow()
        )
        
        self.alerts[alert_id] = alert
        return alert_id
    
    async def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Resolve an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            self.alerts[alert_id].assigned_to = resolved_by
            return True
        return False


# Global analytics engine instance
analytics_engine = AdvancedAnalyticsEngine()
