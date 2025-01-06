"""
This module provides utility functions for environment setup, logging configuration,
error handling, and telemetry instrumentation.
"""

import asyncio
import logging
import sys
from functools import wraps

from dotenv import load_dotenv, find_dotenv


def load_env():
    """
    Load environment variables from a .env file.

    This function searches for a .env file and loads its contents into the environment,
    overriding any existing variables with the same names.
    """
    load_dotenv(find_dotenv(), override=True)


def configure_logging(level=logging.ERROR):
    """
    Configure the root logger with a specific format and log level.

    Args:
        level (int): The logging level to set (default is logging.INFO).

    This function sets up the root logger to output to stdout with a specific format
    that includes timestamp, log level, process ID, thread name, and logger name.
    """
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s %(levelname)s - [Process %(process)d] - [%(threadName)s] - %(name)s - %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)


def catch_errors(exit_on_error=False):
    """
    A decorator factory for catching and logging errors in both async and sync functions.

    Args:
        exit_on_error (bool): If True, the program will exit when an error occurs (not implemented in this version).

    Returns:
        function: A decorator that wraps the original function with error handling.

    This decorator logs any exceptions that occur in the wrapped function and returns None in case of an error.
    It can handle both asynchronous and synchronous functions.
    """

    def inner_trapped_decorator(func):
        @wraps(func)
        async def async_trapped_func(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except Exception:
                self._logger.exception("An error occurred:")
                return None

        def sync_trapped_func(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception:
                self._logger.exception("An error occurred:")
                return None

        return async_trapped_func if asyncio.iscoroutinefunction(func) else sync_trapped_func

    return inner_trapped_decorator


def instrument_telemetry():
    """
    Set up telemetry instrumentation for tracing.

    This function configures OpenTelemetry tracing with an OTLP exporter
    and instruments DSPy for telemetry collection.

    It sets up a tracer provider with a SimpleSpanProcessor and an OTLPSpanExporter
    that sends traces to a local endpoint (http://127.0.0.1:6006/v1/traces).

    Note: This function requires additional dependencies: openinference and opentelemetry.
    """
    from openinference.instrumentation.dspy import DSPyInstrumentor
    from opentelemetry import trace as trace_api
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk import trace as trace_sdk
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    endpoint = "http://127.0.0.1:6006/v1/traces"
    tracer_provider = trace_sdk.TracerProvider()
    span_otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter=span_otlp_exporter))

    trace_api.set_tracer_provider(tracer_provider=tracer_provider)
    DSPyInstrumentor().instrument()
