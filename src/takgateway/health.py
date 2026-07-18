"""
Health monitoring and logging utilities for TAK plugins.
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class HealthStatus:
    """Health status for a plugin component."""
    
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    last_check: datetime = field(default_factory=datetime.utcnow)
    message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "status": self.status,
            "last_check": self.last_check.isoformat(),
            "message": self.message,
            "metrics": self.metrics
        }


class HealthMonitor:
    """
    Health monitoring for TAK plugins.
    
    Tracks component health (TAK-Server connection, external APIs, etc.)
    and provides unified health check endpoint data.
    """
    
    def __init__(self):
        self.components: Dict[str, HealthStatus] = {}
        self._start_time = time.time()
    
    def register(self, name: str, status: str = "unknown", message: Optional[str] = None):
        """Register a component for health monitoring."""
        self.components[name] = HealthStatus(
            name=name,
            status=status,
            message=message
        )
    
    def update(self, name: str, status: str, message: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None):
        """Update component health status."""
        if name not in self.components:
            self.register(name, status, message)
        else:
            self.components[name].status = status
            self.components[name].last_check = datetime.utcnow()
            self.components[name].message = message
            if metrics:
                self.components[name].metrics = metrics
    
    def mark_healthy(self, name: str, message: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None):
        """Mark component as healthy."""
        self.update(name, "healthy", message, metrics)
    
    def mark_degraded(self, name: str, message: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None):
        """Mark component as degraded."""
        self.update(name, "degraded", message, metrics)
    
    def mark_unhealthy(self, name: str, message: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None):
        """Mark component as unhealthy."""
        self.update(name, "unhealthy", message, metrics)
    
    def get_status(self, name: str) -> Optional[HealthStatus]:
        """Get status for a specific component."""
        return self.components.get(name)
    
    def get_overall_status(self) -> str:
        """
        Get overall health status.
        
        Returns:
            "healthy" if all components healthy
            "degraded" if any component degraded
            "unhealthy" if any component unhealthy
        """
        if not self.components:
            return "unknown"
        
        statuses = [c.status for c in self.components.values()]
        
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "degraded" in statuses:
            return "degraded"
        elif all(s == "healthy" for s in statuses):
            return "healthy"
        else:
            return "unknown"
    
    def get_health_report(self) -> Dict[str, Any]:
        """
        Get complete health report.
        
        Returns:
            Dictionary suitable for JSON health endpoint.
        """
        overall_status = self.get_overall_status()
        uptime = time.time() - self._start_time
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(uptime),
            "components": {
                name: component.to_dict()
                for name, component in self.components.items()
            }
        }


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    log_file: Optional[str] = None
):
    """
    Setup logging for TAK plugins.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string (optional)
        log_file: Log to file (optional)
    """
    if format_string is None:
        format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(format_string))
    handlers.append(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(format_string))
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True
    )
    
    # Suppress noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
