"""
Monitoring Domain Services

Health assessment, circuit breaker management, and supervision logic.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from .entities import (
    Alert,
    AlertSeverity,
    CircuitBreaker,
    CircuitBreakerState,
    HealthReport,
    HealthStatus,
    PerformanceMetrics
)

logger = logging.getLogger(__name__)


class CircuitBreakerManager:
    """
    Manages multiple circuit breakers for trading supervision.

    Default circuit breakers:
    - Drawdown > 20%
    - 3+ consecutive losses
    - API latency > 5 seconds
    - Daily loss > 10%
    - Volume anomaly (3+ std deviations)
    """

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._initialize_default_breakers()

    def _initialize_default_breakers(self):
        """Initialize default circuit breakers."""
        self.circuit_breakers = {
            "drawdown": CircuitBreaker(
                name="drawdown",
                description="Maximum drawdown exceeded",
                threshold=0.20,  # 20%
                current_value=0.0,
                max_consecutive=1,  # Immediate trigger
                recovery_time_seconds=3600  # 1 hour
            ),
            "consecutive_losses": CircuitBreaker(
                name="consecutive_losses",
                description="Too many consecutive losses",
                threshold=3.0,
                current_value=0.0,
                max_consecutive=1,
                recovery_time_seconds=1800  # 30 minutes
            ),
            "api_latency": CircuitBreaker(
                name="api_latency",
                description="API latency too high",
                threshold=5000.0,  # 5 seconds
                current_value=0.0,
                max_consecutive=3,
                recovery_time_seconds=600  # 10 minutes
            ),
            "daily_loss": CircuitBreaker(
                name="daily_loss",
                description="Maximum daily loss exceeded",
                threshold=0.10,  # 10%
                current_value=0.0,
                max_consecutive=1,
                recovery_time_seconds=86400  # 24 hours (next day)
            ),
            "api_failures": CircuitBreaker(
                name="api_failures",
                description="Too many API failures",
                threshold=5.0,  # 5 failures per hour
                current_value=0.0,
                max_consecutive=2,
                recovery_time_seconds=1800  # 30 minutes
            )
        }

    def check_all(self, metrics: PerformanceMetrics) -> List[CircuitBreaker]:
        """
        Check all circuit breakers against current metrics.

        Returns:
            List of triggered circuit breakers
        """
        triggered = []

        # Check drawdown
        if self.circuit_breakers["drawdown"].check(abs(metrics.drawdown)):
            triggered.append(self.circuit_breakers["drawdown"])
            logger.warning(
                f"Circuit breaker triggered: drawdown "
                f"({metrics.drawdown:.1%} > 20%)"
            )

        # Check consecutive losses
        if self.circuit_breakers["consecutive_losses"].check(
            float(metrics.consecutive_losses)
        ):
            triggered.append(self.circuit_breakers["consecutive_losses"])
            logger.warning(
                f"Circuit breaker triggered: {metrics.consecutive_losses} "
                f"consecutive losses"
            )

        # Check API latency
        if self.circuit_breakers["api_latency"].check(
            metrics.api_latency_ms
        ):
            triggered.append(self.circuit_breakers["api_latency"])
            logger.warning(
                f"Circuit breaker triggered: API latency "
                f"{metrics.api_latency_ms:.0f}ms > 5000ms"
            )

        # Check daily loss
        if self.circuit_breakers["daily_loss"].check(
            abs(metrics.daily_pnl_pct)
        ):
            triggered.append(self.circuit_breakers["daily_loss"])
            logger.warning(
                f"Circuit breaker triggered: daily loss "
                f"{metrics.daily_pnl_pct:.1%} > 10%"
            )

        return triggered

    def get_active_breakers(self) -> List[CircuitBreaker]:
        """Get all currently triggered circuit breakers."""
        return [
            cb for cb in self.circuit_breakers.values()
            if cb.state == CircuitBreakerState.OPEN
        ]

    def reset_breaker(self, name: str) -> bool:
        """Manually reset a circuit breaker."""
        if name in self.circuit_breakers:
            self.circuit_breakers[name].reset()
            logger.info(f"Circuit breaker reset: {name}")
            return True
        return False

    def reset_all(self):
        """Reset all circuit breakers (use with caution)."""
        for cb in self.circuit_breakers.values():
            cb.reset()
        logger.warning("All circuit breakers reset manually")


class HealthAssessor:
    """
    Assesses system health and generates recommendations.

    Uses metrics, circuit breakers, and trading performance
    to determine overall health status.
    """

    def __init__(self, breaker_manager: CircuitBreakerManager):
        self.breaker_manager = breaker_manager
        self.alerts: List[Alert] = []

    def assess(
        self,
        metrics: PerformanceMetrics,
        daemon_running: bool,
        daemon_pid: Optional[int],
        daemon_uptime: float
    ) -> HealthReport:
        """
        Perform comprehensive health assessment.

        Returns:
            HealthReport with status and recommendations
        """
        # Check circuit breakers
        triggered_breakers = self.breaker_manager.check_all(metrics)

        # Generate alerts
        self._generate_alerts(metrics, triggered_breakers)

        # Calculate risk score (0-100)
        risk_score = self._calculate_risk_score(metrics, triggered_breakers)

        # Determine health status
        status = self._determine_health_status(
            metrics, triggered_breakers, risk_score
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            metrics, triggered_breakers, risk_score, daemon_running
        )

        # Determine actions
        should_pause = risk_score >= 70 or len(triggered_breakers) > 0
        should_stop = risk_score >= 90 or status == HealthStatus.CRITICAL

        return HealthReport(
            timestamp=datetime.now(),
            status=status,
            metrics=metrics,
            circuit_breakers=list(self.breaker_manager.circuit_breakers.values()),
            active_alerts=[a for a in self.alerts if not a.resolved],
            recommendations=recommendations,
            daemon_running=daemon_running,
            daemon_pid=daemon_pid,
            daemon_uptime_seconds=daemon_uptime,
            risk_score=risk_score,
            should_pause=should_pause,
            should_stop=should_stop
        )

    def _calculate_risk_score(
        self,
        metrics: PerformanceMetrics,
        triggered_breakers: List[CircuitBreaker]
    ) -> float:
        """
        Calculate risk score (0-100).

        Higher score = more risky situation.
        """
        score = 0.0

        # Circuit breakers (+30 per breaker)
        score += len(triggered_breakers) * 30

        # Drawdown risk (+20 at 15%, +30 at 20%)
        if abs(metrics.drawdown) > 0.15:
            score += 20
        if abs(metrics.drawdown) > 0.20:
            score += 30

        # Consecutive losses (+10 per loss after 2)
        if metrics.consecutive_losses > 2:
            score += (metrics.consecutive_losses - 2) * 10

        # Daily loss (+15 at 7%, +25 at 10%)
        if abs(metrics.daily_pnl_pct) > 0.07:
            score += 15
        if abs(metrics.daily_pnl_pct) > 0.10:
            score += 25

        # Win rate risk (+10 if < 40%)
        if metrics.win_rate < 0.40:
            score += 10

        # Sharpe ratio risk (+10 if < 0.5)
        if metrics.sharpe_ratio < 0.5:
            score += 10

        # API latency (+15 if > 3s)
        if metrics.api_latency_ms > 3000:
            score += 15

        # Data staleness (+20 if > 60s)
        if metrics.data_freshness_seconds > 60:
            score += 20

        return min(score, 100.0)

    def _determine_health_status(
        self,
        metrics: PerformanceMetrics,
        triggered_breakers: List[CircuitBreaker],
        risk_score: float
    ) -> HealthStatus:
        """Determine overall health status."""
        if risk_score >= 90 or len(triggered_breakers) >= 3:
            return HealthStatus.CRITICAL

        if risk_score >= 70 or len(triggered_breakers) >= 2:
            return HealthStatus.UNHEALTHY

        if risk_score >= 50 or len(triggered_breakers) >= 1:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def _generate_alerts(
        self,
        metrics: PerformanceMetrics,
        triggered_breakers: List[CircuitBreaker]
    ):
        """Generate alerts for anomalies."""
        # Circuit breaker alerts
        for breaker in triggered_breakers:
            alert = Alert(
                alert_id=str(uuid4()),
                severity=AlertSeverity.CRITICAL,
                title=f"Circuit Breaker: {breaker.name}",
                message=breaker.description,
                timestamp=datetime.now(),
                metadata={
                    "current_value": breaker.current_value,
                    "threshold": breaker.threshold
                }
            )
            self.alerts.append(alert)

        # Performance alerts
        if abs(metrics.drawdown) > 0.15:
            self.alerts.append(Alert(
                alert_id=str(uuid4()),
                severity=AlertSeverity.WARNING,
                title="High Drawdown",
                message=f"Drawdown at {metrics.drawdown:.1%}",
                timestamp=datetime.now()
            ))

        if metrics.consecutive_losses >= 2:
            self.alerts.append(Alert(
                alert_id=str(uuid4()),
                severity=AlertSeverity.WARNING,
                title="Consecutive Losses",
                message=f"{metrics.consecutive_losses} losses in a row",
                timestamp=datetime.now()
            ))

    def _generate_recommendations(
        self,
        metrics: PerformanceMetrics,
        triggered_breakers: List[CircuitBreaker],
        risk_score: float,
        daemon_running: bool
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if not daemon_running:
            recommendations.append(
                "Daemon not running. Start with: "
                "python scripts/monitor_paper_trading.py start"
            )
            return recommendations

        if risk_score >= 90:
            recommendations.append(
                "CRITICAL: Stop trading immediately. "
                "Run: python scripts/monitor_paper_trading.py stop"
            )

        if len(triggered_breakers) > 0:
            recommendations.append(
                f"Pause trading. {len(triggered_breakers)} circuit breaker(s) "
                "triggered. Run: python scripts/monitor_paper_trading.py pause"
            )

        if abs(metrics.drawdown) > 0.15:
            recommendations.append(
                "Review positions. Consider reducing exposure or "
                "tightening stop-losses."
            )

        if metrics.consecutive_losses >= 3:
            recommendations.append(
                "Strategy may not suit current market conditions. "
                "Pause and analyze recent trades."
            )

        if metrics.api_latency_ms > 3000:
            recommendations.append(
                "High API latency detected. Check network connection "
                "or Binance API status."
            )

        if metrics.win_rate < 0.40 and metrics.total_trades_today > 5:
            recommendations.append(
                f"Low win rate ({metrics.win_rate:.1%}). "
                "Review strategy parameters."
            )

        if not recommendations:
            recommendations.append(
                "System healthy. Continue monitoring. "
                "Next check in 1 hour."
            )

        return recommendations
