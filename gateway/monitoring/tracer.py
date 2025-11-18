"""Distributed tracing with OpenTelemetry."""
from typing import Optional
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

from gateway.config.settings import settings


class Span:
    """Represents a trace span."""

    def __init__(
        self,
        name: str,
        trace_id: str,
        span_id: str,
        parent_span_id: Optional[str] = None,
    ):
        """
        Initialize span.

        Args:
            name: Span name
            trace_id: Trace ID
            span_id: Span ID
            parent_span_id: Parent span ID
        """
        self.name = name
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.attributes: dict = {}
        self.events: list = []

    def set_attribute(self, key: str, value):
        """Set span attribute."""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict = None):
        """Add event to span."""
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        })

    def end(self):
        """End the span."""
        self.end_time = datetime.utcnow()

    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        if self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return 0

    def to_dict(self) -> dict:
        """Convert span to dictionary."""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
        }


class Tracer:
    """Distributed tracing implementation."""

    def __init__(self):
        """Initialize tracer."""
        self.enabled = settings.tracing_enabled
        self.current_trace_id: Optional[str] = None
        self.current_span: Optional[Span] = None

    def generate_trace_id(self) -> str:
        """Generate a new trace ID."""
        return str(uuid.uuid4())

    def generate_span_id(self) -> str:
        """Generate a new span ID."""
        return str(uuid.uuid4())[:16]

    def start_trace(self, name: str) -> Span:
        """
        Start a new trace.

        Args:
            name: Trace name

        Returns:
            Root span
        """
        if not self.enabled:
            return None

        trace_id = self.generate_trace_id()
        span_id = self.generate_span_id()

        self.current_trace_id = trace_id
        span = Span(name=name, trace_id=trace_id, span_id=span_id)
        self.current_span = span

        return span

    def start_span(
        self,
        name: str,
        parent_span: Optional[Span] = None,
    ) -> Span:
        """
        Start a new span.

        Args:
            name: Span name
            parent_span: Parent span (uses current if None)

        Returns:
            New span
        """
        if not self.enabled:
            return None

        parent = parent_span or self.current_span
        trace_id = parent.trace_id if parent else self.generate_trace_id()
        span_id = self.generate_span_id()
        parent_span_id = parent.span_id if parent else None

        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
        )

        return span

    @asynccontextmanager
    async def trace(self, name: str, attributes: dict = None):
        """
        Context manager for tracing.

        Args:
            name: Span name
            attributes: Optional attributes

        Example:
            async with tracer.trace("my_operation") as span:
                # Your code here
                span.set_attribute("key", "value")
        """
        if not self.enabled:
            yield None
            return

        span = self.start_span(name)

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        try:
            yield span
        finally:
            if span:
                span.end()

    def extract_trace_context(self, headers: dict) -> Optional[str]:
        """
        Extract trace context from headers.

        Args:
            headers: Request headers

        Returns:
            Trace ID if found
        """
        # Check for common trace headers
        trace_headers = [
            "X-Trace-Id",
            "X-Request-ID",
            "traceparent",  # W3C Trace Context
        ]

        for header in trace_headers:
            if header in headers:
                return headers[header]

        return None

    def inject_trace_context(self, headers: dict, span: Span) -> dict:
        """
        Inject trace context into headers.

        Args:
            headers: Headers dictionary
            span: Current span

        Returns:
            Updated headers
        """
        if not self.enabled or not span:
            return headers

        headers["X-Trace-Id"] = span.trace_id
        headers["X-Span-Id"] = span.span_id

        if span.parent_span_id:
            headers["X-Parent-Span-Id"] = span.parent_span_id

        return headers


# Global tracer instance
tracer = Tracer()
