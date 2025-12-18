"""
Resource monitoring and alerting for deployment optimization
"""
import asyncio
import psutil
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
from app.core.config import settings

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Monitor system resources and send alerts when thresholds are exceeded"""
    
    def __init__(self):
        self.last_alert_time: Dict[str, datetime] = {}
        self.alert_cooldown = timedelta(minutes=5)  # Prevent spam alerts
        
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Process count
            process_count = len(psutil.pids())
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "percent": memory_percent,
                    "total_mb": memory.total / (1024 * 1024),
                    "available_mb": memory_available_mb,
                    "used_mb": memory.used / (1024 * 1024)
                },
                "disk": {
                    "percent": disk_percent,
                    "total_gb": disk.total / (1024 * 1024 * 1024),
                    "free_gb": disk_free_gb,
                    "used_gb": disk.used / (1024 * 1024 * 1024)
                },
                "processes": process_count,
                "environment": settings.ENVIRONMENT
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    async def check_thresholds(self, metrics: Dict[str, Any]) -> None:
        """Check if any metrics exceed alert thresholds"""
        alerts = []
        
        # Check CPU threshold
        if metrics.get("cpu", {}).get("percent", 0) > settings.CPU_ALERT_THRESHOLD:
            alerts.append({
                "type": "cpu_high",
                "message": f"CPU usage is {metrics['cpu']['percent']:.1f}% (threshold: {settings.CPU_ALERT_THRESHOLD}%)",
                "severity": "warning" if metrics['cpu']['percent'] < 95 else "critical"
            })
        
        # Check memory threshold
        if metrics.get("memory", {}).get("percent", 0) > settings.MEMORY_ALERT_THRESHOLD:
            alerts.append({
                "type": "memory_high",
                "message": f"Memory usage is {metrics['memory']['percent']:.1f}% (threshold: {settings.MEMORY_ALERT_THRESHOLD}%)",
                "severity": "warning" if metrics['memory']['percent'] < 95 else "critical"
            })
        
        # Check disk threshold
        if metrics.get("disk", {}).get("percent", 0) > settings.DISK_ALERT_THRESHOLD:
            alerts.append({
                "type": "disk_high",
                "message": f"Disk usage is {metrics['disk']['percent']:.1f}% (threshold: {settings.DISK_ALERT_THRESHOLD}%)",
                "severity": "warning" if metrics['disk']['percent'] < 98 else "critical"
            })
        
        # Check available memory for free platforms
        if settings.is_free_platform and metrics.get("memory", {}).get("available_mb", 0) < 100:
            alerts.append({
                "type": "memory_low",
                "message": f"Available memory is {metrics['memory']['available_mb']:.1f}MB",
                "severity": "critical"
            })
        
        # Send alerts
        for alert in alerts:
            await self.send_alert(alert, metrics)
    
    async def send_alert(self, alert: Dict[str, Any], metrics: Dict[str, Any]) -> None:
        """Send alert notification"""
        alert_type = alert["type"]
        now = datetime.utcnow()
        
        # Check cooldown
        if alert_type in self.last_alert_time:
            if now - self.last_alert_time[alert_type] < self.alert_cooldown:
                return
        
        self.last_alert_time[alert_type] = now
        
        # Log alert
        log_level = logging.CRITICAL if alert["severity"] == "critical" else logging.WARNING
        logger.log(log_level, f"ALERT: {alert['message']}")
        
        # Send webhook if configured
        if settings.ALERT_WEBHOOK_URL:
            await self.send_webhook_alert(alert, metrics)
    
    async def send_webhook_alert(self, alert: Dict[str, Any], metrics: Dict[str, Any]) -> None:
        """Send alert via webhook"""
        try:
            payload = {
                "alert": alert,
                "metrics": metrics,
                "service": settings.PROJECT_NAME,
                "environment": settings.ENVIRONMENT,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.ALERT_WEBHOOK_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Alert webhook sent successfully for {alert['type']}")
                    else:
                        logger.error(f"Alert webhook failed with status {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    async def start_monitoring(self, interval: int = 60) -> None:
        """Start continuous resource monitoring"""
        logger.info(f"Starting resource monitoring (interval: {interval}s)")
        
        while True:
            try:
                metrics = await self.get_system_metrics()
                if metrics:
                    await self.check_thresholds(metrics)
                    
                    # Log metrics periodically
                    if int(time.time()) % 300 == 0:  # Every 5 minutes
                        logger.info(f"System metrics: CPU={metrics['cpu']['percent']:.1f}%, "
                                  f"Memory={metrics['memory']['percent']:.1f}%, "
                                  f"Disk={metrics['disk']['percent']:.1f}%")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(interval)


# Global monitor instance
resource_monitor = ResourceMonitor()


async def get_health_metrics() -> Dict[str, Any]:
    """Get health metrics for health check endpoint"""
    try:
        metrics = await resource_monitor.get_system_metrics()
        
        # Determine health status
        status = "healthy"
        if metrics.get("cpu", {}).get("percent", 0) > 90:
            status = "degraded"
        if metrics.get("memory", {}).get("percent", 0) > 90:
            status = "degraded"
        if metrics.get("disk", {}).get("percent", 0) > 95:
            status = "critical"
        
        return {
            "status": status,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "metrics": metrics,
            "uptime": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get health metrics: {e}")
        return {
            "status": "unknown",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "error": str(e)
        }