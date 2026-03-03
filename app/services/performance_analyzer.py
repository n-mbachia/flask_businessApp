"""
Performance Analyzer Module

This module provides functionality for analyzing and optimizing application performance.
It includes decorators and utilities for measuring execution time, memory usage,
and other performance metrics.
"""

from typing import Dict, Any, List, Optional, Callable, TypeVar, Union
from datetime import datetime
from functools import wraps
import time
import logging
import tracemalloc
import psutil
import os

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])

class PerformanceMetrics:
    """Container class for performance metrics."""
    def __init__(self):
        self.execution_time: float = 0.0
        self.memory_usage: float = 0.0  # in MB
        self.cpu_usage: float = 0.0     # in %
        self.call_count: int = 0
        self.last_called: Optional[datetime] = None
        self.average_time: float = 0.0

    def update(self, execution_time: float, memory_usage: float, cpu_usage: float):
        """Update metrics with new measurement."""
        self.call_count += 1
        self.execution_time = execution_time
        self.memory_usage = memory_usage
        self.cpu_usage = cpu_usage
        self.last_called = datetime.utcnow()
        
        # Update running average
        if self.average_time == 0:
            self.average_time = execution_time
        else:
            self.average_time = (self.average_time * (self.call_count - 1) + execution_time) / self.call_count


class PerformanceAnalyzer:
    """
    Performance analysis and monitoring utility.
    
    This class provides decorators and methods to measure and track the performance
    of functions and methods, including execution time, memory usage, and CPU usage.
    """
    
    def __init__(self):
        """Initialize the PerformanceAnalyzer with an empty metrics dictionary."""
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self._process = psutil.Process(os.getpid())
        tracemalloc.start()
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        return self._process.memory_info().rss / 1024 / 1024  # Convert to MB
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return self._process.cpu_percent(interval=0.1)
    
    def measure_performance(self, func: F) -> F:
        """
        Decorator to measure function performance.
        
        Tracks execution time, memory usage, and CPU usage for the decorated function.
        
        Args:
            func: The function to be decorated.
            
        Returns:
            The decorated function with performance tracking.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get initial metrics
            start_time = time.time()
            start_mem = self.get_memory_usage()
            start_cpu = self.get_cpu_usage()
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Calculate metrics
            end_time = time.time()
            end_mem = self.get_memory_usage()
            end_cpu = self.get_cpu_usage()
            
            execution_time = end_time - start_time
            memory_usage = end_mem - start_mem
            cpu_usage = max(0, end_cpu - start_cpu)  # Ensure non-negative
            
            # Update metrics
            func_name = f"{func.__module__}.{func.__qualname__}"
            if func_name not in self.metrics:
                self.metrics[func_name] = PerformanceMetrics()
            
            self.metrics[func_name].update(execution_time, memory_usage, cpu_usage)
            
            # Log the metrics
            logger.debug(
                f"Performance - {func_name}: "
                f"{execution_time:.4f}s, "
                f"{memory_usage:.2f}MB, "
                f"{cpu_usage:.1f}% CPU"
            )
            
            return result
        return wrapper
    
    def get_metrics(self, func_name: str = None) -> Union[Dict[str, PerformanceMetrics], PerformanceMetrics]:
        """
        Get performance metrics for a specific function or all functions.
        
        Args:
            func_name: Optional name of the function to get metrics for.
                      If None, returns metrics for all functions.
                      
        Returns:
            PerformanceMetrics object if func_name is specified, 
            otherwise a dictionary of all metrics.
        """
        if func_name:
            return self.metrics.get(func_name)
        return self.metrics
    
    def reset_metrics(self, func_name: str = None):
        """
        Reset performance metrics.
        
        Args:
            func_name: Optional name of the function to reset metrics for.
                      If None, resets all metrics.
        """
        if func_name:
            if func_name in self.metrics:
                del self.metrics[func_name]
        else:
            self.metrics.clear()


# Create a default instance for easy use
performance_analyzer = PerformanceAnalyzer()

# Shortcut decorator for performance monitoring
track_performance = performance_analyzer.measure_performance
