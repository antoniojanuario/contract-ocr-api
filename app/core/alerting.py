"""
Error notification and alerting system
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque

from app.core.logging import get_logger


logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts"""
    ERROR_FREQUENCY = "error_frequency"
    SYSTEM_HEALTH = "system_health"
    PERFORMANCE = "performance"
    SECURITY = "security"
    RESOURCE_USAGE = "resource_usage"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


class AlertThreshold:
    """Alert threshold configuration"""
    
    def __init__(
        self,
        error_code: str,
        count_threshold: int,
        time_window_minutes: int,
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        cooldown_minutes: int = 60
    ):
        self.error_code = error_code
        self.count_threshold = count_threshold
        self.time_window_minutes = time_window_minutes
        self.severity = severity
        self.cooldown_minutes = cooldown_minutes


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.error_counts: Dict[str, deque] = defaultdict(deque)
        self.last_alert_time: Dict[str, datetime] = {}
        self.alert_handlers: List[callable] = []
        
        # Default alert thresholds
        self.thresholds = {
            "INTERNAL_SERVER_ERROR": AlertThreshold("INTERNAL_SERVER_ERROR", 5, 10, AlertSeverity.HIGH),
            "DATABASE_ERROR": AlertThreshold("DATABASE_ERROR", 3, 5, AlertSeverity.CRITICAL),
            "OCR_PROCESSING_ERROR": AlertThreshold("OCR_PROCESSING_ERROR", 10, 15, AlertSeverity.MEDIUM),
            "RATE_LIMIT_EXCEEDED": AlertThreshold("RATE_LIMIT_EXCEEDED", 20, 5, AlertSeverity.LOW),
            "EXTERNAL_SERVICE_ERROR": AlertThreshold("EXTERNAL_SERVICE_ERROR", 5, 10, AlertSeverity.HIGH),
            "FILE_STORAGE_ERROR": AlertThreshold("FILE_STORAGE_ERROR", 3, 10, AlertSeverity.HIGH),
            "AUTHENTICATION_ERROR": AlertThreshold("AUTHENTICATION_ERROR", 50, 10, AlertSeverity.MEDIUM, 30),
        }
    
    def add_alert_handler(self, handler: callable):
        """Add an alert handler function"""
        self.alert_handlers.append(handler)
    
    def track_error(
        self,
        error_code: str,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Track an error occurrence for alerting"""
        now = datetime.utcnow()
        
        # Add to error count tracking
        self.error_counts[error_code].append(now)
        
        # Clean old entries outside the time window
        threshold = self.thresholds.get(error_code)
        if threshold:
            cutoff_time = now - timedelta(minutes=threshold.time_window_minutes)
            while (self.error_counts[error_code] and 
                   self.error_counts[error_code][0] < cutoff_time):
                self.error_counts[error_code].popleft()
            
            # Check if we should trigger an alert
            self._check_alert_threshold(error_code, threshold, request_id, details)
    
    def _check_alert_threshold(
        self,
        error_code: str,
        threshold: AlertThreshold,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Check if error count exceeds threshold and trigger alert"""
        current_count = len(self.error_counts[error_code])
        
        if current_count >= threshold.count_threshold:
            # Check cooldown period
            last_alert = self.last_alert_time.get(error_code)
            now = datetime.utcnow()
            
            if (not last_alert or 
                (now - last_alert).total_seconds() >= threshold.cooldown_minutes * 60):
                
                self._create_error_frequency_alert(
                    error_code, threshold, current_count, request_id, details
                )
                self.last_alert_time[error_code] = now
    
    def _create_error_frequency_alert(
        self,
        error_code: str,
        threshold: AlertThreshold,
        count: int,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Create an error frequency alert"""
        alert_id = f"error_freq_{error_code}_{int(datetime.utcnow().timestamp())}"
        
        alert = Alert(
            id=alert_id,
            type=AlertType.ERROR_FREQUENCY,
            severity=threshold.severity,
            title=f"High Error Frequency: {error_code}",
            message=f"Error {error_code} occurred {count} times in {threshold.time_window_minutes} minutes",
            details={
                "error_code": error_code,
                "count": count,
                "time_window_minutes": threshold.time_window_minutes,
                "threshold": threshold.count_threshold,
                "request_id": request_id,
                "additional_details": details or {}
            }
        )
        
        self.alerts[alert_id] = alert
        self._send_alert(alert)
    
    def create_system_health_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a system health alert"""
        alert_id = f"health_{int(datetime.utcnow().timestamp())}"
        
        alert = Alert(
            id=alert_id,
            type=AlertType.SYSTEM_HEALTH,
            severity=severity,
            title=title,
            message=message,
            details=details or {}
        )
        
        self.alerts[alert_id] = alert
        self._send_alert(alert)
        return alert_id
    
    def create_performance_alert(
        self,
        operation: str,
        duration: float,
        threshold: float,
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a performance alert"""
        alert_id = f"perf_{operation}_{int(datetime.utcnow().timestamp())}"
        
        alert = Alert(
            id=alert_id,
            type=AlertType.PERFORMANCE,
            severity=severity,
            title=f"Performance Issue: {operation}",
            message=f"Operation {operation} took {duration:.2f}s (threshold: {threshold:.2f}s)",
            details={
                "operation": operation,
                "duration": duration,
                "threshold": threshold,
                "additional_details": details or {}
            }
        )
        
        self.alerts[alert_id] = alert
        self._send_alert(alert)
        return alert_id
    
    def create_security_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.HIGH,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a security alert"""
        alert_id = f"security_{int(datetime.utcnow().timestamp())}"
        
        alert = Alert(
            id=alert_id,
            type=AlertType.SECURITY,
            severity=severity,
            title=title,
            message=message,
            details=details or {}
        )
        
        self.alerts[alert_id] = alert
        self._send_alert(alert)
        return alert_id
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            self.alerts[alert_id].resolved_at = datetime.utcnow()
            
            logger.info(
                f"Alert resolved: {alert_id}",
                extra={
                    "alert_id": alert_id,
                    "alert_type": self.alerts[alert_id].type.value
                }
            )
            return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts"""
        return [alert for alert in self.alerts.values() if not alert.resolved]
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity level"""
        return [alert for alert in self.alerts.values() if alert.severity == severity]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alerts"""
        active_alerts = self.get_active_alerts()
        
        summary = {
            "total_alerts": len(self.alerts),
            "active_alerts": len(active_alerts),
            "resolved_alerts": len(self.alerts) - len(active_alerts),
            "by_severity": {
                "critical": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                "high": len([a for a in active_alerts if a.severity == AlertSeverity.HIGH]),
                "medium": len([a for a in active_alerts if a.severity == AlertSeverity.MEDIUM]),
                "low": len([a for a in active_alerts if a.severity == AlertSeverity.LOW])
            },
            "by_type": {}
        }
        
        # Count by type
        for alert_type in AlertType:
            summary["by_type"][alert_type.value] = len([
                a for a in active_alerts if a.type == alert_type
            ])
        
        return summary
    
    def _send_alert(self, alert: Alert):
        """Send alert to all registered handlers"""
        logger.warning(
            f"Alert triggered: {alert.title}",
            extra={
                "alert_id": alert.id,
                "alert_type": alert.type.value,
                "alert_severity": alert.severity.value,
                "alert_message": alert.message
            }
        )
        
        # Send to all handlers
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(alert))
                else:
                    handler(alert)
            except Exception as e:
                logger.error(
                    f"Failed to send alert to handler: {str(e)}",
                    extra={
                        "alert_id": alert.id,
                        "handler": str(handler),
                        "error": str(e)
                    }
                )
    
    def cleanup_old_alerts(self, max_age_days: int = 30) -> int:
        """Clean up old resolved alerts"""
        cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
        
        alerts_to_remove = []
        for alert_id, alert in self.alerts.items():
            if (alert.resolved and 
                alert.resolved_at and 
                alert.resolved_at < cutoff_time):
                alerts_to_remove.append(alert_id)
        
        for alert_id in alerts_to_remove:
            del self.alerts[alert_id]
        
        logger.info(
            f"Cleaned up {len(alerts_to_remove)} old alerts",
            extra={"cleaned_count": len(alerts_to_remove)}
        )
        
        return len(alerts_to_remove)


# Default alert handlers

async def log_alert_handler(alert: Alert):
    """Default alert handler that logs to the error log"""
    logger.error(
        f"ALERT [{alert.severity.upper()}] {alert.title}: {alert.message}",
        extra={
            "alert_id": alert.id,
            "alert_type": alert.type.value,
            "alert_severity": alert.severity.value,
            "alert_details": alert.details
        }
    )


def console_alert_handler(alert: Alert):
    """Alert handler that prints to console"""
    print(f"\n🚨 ALERT [{alert.severity.upper()}] 🚨")
    print(f"Title: {alert.title}")
    print(f"Message: {alert.message}")
    print(f"Time: {alert.timestamp}")
    print(f"Details: {alert.details}")
    print("-" * 50)


# Global alert manager instance
_alert_manager = None


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
        # Add default handlers
        _alert_manager.add_alert_handler(log_alert_handler)
        # Uncomment for console alerts in development
        # _alert_manager.add_alert_handler(console_alert_handler)
    return _alert_manager


def track_error_for_alerting(
    error_code: str,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """Convenience function to track errors for alerting"""
    alert_manager = get_alert_manager()
    alert_manager.track_error(error_code, request_id, details)