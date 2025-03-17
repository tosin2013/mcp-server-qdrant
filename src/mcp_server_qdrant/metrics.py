"""Metrics collection for MCP Server Qdrant."""
import time
from typing import Dict, Any
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
QDRANT_OPERATIONS = Counter(
    'qdrant_operations_total',
    'Total number of operations performed on Qdrant',
    ['operation', 'status']
)

QDRANT_OPERATION_DURATION = Histogram(
    'qdrant_operation_duration_seconds',
    'Duration of Qdrant operations in seconds',
    ['operation'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, float('inf'))
)

QDRANT_COLLECTION_SIZE = Gauge(
    'qdrant_collection_size',
    'Number of points in Qdrant collection',
    ['collection']
)

QDRANT_EMBEDDING_QUEUE = Gauge(
    'qdrant_embedding_queue_size',
    'Number of items waiting for embedding',
)

QDRANT_CONNECTION_POOL = Gauge(
    'qdrant_connection_pool_size',
    'Number of active connections in the pool',
)

def track_operation_metrics(operation_name: str):
    """Decorator to track Qdrant operation metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                QDRANT_OPERATIONS.labels(
                    operation=operation_name,
                    status='success'
                ).inc()
                return result
            except Exception as e:
                QDRANT_OPERATIONS.labels(
                    operation=operation_name,
                    status='error'
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                QDRANT_OPERATION_DURATION.labels(
                    operation=operation_name
                ).observe(duration)
        return wrapper
    return decorator

def update_collection_metrics(collection_name: str, size: int):
    """Update collection size metrics."""
    QDRANT_COLLECTION_SIZE.labels(collection=collection_name).set(size)

def update_embedding_queue_size(size: int):
    """Update embedding queue size metric."""
    QDRANT_EMBEDDING_QUEUE.set(size)

def update_connection_pool_size(size: int):
    """Update connection pool size metric."""
    QDRANT_CONNECTION_POOL.set(size)

class MetricsCollector:
    """Collector for custom metrics."""
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level metrics."""
        import psutil
        
        process = psutil.Process()
        return {
            "memory_usage_percent": process.memory_percent(),
            "cpu_usage_percent": process.cpu_percent(),
            "open_files": len(process.open_files()),
            "threads": process.num_threads(),
            "connections": len(process.connections()),
        }
    
    def collect_qdrant_metrics(self, collection_info: Any) -> Dict[str, Any]:
        """Collect Qdrant-specific metrics."""
        return {
            "points_count": collection_info.points_count,
            "vectors_config": str(collection_info.config.params.vectors),
            "status": collection_info.status,
            "optimization_status": collection_info.optimization_status,
        }
    
    def collect_embedding_metrics(self, provider: Any) -> Dict[str, Any]:
        """Collect embedding provider metrics."""
        return {
            "model": provider.model_name,
            "batch_size": provider.batch_size,
            "device": provider.device,
        } 