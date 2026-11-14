"""
FinGuard AI — Phase 33: Distributed Saga Orchestrator.
Manages multi-service transaction workflows with forward execution and reverse-order compensation.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from events.event_bus import EventBus, event_bus
from events.models import (
    EventContract,
    EventType,
    SagaInstance,
    SagaStatus,
    SagaStep,
)

logger = logging.getLogger("finguard-saga")


class SagaOrchestrator:
    def __init__(self, bus: EventBus = event_bus):
        self.bus = bus
        self._sagas: Dict[str, SagaInstance] = {}

    def get_saga(self, saga_id: str) -> Optional[SagaInstance]:
        return self._sagas.get(saga_id)

    def list_sagas(self) -> List[SagaInstance]:
        return sorted(self._sagas.values(), key=lambda s: s.created_at, reverse=True)

    def execute_transaction_saga(
        self,
        transaction_id: str,
        customer_id: str,
        amount: float,
        correlation_id: Optional[str] = None,
        force_failure_at_step: Optional[str] = None,
    ) -> SagaInstance:
        """
        Executes a 4-step distributed transaction Saga across microservice boundaries:
        1. AuthorizeHold (Transaction Service)
        2. EvaluateFraudRisk (Fraud-Scoring Service)
        3. SettleTransaction (Ledger / Payment Service)
        4. SendNotification (Notification Service)

        If any step fails, triggers reverse-order compensation across executed steps.
        """
        corr_id = correlation_id or f"corr-{uuid.uuid4().hex[:8]}"
        saga = SagaInstance(
            transaction_id=transaction_id,
            correlation_id=corr_id,
            status=SagaStatus.PROCESSING,
            steps=[
                SagaStep(
                    step_name="AuthorizeHold",
                    service_name="transaction-service",
                    forward_action="account.hold.placed",
                    compensation_action="account.hold.released",
                ),
                SagaStep(
                    step_name="EvaluateFraudRisk",
                    service_name="fraud-scoring-service",
                    forward_action="fraud.risk.evaluated",
                    compensation_action="fraud.reservation.cancelled",
                ),
                SagaStep(
                    step_name="SettleTransaction",
                    service_name="ledger-service",
                    forward_action="ledger.debit.committed",
                    compensation_action="ledger.debit.reversed",
                ),
                SagaStep(
                    step_name="SendNotification",
                    service_name="notification-service",
                    forward_action="customer.notification.dispatched",
                    compensation_action="customer.cancellation.dispatched",
                ),
            ],
        )
        self._sagas[saga.saga_id] = saga

        # Emit Saga Started Event
        self.bus.publish(
            EventContract(
                event_type="saga.started.v1",
                source="saga-orchestrator",
                correlation_id=corr_id,
                payload={"saga_id": saga.saga_id, "transaction_id": transaction_id},
            )
        )

        executed_steps: List[SagaStep] = []
        failed_step_name: Optional[str] = None
        failure_reason: Optional[str] = None

        # Forward execution phase
        for idx, step in enumerate(saga.steps):
            saga.current_step = idx
            logger.info("Executing Saga %s step %s (%s)", saga.saga_id, step.step_name, step.service_name)

            # Check for simulated or business rule failure
            if force_failure_at_step and step.step_name.lower() == force_failure_at_step.lower():
                step.status = "FAILED"
                step.error = f"Simulated failure at {step.step_name}"
                failed_step_name = step.step_name
                failure_reason = step.error
                break

            # Execute forward microservice action
            step.status = "EXECUTED"
            step.executed_at = datetime.now(timezone.utc)
            executed_steps.append(step)

            # Emit step completion event
            self.bus.publish(
                EventContract(
                    event_type=f"{step.step_name.lower()}.completed.v1",
                    source=step.service_name,
                    correlation_id=corr_id,
                    causation_id=saga.saga_id,
                    payload={"saga_id": saga.saga_id, "transaction_id": transaction_id, "amount": amount},
                )
            )

        if failed_step_name:
            # Trigger Reverse-Order Compensation
            logger.warning("Saga %s failed at %s. Commencing reverse compensation.", saga.saga_id, failed_step_name)
            saga.status = SagaStatus.COMPENSATING
            saga.error = failure_reason

            # Reverse the executed steps
            for step in reversed(executed_steps):
                logger.info("Compensating Saga step %s via %s", step.step_name, step.compensation_action)
                step.status = "COMPENSATED"
                step.compensated_at = datetime.now(timezone.utc)
                comp_log = f"Compensated [{step.step_name}] on [{step.service_name}] via action [{step.compensation_action}]"
                saga.compensation_log.append(comp_log)

                # Emit compensation event
                self.bus.publish(
                    EventContract(
                        event_type=f"{step.step_name.lower()}.compensated.v1",
                        source=step.service_name,
                        correlation_id=corr_id,
                        causation_id=saga.saga_id,
                        payload={"saga_id": saga.saga_id, "transaction_id": transaction_id, "action": step.compensation_action},
                    )
                )

            saga.status = SagaStatus.COMPENSATED
            saga.updated_at = datetime.now(timezone.utc)

            self.bus.publish(
                EventContract(
                    event_type=EventType.SAGA_COMPENSATED.value,
                    source="saga-orchestrator",
                    correlation_id=corr_id,
                    causation_id=saga.saga_id,
                    payload={"saga_id": saga.saga_id, "compensated_steps": len(executed_steps)},
                )
            )
        else:
            # All steps succeeded
            saga.status = SagaStatus.COMPLETED
            saga.updated_at = datetime.now(timezone.utc)
            self.bus.publish(
                EventContract(
                    event_type="saga.completed.v1",
                    source="saga-orchestrator",
                    correlation_id=corr_id,
                    causation_id=saga.saga_id,
                    payload={"saga_id": saga.saga_id, "status": "COMPLETED"},
                )
            )

        return saga

    def clear(self):
        self._sagas.clear()


# Global singleton orchestrator
saga_orchestrator = SagaOrchestrator()

