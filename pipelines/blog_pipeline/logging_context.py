"""
Sequence-aware logging adapted from docs/05-development/code-examples/sequence-aware-logging.py.

Extensions over the reference:
- ExecutionContext carries llm_model, token_count_input/output, cost_usd, decision_confidence
  to match the agent_decisions schema columns.
- A Postgres handler writes each completed sequence to agent_decisions on exit.
"""
from __future__ import annotations

import logging
import threading
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Iterator, Optional

from pythonjsonlogger import jsonlogger


@dataclass
class ExecutionContext:
    task_id: str
    sequence_id: str
    parent_sequence_id: Optional[str]
    step_number: int
    tool_name: Optional[str]
    reason: Optional[str]
    start_time: datetime
    end_time: Optional[datetime] = None

    # LLM usage — populated by caller on exit
    llm_model: Optional[str] = None
    llm_provider: Optional[str] = None
    token_count_input: int = 0
    token_count_output: int = 0
    cost_usd: float = 0.0
    decision_confidence: Optional[float] = None

    # Free-form payload for agent-specific data (draft text, link choices, etc.)
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[int]:
        if not self.end_time:
            return None
        return int((self.end_time - self.start_time).total_seconds() * 1000)


class SequenceAwareJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        now = datetime.utcnow()
        log_record["timestamp"] = now.isoformat()
        context: ExecutionContext | None = getattr(record, "execution_context", None)
        if context:
            log_record.update(asdict(context))
            log_record["start_time"] = context.start_time.isoformat()
            log_record["end_time"] = (
                context.end_time.isoformat() if context.end_time else None
            )
            log_record["duration_ms"] = context.duration_ms


class SequenceAwareLogManager:
    """Context-managed sequence logger. Thread-local context stack."""

    def __init__(self, db_writer: "DecisionWriter | None" = None) -> None:
        self.logger = logging.getLogger("uzelhub_crew")
        self._storage = threading.local()
        self._db_writer = db_writer
        self._configure_logging()

    def _configure_logging(self) -> None:
        if self.logger.handlers:
            return
        handler = logging.StreamHandler()
        handler.setFormatter(SequenceAwareJsonFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _current(self) -> ExecutionContext | None:
        return getattr(self._storage, "context", None)

    @contextmanager
    def task_sequence(
        self, task_id: str, description: str
    ) -> Iterator[ExecutionContext]:
        context = ExecutionContext(
            task_id=task_id,
            sequence_id=str(uuid.uuid4()),
            parent_sequence_id=None,
            step_number=0,
            tool_name=None,
            reason=description,
            start_time=datetime.utcnow(),
        )
        previous = self._current()
        self._storage.context = context
        self.logger.info(
            "task.start", extra={"execution_context": context}
        )
        try:
            yield context
        finally:
            context.end_time = datetime.utcnow()
            self.logger.info("task.end", extra={"execution_context": context})
            if self._db_writer:
                self._db_writer.write(context)
            self._storage.context = previous

    @contextmanager
    def tool_sequence(
        self, tool_name: str, reason: str
    ) -> Iterator[ExecutionContext]:
        parent = self._current()
        if not parent:
            raise RuntimeError("tool_sequence requires an enclosing task_sequence")
        context = ExecutionContext(
            task_id=parent.task_id,
            sequence_id=str(uuid.uuid4()),
            parent_sequence_id=parent.sequence_id,
            step_number=parent.step_number + 1,
            tool_name=tool_name,
            reason=reason,
            start_time=datetime.utcnow(),
        )
        previous = self._storage.context
        self._storage.context = context
        self.logger.info("tool.start", extra={"execution_context": context})
        try:
            yield context
        finally:
            context.end_time = datetime.utcnow()
            self.logger.info("tool.end", extra={"execution_context": context})
            if self._db_writer:
                self._db_writer.write(context)
            self._storage.context = previous


class DecisionWriter:
    """Writes a completed ExecutionContext into agent_decisions.

    Kept as a protocol-ish class so tests can substitute an in-memory recorder.
    Real implementation wires to psycopg at runner-construction time.
    """

    def __init__(self, conn) -> None:
        self.conn = conn

    def write(self, context: ExecutionContext) -> None:
        if not context.tool_name:
            return
        from psycopg.types.json import Jsonb

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_decisions (
                    run_id, workflow_sequence_id, parent_decision_id, step_number,
                    agent_name, decision_type, decision_timestamp,
                    processing_time_ms, llm_model, llm_provider,
                    token_count_input, token_count_output, cost_usd,
                    decision_confidence, routing_reason, decision_payload
                )
                VALUES (
                    %(task_id)s, %(task_id)s, NULL, %(step_number)s,
                    %(tool_name)s, 'invoke', %(start_time)s,
                    %(duration_ms)s, %(llm_model)s, %(llm_provider)s,
                    %(token_in)s, %(token_out)s, %(cost)s,
                    %(confidence)s, %(reason)s, %(payload)s
                )
                """,
                {
                    "task_id": context.task_id,
                    "step_number": context.step_number,
                    "tool_name": context.tool_name,
                    "start_time": context.start_time,
                    "duration_ms": context.duration_ms,
                    "llm_model": context.llm_model,
                    "llm_provider": context.llm_provider,
                    "token_in": context.token_count_input,
                    "token_out": context.token_count_output,
                    "cost": context.cost_usd,
                    "confidence": context.decision_confidence,
                    "reason": context.reason,
                    "payload": Jsonb(context.payload),
                },
            )
            self.conn.commit()
