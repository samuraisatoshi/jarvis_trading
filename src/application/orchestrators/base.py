"""
Base orchestrator for coordinating complex workflows.

This module defines the Orchestrator Pattern base class. Orchestrators are
responsible for coordinating workflows that involve multiple domain services,
repositories, and external systems. They contain NO business logic - that
belongs in the domain layer.

SOLID Principles:
- Single Responsibility: Only coordinates workflow
- Open/Closed: Open for extension (new orchestrators), closed for modification
- Liskov Substitution: All orchestrators follow same interface
- Interface Segregation: Minimal interface for orchestration
- Dependency Inversion: Depends on abstractions (services, repos)

Key Differences from Services:
- Services: Single-domain business logic
- Orchestrators: Multi-domain workflow coordination
- Orchestrators use services, never contain domain logic
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from loguru import logger


class BaseOrchestrator(ABC):
    """
    Abstract base class for orchestrators.

    Orchestrators coordinate workflows that span multiple domains,
    services, and external systems. They handle:
    - Service coordination
    - Error recovery
    - Retry logic
    - Transaction boundaries
    - Workflow state management

    They should NOT contain:
    - Business logic (domain layer)
    - Data access (repositories)
    - External API calls (infrastructure)

    Example:
        >>> class MyOrchestrator(BaseOrchestrator):
        ...     def __init__(self, service_a, service_b):
        ...         self.service_a = service_a
        ...         self.service_b = service_b
        ...
        ...     def execute(self, params: Dict) -> Dict:
        ...         # Coordinate services
        ...         result_a = self.service_a.do_something()
        ...         result_b = self.service_b.do_something_else(result_a)
        ...         return {'status': 'success', 'data': result_b}
    """

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the orchestrated workflow.

        This is the main entry point for the orchestrator. It should
        coordinate all necessary services and return a result dictionary.

        Args:
            **kwargs: Workflow-specific parameters

        Returns:
            Dict with workflow results:
                {
                    'status': 'success' | 'failure',
                    'data': <workflow results>,
                    'error': <error message if failed>,
                    'metadata': <execution metadata>
                }

        Raises:
            OrchestrationError: If workflow cannot complete
        """
        pass

    def _handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        retry_count: int = 0,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Handle orchestration errors with retry logic.

        Args:
            error: The exception that occurred
            context: Execution context for debugging
            retry_count: Current retry attempt
            max_retries: Maximum retries before failing

        Returns:
            Error result dict or None if should retry
        """
        logger.error(
            f"Orchestration error (attempt {retry_count + 1}/{max_retries}): {error}",
            exc_info=True,
            extra={'context': context}
        )

        if retry_count < max_retries:
            logger.info(f"Retrying... (attempt {retry_count + 1}/{max_retries})")
            return None  # Signal caller to retry

        return {
            'status': 'failure',
            'error': str(error),
            'context': context,
            'retry_count': retry_count
        }

    def _log_execution_start(self, workflow_name: str, params: Dict[str, Any]):
        """Log workflow execution start."""
        logger.info(
            f"\n{'=' * 80}\n"
            f"Orchestrator: {workflow_name}\n"
            f"{'=' * 80}\n"
            f"Parameters: {params}"
        )

    def _log_execution_end(
        self,
        workflow_name: str,
        result: Dict[str, Any],
        duration_seconds: float = None
    ):
        """Log workflow execution end."""
        status_emoji = "✅" if result.get('status') == 'success' else "❌"
        duration_str = f" ({duration_seconds:.2f}s)" if duration_seconds else ""

        logger.info(
            f"\n{status_emoji} Orchestrator '{workflow_name}' completed{duration_str}\n"
            f"Status: {result.get('status')}\n"
            f"{'=' * 80}\n"
        )


class OrchestrationError(Exception):
    """Exception raised when orchestration workflow fails."""

    def __init__(self, message: str, context: Dict[str, Any] = None):
        """
        Initialize orchestration error.

        Args:
            message: Error description
            context: Additional context (params, state, etc.)
        """
        self.message = message
        self.context = context or {}
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} | Context: {self.context}"
