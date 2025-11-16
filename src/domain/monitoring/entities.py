"""
Monitoring Domain Entities

Circuit breakers, health checks, and trading supervision entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Broken, no trading
    HALF_OPEN = "half_open"  # Testing recovery


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """Overall system health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for automatic trading suspension.

    Monitors specific condition and triggers open state when
    threshold is exceeded.
    """
    name: str
    description: str
    threshold: float
    current_value: float
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    triggered_at: Optional[datetime] = None
    recovery_time_seconds: int = 3600  # 1 hour default
    consecutive_violations: int = 0
    max_consecutive: int = 3

    def check(self, current_value: float) -> bool:
        """
        Check if circuit breaker should trigger.

        Returns:
            True if threshold exceeded, False otherwise
        """
        self.current_value = current_value

        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery time elapsed
            if self.triggered_at:
                elapsed = (datetime.now() - self.triggered_at).total_seconds()
                if elapsed >= self.recovery_time_seconds:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.consecutive_violations = 0
                    return False
            return True

        # Check threshold
        exceeded = current_value >= self.threshold

        if exceeded:
            self.consecutive_violations += 1
            if self.consecutive_violations >= self.max_consecutive:
                self.trigger()
                return True
        else:
            self.consecutive_violations = 0
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.reset()

        return self.state == CircuitBreakerState.OPEN

    def trigger(self):
        """Trigger circuit breaker (open state)."""
        self.state = CircuitBreakerState.OPEN
        self.triggered_at = datetime.now()

    def reset(self):
        """Reset circuit breaker (closed state)."""
        self.state = CircuitBreakerState.CLOSED
        self.triggered_at = None
        self.consecutive_violations = 0


@dataclass
class PerformanceMetrics:
    """Trading performance metrics for health assessment."""
    timestamp: datetime
    portfolio_value: float
    daily_pnl: float
    daily_pnl_pct: float
    drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    active_positions: int
    total_trades_today: int
    winning_trades_today: int
    losing_trades_today: int
    consecutive_losses: int
    api_latency_ms: float
    data_freshness_seconds: float


@dataclass
class Alert:
    """System alert for anomalies or issues."""
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class HealthReport:
    """
    Comprehensive health assessment report.

    Used by JARVIS to make supervision decisions.
    """
    timestamp: datetime
    status: HealthStatus
    metrics: PerformanceMetrics
    circuit_breakers: List[CircuitBreaker]
    active_alerts: List[Alert]
    recommendations: List[str]

    # Daemon status
    daemon_running: bool
    daemon_pid: Optional[int]
    daemon_uptime_seconds: float

    # Risk assessment
    risk_score: float  # 0-100 (higher = riskier)
    should_pause: bool
    should_stop: bool

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "metrics": {
                "portfolio_value": self.metrics.portfolio_value,
                "daily_pnl": self.metrics.daily_pnl,
                "daily_pnl_pct": self.metrics.daily_pnl_pct,
                "drawdown": self.metrics.drawdown,
                "sharpe_ratio": self.metrics.sharpe_ratio,
                "win_rate": self.metrics.win_rate,
                "profit_factor": self.metrics.profit_factor,
                "active_positions": self.metrics.active_positions,
                "consecutive_losses": self.metrics.consecutive_losses,
                "api_latency_ms": self.metrics.api_latency_ms
            },
            "circuit_breakers": [
                {
                    "name": cb.name,
                    "state": cb.state.value,
                    "current_value": cb.current_value,
                    "threshold": cb.threshold,
                    "triggered_at": cb.triggered_at.isoformat() if cb.triggered_at else None
                }
                for cb in self.circuit_breakers
            ],
            "active_alerts": [
                {
                    "alert_id": a.alert_id,
                    "severity": a.severity.value,
                    "title": a.title,
                    "message": a.message,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in self.active_alerts
            ],
            "recommendations": self.recommendations,
            "daemon": {
                "running": self.daemon_running,
                "pid": self.daemon_pid,
                "uptime_seconds": self.daemon_uptime_seconds
            },
            "risk": {
                "score": self.risk_score,
                "should_pause": self.should_pause,
                "should_stop": self.should_stop
            }
        }
