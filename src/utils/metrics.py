"""
Metrics Collector - Performance and compliance metrics for MedinovAI
Collects and reports on conversation metrics, PHI detection, and system performance
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

import structlog
from prometheus_client import Counter, Histogram, Gauge, Summary

from utils.config import Settings

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """
    Collects and manages metrics for MedinovAI healthcare conversations.
    Provides real-time monitoring and compliance reporting.
    """
    
    def __init__(self):
        # Prometheus metrics
        self.conversation_counter = Counter(
            'medinovai_conversations_total',
            'Total number of conversations',
            ['channel', 'language', 'outcome']
        )
        
        self.message_counter = Counter(
            'medinovai_messages_total',
            'Total number of messages processed',
            ['channel', 'type']
        )
        
        self.response_time_histogram = Histogram(
            'medinovai_response_time_seconds',
            'Message response time in seconds',
            ['channel']
        )
        
        self.phi_detection_counter = Counter(
            'medinovai_phi_detections_total',
            'Total PHI detections',
            ['detection_type']
        )
        
        self.escalation_counter = Counter(
            'medinovai_escalations_total',
            'Total conversation escalations',
            ['reason', 'channel']
        )
        
        self.active_conversations_gauge = Gauge(
            'medinovai_active_conversations',
            'Number of active conversations'
        )
        
        self.agent_workload_gauge = Gauge(
            'medinovai_agent_workload',
            'Agent workload',
            ['agent_id']
        )
        
        self.error_counter = Counter(
            'medinovai_errors_total',
            'Total errors',
            ['error_type', 'component']
        )
        
        # In-memory metrics for dashboard
        self.conversation_metrics = defaultdict(int)
        self.response_times = deque(maxlen=1000)  # Last 1000 response times
        self.phi_detections = deque(maxlen=1000)  # Last 1000 PHI detections
        self.hourly_stats = defaultdict(lambda: defaultdict(int))
        
        # Performance tracking
        self.start_time = datetime.utcnow()
        
        logger.info("Metrics collector initialized")
    
    def record_conversation_started(
        self,
        channel: str,
        language: str = "en"
    ) -> None:
        """Record when a conversation starts."""
        self.conversation_counter.labels(
            channel=channel,
            language=language,
            outcome="started"
        ).inc()
        
        self.conversation_metrics["total_started"] += 1
        self.conversation_metrics[f"started_{channel}"] += 1
        
        # Update active conversations gauge
        self.active_conversations_gauge.inc()
        
        # Update hourly stats
        hour_key = datetime.utcnow().strftime("%Y-%m-%d_%H")
        self.hourly_stats[hour_key]["conversations_started"] += 1
        
        logger.debug(
            "Conversation started recorded",
            channel=channel,
            language=language
        )
    
    def record_conversation_completed(
        self,
        channel: str,
        message_count: int,
        satisfaction_score: Optional[int] = None
    ) -> None:
        """Record when a conversation completes."""
        self.conversation_counter.labels(
            channel=channel,
            language="unknown",  # Not available at completion
            outcome="completed"
        ).inc()
        
        self.conversation_metrics["total_completed"] += 1
        self.conversation_metrics[f"completed_{channel}"] += 1
        
        if satisfaction_score:
            self.conversation_metrics["satisfaction_sum"] += satisfaction_score
            self.conversation_metrics["satisfaction_count"] += 1
        
        # Update active conversations gauge
        self.active_conversations_gauge.dec()
        
        # Update hourly stats
        hour_key = datetime.utcnow().strftime("%Y-%m-%d_%H")
        self.hourly_stats[hour_key]["conversations_completed"] += 1
        self.hourly_stats[hour_key]["total_messages"] += message_count
        
        logger.debug(
            "Conversation completed recorded",
            channel=channel,
            message_count=message_count,
            satisfaction_score=satisfaction_score
        )
    
    def record_conversation_escalated(
        self,
        channel: str,
        reason: str
    ) -> None:
        """Record when a conversation is escalated."""
        self.escalation_counter.labels(
            reason=reason,
            channel=channel
        ).inc()
        
        self.conversation_counter.labels(
            channel=channel,
            language="unknown",
            outcome="escalated"
        ).inc()
        
        self.conversation_metrics["total_escalated"] += 1
        self.conversation_metrics[f"escalated_{channel}"] += 1
        
        # Update hourly stats
        hour_key = datetime.utcnow().strftime("%Y-%m-%d_%H")
        self.hourly_stats[hour_key]["escalations"] += 1
        
        logger.info(
            "Conversation escalation recorded",
            channel=channel,
            reason=reason
        )
    
    def record_message_processed(
        self,
        channel: str,
        response_time_ms: float,
        phi_detected: bool = False
    ) -> None:
        """Record message processing metrics."""
        self.message_counter.labels(
            channel=channel,
            type="user"
        ).inc()
        
        # Record response time
        response_time_seconds = response_time_ms / 1000
        self.response_time_histogram.labels(channel=channel).observe(response_time_seconds)
        
        # Store for dashboard
        self.response_times.append({
            "timestamp": datetime.utcnow(),
            "response_time_ms": response_time_ms,
            "channel": channel
        })
        
        # Record PHI detection
        if phi_detected:
            self.phi_detection_counter.labels(detection_type="automated").inc()
            self.phi_detections.append({
                "timestamp": datetime.utcnow(),
                "channel": channel,
                "method": "automated"
            })
        
        # Update hourly stats
        hour_key = datetime.utcnow().strftime("%Y-%m-%d_%H")
        self.hourly_stats[hour_key]["messages_processed"] += 1
        if phi_detected:
            self.hourly_stats[hour_key]["phi_detections"] += 1
        
        logger.debug(
            "Message processing recorded",
            channel=channel,
            response_time_ms=response_time_ms,
            phi_detected=phi_detected
        )
    
    def record_message_error(
        self,
        conversation_id: str,
        error_type: str
    ) -> None:
        """Record message processing error."""
        self.error_counter.labels(
            error_type=error_type,
            component="message_processing"
        ).inc()
        
        self.conversation_metrics["total_errors"] += 1
        
        # Update hourly stats
        hour_key = datetime.utcnow().strftime("%Y-%m-%d_%H")
        self.hourly_stats[hour_key]["errors"] += 1
        
        logger.warning(
            "Message error recorded",
            conversation_id=conversation_id,
            error_type=error_type
        )
    
    def record_request_start(self, method: str, path: str) -> None:
        """Record API request start."""
        # This would be called by middleware
        pass
    
    def record_request_end(
        self,
        method: str,
        path: str,
        status_code: int
    ) -> None:
        """Record API request completion."""
        # This would be called by middleware
        pass
    
    def record_request_error(
        self,
        method: str,
        path: str,
        error_type: str
    ) -> None:
        """Record API request error."""
        self.error_counter.labels(
            error_type=error_type,
            component="api"
        ).inc()
    
    def update_agent_workload(self, agent_id: str, workload: int) -> None:
        """Update agent workload metric."""
        self.agent_workload_gauge.labels(agent_id=agent_id).set(workload)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics for dashboard."""
        current_time = datetime.utcnow()
        uptime_seconds = (current_time - self.start_time).total_seconds()
        
        # Calculate average satisfaction score
        avg_satisfaction = 0.0
        if self.conversation_metrics["satisfaction_count"] > 0:
            avg_satisfaction = (
                self.conversation_metrics["satisfaction_sum"] /
                self.conversation_metrics["satisfaction_count"]
            )
        
        # Calculate average response time
        recent_response_times = [
            r["response_time_ms"] for r in self.response_times
            if (current_time - r["timestamp"]).total_seconds() < 3600  # Last hour
        ]
        avg_response_time = sum(recent_response_times) / len(recent_response_times) if recent_response_times else 0
        
        # Calculate escalation rate
        total_conversations = (
            self.conversation_metrics["total_completed"] +
            self.conversation_metrics["total_escalated"]
        )
        escalation_rate = 0.0
        if total_conversations > 0:
            escalation_rate = (
                self.conversation_metrics["total_escalated"] / total_conversations
            ) * 100
        
        return {
            "timestamp": current_time.isoformat(),
            "uptime_seconds": uptime_seconds,
            "conversations": {
                "total_started": self.conversation_metrics["total_started"],
                "total_completed": self.conversation_metrics["total_completed"],
                "total_escalated": self.conversation_metrics["total_escalated"],
                "escalation_rate_percent": round(escalation_rate, 2)
            },
            "performance": {
                "avg_response_time_ms": round(avg_response_time, 2),
                "avg_satisfaction_score": round(avg_satisfaction, 2),
                "total_errors": self.conversation_metrics["total_errors"]
            },
            "compliance": {
                "phi_detections_last_hour": len([
                    p for p in self.phi_detections
                    if (current_time - p["timestamp"]).total_seconds() < 3600
                ]),
                "phi_detection_rate": self._calculate_phi_detection_rate()
            },
            "channels": self._get_channel_metrics()
        }
    
    def get_hourly_stats(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly statistics for the last N hours."""
        stats = []
        current_time = datetime.utcnow()
        
        for i in range(hours):
            hour_time = current_time - timedelta(hours=i)
            hour_key = hour_time.strftime("%Y-%m-%d_%H")
            hour_data = self.hourly_stats.get(hour_key, {})
            
            stats.append({
                "hour": hour_time.strftime("%Y-%m-%d %H:00"),
                "conversations_started": hour_data.get("conversations_started", 0),
                "conversations_completed": hour_data.get("conversations_completed", 0),
                "escalations": hour_data.get("escalations", 0),
                "messages_processed": hour_data.get("messages_processed", 0),
                "phi_detections": hour_data.get("phi_detections", 0),
                "errors": hour_data.get("errors", 0)
            })
        
        return list(reversed(stats))  # Return chronologically
    
    def get_sla_metrics(self) -> Dict[str, Any]:
        """Get SLA compliance metrics."""
        current_time = datetime.utcnow()
        
        # Response time SLA (target: < 3 seconds)
        recent_times = [
            r["response_time_ms"] for r in self.response_times
            if (current_time - r["timestamp"]).total_seconds() < 3600
        ]
        
        response_time_sla = 0.0
        if recent_times:
            under_sla = sum(1 for t in recent_times if t < 3000)
            response_time_sla = (under_sla / len(recent_times)) * 100
        
        # Escalation SLA (target: > 80% resolution without escalation)
        resolution_sla = 100 - self._calculate_escalation_rate()
        
        return {
            "response_time_sla_percent": round(response_time_sla, 2),
            "target_response_time_ms": 3000,
            "resolution_sla_percent": round(resolution_sla, 2),
            "target_resolution_percent": 80.0,
            "last_updated": current_time.isoformat()
        }
    
    def _calculate_phi_detection_rate(self) -> float:
        """Calculate PHI detection rate."""
        current_time = datetime.utcnow()
        
        # PHI detections in last hour
        recent_phi = len([
            p for p in self.phi_detections
            if (current_time - p["timestamp"]).total_seconds() < 3600
        ])
        
        # Messages processed in last hour
        recent_messages = len([
            r for r in self.response_times
            if (current_time - r["timestamp"]).total_seconds() < 3600
        ])
        
        if recent_messages == 0:
            return 0.0
        
        return (recent_phi / recent_messages) * 100
    
    def _calculate_escalation_rate(self) -> float:
        """Calculate current escalation rate."""
        total_conversations = (
            self.conversation_metrics["total_completed"] +
            self.conversation_metrics["total_escalated"]
        )
        
        if total_conversations == 0:
            return 0.0
        
        return (
            self.conversation_metrics["total_escalated"] / total_conversations
        ) * 100
    
    def _get_channel_metrics(self) -> Dict[str, Dict[str, int]]:
        """Get metrics broken down by channel."""
        channels = {}
        
        for key, value in self.conversation_metrics.items():
            if "_" in key:
                parts = key.split("_", 1)
                if len(parts) == 2:
                    metric_type, channel = parts
                    if channel not in channels:
                        channels[channel] = {}
                    channels[channel][metric_type] = value
        
        return channels 