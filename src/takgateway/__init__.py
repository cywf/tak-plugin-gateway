"""
TAK Plugin Gateway - Shared library for TAK-Server integration.

Provides CoT message generation, TAK-Server client (mTLS), and health monitoring.
"""

__version__ = "1.0.0"

from .cot import (
    CoTEvent,
    CoTTypes,
    CoTBuilder,
    create_alert,
    create_marker,
)

from .client import (
    TAKServerConfig,
    TAKServerClient,
    create_client_from_env,
)

from .health import (
    HealthStatus,
    HealthMonitor,
    setup_logging,
)

__all__ = [
    # CoT
    "CoTEvent",
    "CoTTypes",
    "CoTBuilder",
    "create_alert",
    "create_marker",
    
    # Client
    "TAKServerConfig",
    "TAKServerClient",
    "create_client_from_env",
    
    # Health
    "HealthStatus",
    "HealthMonitor",
    "setup_logging",
]
