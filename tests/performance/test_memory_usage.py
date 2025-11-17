"""Performance tests for memory usage under 100MB requirement."""

import gc
import os

import psutil
import pytest

from oom_diag_bot.services.alert_detector import AlertDetector
from oom_diag_bot.services.report_generator import ReportGenerator


@pytest.fixture
def memory_tracker():
    """Fixture for tracking memory usage."""
    # Force garbage collection before tests
    gc.collect()

    # Get current process
    process = psutil.Process(os.getpid())

    # Record baseline memory
    baseline_memory = process.memory_info().rss

    def get_memory_usage_mb():
        """Get current memory usage in MB."""
        current_memory = process.memory_info().rss
        return (current_memory - baseline_memory) / (1024 * 1024)

    yield get_memory_usage_mb

    # Clean up after tests
    gc.collect()


def test_alert_detector_memory_efficiency(memory_tracker):
    """Test memory usage during alert detection."""
    initial_memory = memory_tracker()

    # Create alert detector
    detector = AlertDetector(oom_keywords=["OOMKilled", "memory limit exceeded"])

    # Process 1000 messages to test memory efficiency
    for i in range(1000):
        message = f"Pod nginx-deployment-{i:03d} was OOMKilled in namespace production"

        # Find keywords
        keywords = detector._find_oom_keywords(message)

        # Extract pod and namespace
        extracted = detector.extract_pod_namespace(message)

        # Force garbage collection every 100 iterations
        if i % 100 == 0:
            gc.collect()

    memory_used = memory_tracker() - initial_memory

    # Alert detection should be memory efficient (less than 10MB for 1000 messages)
    assert memory_used < 10.0, f"Alert detection used {memory_used:.1f}MB (limit: 10MB)"


def test_report_generator_memory_efficiency(memory_tracker):
    """Test memory usage during report generation."""
    initial_memory = memory_tracker()

    # Create 100 report generators to test memory usage
    generators = []
    for i in range(100):
        generators.append(ReportGenerator())

        # Force garbage collection every 20 iterations
        if i % 20 == 0:
            gc.collect()

    memory_used = memory_tracker() - initial_memory

    # Report generator instances should be lightweight (less than 5MB for 100 instances)
    assert memory_used < 5.0, f"Report generators used {memory_used:.1f}MB (limit: 5MB)"


def test_large_string_processing_memory(memory_tracker):
    """Test memory usage when processing large strings."""
    initial_memory = memory_tracker()

    detector = AlertDetector()

    # Create large message (100KB)
    large_message = "Pod nginx-deployment-abc123 was OOMKilled in namespace production. " * 1000

    # Process large message 100 times
    for i in range(100):
        keywords = detector._find_oom_keywords(large_message)
        extracted = detector.extract_pod_namespace(large_message)

        # Force garbage collection every 10 iterations
        if i % 10 == 0:
            gc.collect()

    memory_used = memory_tracker() - initial_memory

    # Large string processing should not leak memory (less than 20MB)
    assert memory_used < 20.0, f"Large string processing used {memory_used:.1f}MB (limit: 20MB)"


def test_memory_cleanup_after_processing(memory_tracker):
    """Test that memory is properly cleaned up after processing."""
    initial_memory = memory_tracker()

    detector = AlertDetector()

    # Process many alerts
    for i in range(500):
        message = f"Pod nginx-{i} was OOMKilled in namespace prod-{i % 10}"
        detector._find_oom_keywords(message)
        detector.extract_pod_namespace(message)

    # Force garbage collection
    gc.collect()

    memory_after_gc = memory_tracker()
    memory_used = memory_after_gc - initial_memory

    # Memory should be cleaned up efficiently (less than 5MB after GC)
    assert memory_used < 5.0, f"Memory not cleaned up: {memory_used:.1f}MB remaining (limit: 5MB)"
