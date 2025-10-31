 
# src/core/logging.py
from typing import Dict, Any, Optional
import uuid
from contextlib import contextmanager
from datetime import datetime
import logging
from pythonjsonlogger import jsonlogger
from dataclasses import dataclass, asdict
import threading

@dataclass
class ExecutionContext:
    """
    Tracks the context of an agent's execution sequence.
    
    This is like a breadcrumb trail of what the agent has done and why.
    """
    task_id: str                    # Unique identifier for the overall task
    sequence_id: str                # Unique identifier for this specific sequence
    parent_sequence_id: Optional[str]  # ID of the parent sequence (if this is a subtask)
    step_number: int                # Position in the sequence
    tool_name: Optional[str]        # Name of the tool being used
    reason: Optional[str]           # Why this step was chosen
    start_time: datetime
    end_time: Optional[datetime] = None

class SequenceAwareJsonFormatter(jsonlogger.JsonFormatter):
    """
    Enhanced JSON formatter that understands execution sequences.
    """
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add basic timing fields
        now = datetime.utcnow()
        log_record.update({
            'timestamp': now.isoformat(),
            'date': now.date().isoformat(),
            'time': now.time().isoformat(),
            'hour': now.hour,
            'day_of_week': now.weekday(),
            'month': now.month,
            'year': now.year,
        })
        
        # Add execution context if available
        if hasattr(record, 'execution_context'):
            context = record.execution_context
            log_record.update({
                'task_id': context.task_id,
                'sequence_id': context.sequence_id,
                'parent_sequence_id': context.parent_sequence_id,
                'step_number': context.step_number,
                'tool_name': context.tool_name,
                'reason': context.reason,
                'sequence_start_time': context.start_time.isoformat(),
                'sequence_end_time': context.end_time.isoformat() if context.end_time else None,
            })

class SequenceAwareLogManager:
    """
    Enhanced LogManager that tracks execution sequences.
    """
    def __init__(self):
        self.logger = logging.getLogger('ai_agent')
        self._context_storage = threading.local()
        self._configure_logging()
    
    def _configure_logging(self):
        """Configure the logging system with our sequence-aware formatter"""
        handler = logging.StreamHandler()
        handler.setFormatter(SequenceAwareJsonFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    @contextmanager
    def task_sequence(self, task_id: str, description: str):
        """
        Create a context manager for tracking a main task sequence.
        
        Example:
            with log_manager.task_sequence("user_query_123", "Process user question") as seq:
                # Do main task work
        """
        sequence_id = str(uuid.uuid4())
        context = ExecutionContext(
            task_id=task_id,
            sequence_id=sequence_id,
            parent_sequence_id=None,
            step_number=0,
            tool_name=None,
            reason=description,
            start_time=datetime.utcnow()
        )
        
        self._context_storage.context = context
        self.logger.info(f"Starting task sequence: {description}", extra={'execution_context': context})
        
        try:
            yield context
        finally:
            context.end_time = datetime.utcnow()
            self.logger.info(f"Completed task sequence: {description}", extra={'execution_context': context})
            self._context_storage.context = None
    
    @contextmanager
    def tool_sequence(self, tool_name: str, reason: str):
        """
        Create a context manager for tracking a tool's execution within a sequence.
        
        Example:
            with log_manager.task_sequence("query_123", "Process question") as main_seq:
                with log_manager.tool_sequence("web_search", "Find relevant information") as tool_seq:
                    # Do tool-specific work
        """
        parent_context = getattr(self._context_storage, 'context', None)
        if not parent_context:
            raise RuntimeError("Tool sequence must be within a task sequence")
        
        sequence_id = str(uuid.uuid4())
        context = ExecutionContext(
            task_id=parent_context.task_id,
            sequence_id=sequence_id,
            parent_sequence_id=parent_context.sequence_id,
            step_number=parent_context.step_number + 1,
            tool_name=tool_name,
            reason=reason,
            start_time=datetime.utcnow()
        )
        
        previous_context = self._context_storage.context
        self._context_storage.context = context
        self.logger.info(f"Starting tool sequence: {tool_name}", extra={'execution_context': context})
        
        try:
            yield context
        finally:
            context.end_time = datetime.utcnow()
            self.logger.info(f"Completed tool sequence: {tool_name}", extra={'execution_context': context})
            self._context_storage.context = previous_context
    
    def log_with_context(self, level: int, msg: str, **kwargs):
        """Log a message with the current execution context"""
        context = getattr(self._context_storage, 'context', None)
        extra = kwargs.get('extra', {})
        if context:
            extra['execution_context'] = context
        self.logger.log(level, msg, extra=extra)

# Example usage:
"""
log_manager = SequenceAwareLogManager()

async def process_user_query(query: str):
    with log_manager.task_sequence("query_123", "Process user question about weather") as main_seq:
        # First tool: Natural Language Understanding
        with log_manager.tool_sequence("nlu", "Extract location and time from query") as nlu_seq:
            location = "New York"
            time = "tomorrow"
            log_manager.log_with_context(logging.INFO, f"Extracted location: {location}")
        
        # Second tool: Weather API
        with log_manager.tool_sequence("weather_api", "Fetch weather forecast") as weather_seq:
            forecast = "sunny"
            log_manager.log_with_context(logging.INFO, f"Retrieved forecast: {forecast}")
        
        # Third tool: Response Generation
        with log_manager.tool_sequence("response_gen", "Generate natural language response") as resp_seq:
            response = f"The weather in {location} will be {forecast}"
            log_manager.log_with_context(logging.INFO, "Generated response")
"""